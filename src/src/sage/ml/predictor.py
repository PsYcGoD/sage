"""ML-based failure prediction."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

from ..store import connect
from .features import FeatureExtractor


class FailurePredictor:
    """Predict command failure probability using ML."""

    def __init__(self):
        self.feature_extractor = FeatureExtractor()
        self.model = None
        self.trained = False

    def predict(self, command: str) -> Tuple[bool, float, str]:
        """
        Predict if command will fail.
        
        Returns:
            (will_fail, confidence, reason)
        """
        # Extract features
        context = self._get_context()
        features = self.feature_extractor.extract(command, context)

        # Simple heuristic-based prediction for now
        # TODO: Train actual ML model when we have enough data

        # High probability of failure if:
        failure_indicators = []
        confidence = 0.5

        # Check recent failure rate
        if context.get('num_recent_failures', 0) > 3:
            failure_indicators.append("High recent failure rate")
            confidence += 0.2

        # Check if it's a Monday (higher failure rate!)
        if features.get('is_monday', 0) == 1.0:
            failure_indicators.append("It's Monday")
            confidence += 0.1

        # Check if installing without requirements file
        if features.get('has_install_keyword', 0) == 1.0:
            if features.get('has_requirements_txt', 0) == 0.0 and 'pip' in command:
                failure_indicators.append("pip install without requirements.txt")
                confidence += 0.15

        # Check time since last failure
        if context.get('minutes_since_last_failure', 1440) < 5:
            failure_indicators.append("Recent failure <5 min ago")
            confidence += 0.2

        will_fail = confidence > 0.65
        reason = "; ".join(failure_indicators) if failure_indicators else "Low risk"

        return (will_fail, min(confidence, 0.95), reason)

    def _get_context(self) -> Dict:
        """Get context from recent command history."""
        with connect() as conn:
            # Get recent failures
            recent_failures = conn.execute(
                """
                SELECT COUNT(*) as count
                FROM runs
                WHERE exit_code != 0
                AND created_at > datetime('now', '-1 hour')
                """
            ).fetchone()

            # Get last failure time
            last_failure = conn.execute(
                """
                SELECT created_at
                FROM runs
                WHERE exit_code != 0
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()

            context = {
                'num_recent_failures': recent_failures['count'] if recent_failures else 0,
            }

            if last_failure:
                try:
                    last_time = datetime.fromisoformat(last_failure['created_at'])
                    now = datetime.now(timezone.utc)
                    delta = (now - last_time).total_seconds() / 60
                    context['minutes_since_last_failure'] = delta
                except Exception:
                    context['minutes_since_last_failure'] = 1440.0

            return context

    def train(self, training_data: Optional[list] = None):
        """Train the ML model on historical data."""
        # TODO: Implement actual ML training
        # For now, we use heuristics above
        self.trained = True
        return True
