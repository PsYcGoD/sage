"""Fix generators for different error types."""

from __future__ import annotations

from typing import Protocol

from ..analyzers import ErrorAnalysis


class Fixer(Protocol):
    """Protocol for fix generators."""
    
    confidence: float

    def can_fix(self, analysis: ErrorAnalysis) -> bool:
        """Check if this fixer can fix the error."""
        ...

    def generate_fix(self, analysis: ErrorAnalysis) -> str:
        """Generate a fix template for the error."""
        ...
