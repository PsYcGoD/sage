"""JavaScript/TypeScript error analyzer."""

from __future__ import annotations

import re

from . import ErrorAnalysis


class JavaScriptAnalyzer:
    """Analyzes JavaScript/TypeScript errors from command output."""

    def can_handle(self, output: str, command: str) -> bool:
        """Check if this is a JS/TS error."""
        js_indicators = [
            "SyntaxError:",
            "ReferenceError:",
            "TypeError:",
            "Cannot find module",
            "npm ERR!",
            "TS",
        ]
        return any(indicator in output for indicator in js_indicators)

    def analyze(self, output: str, command: str) -> ErrorAnalysis:
        """Analyze JavaScript/TypeScript error."""
        # Detect missing module
        module_match = re.search(r"Cannot find module '([^']+)'", output)
        if module_match:
            module_name = module_match.group(1)
            return ErrorAnalysis(
                pattern=f"Cannot find module: {module_name}",
                language="javascript",
                error_type="missing_module",
                details={"module": module_name},
            )

        # Detect TypeScript error
        ts_match = re.search(r"TS(\d+):", output)
        if ts_match:
            error_code = ts_match.group(1)
            return ErrorAnalysis(
                pattern=f"TypeScript TS{error_code}",
                language="typescript",
                error_type="typescript_error",
                details={"error_code": error_code},
            )

        # Generic JS error
        return ErrorAnalysis(
            pattern="JavaScript error",
            language="javascript",
            error_type="generic",
            details={},
        )
