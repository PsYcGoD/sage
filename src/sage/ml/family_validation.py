"""Validation for per-family failure prediction models.

Produces honest temporal validation metrics for each family model separately,
plus aggregate metrics across all families.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score, f1_score

from ..classify import classify_command, command_fingerprint
from ..store import connect, data_dir
from .family_model import MODEL_VERSION


FEATURE_VERSION = 2
REPORT_VERSION = "family-ml-validation-v1"


def label_run(exit_code: int) -> int:
    """Single labeling rule: non-zero exit means failure."""
    return 1 if int(exit_code) != 0 else 0


def load_real_history() -> list[dict[str, Any]]:
    """Load real samples only."""
    with connect() as conn:
        run_rows = conn.execute(
            "SELECT command, exit_code, created_at FROM runs ORDER BY created_at ASC, id ASC"
        ).fetchall()
        imported_rows = conn.execute(
            "SELECT command, exit_code, created_at FROM ml_training_examples ORDER BY created_at ASC, id ASC"
        ).fetchall()

    samples = [
        {
            "command": str(row["command"]),
            "label": label_run(row["exit_code"]),
            "created_at": str(row["created_at"] or ""),
            "provenance": provenance,
        }
        for rows, provenance in ((imported_rows, "imported"), (run_rows, "local_run"))
        for row in rows
    ]
    samples.sort(key=lambda item: item["created_at"])
    return samples


def deduplicate(samples: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int, int]:
    """Keep first occurrence per fingerprint."""
    seen: dict[str, int] = {}
    kept: list[dict[str, Any]] = []
    dropped = 0
    conflicts = 0
    for sample in samples:
        fingerprint = command_fingerprint(sample["command"])
        family = classify_command(sample["command"]).family
        if fingerprint in seen:
            dropped += 1
            if seen[fingerprint] != sample["label"]:
                conflicts += 1
            continue
        seen[fingerprint] = sample["label"]
        kept.append(sample | {"fingerprint": fingerprint, "family": family})
    return kept, dropped, conflicts


def dataset_hash(samples: list[dict[str, Any]]) -> str:
    """Deterministic hash of validation dataset."""
    digest = hashlib.sha256()
    for sample in samples:
        digest.update(f"{sample['fingerprint']}:{sample['label']}\n".encode("utf-8"))
    return digest.hexdigest()


def validate_family_models(test_fraction: float = 0.25) -> dict[str, Any]:
    """Validate per-family models with temporal split."""
    if not 0.05 <= test_fraction <= 0.5:
        raise ValueError("test_fraction must be between 0.05 and 0.5")

    raw = load_real_history()
    samples, dropped_duplicates, label_conflicts = deduplicate(raw)

    # Group by family
    families: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sample in samples:
        families[sample["family"]].append(sample)

    report: dict[str, Any] = {
        "report_version": REPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model_version": MODEL_VERSION,
        "feature_version": FEATURE_VERSION,
        "split": "temporal",
        "test_fraction": test_fraction,
        "raw_samples": len(raw),
        "dropped_duplicates": dropped_duplicates,
        "label_conflicts": label_conflicts,
        "samples": len(samples),
        "families_count": len(families),
        "dataset_hash": dataset_hash(samples),
    }

    # Validate each family separately
    family_reports: dict[str, dict[str, Any]] = {}
    aggregate_predictions = []
    aggregate_labels = []

    from .family_model import FamilyFailureModel
    family_model = FamilyFailureModel()

    for family, fam_samples in families.items():
        if len(fam_samples) < 20:
            continue

        split_index = int(len(fam_samples) * (1 - test_fraction))
        train, test = fam_samples[:split_index], fam_samples[split_index:]

        if len(test) < 5 or len(set(item["label"] for item in test)) < 2:
            continue

        # Try loading family-specific model
        model_path = family_model.models_dir / f"{family}.joblib"
        if not model_path.exists():
            continue

        import joblib
        try:
            package = joblib.load(model_path)
            if package.get("version") != MODEL_VERSION:
                continue
        except Exception:
            continue

        # Predict on test set
        from .history_features import build_expanding_rows
        rows, _ = build_expanding_rows(
            [(item["command"], item["label"]) for item in fam_samples],
            family_model.extractor.extract,
        )

        import pandas as pd
        feature_names = family_model._feature_names()
        frame = pd.DataFrame(rows)[feature_names]
        test_frame = frame.iloc[split_index:]
        test_labels = [item["label"] for item in test]

        model = package["model"]
        threshold = package.get("threshold", 0.5)
        probabilities = model.predict_proba(test_frame)[:, 1]
        predictions = [1 if p >= threshold else 0 for p in probabilities]

        # Metrics for this family
        family_reports[family] = {
            "train_samples": len(train),
            "test_samples": len(test),
            "failures": sum(test_labels),
            "threshold": threshold,
            "accuracy": float(accuracy_score(test_labels, predictions)),
            "precision": float(precision_score(test_labels, predictions, zero_division=0)),
            "recall": float(recall_score(test_labels, predictions, zero_division=0)),
            "f1": float(f1_score(test_labels, predictions, zero_division=0)),
            "roc_auc": float(roc_auc_score(test_labels, probabilities)),
        }

        aggregate_predictions.extend(predictions)
        aggregate_labels.extend(test_labels)

    # Aggregate metrics across all families
    if aggregate_predictions:
        report["aggregate_metrics"] = {
            "test_samples": len(aggregate_labels),
            "failures": sum(aggregate_labels),
            "accuracy": float(accuracy_score(aggregate_labels, aggregate_predictions)),
            "precision": float(precision_score(aggregate_labels, aggregate_predictions, zero_division=0)),
            "recall": float(recall_score(aggregate_labels, aggregate_predictions, zero_division=0)),
            "f1": float(f1_score(aggregate_labels, aggregate_predictions, zero_division=0)),
        }
    else:
        report["aggregate_metrics"] = {}

    report["families"] = family_reports
    report["validated"] = len(family_reports) > 0
    report["message"] = (
        f"Per-family temporal validation on {len(family_reports)} families with sufficient test data."
        if report["validated"]
        else "Not enough data per family for validation."
    )

    return report


def write_family_validation_report(report: dict[str, Any], output: str | Path | None = None) -> Path:
    """Persist the family validation report."""
    if output:
        path = Path(output)
    else:
        folder = data_dir() / "models"
        folder.mkdir(parents=True, exist_ok=True)
        stamp = report.get("generated_at", "report").replace(":", "-")
        path = folder / f"family-validation-{stamp}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
