"""Base class for specialized predictors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Prediction:
    """Result from a specialized predictor."""

    category: str
    probability: float
    will_trigger: bool
    reason: str
    suggestion: Optional[str] = None


class BasePredictor:
    """Base class for all specialized predictors."""

    CATEGORY = "unknown"

    def predict(self, command: str, **context) -> Optional[Prediction]:
        """Predict failure for this category. Returns None if not applicable."""
        raise NotImplementedError
