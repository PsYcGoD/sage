"""Quality validator for TODO comments and code quality markers."""

from __future__ import annotations

import re
from pathlib import Path

from .base import ValidationIssue


class QualityValidator:
    """Detect TODO comments, FIXME markers, and other quality indicators."""

    TODO_PATTERNS = [
        (re.compile(r"#\s*TODO\b", re.IGNORECASE), "TODO"),
        (re.compile(r"//\s*TODO\b", re.IGNORECASE), "TODO"),
        (re.compile(r"/\*\s*TODO\b", re.IGNORECASE), "TODO"),
        (re.compile(r"#\s*FIXME\b", re.IGNORECASE), "FIXME"),
        (re.compile(r"//\s*FIXME\b", re.IGNORECASE), "FIXME"),
        (re.compile(r"#\s*HACK\b", re.IGNORECASE), "HACK"),
        (re.compile(r"//\s*HACK\b", re.IGNORECASE), "HACK"),
        (re.compile(r"#\s*XXX\b", re.IGNORECASE), "XXX"),
        (re.compile(r"//\s*XXX\b", re.IGNORECASE), "XXX"),
        (re.compile(r"#\s*BUG\b", re.IGNORECASE), "BUG"),
        (re.compile(r"//\s*BUG\b", re.IGNORECASE), "BUG"),
        (re.compile(r"#\s*OPTIMIZE\b", re.IGNORECASE), "OPTIMIZE"),
        (re.compile(r"#\s*REFACTOR\b", re.IGNORECASE), "REFACTOR"),
    ]

    # Patterns that indicate incomplete implementation
    INCOMPLETE_PATTERNS = [
        (re.compile(r"raise\s+NotImplementedError"), "NotImplementedError"),
        (re.compile(r'raise\s+NotImplementedError\s*\(\s*\)'), "NotImplementedError"),
        (re.compile(r"pass\s*#\s*placeholder", re.IGNORECASE), "placeholder"),
        (re.compile(r"\.\.\.\s*#\s*implement", re.IGNORECASE), "stub"),
    ]

    # Debug/logging patterns that shouldn't be in production
    DEBUG_PATTERNS = [
        (re.compile(r"\bprint\s*\("), "print statement"),
        (re.compile(r"\bconsole\.log\s*\("), "console.log"),
        (re.compile(r"\bdebugger\s*;?"), "debugger statement"),
        (re.compile(r"import\s+pdb|pdb\.set_trace\(\)"), "pdb debugger"),
        (re.compile(r"import\s+ipdb|ipdb\.set_trace\(\)"), "ipdb debugger"),
        (re.compile(r"breakpoint\s*\(\)"), "breakpoint"),
    ]

    def can_validate(self, path: Path) -> bool:
        # Validate most code files
        code_extensions = {
            ".py", ".pyi", ".js", ".jsx", ".ts", ".tsx",
            ".java", ".go", ".rs", ".rb", ".php", ".c", ".cpp", ".h",
        }
        return path.suffix.lower() in code_extensions

    def validate(self, path: Path, content: str) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        is_test_file = "test" in str(path).lower()

        for line_no, line in enumerate(content.splitlines(), 1):
            # Check TODO patterns
            for pattern, marker in self.TODO_PATTERNS:
                if pattern.search(line):
                    issues.append(
                        ValidationIssue(
                            file=str(path),
                            line=line_no,
                            severity="info",
                            category="todo_comment",
                            message=f"{marker} comment found",
                            suggestion=None,
                            code_snippet=line.strip()[:80],
                        )
                    )
                    break

            # Check incomplete implementation patterns
            for pattern, marker in self.INCOMPLETE_PATTERNS:
                if pattern.search(line):
                    issues.append(
                        ValidationIssue(
                            file=str(path),
                            line=line_no,
                            severity="warning",
                            category="incomplete_implementation",
                            message=f"Incomplete implementation: {marker}",
                            suggestion="Complete the implementation before release",
                        )
                    )
                    break

            # Check debug patterns (not in test files)
            if not is_test_file:
                for pattern, marker in self.DEBUG_PATTERNS:
                    if pattern.search(line):
                        # Skip if it's in a comment
                        stripped = line.strip()
                        if stripped.startswith("#") or stripped.startswith("//"):
                            continue

                        issues.append(
                            ValidationIssue(
                                file=str(path),
                                line=line_no,
                                severity="warning",
                                category="debug_code",
                                message=f"Debug code found: {marker}",
                                suggestion="Remove debug statements before production",
                            )
                        )
                        break

        return issues
