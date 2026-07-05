from __future__ import annotations
"""Per-family failure prediction models.

Each command family (pytest, npm, git, python, etc.) has unique failure modes.
A single global model struggles with this diversity. Per-family models learn
specialized patterns for each tool's error signatures.
"""

import logging

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, GradientBoostingClassifier, RandomForestClassifier, VotingClassifier
from sklearn.metrics import accuracy_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ..classify import classify_command
from ..store import connect, data_dir
from .features import FeatureExtractor

log = logging.getLogger(__name__)

MODEL_VERSION = 4  # v4: per-family models with tuned thresholds

@dataclass(frozen=True)
class FamilyTrainingResult:
    """Training result for per-family models."""

    trained: bool
    model_paths: dict[str, Path]
    families: dict[str, dict[str, Any]]
    fallback_accuracy: float
    fallback_samples: int
    message: str

class FamilyFailureModel:
    """Per-family specialized failure prediction models."""

    def __init__(self, models_dir: Path | None = None, extractor: FeatureExtractor | None = None):
        self.extractor = extractor or FeatureExtractor()
        self.models_dir = models_dir or (data_dir() / "models" / "families")
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, Any] = {}

    def train_from_history(
        self,
        min_samples_per_family: int = 30,
        fallback_min_samples: int = 100,
    ) -> FamilyTrainingResult:
        """Train per-family models from command history."""
        commands, labels = self._load_history()

        # Group by family
        families: dict[str, tuple[list[str], list[int]]] = {}
        for cmd, label in zip(commands, labels):
            klass = classify_command(cmd)
            family = klass.family
            if family not in families:
                families[family] = ([], [])
            families[family][0].append(cmd)
            families[family][1].append(label)

        model_paths: dict[str, Path] = {}
        family_stats: dict[str, dict[str, Any]] = {}
        trained_count = 0

        # Train per-family models
        for family, (fam_cmds, fam_labels) in families.items():
            if len(fam_cmds) < min_samples_per_family or len(set(fam_labels)) < 2:
                continue

            # Check class balance
            positives = sum(fam_labels)
            negatives = len(fam_labels) - positives
            if positives < 5 or negatives < 5:
                continue

            try:
                frame = self._training_frame(fam_cmds, fam_labels)
                labels_series = pd.Series(fam_labels, name="failed")

                # Pick the threshold on a temporal holdout (newest 25%) so it is
                # not tuned on the model's own training predictions, then refit
                # the final model on the full family history.
                threshold = self._holdout_threshold(frame, fam_labels)
                model = self._build_family_model(len(fam_cmds))
                model.fit(frame, labels_series)

                # Save model
                model_path = self.models_dir / f"{family}.joblib"
                package = {
                    "version": MODEL_VERSION,
                    "family": family,
                    "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "samples": len(fam_cmds),
                    "failures": positives,
                    "threshold": threshold,
                    "model": model,
                    "feature_names": self._feature_names(),
                }
                joblib.dump(package, model_path)

                model_paths[family] = model_path
                family_stats[family] = {
                    "samples": len(fam_cmds),
                    "failures": positives,
                    "threshold": threshold,
                }
                trained_count += 1
            except Exception:
                # Skip families that fail to train
                continue

        # Train fallback model on all data
        fallback_accuracy = 0.0
        fallback_samples = len(commands)
        if len(commands) >= fallback_min_samples and len(set(labels)) >= 2:
            try:
                frame = self._training_frame(commands, labels)
                labels_series = pd.Series(labels, name="failed")

                threshold = self._holdout_threshold(frame, labels, builder=self._build_fallback_model)
                model = self._build_fallback_model()
                model.fit(frame, labels_series)

                predictions = model.predict_proba(frame)[:, 1]

                fallback_path = self.models_dir / "fallback.joblib"
                package = {
                    "version": MODEL_VERSION,
                    "family": "fallback",
                    "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "samples": len(commands),
                    "failures": sum(labels),
                    "threshold": threshold,
                    "model": model,
                    "feature_names": self._feature_names(),
                }
                joblib.dump(package, fallback_path)
                model_paths["fallback"] = fallback_path

                # Evaluate
                predictions_binary = (predictions >= threshold).astype(int)
                fallback_accuracy = float(accuracy_score(labels, predictions_binary))
            except Exception:
                log.debug("suppressed", exc_info=True)

        return FamilyTrainingResult(
            trained=trained_count > 0,
            model_paths=model_paths,
            families=family_stats,
            fallback_accuracy=fallback_accuracy,
            fallback_samples=fallback_samples,
            message=f"Trained {trained_count} family-specific models + fallback model.",
        )

    def predict(self, command: str) -> tuple[bool, float, str] | None:
        """Predict using family-specific model, fallback if not available."""
        klass = classify_command(command)
        family = klass.family

        # Try family-specific model
        family_path = self.models_dir / f"{family}.joblib"
        if family_path.exists():
            package = self._load_model(family_path)
            if package:
                return self._predict_with_package(command, package, f"family={family}")

        # Fallback to global model
        fallback_path = self.models_dir / "fallback.joblib"
        if fallback_path.exists():
            package = self._load_model(fallback_path)
            if package:
                return self._predict_with_package(command, package, "fallback")

        return None

    def status(self) -> dict[str, Any]:
        """Return status of all trained models."""
        family_models = list(self.models_dir.glob("*.joblib"))
        families = {}
        fallback = None

        for model_path in family_models:
            package = self._load_model(model_path)
            if not package:
                continue

            family = package.get("family", "unknown")
            info = {
                "trained_at": package.get("trained_at"),
                "samples": package.get("samples", 0),
                "failures": package.get("failures", 0),
                "threshold": package.get("threshold", 0.5),
            }

            if family == "fallback":
                fallback = info
            else:
                families[family] = info

        return {
            "trained": len(families) > 0,
            "families": families,
            "fallback": fallback,
            "models_dir": str(self.models_dir),
        }

    def _predict_with_package(
        self, command: str, package: dict[str, Any], model_type: str
    ) -> tuple[bool, float, str]:
        """Predict using a loaded model package."""
        model = package["model"]
        threshold = package.get("threshold", 0.5)

        # Extract features
        row = self.extractor.extract(command)
        row.update(self._live_history_builder().features_for(command))

        frame = pd.DataFrame([row])[self._feature_names()]
        probability = float(model.predict_proba(frame)[0][1])
        will_fail = probability >= threshold

        trained_at = package.get("trained_at", "unknown")
        reason = f"per-family model v{MODEL_VERSION} ({model_type}, threshold={threshold:.2f}, trained_at={trained_at})"

        return will_fail, probability, reason

    def _load_model(self, path: Path) -> dict[str, Any] | None:
        """Load and cache a model package."""
        cache_key = str(path)
        if cache_key in self._cache:
            return self._cache[cache_key]

        if not path.exists():
            return None

        try:
            package = joblib.load(path)
            if package.get("version") != MODEL_VERSION:
                return None
            self._cache[cache_key] = package
            return package
        except Exception:
            return None

    def _load_history(self) -> tuple[list[str], list[int]]:
        """Load real history chronologically."""
        with connect() as conn:
            run_rows = conn.execute(
                "SELECT command, exit_code FROM runs ORDER BY created_at ASC, id ASC"
            ).fetchall()
            imported_rows = conn.execute(
                "SELECT command, exit_code FROM ml_training_examples ORDER BY created_at ASC, id ASC"
            ).fetchall()

        from ..classify import label_failure

        rows = list(run_rows) + list(imported_rows)
        commands = [str(row["command"]) for row in rows]
        labels = [label_failure(command, int(row["exit_code"])) for command, row in zip(commands, rows)]
        return commands, labels

    def _feature_names(self) -> list[str]:
        from .history_features import HISTORY_FEATURE_NAMES
        return self.extractor.get_feature_names() + HISTORY_FEATURE_NAMES

    def _training_frame(self, commands: list[str], labels: list[int]) -> pd.DataFrame:
        """Build training frame with expanding-window history features."""
        from .history_features import build_expanding_rows

        rows, _ = build_expanding_rows(list(zip(commands, labels)), self.extractor.extract)
        return pd.DataFrame(rows)[self._feature_names()]

    def _live_history_builder(self):
        """History stats from all recorded runs."""
        from .history_features import HistoryFeatureBuilder

        commands, labels = self._load_history()
        return HistoryFeatureBuilder.from_samples(list(zip(commands, labels)))

    def _build_family_model(self, sample_count: int) -> VotingClassifier:
        """Build a lightweight model for per-family training."""
        forest = RandomForestClassifier(
            n_estimators=120,
            max_depth=16,
            min_samples_leaf=2,
            class_weight="balanced_subsample",
            random_state=42,
            n_jobs=-1,
        )
        extra = ExtraTreesClassifier(
            n_estimators=120,
            max_depth=16,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=43,
            n_jobs=-1,
        )
        return VotingClassifier(
            estimators=[("forest", forest), ("extra", extra)],
            voting="soft",
            n_jobs=-1,
        )

    def _build_fallback_model(self) -> VotingClassifier:
        """Build stronger fallback model for commands without family models."""
        forest = RandomForestClassifier(
            n_estimators=200,
            max_depth=None,
            min_samples_leaf=1,
            class_weight="balanced_subsample",
            random_state=42,
            n_jobs=-1,
        )
        extra = ExtraTreesClassifier(
            n_estimators=200,
            max_depth=None,
            min_samples_leaf=1,
            class_weight="balanced",
            random_state=43,
            n_jobs=-1,
        )
        gradient = Pipeline(
            steps=[
                ("scale", StandardScaler()),
                ("model", GradientBoostingClassifier(n_estimators=150, learning_rate=0.05, random_state=44)),
            ]
        )
        return VotingClassifier(
            estimators=[
                ("forest", forest),
                ("extra", extra),
                ("gradient", gradient),
            ],
            voting="soft",
            weights=[2, 2, 1],
            n_jobs=-1,
        )

    def _holdout_threshold(self, frame: pd.DataFrame, labels: list[int], builder=None) -> float:
        """Pick the decision threshold on a temporal holdout (newest 25%).

        Fits a throwaway model on the oldest 75% and tunes the threshold on the
        newest 25%, so the threshold is chosen on rows the model never saw.
        Falls back to 0.5 when the holdout is too small or single-class.
        """
        build = builder or (lambda: self._build_family_model(len(labels)))
        split = int(len(labels) * 0.75)
        head_labels, tail_labels = labels[:split], labels[split:]
        if (
            len(tail_labels) < 8
            or len(set(tail_labels)) < 2
            or len(set(head_labels)) < 2
        ):
            return 0.5
        try:
            probe = build()
            probe.fit(frame.iloc[:split], pd.Series(head_labels, name="failed"))
            tail_probabilities = probe.predict_proba(frame.iloc[split:])[:, 1]
            return self._optimal_threshold(tail_labels, list(tail_probabilities))
        except Exception:
            return 0.5

    def _optimal_threshold(self, labels: list[int], probabilities: list[float]) -> float:
        """Find optimal classification threshold via F1 score."""
        from sklearn.metrics import f1_score

        best_threshold = 0.5
        best_f1 = 0.0

        for threshold in [i * 0.05 for i in range(1, 20)]:  # 0.05 to 0.95
            predictions = [1 if p >= threshold else 0 for p in probabilities]
            f1 = f1_score(labels, predictions, zero_division=0)
            if f1 > best_f1:
                best_f1 = f1
                best_threshold = threshold

        # Clamp to reasonable range
        return max(0.3, min(0.8, best_threshold))
