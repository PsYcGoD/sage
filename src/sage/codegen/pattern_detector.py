"""Pattern detection for SAGE codegen - detects naming, error handling, testing patterns."""

from __future__ import annotations

import ast
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class DetectedPattern:
    """A detected code pattern in the codebase."""

    category: str  # "naming", "error_handling", "testing", "imports", "structure"
    pattern: str  # Description of the pattern
    examples: list[str] = field(default_factory=list)  # File:line examples
    confidence: float = 0.5  # 0.0-1.0
    applicable_to: list[str] = field(default_factory=list)  # File extensions


class PatternDetector:
    """Detect coding patterns from an existing codebase."""

    def __init__(self, root: Path):
        self.root = root
        self._cache: dict[str, list[DetectedPattern]] = {}

    def detect_all(self, sample_size: int = 20) -> list[DetectedPattern]:
        """Detect all patterns from the codebase."""
        patterns: list[DetectedPattern] = []
        patterns.extend(self.detect_naming_patterns(sample_size))
        patterns.extend(self.detect_error_patterns(sample_size))
        patterns.extend(self.detect_testing_patterns())
        patterns.extend(self.detect_import_patterns(sample_size))
        return patterns

    def detect_naming_patterns(self, sample_size: int = 20) -> list[DetectedPattern]:
        """Detect naming convention patterns."""
        patterns: list[DetectedPattern] = []
        py_files = list(self.root.rglob("*.py"))[:sample_size]

        function_styles: Counter[str] = Counter()
        class_styles: Counter[str] = Counter()
        variable_styles: Counter[str] = Counter()
        examples: dict[str, list[str]] = {"snake": [], "camel": [], "pascal": []}

        for py_file in py_files:
            try:
                content = py_file.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(content)
            except (SyntaxError, OSError):
                continue

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    style = self._classify_naming_style(node.name)
                    function_styles[style] += 1
                    if len(examples.get(style, [])) < 3:
                        examples.setdefault(style, []).append(
                            f"{py_file.name}:{node.lineno} - {node.name}"
                        )

                elif isinstance(node, ast.ClassDef):
                    style = self._classify_naming_style(node.name)
                    class_styles[style] += 1

                elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                    style = self._classify_naming_style(node.id)
                    variable_styles[style] += 1

        # Determine dominant function naming
        if function_styles:
            dominant = function_styles.most_common(1)[0]
            total = sum(function_styles.values())
            confidence = dominant[1] / total if total > 0 else 0
            if confidence > 0.7:
                patterns.append(
                    DetectedPattern(
                        category="naming",
                        pattern=f"Functions use {dominant[0]} naming",
                        examples=examples.get(dominant[0], [])[:3],
                        confidence=confidence,
                        applicable_to=[".py"],
                    )
                )

        # Determine dominant class naming
        if class_styles:
            dominant = class_styles.most_common(1)[0]
            total = sum(class_styles.values())
            confidence = dominant[1] / total if total > 0 else 0
            if confidence > 0.7:
                patterns.append(
                    DetectedPattern(
                        category="naming",
                        pattern=f"Classes use {dominant[0]} naming",
                        confidence=confidence,
                        applicable_to=[".py"],
                    )
                )

        return patterns

    def detect_error_patterns(self, sample_size: int = 20) -> list[DetectedPattern]:
        """Detect error handling patterns."""
        patterns: list[DetectedPattern] = []
        py_files = list(self.root.rglob("*.py"))[:sample_size]

        specific_except_count = 0
        bare_except_count = 0
        exception_types: Counter[str] = Counter()
        examples: list[str] = []

        for py_file in py_files:
            try:
                content = py_file.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(content)
            except (SyntaxError, OSError):
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    if node.type is None:
                        bare_except_count += 1
                    else:
                        specific_except_count += 1
                        if isinstance(node.type, ast.Name):
                            exception_types[node.type.id] += 1
                            if len(examples) < 3:
                                examples.append(
                                    f"{py_file.name}:{node.lineno} - except {node.type.id}"
                                )

        total = specific_except_count + bare_except_count
        if total > 0:
            specific_ratio = specific_except_count / total
            if specific_ratio > 0.8:
                patterns.append(
                    DetectedPattern(
                        category="error_handling",
                        pattern="Uses specific exception types (not bare except)",
                        examples=examples,
                        confidence=specific_ratio,
                        applicable_to=[".py"],
                    )
                )

            # Report common exception types
            if exception_types:
                common = exception_types.most_common(3)
                patterns.append(
                    DetectedPattern(
                        category="error_handling",
                        pattern=f"Common exceptions: {', '.join(e[0] for e in common)}",
                        confidence=0.8,
                        applicable_to=[".py"],
                    )
                )

        return patterns

    def detect_testing_patterns(self) -> list[DetectedPattern]:
        """Detect testing framework and patterns."""
        patterns: list[DetectedPattern] = []

        # Find test files
        test_files = list(self.root.rglob("test_*.py")) + list(
            self.root.rglob("*_test.py")
        )
        if not test_files:
            test_dirs = [d for d in self.root.iterdir() if d.is_dir() and "test" in d.name.lower()]
            for d in test_dirs:
                test_files.extend(d.rglob("*.py"))

        if not test_files:
            return patterns

        pytest_markers = 0
        unittest_classes = 0
        fixtures = 0
        parametrize = 0
        examples: dict[str, list[str]] = {"fixture": [], "parametrize": []}

        for test_file in test_files[:20]:
            try:
                content = test_file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            if "@pytest.fixture" in content:
                fixtures += 1
                if len(examples["fixture"]) < 2:
                    examples["fixture"].append(str(test_file.name))

            if "@pytest.mark.parametrize" in content:
                parametrize += 1
                if len(examples["parametrize"]) < 2:
                    examples["parametrize"].append(str(test_file.name))

            if "import pytest" in content or "from pytest" in content:
                pytest_markers += 1

            if "import unittest" in content or "class Test" in content:
                unittest_classes += 1

        # Determine test framework
        if pytest_markers > unittest_classes:
            patterns.append(
                DetectedPattern(
                    category="testing",
                    pattern="Uses pytest framework",
                    confidence=0.9 if pytest_markers > 5 else 0.7,
                    applicable_to=[".py"],
                )
            )

            if fixtures > 0:
                patterns.append(
                    DetectedPattern(
                        category="testing",
                        pattern="Uses pytest fixtures for setup",
                        examples=examples["fixture"],
                        confidence=min(fixtures / len(test_files), 1.0),
                        applicable_to=[".py"],
                    )
                )

            if parametrize > 0:
                patterns.append(
                    DetectedPattern(
                        category="testing",
                        pattern="Uses @pytest.mark.parametrize for test cases",
                        examples=examples["parametrize"],
                        confidence=min(parametrize / len(test_files), 1.0),
                        applicable_to=[".py"],
                    )
                )

        elif unittest_classes > 0:
            patterns.append(
                DetectedPattern(
                    category="testing",
                    pattern="Uses unittest framework",
                    confidence=0.9 if unittest_classes > 5 else 0.7,
                    applicable_to=[".py"],
                )
            )

        return patterns

    def detect_import_patterns(self, sample_size: int = 20) -> list[DetectedPattern]:
        """Detect import organization patterns."""
        patterns: list[DetectedPattern] = []
        py_files = list(self.root.rglob("*.py"))[:sample_size]

        grouped_imports = 0
        alphabetized = 0
        absolute_imports = 0
        relative_imports = 0

        for py_file in py_files:
            try:
                content = py_file.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(content)
            except (SyntaxError, OSError):
                continue

            imports: list[tuple[int, str, bool]] = []  # (line, module, is_relative)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append((node.lineno, alias.name, False))
                        absolute_imports += 1
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    is_relative = node.level > 0
                    imports.append((node.lineno, module, is_relative))
                    if is_relative:
                        relative_imports += 1
                    else:
                        absolute_imports += 1

            # Check if imports are grouped (stdlib, third-party, local)
            if self._check_grouped_imports(imports):
                grouped_imports += 1

            # Check if imports are alphabetized within groups
            if self._check_alphabetized_imports(imports):
                alphabetized += 1

        total = len(py_files)
        if total > 0:
            if grouped_imports / total > 0.5:
                patterns.append(
                    DetectedPattern(
                        category="imports",
                        pattern="Imports grouped by type (stdlib, third-party, local)",
                        confidence=grouped_imports / total,
                        applicable_to=[".py"],
                    )
                )

            if absolute_imports > relative_imports * 3:
                patterns.append(
                    DetectedPattern(
                        category="imports",
                        pattern="Prefers absolute imports over relative",
                        confidence=0.8,
                        applicable_to=[".py"],
                    )
                )

        return patterns

    def _classify_naming_style(self, name: str) -> str:
        """Classify a name's style."""
        if name.startswith("_"):
            name = name.lstrip("_")
        if not name:
            return "other"

        if name.isupper():
            return "constant"
        if "_" in name:
            return "snake"
        if name[0].isupper():
            return "pascal"
        if any(c.isupper() for c in name[1:]):
            return "camel"
        return "snake"

    def _check_grouped_imports(
        self, imports: list[tuple[int, str, bool]]
    ) -> bool:
        """Check if imports appear to be grouped."""
        if len(imports) < 4:
            return False
        # Simple heuristic: look for blank line gaps in line numbers
        lines = sorted(i[0] for i in imports)
        gaps = sum(1 for i in range(1, len(lines)) if lines[i] - lines[i - 1] > 1)
        return gaps >= 1

    def _check_alphabetized_imports(
        self, imports: list[tuple[int, str, bool]]
    ) -> bool:
        """Check if imports are alphabetized."""
        if len(imports) < 3:
            return True
        modules = [i[1].lower() for i in sorted(imports, key=lambda x: x[0])]
        return modules == sorted(modules)

    def summarize_patterns(self, patterns: list[DetectedPattern]) -> str:
        """Generate a summary of detected patterns for LLM context."""
        if not patterns:
            return "No patterns detected."

        lines = ["Detected coding patterns:"]
        by_category: dict[str, list[DetectedPattern]] = {}
        for p in patterns:
            by_category.setdefault(p.category, []).append(p)

        for category, cat_patterns in by_category.items():
            lines.append(f"\n{category.title()}:")
            for p in cat_patterns:
                conf = f"({p.confidence:.0%})" if p.confidence < 1.0 else ""
                lines.append(f"  - {p.pattern} {conf}")

        return "\n".join(lines)
