"""Style enforcement for SAGE codegen - indent, quotes, line-length rules."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class StyleRule:
    """A detected or configured style rule."""

    name: str
    category: str  # "indent", "quotes", "line_length", "spacing", "imports"
    value: Any
    confidence: float = 1.0
    source: str = "default"  # "detected", "config", "default"


@dataclass
class StyleViolation:
    """A style violation found in code."""

    file: str
    line: int
    rule: str
    expected: str
    found: str


@dataclass
class StyleProfile:
    """Complete style profile for a project."""

    indent_type: str = "spaces"  # "spaces" or "tabs"
    indent_size: int = 4
    quote_style: str = "double"  # "single" or "double"
    max_line_length: int = 88
    trailing_comma: bool = True
    trailing_newline: bool = True
    rules: list[StyleRule] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "indent_type": self.indent_type,
            "indent_size": self.indent_size,
            "quote_style": self.quote_style,
            "max_line_length": self.max_line_length,
            "trailing_comma": self.trailing_comma,
            "trailing_newline": self.trailing_newline,
        }


class StyleEnforcer:
    """Detect and enforce code style rules."""

    def __init__(self, root: Path):
        self.root = root
        self._profile: StyleProfile | None = None

    def get_profile(self) -> StyleProfile:
        """Get style profile (detected or from config)."""
        if self._profile is None:
            # Try to load from config first
            self._profile = self._load_config() or self._detect_style()
        return self._profile

    def _load_config(self) -> StyleProfile | None:
        """Load style from project config files."""
        profile = StyleProfile()
        found_config = False

        # Try pyproject.toml
        pyproject = self.root / "pyproject.toml"
        if pyproject.exists():
            try:
                import tomllib

                content = pyproject.read_text(encoding="utf-8")
                data = tomllib.loads(content)

                # Black config
                if black := data.get("tool", {}).get("black", {}):
                    if "line-length" in black:
                        profile.max_line_length = black["line-length"]
                        found_config = True

                # Ruff config
                if ruff := data.get("tool", {}).get("ruff", {}):
                    if "line-length" in ruff:
                        profile.max_line_length = ruff["line-length"]
                        found_config = True
                    if "indent-width" in ruff:
                        profile.indent_size = ruff["indent-width"]
                        found_config = True

            except Exception:
                pass

        # Try .editorconfig
        editorconfig = self.root / ".editorconfig"
        if editorconfig.exists():
            try:
                content = editorconfig.read_text(encoding="utf-8")
                # Simple parsing
                if "indent_style = tab" in content:
                    profile.indent_type = "tabs"
                    found_config = True
                if match := re.search(r"indent_size\s*=\s*(\d+)", content):
                    profile.indent_size = int(match.group(1))
                    found_config = True
                if match := re.search(r"max_line_length\s*=\s*(\d+)", content):
                    profile.max_line_length = int(match.group(1))
                    found_config = True
            except Exception:
                pass

        return profile if found_config else None

    def _detect_style(self, sample_size: int = 10) -> StyleProfile:
        """Auto-detect style from existing code."""
        profile = StyleProfile()
        py_files = list(self.root.rglob("*.py"))[:sample_size]

        indent_spaces = 0
        indent_tabs = 0
        indent_sizes: list[int] = []
        single_quotes = 0
        double_quotes = 0
        trailing_commas = 0
        no_trailing_commas = 0

        for py_file in py_files:
            try:
                content = py_file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            for line in content.splitlines():
                # Detect indentation
                if line and not line[0].isspace():
                    continue
                indent_match = re.match(r"^(\s+)\S", line)
                if indent_match:
                    indent = indent_match.group(1)
                    if "\t" in indent:
                        indent_tabs += 1
                    else:
                        indent_spaces += 1
                        # Detect indent size
                        if indent and indent[0] == " ":
                            size = len(indent)
                            if size <= 8:
                                indent_sizes.append(size)

            # Detect quote style (simple heuristic)
            # Count string literals
            single_quotes += len(re.findall(r"'[^']*'", content))
            double_quotes += len(re.findall(r'"[^"]*"', content))

            # Detect trailing commas in multi-line structures
            trailing_commas += len(re.findall(r",\s*\n\s*[\)\]\}]", content))
            no_trailing_commas += len(re.findall(r"[^\s,]\s*\n\s*[\)\]\}]", content))

        # Set profile based on detection
        if indent_tabs > indent_spaces:
            profile.indent_type = "tabs"
            profile.indent_size = 1
        else:
            profile.indent_type = "spaces"
            if indent_sizes:
                # Find most common indent that's 2 or 4
                from collections import Counter
                size_counts = Counter(indent_sizes)
                for preferred in [4, 2]:
                    if preferred in size_counts:
                        profile.indent_size = preferred
                        break

        profile.quote_style = "single" if single_quotes > double_quotes else "double"
        profile.trailing_comma = trailing_commas > no_trailing_commas

        return profile

    def check_file(self, path: Path, content: str | None = None) -> list[StyleViolation]:
        """Check a file against style rules."""
        violations: list[StyleViolation] = []
        profile = self.get_profile()

        if content is None:
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return violations

        lines = content.splitlines()

        for i, line in enumerate(lines, 1):
            # Check line length
            if len(line) > profile.max_line_length:
                violations.append(
                    StyleViolation(
                        file=str(path),
                        line=i,
                        rule="line_length",
                        expected=f"<= {profile.max_line_length} chars",
                        found=f"{len(line)} chars",
                    )
                )

            # Check indentation
            indent_match = re.match(r"^(\s+)", line)
            if indent_match:
                indent = indent_match.group(1)
                if profile.indent_type == "spaces" and "\t" in indent:
                    violations.append(
                        StyleViolation(
                            file=str(path),
                            line=i,
                            rule="indent_type",
                            expected="spaces",
                            found="tabs",
                        )
                    )
                elif profile.indent_type == "tabs" and " " in indent:
                    violations.append(
                        StyleViolation(
                            file=str(path),
                            line=i,
                            rule="indent_type",
                            expected="tabs",
                            found="spaces",
                        )
                    )

        # Check trailing newline
        if profile.trailing_newline and content and not content.endswith("\n"):
            violations.append(
                StyleViolation(
                    file=str(path),
                    line=len(lines),
                    rule="trailing_newline",
                    expected="newline at end of file",
                    found="no trailing newline",
                )
            )

        return violations

    def fix_content(self, content: str, path: Path | None = None) -> str:
        """Fix style violations in content."""
        profile = self.get_profile()
        lines = content.splitlines()
        fixed_lines: list[str] = []

        for line in lines:
            # Fix indentation
            indent_match = re.match(r"^(\s+)", line)
            if indent_match:
                indent = indent_match.group(1)
                rest = line[len(indent):]

                if profile.indent_type == "spaces" and "\t" in indent:
                    # Convert tabs to spaces
                    indent = indent.replace("\t", " " * profile.indent_size)
                elif profile.indent_type == "tabs" and " " in indent:
                    # Convert spaces to tabs (approximate)
                    num_spaces = len(indent)
                    num_tabs = num_spaces // profile.indent_size
                    indent = "\t" * num_tabs

                line = indent + rest

            fixed_lines.append(line)

        result = "\n".join(fixed_lines)

        # Ensure trailing newline
        if profile.trailing_newline and result and not result.endswith("\n"):
            result += "\n"

        return result

    def summarize_style(self) -> str:
        """Generate a summary of style rules for LLM context."""
        profile = self.get_profile()
        return (
            f"Code style: {profile.indent_type} ({profile.indent_size}), "
            f"{profile.quote_style} quotes, max {profile.max_line_length} chars/line"
        )
