"""Error analyzers for different languages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class ErrorAnalysis:
    """Result of error analysis."""
    pattern: str
    language: str
    error_type: str
    details: dict


class Analyzer(Protocol):
    """Protocol for error analyzers."""

    def can_handle(self, output: str, command: str) -> bool:
        """Check if this analyzer can handle the error."""
        ...

    def analyze(self, output: str, command: str) -> ErrorAnalysis:
        """Analyze the error and return structured information."""
        ...
