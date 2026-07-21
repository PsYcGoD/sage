"""Base validation protocol and data classes for SAGE codegen validators."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass
class ValidationIssue:
    """A validation issue found in code."""

    file: str
    line: int
    severity: str  # "error", "warning", "info"
    category: str  # "empty_function", "todo", "hardcoded_secret", etc.
    message: str
    suggestion: str | None = None
    code_snippet: str | None = None

    def __str__(self) -> str:
        sev = self.severity.upper()
        loc = f"{self.file}:{self.line}" if self.line > 0 else self.file
        return f"[{sev}] {loc}: {self.message}"


@dataclass
class ValidationResult:
    """Result of validating one or more files."""

    valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    files_checked: int = 0

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def infos(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "info"]

    def summary(self) -> str:
        """Generate a summary string."""
        parts = []
        if self.errors:
            parts.append(f"{len(self.errors)} error(s)")
        if self.warnings:
            parts.append(f"{len(self.warnings)} warning(s)")
        if self.infos:
            parts.append(f"{len(self.infos)} info(s)")
        if not parts:
            return "No issues found"
        return ", ".join(parts)


@runtime_checkable
class Validator(Protocol):
    """Protocol for code validators."""

    def can_validate(self, path: Path) -> bool:
        """Check if this validator can handle this file type."""
        ...

    def validate(self, path: Path, content: str) -> list[ValidationIssue]:
        """Validate file content and return issues found."""
        ...


class ValidatorRegistry:
    """Registry for all validators."""

    def __init__(self):
        self._validators: list[Validator] = []

    def register(self, validator: Validator) -> None:
        """Register a validator."""
        self._validators.append(validator)

    def validate_file(self, path: Path, content: str) -> list[ValidationIssue]:
        """Run all applicable validators on a file."""
        issues: list[ValidationIssue] = []
        for validator in self._validators:
            if validator.can_validate(path):
                issues.extend(validator.validate(path, content))
        return issues

    def validate(self, path: Path, content: str) -> ValidationResult:
        """Validate a single file and return result."""
        issues = self.validate_file(path, content)
        has_errors = any(i.severity == "error" for i in issues)
        return ValidationResult(
            valid=not has_errors,
            issues=issues,
            files_checked=1,
        )

    def validate_files(self, files: list[tuple[Path, str]]) -> ValidationResult:
        """Validate multiple files and return combined result."""
        all_issues: list[ValidationIssue] = []
        for path, content in files:
            all_issues.extend(self.validate_file(path, content))

        has_errors = any(i.severity == "error" for i in all_issues)
        return ValidationResult(
            valid=not has_errors,
            issues=all_issues,
            files_checked=len(files),
        )
