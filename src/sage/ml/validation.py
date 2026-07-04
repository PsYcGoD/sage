"""Clean, temporal validation for the failure-prediction model.

Produces launch-credible ML numbers by fixing the weaknesses of the
training-time metrics:

- real history only — no synthetic bootstrap rows, no class balancing
- deduplicated by normalized command fingerprint (label conflicts counted)
- temporal split — oldest runs train, newest runs test, so the model is
  scored on commands it could not have seen
- versioned report — model version, feature version, dataset hash, and
  sample provenance (local runs vs imported history) are all recorded

Exposed via `sage ml validate`.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score

from ..classify import command_fingerprint
from ..store import connect, data_dir
from .model import MODEL_VERSION, SklearnFailureModel

FEATURE_VERSION = 2  # v2: adds leak-free expanding-window history features
REPORT_VERSION = "ml-validation-v1"


def label_run(exit_code: int) -> int:
    """Single labeling rule used everywhere: non-zero exit means failure."""
    return 1 if int(exit_code) != 0 else 0


def load_real_history() -> list[dict[str, Any]]:
    """Load real samples only: local runs plus imported CLI history."""
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
    """Keep the first occurrence per fingerprint; count dropped rows and label conflicts."""
    seen: dict[str, int] = {}
    kept: list[dict[str, Any]] = []
    dropped = 0
    conflicts = 0
    for sample in samples:
        fingerprint = command_fingerprint(sample["command"])
        if fingerprint in seen:
            dropped += 1
            if seen[fingerprint] != sample["label"]:
                conflicts += 1
            continue
        seen[fingerprint] = sample["label"]
        kept.append(sample | {"fingerprint": fingerprint})
    return kept, dropped, conflicts


def dataset_hash(samples: list[dict[str, Any]]) -> str:
    """Deterministic hash of the exact validation dataset (fingerprint + label)."""
    digest = hashlib.sha256()
    for sample in samples:
        digest.update(f"{sample['fingerprint']}:{sample['label']}\n".encode("utf-8"))
    return digest.hexdigest()


def validate_temporal(test_fraction: float = 0.25) -> dict[str, Any]:
    """Train on the oldest real samples, score on the newest, report honestly."""
    if not 0.05 <= test_fraction <= 0.5:
        raise ValueError("test_fraction must be between 0.05 and 0.5")

    raw = load_real_history()
    samples, dropped_duplicates, label_conflicts = deduplicate(raw)

    report: dict[str, Any] = {
        "report_version": REPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model_version": MODEL_VERSION,
        "feature_version": FEATURE_VERSION,
        "split": "temporal",
        "test_fraction": test_fraction,
        "synthetic_samples": 0,
        "raw_samples": len(raw),
        "dropped_duplicates": dropped_duplicates,
        "label_conflicts": label_conflicts,
        "samples": len(samples),
        "provenance": {
            "local_run": sum(1 for item in samples if item["provenance"] == "local_run"),
            "imported": sum(1 for item in samples if item["provenance"] == "imported"),
        },
        "dataset_hash": dataset_hash(samples),
    }

    split_index = int(len(samples) * (1 - test_fraction))
    train, test = samples[:split_index], samples[split_index:]
    train_labels = [item["label"] for item in train]
    test_labels = [item["label"] for item in test]

    if len(train) < 20 or len(test) < 10 or len(set(train_labels)) < 2 or len(set(test_labels)) < 2:
        report["validated"] = False
        report["message"] = (
            "Not enough real history for a temporal validation split "
            f"(train={len(train)}, test={len(test)}). Run more commands through sage first."
        )
        return report

    import pandas as pd

    from .history_features import HISTORY_FEATURE_NAMES, build_expanding_rows

    model_helper = SklearnFailureModel()
    feature_names = model_helper.extractor.get_feature_names() + HISTORY_FEATURE_NAMES
    # One chronological pass: every row's history features see only prior runs,
    # so test rows are scored exactly as live prediction would have scored them.
    rows, _ = build_expanding_rows(
        [(item["command"], item["label"]) for item in samples],
        model_helper.extractor.extract,
    )
    frame = pd.DataFrame(rows)[feature_names]
    train_frame, test_frame = frame.iloc[:split_index], frame.iloc[split_index:]

    model = model_helper._build_model()
    model.fit(train_frame, train_labels)

    predictions = model.predict(test_frame)
    probabilities = model.predict_proba(test_frame)[:, 1]

    report["validated"] = True
    report["message"] = "Temporal validation on deduplicated real history (no synthetic rows)."
    report["train"] = {
        "samples": len(train),
        "failures": sum(train_labels),
        "from": train[0]["created_at"],
        "to": train[-1]["created_at"],
    }
    report["test"] = {
        "samples": len(test),
        "failures": sum(test_labels),
        "from": test[0]["created_at"],
        "to": test[-1]["created_at"],
    }
    report["metrics"] = {
        "accuracy": float(accuracy_score(test_labels, predictions)),
        "precision": float(precision_score(test_labels, predictions, zero_division=0)),
        "recall": float(recall_score(test_labels, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(test_labels, probabilities)),
    }
    return report


def write_validation_report(report: dict[str, Any], output: str | Path | None = None) -> Path:
    """Persist the validation report next to the model as JSON proof."""
    if output:
        path = Path(output)
    else:
        folder = data_dir() / "models"
        folder.mkdir(parents=True, exist_ok=True)
        stamp = report.get("generated_at", "report").replace(":", "-")
        path = folder / f"validation-report-{stamp}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
