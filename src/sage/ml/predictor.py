"""Failure prediction for SAGE commands."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Mapping

from ..store import connect, db_path
from .features import FeatureExtractor
from .model import SklearnFailureModel
from .family_model import FamilyFailureModel

try:
    from .embeddings import CommandEmbedder, _HAS_ML_DEPS
    from .vector_store import CommandVectorStore, build_vector_store

    _HAS_V2 = _HAS_ML_DEPS
except ImportError:
    _HAS_V2 = False

logger = logging.getLogger(__name__)


class FailurePredictor:
    """Predict command failure probability from local command history.

    This is a deterministic heuristic predictor today. It exposes the same API a
    trained model can use later, while still providing useful risk signals now.
    """

    def __init__(self, feature_extractor: FeatureExtractor | None = None):
        self.feature_extractor = feature_extractor or FeatureExtractor()
        self.sklearn_model = SklearnFailureModel(extractor=self.feature_extractor)
        self.family_model = FamilyFailureModel(extractor=self.feature_extractor)
        self.model = None
        self.trained = False
        self._vector_store: CommandVectorStore | None = None
        self._v2_failed = False

    def _get_vector_store(self) -> CommandVectorStore | None:
        """Lazily initialize the V2 vector store (returns None if unavailable)."""
        if not _HAS_V2 or self._v2_failed:
            return None
        if self._vector_store is not None:
            return self._vector_store

        try:
            store = build_vector_store(db_path(), use_cache=True)
            self._vector_store = store
            logger.info(f"ML V2 vector store ready: {store.size} commands indexed")
            return store
        except (ValueError, RuntimeError, ImportError) as e:
            logger.debug(f"ML V2 not available: {e}")
            self._v2_failed = True
            return None

    def predict(self, command: str) -> tuple[bool, float, str]:
        """Return (will_fail, confidence, reason)."""
        # Try V2 embedding-based prediction first
        v2_prediction = self._predict_v2(command)
        if v2_prediction is not None:
            return self._with_recent_failure_context(command, v2_prediction)

        # Try family-specific models (v4)
        family_prediction = self.family_model.predict(command)
        if family_prediction is not None:
            return self._with_recent_failure_context(command, family_prediction)

        # Fall back to global sklearn model (v3)
        trained_prediction = self.sklearn_model.predict(command)
        if trained_prediction is not None:
            return self._with_recent_failure_context(command, trained_prediction)

        # Heuristic fallback
        context = self._get_context()
        features = self.feature_extractor.extract(command, context)
        confidence, reasons = self._score(command, features, context)
        will_fail = confidence >= 0.65
        reason = "; ".join(reasons) if reasons else "Low risk"
        return will_fail, min(confidence, 0.95), reason

    def _with_recent_failure_context(
        self,
        command: str,
        prediction: tuple[bool, float, str],
    ) -> tuple[bool, float, str]:
        """Blend live failure context into trained predictions.

        The trained models already capture long-term family behavior. This
        overlay handles the short-lived "everything is failing right now" case
        without requiring retraining or weakening the per-family thresholds.
        """
        will_fail, confidence, reason = prediction
        context = self._get_context()
        recent_failures = context.get("num_recent_failures", 0.0)
        minutes = context.get("minutes_since_last_failure", 1440.0)
        command_lower = command.lower()

        context_reasons: list[str] = []
        if recent_failures >= 4:
            confidence = max(confidence, 0.6)
            context_reasons.append("high recent failure rate")
        elif recent_failures >= 2:
            confidence = max(confidence, 0.5)
            context_reasons.append("multiple recent failures")

        if minutes < 5:
            confidence = max(confidence + 0.04, confidence)
            context_reasons.append("last failure was under 5 minutes ago")

        if recent_failures and any(token in command_lower for token in ("test", "pytest", "unittest", "jest")):
            confidence = max(confidence + 0.03, confidence)
            context_reasons.append("test command after recent failures")

        confidence = min(confidence, 0.95)
        will_fail = will_fail or confidence >= 0.65
        if context_reasons:
            reason = f"{reason}; " + "; ".join(context_reasons)
        return will_fail, confidence, reason

    def _predict_v2(self, command: str) -> tuple[bool, float, str] | None:
        """Embedding-based prediction using V2 vector similarity search."""
        store = self._get_vector_store()
        if store is None:
            return None

        try:
            prob, neighbors = store.predict_success(command, k=10)
            if not neighbors:
                return None

            # Only use V2 if we have reasonably close neighbors
            best_sim = neighbors[0].similarity if neighbors else 0
            if best_sim < 0.5:
                return None

            fail_prob = 1.0 - prob
            will_fail = fail_prob >= 0.55
            confidence = min(0.95, 0.4 + (best_sim * 0.5))

            # Build explanation from neighbors
            n_fail = sum(1 for n in neighbors if not n.success)
            n_total = len(neighbors)
            reason = (
                f"V2 embedding: {n_fail}/{n_total} similar commands failed "
                f"(best match: {neighbors[0].command!r}, sim={best_sim:.2f})"
            )

            return will_fail, confidence, reason
        except Exception as e:
            logger.debug(f"V2 prediction error: {e}")
            return None

    def train(self, training_data: list | None = None, use_family_models: bool = True) -> bool:
        """Train and persist ML models from local command history."""
        if use_family_models:
            result = self.family_model.train_from_history()
            self.trained = result.trained
            return result.trained
        else:
            result = self.sklearn_model.train_from_history()
            self.trained = result.trained
            return result.trained

    def _score(
        self,
        command: str,
        features: Mapping[str, float],
        context: Mapping[str, float],
    ) -> tuple[float, list[str]]:
        confidence = 0.35
        reasons: list[str] = []
        command_lower = command.lower()

        recent_failures = context.get("num_recent_failures", 0.0)
        if recent_failures >= 4:
            confidence += 0.25
            reasons.append("high recent failure rate")
        elif recent_failures >= 2:
            confidence += 0.15
            reasons.append("multiple recent failures")

        if context.get("minutes_since_last_failure", 1440.0) < 5:
            confidence += 0.2
            reasons.append("last failure was under 5 minutes ago")

        if features.get("has_install_keyword", 0.0):
            if "pip" in command_lower and not features.get("has_requirements_txt", 0.0):
                confidence += 0.15
                reasons.append("pip command without requirements.txt in project")
            if ("npm" in command_lower or "yarn" in command_lower) and not features.get("has_package_json", 0.0):
                confidence += 0.15
                reasons.append("node package command without package.json in project")

        if features.get("has_test_keyword", 0.0) and recent_failures:
            confidence += 0.1
            reasons.append("test command after recent failures")

        if features.get("is_monday", 0.0):
            confidence += 0.05
            reasons.append("Monday risk adjustment")

        return confidence, reasons

    def _get_context(self) -> dict[str, float]:
        """Get recent command-history context."""
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        context: dict[str, float] = {
            "num_recent_failures": 0.0,
            "minutes_since_last_failure": 1440.0,
        }

        with connect() as conn:
            recent_failures = conn.execute(
                """
                SELECT COUNT(*) as count
                FROM runs
                WHERE exit_code != 0
                AND created_at > ?
                """,
                (one_hour_ago.isoformat(timespec="seconds"),),
            ).fetchone()
            if recent_failures:
                context["num_recent_failures"] = float(recent_failures["count"])

            last_failure = conn.execute(
                """
                SELECT created_at
                FROM runs
                WHERE exit_code != 0
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()

        if last_failure:
            try:
                last_time = datetime.fromisoformat(str(last_failure["created_at"]))
                if last_time.tzinfo is None:
                    last_time = last_time.replace(tzinfo=timezone.utc)
                delta = datetime.now(timezone.utc) - last_time
                context["minutes_since_last_failure"] = max(0.0, delta.total_seconds() / 60)
            except ValueError:
                pass

        return context
