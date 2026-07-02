"""Import fixer for missing imports."""

from __future__ import annotations

from ..analyzers import ErrorAnalysis


class ImportFixer:
    """Generates fixes for missing imports."""

    confidence = 0.85

    def can_fix(self, analysis: ErrorAnalysis) -> bool:
        """Check if this is an import error."""
        return analysis.error_type in ["missing_module", "import_error"]

    def generate_fix(self, analysis: ErrorAnalysis) -> str:
        """Generate import fix."""
        if analysis.language == "python":
            module = analysis.details.get("module", "unknown")
            return f"pip install {module}"
        elif analysis.language in ["javascript", "typescript"]:
            module = analysis.details.get("module", "unknown")
            return f"npm install {module}"
        return "Unknown import error"
