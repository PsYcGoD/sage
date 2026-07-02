"""Python error analyzer."""

from __future__ import annotations

import re

from . import ErrorAnalysis


class PythonAnalyzer:
    """Analyzes Python errors from command output."""

    def can_handle(self, output: str, command: str) -> bool:
        """Check if this is a Python error."""
        python_indicators = [
            "Traceback (most recent call last):",
            "ModuleNotFoundError:",
            "ImportError:",
            "SyntaxError:",
            "NameError:",
            "TypeError:",
            "ValueError:",
        ]
        return any(indicator in output for indicator in python_indicators)

    def analyze(self, output: str, command: str) -> ErrorAnalysis:
        """Analyze Python error."""
        # Detect ModuleNotFoundError
        module_match = re.search(r"ModuleNotFoundError: No module named '([^']+)'", output)
        if module_match:
            module_name = module_match.group(1)
            return ErrorAnalysis(
                pattern=f"ModuleNotFoundError: {module_name}",
                language="python",
                error_type="missing_module",
                details={"module": module_name},
            )

        # Detect ImportError
        import_match = re.search(r"ImportError: cannot import name '([^']+)'", output)
        if import_match:
            name = import_match.group(1)
            return ErrorAnalysis(
                pattern=f"ImportError: {name}",
                language="python",
                error_type="import_error",
                details={"name": name},
            )

        # Detect SyntaxError
        if "SyntaxError:" in output:
            return ErrorAnalysis(
                pattern="SyntaxError",
                language="python",
                error_type="syntax_error",
                details={},
            )

        # Generic Python error
        return ErrorAnalysis(
            pattern="Python error",
            language="python",
            error_type="generic",
            details={},
        )
