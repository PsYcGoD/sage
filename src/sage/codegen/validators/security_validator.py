"""Security validator for detecting hardcoded secrets."""

from __future__ import annotations

import re
from pathlib import Path

from .base import ValidationIssue


class SecurityValidator:
    """Detect hardcoded secrets and sensitive data in code."""

    SECRET_PATTERNS = [
        # API keys
        (
            "api_key",
            re.compile(
                r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\'][A-Za-z0-9_\-./+=]{10,}["\']'
            ),
        ),
        # Passwords
        (
            "password",
            re.compile(
                r'(?i)(password|passwd|pwd|secret)\s*[=:]\s*["\'][^"\']{4,}["\']'
            ),
        ),
        # Generic tokens
        (
            "token",
            re.compile(r'(?i)(token|auth[_-]?token)\s*[=:]\s*["\'][A-Za-z0-9_\-./+=]{20,}["\']'),
        ),
        # AWS access keys
        ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
        # AWS secret keys
        (
            "aws_secret_key",
            re.compile(r'(?i)aws[_-]?secret[_-]?(?:access[_-]?)?key\s*[=:]\s*["\'][A-Za-z0-9/+=]{40}["\']'),
        ),
        # Private keys
        ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
        # GitHub tokens
        ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,}")),
        # Slack tokens
        ("slack_token", re.compile(r"xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24}")),
        # Discord tokens
        ("discord_token", re.compile(r"[MN][A-Za-z\d]{23,}\.[\w-]{6}\.[\w-]{27}")),
        # JWT tokens
        ("jwt_token", re.compile(r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")),
        # Generic secrets in common variable names
        (
            "generic_secret",
            re.compile(
                r'(?i)(client[_-]?secret|secret[_-]?key|encryption[_-]?key)\s*[=:]\s*["\'][^"\']{8,}["\']'
            ),
        ),
    ]

    # Patterns that indicate it's likely not a real secret
    FALSE_POSITIVE_PATTERNS = [
        re.compile(r'["\']<[^>]+>["\']'),  # Placeholder like "<your-api-key>"
        re.compile(r'["\']your[_-]?[^"\']+["\']', re.IGNORECASE),  # "your_api_key"
        re.compile(r'["\']xxx+["\']', re.IGNORECASE),  # "xxx" placeholders
        re.compile(r'["\']example[^"\']*["\']', re.IGNORECASE),  # "example_key"
        re.compile(r'["\']test[^"\']*["\']', re.IGNORECASE),  # "test_key"
        re.compile(r'["\']dummy[^"\']*["\']', re.IGNORECASE),  # "dummy_key"
        re.compile(r'["\']fake[^"\']*["\']', re.IGNORECASE),  # "fake_key"
        re.compile(r"os\.environ|getenv|config\["),  # Environment variable access
    ]

    def can_validate(self, path: Path) -> bool:
        # Skip known safe file types
        skip_extensions = {".md", ".txt", ".rst", ".lock", ".sum"}
        if path.suffix.lower() in skip_extensions:
            return False
        # Skip test files for some checks
        return True

    def validate(self, path: Path, content: str) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        is_test_file = "test" in str(path).lower()

        for line_no, line in enumerate(content.splitlines(), 1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("//"):
                continue

            # Check for false positives first
            if any(fp.search(line) for fp in self.FALSE_POSITIVE_PATTERNS):
                continue

            for secret_name, pattern in self.SECRET_PATTERNS:
                if pattern.search(line):
                    # Be more lenient in test files
                    severity = "warning" if is_test_file else "error"

                    issues.append(
                        ValidationIssue(
                            file=str(path),
                            line=line_no,
                            severity=severity,
                            category="hardcoded_secret",
                            message=f"Possible hardcoded {secret_name.replace('_', ' ')} detected",
                            suggestion="Use environment variables or a secrets manager",
                            code_snippet=self._mask_secret(line.strip()[:80]),
                        )
                    )
                    break  # One issue per line

        return issues

    def _mask_secret(self, line: str) -> str:
        """Mask potential secrets in code snippet."""
        # Replace quoted strings with masked version
        masked = re.sub(r'["\'][^"\']{4,}["\']', '"***MASKED***"', line)
        return masked
