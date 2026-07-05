"""Sklearn ensemble training for command failure prediction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, GradientBoostingClassifier, HistGradientBoostingClassifier, RandomForestClassifier, VotingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ..store import connect, data_dir
from .features import FeatureExtractor


MODEL_VERSION = 3  # v3: leak-free expanding-window history features


@dataclass(frozen=True)
class TrainingResult:
    """Training result metadata."""

    trained: bool
    model_path: Path
    samples: int
    positives: int
    negatives: int
    accuracy: float
    precision: float
    recall: float
    roc_auc: float | None
    message: str
    model_kind: str = "standard"


class SklearnFailureModel:
    """Persisted heavyweight sklearn ensemble for failure prediction."""

    def __init__(self, model_path: Path | None = None, extractor: FeatureExtractor | None = None):
        self.extractor = extractor or FeatureExtractor()
        self.model_path = model_path or data_dir() / "models" / "failure_predictor.joblib"

    def train_from_history(
        self,
        min_samples: int = 40,
        synthetic_floor: int = 120,
        target_samples: int | None = None,
    ) -> TrainingResult:
        """Train from SAGE command history with synthetic priors if history is sparse."""
        commands, labels = self._load_history()
        history_samples = len(labels)
        target_samples = max(0, int(target_samples or 0))

        needs_bootstrap = len(set(labels)) < 2 or len(labels) < min_samples
        if labels and len(set(labels)) == 2:
            positives = sum(labels)
            negatives = len(labels) - positives
            needs_bootstrap = needs_bootstrap or max(positives, negatives) / max(1, min(positives, negatives)) > 2

        bootstrap_target = max(synthetic_floor, target_samples - len(labels))
        if needs_bootstrap or target_samples > len(labels):
            synthetic_commands, synthetic_labels = self._synthetic_training_rows(bootstrap_target)
            commands = commands + synthetic_commands
            labels = labels + synthetic_labels

        commands, labels = self._balance_training_rows(commands, labels)

        if target_samples and len(labels) > target_samples:
            commands = commands[:target_samples]
            labels = labels[:target_samples]

        if len(set(labels)) < 2:
            return TrainingResult(
                trained=False,
                model_path=self.model_path,
                samples=len(labels),
                positives=sum(labels),
                negatives=len(labels) - sum(labels),
                accuracy=0.0,
                precision=0.0,
                recall=0.0,
                roc_auc=None,
                message="Need both successful and failed runs to train.",
            )

        frame = self._training_frame(commands, labels)
        labels_series = pd.Series(labels, name="failed")

        stratify = labels_series if labels_series.nunique() > 1 and labels_series.value_counts().min() >= 2 else None
        x_train, x_test, y_train, y_test = train_test_split(
            frame,
            labels_series,
            test_size=0.25,
            random_state=42,
            stratify=stratify,
        )

        model_kind = "large_ensemble" if len(labels) >= 200_000 else "standard_ensemble"
        model = self._build_large_model() if model_kind == "large_ensemble" else self._build_model()
        model.fit(x_train, y_train)

        predictions = model.predict(x_test)
        probabilities = model.predict_proba(x_test)[:, 1]
        roc_auc = None
        if len(set(y_test)) == 2:
            roc_auc = float(roc_auc_score(y_test, probabilities))

        package = {
            "version": MODEL_VERSION,
            "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "history_samples": history_samples,
            "training_samples": len(labels),
            "model_kind": model_kind,
            "feature_names": self._feature_names(),
            "model": model,
            "metrics": {
                "accuracy": float(accuracy_score(y_test, predictions)),
                "precision": float(precision_score(y_test, predictions, zero_division=0)),
                "recall": float(recall_score(y_test, predictions, zero_division=0)),
                "roc_auc": roc_auc,
            },
        }

        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(package, self.model_path)

        return TrainingResult(
            trained=True,
            model_path=self.model_path,
            samples=len(labels),
            positives=sum(labels),
            negatives=len(labels) - sum(labels),
            accuracy=package["metrics"]["accuracy"],
            precision=package["metrics"]["precision"],
            recall=package["metrics"]["recall"],
            roc_auc=roc_auc,
            message="Trained sklearn ensemble from command history and bootstrap priors.",
            model_kind=model_kind,
        )

    def predict(self, command: str) -> tuple[bool, float, str] | None:
        """Predict with persisted model. Return None when no compatible model exists."""
        package = self.load()
        if not package:
            return None

        import pandas as pd

        model = package["model"]
        row = self.extractor.extract(command)
        row.update(self._live_history_builder().features_for(command))
        frame = pd.DataFrame([row])[self._feature_names()]
        probability = float(model.predict_proba(frame)[0][1])
        will_fail = probability >= 0.55
        trained_at = package.get("trained_at", "unknown")
        hist = row.get("hist_cmd_fail_rate", 0.0)
        reason = (
            f"trained ensemble v{MODEL_VERSION} (trained_at={trained_at}); "
            f"this command's past failure rate: {hist:.0%}"
        )
        return will_fail, probability, reason

    def status(self) -> dict[str, Any]:
        """Return persisted model status."""
        package = self.load()
        if not package:
            return {"trained": False, "model_path": str(self.model_path)}

        return {
            "trained": True,
            "model_path": str(self.model_path),
            "trained_at": package.get("trained_at"),
            "history_samples": package.get("history_samples", 0),
            "training_samples": package.get("training_samples", 0),
            "model_kind": package.get("model_kind", "unknown"),
            "metrics": package.get("metrics", {}),
            "features": package.get("feature_names", []),
        }

    def load(self) -> dict[str, Any] | None:
        """Load a compatible model package from disk."""
        if not self.model_path.exists():
            return None
        try:
            package = joblib.load(self.model_path)
        except Exception:
            return None
        if package.get("version") != MODEL_VERSION:
            return None
        return package

    def _load_history(self) -> tuple[list[str], list[int]]:
        """Load real history chronologically so expanding-window features are honest."""
        with connect() as conn:
            run_rows = conn.execute(
                "SELECT command, exit_code, created_at FROM runs ORDER BY created_at ASC, id ASC"
            ).fetchall()
            imported_rows = conn.execute(
                "SELECT command, exit_code, created_at FROM ml_training_examples ORDER BY created_at ASC, id ASC"
            ).fetchall()

        rows = sorted(
            list(run_rows) + list(imported_rows),
            key=lambda row: str(row["created_at"] or ""),
        )
        from ..classify import label_failure

        commands = [str(row["command"]) for row in rows]
        labels = [label_failure(command, int(row["exit_code"])) for command, row in zip(commands, rows)]
        return commands, labels

    def _commands_to_frame(self, commands: list[str]) -> pd.DataFrame:
        rows = [self.extractor.extract(command) for command in commands]
        frame = pd.DataFrame(rows)
        return frame[self.extractor.get_feature_names()]

    def _feature_names(self) -> list[str]:
        from .history_features import HISTORY_FEATURE_NAMES

        return self.extractor.get_feature_names() + HISTORY_FEATURE_NAMES

    def _training_frame(self, commands: list[str], labels: list[int]) -> pd.DataFrame:
        """Chronological expanding-window frame: no row sees its own or future outcomes."""
        from .history_features import build_expanding_rows

        rows, _ = build_expanding_rows(list(zip(commands, labels)), self.extractor.extract)
        return pd.DataFrame(rows)[self._feature_names()]

    def _live_history_builder(self):
        """History stats from ALL recorded runs, cached per latest run id."""
        from .history_features import HistoryFeatureBuilder

        with connect() as conn:
            latest = conn.execute("SELECT COALESCE(MAX(id), 0) FROM runs").fetchone()[0]
        cached = getattr(self, "_history_cache", None)
        if cached and cached[0] == latest:
            return cached[1]
        commands, labels = self._load_history()
        builder = HistoryFeatureBuilder.from_samples(list(zip(commands, labels)))
        self._history_cache = (latest, builder)
        return builder

    def _build_model(self) -> VotingClassifier:
        forest = RandomForestClassifier(
            n_estimators=300,
            max_depth=None,
            min_samples_leaf=1,
            class_weight="balanced_subsample",
            random_state=42,
            n_jobs=-1,
        )
        extra_trees = ExtraTreesClassifier(
            n_estimators=300,
            max_depth=None,
            min_samples_leaf=1,
            class_weight="balanced",
            random_state=43,
            n_jobs=-1,
        )
        gradient = Pipeline(
            steps=[
                ("scale", StandardScaler()),
                ("model", GradientBoostingClassifier(n_estimators=180, learning_rate=0.04, random_state=44)),
            ]
        )
        return VotingClassifier(
            estimators=[
                ("random_forest", forest),
                ("extra_trees", extra_trees),
                ("gradient_boosting", gradient),
            ],
            voting="soft",
            weights=[2, 2, 1],
            n_jobs=-1,
        )

    def _build_large_model(self) -> VotingClassifier:
        forest = RandomForestClassifier(
            n_estimators=120,
            max_depth=28,
            min_samples_leaf=2,
            class_weight="balanced_subsample",
            random_state=142,
            n_jobs=-1,
        )
        extra_trees = ExtraTreesClassifier(
            n_estimators=220,
            max_depth=32,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=143,
            n_jobs=-1,
        )
        histogram = HistGradientBoostingClassifier(
            max_iter=260,
            learning_rate=0.045,
            max_leaf_nodes=63,
            l2_regularization=0.02,
            random_state=144,
        )
        return VotingClassifier(
            estimators=[
                ("random_forest", forest),
                ("extra_trees", extra_trees),
                ("hist_gradient_boosting", histogram),
            ],
            voting="soft",
            weights=[2, 3, 2],
            n_jobs=-1,
        )

    def _synthetic_training_rows(self, target: int) -> tuple[list[str], list[int]]:
        commands: list[str] = []
        labels: list[int] = []
        packages = ["requests", "numpy", "pandas", "fastapi", "missing_pkg", "private_lib", "pytest", "pywinpty"]
        files = ["app.py", "tests/test_app.py", "src/sage/runner.py", "missing_file.py", "package.json", "pyproject.toml"]
        scripts = ["test", "build", "lint", "missing-script", "dev", "typecheck"]
        branches = ["main", "feature/ml", "release", "bad-ref"]
        safe_templates = [
            "python --version",
            "python -m pip --version",
            "python -c \"print({n})\"",
            "git status",
            "git rev-parse --show-toplevel",
            "npm --version",
            "sage context stats",
            "sage agents status",
            "python -m pytest --version",
            "dir",
            "echo command-{n}",
            "python {file} --help",
        ]
        risky_templates = [
            "pytest {file}",
            "python -m pytest {file} --maxfail=1",
            "python missing_file_{n}.py",
            "python -c \"import {package}_missing\"",
            "pip install {package}_missing_{n}",
            "npm run {script}",
            "npm test -- --runInBand",
            "git push origin {branch}",
            "make {script}",
            "docker build . --file missing.Dockerfile",
            "sage run -- python -c \"raise Exception('failure {n}')\"",
            "python {file} && pytest missing_tests_{n}",
        ]
        while len(commands) < target:
            n = len(commands)
            context = {
                "n": n,
                "package": packages[n % len(packages)],
                "file": files[n % len(files)],
                "script": scripts[n % len(scripts)],
                "branch": branches[n % len(branches)],
            }
            if n % 2 == 0:
                template = risky_templates[(n // 2) % len(risky_templates)]
                labels.append(1)
            else:
                template = safe_templates[(n // 2) % len(safe_templates)]
                labels.append(0)
            commands.append(template.format(**context))
        return commands[:target], labels[:target]

    def _balance_training_rows(self, commands: list[str], labels: list[int]) -> tuple[list[str], list[int]]:
        """Balance labels enough that the model learns both classes."""
        if not labels or len(set(labels)) < 2:
            return commands, labels

        positives = sum(labels)
        negatives = len(labels) - positives
        synthetic_commands, synthetic_labels = self._synthetic_training_rows(20)
        risky = [command for command, label in zip(synthetic_commands, synthetic_labels) if label == 1]
        safe = [command for command, label in zip(synthetic_commands, synthetic_labels) if label == 0]

        if positives < negatives:
            index = 0
            while positives < negatives:
                commands.append(risky[index % len(risky)])
                labels.append(1)
                positives += 1
                index += 1
        elif negatives < positives:
            index = 0
            while negatives < positives:
                commands.append(safe[index % len(safe)])
                labels.append(0)
                negatives += 1
                index += 1

        return commands, labels
