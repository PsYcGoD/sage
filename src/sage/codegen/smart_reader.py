"""Smart file reader for SAGE codegen - multi-strategy reading."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class ReadStrategy(Enum):
    """File reading strategies."""

    FULL = "full"  # Read entire file
    RANGE = "range"  # Read specific line range
    CHUNK = "chunk"  # Read in chunks
    SMART = "smart"  # Imports + signatures + relevant sections
    SUMMARY = "summary"  # Just structure/outline


@dataclass
class ReadResult:
    """Result of a file read operation."""

    content: str
    strategy: ReadStrategy
    lines_read: int
    total_lines: int
    truncated: bool = False
    sections: list[tuple[int, int, str]] | None = None  # (start, end, label)


class SmartReader:
    """Multi-strategy file reader optimized for LLM context."""

    # Size thresholds in bytes
    SMALL_FILE = 5_000  # ~150 lines
    MEDIUM_FILE = 20_000  # ~600 lines
    LARGE_FILE = 100_000  # ~3000 lines

    # Line thresholds
    CONTEXT_BUDGET = 500  # Target lines for smart reading
    CHUNK_SIZE = 200  # Lines per chunk

    def __init__(self, root: Path):
        self.root = root

    def read(
        self,
        path: Path,
        strategy: ReadStrategy | str | None = None,
        start_line: int | None = None,
        end_line: int | None = None,
        focus: str | None = None,
    ) -> ReadResult:
        """Read a file with the specified or auto-selected strategy."""
        if isinstance(strategy, str):
            strategy = ReadStrategy(strategy)

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            return ReadResult(
                content=f"Error reading file: {e}",
                strategy=ReadStrategy.FULL,
                lines_read=0,
                total_lines=0,
            )

        lines = content.splitlines()
        total_lines = len(lines)

        # Auto-select strategy if not specified
        if strategy is None:
            strategy = self._select_strategy(path, len(content), total_lines, focus)

        if strategy == ReadStrategy.FULL:
            return ReadResult(
                content=content,
                strategy=strategy,
                lines_read=total_lines,
                total_lines=total_lines,
            )

        if strategy == ReadStrategy.RANGE:
            return self._read_range(lines, start_line or 1, end_line, total_lines)

        if strategy == ReadStrategy.CHUNK:
            return self._read_chunk(lines, start_line or 1, total_lines)

        if strategy == ReadStrategy.SMART:
            return self._read_smart(path, content, lines, focus)

        if strategy == ReadStrategy.SUMMARY:
            return self._read_summary(path, content, lines)

        return ReadResult(
            content=content,
            strategy=ReadStrategy.FULL,
            lines_read=total_lines,
            total_lines=total_lines,
        )

    def _select_strategy(
        self, path: Path, size: int, total_lines: int, focus: str | None
    ) -> ReadStrategy:
        """Auto-select the best reading strategy."""
        # Small files: always full
        if size <= self.SMALL_FILE:
            return ReadStrategy.FULL

        # Python files with focus: smart read
        if path.suffix == ".py" and focus:
            return ReadStrategy.SMART

        # Medium files without focus: full
        if size <= self.MEDIUM_FILE:
            return ReadStrategy.FULL

        # Large Python files: smart
        if path.suffix == ".py":
            return ReadStrategy.SMART

        # Large non-Python: summary
        if size > self.LARGE_FILE:
            return ReadStrategy.SUMMARY

        # Default: chunk
        return ReadStrategy.CHUNK

    def _read_range(
        self, lines: list[str], start: int, end: int | None, total: int
    ) -> ReadResult:
        """Read a specific line range."""
        start = max(1, start) - 1  # Convert to 0-indexed
        end = min(end or total, total)

        selected = lines[start:end]
        content = "\n".join(f"{i+start+1}: {line}" for i, line in enumerate(selected))

        return ReadResult(
            content=content,
            strategy=ReadStrategy.RANGE,
            lines_read=len(selected),
            total_lines=total,
            truncated=end < total,
            sections=[(start + 1, end, "requested range")],
        )

    def _read_chunk(self, lines: list[str], start: int, total: int) -> ReadResult:
        """Read a chunk of the file."""
        start_idx = max(0, start - 1)
        end_idx = min(start_idx + self.CHUNK_SIZE, total)

        selected = lines[start_idx:end_idx]
        content = "\n".join(f"{i+start_idx+1}: {line}" for i, line in enumerate(selected))

        return ReadResult(
            content=content,
            strategy=ReadStrategy.CHUNK,
            lines_read=len(selected),
            total_lines=total,
            truncated=end_idx < total,
            sections=[(start_idx + 1, end_idx, f"chunk {start_idx+1}-{end_idx}")],
        )

    def _read_smart(
        self, path: Path, content: str, lines: list[str], focus: str | None
    ) -> ReadResult:
        """Smart read: imports + signatures + relevant sections."""
        if path.suffix != ".py":
            # Fall back to chunk for non-Python
            return self._read_chunk(lines, 1, len(lines))

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return self._read_chunk(lines, 1, len(lines))

        sections: list[tuple[int, int, str]] = []
        included_lines: set[int] = set()

        # Always include imports (top of file)
        import_end = 0
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                import_end = max(import_end, node.lineno)
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                # Module docstring
                import_end = max(import_end, node.lineno)
            else:
                break

        if import_end > 0:
            sections.append((1, import_end + 1, "imports"))
            for i in range(1, import_end + 2):
                included_lines.add(i)

        # Find focus sections
        if focus:
            focus_lower = focus.lower()
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if focus_lower in node.name.lower():
                        start = node.lineno
                        end = node.end_lineno or start + 10
                        sections.append((start, end, f"match: {node.name}"))
                        for i in range(start, end + 1):
                            included_lines.add(i)

        # Add class/function signatures if not too many
        budget = self.CONTEXT_BUDGET - len(included_lines)
        if budget > 50:
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ClassDef):
                    # Class header + docstring
                    start = node.lineno
                    end = start + 5
                    if node.body and isinstance(node.body[0], ast.Expr):
                        end = max(end, node.body[0].lineno + 2)
                    sections.append((start, end, f"class {node.name}"))
                    for i in range(start, min(end + 1, len(lines) + 1)):
                        included_lines.add(i)

                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Function signature + docstring
                    start = node.lineno
                    end = start + 3
                    sections.append((start, end, f"def {node.name}"))
                    for i in range(start, min(end + 1, len(lines) + 1)):
                        included_lines.add(i)

        # Build content from included lines
        sorted_lines = sorted(included_lines)
        output_lines: list[str] = []
        last_line = 0

        for line_no in sorted_lines:
            if line_no <= 0 or line_no > len(lines):
                continue
            if last_line > 0 and line_no - last_line > 1:
                output_lines.append("...")
            output_lines.append(f"{line_no}: {lines[line_no - 1]}")
            last_line = line_no

        if last_line < len(lines):
            output_lines.append(f"... ({len(lines) - last_line} more lines)")

        return ReadResult(
            content="\n".join(output_lines),
            strategy=ReadStrategy.SMART,
            lines_read=len(included_lines),
            total_lines=len(lines),
            truncated=len(included_lines) < len(lines),
            sections=sections,
        )

    def _read_summary(
        self, path: Path, content: str, lines: list[str]
    ) -> ReadResult:
        """Read just the structure/outline."""
        if path.suffix != ".py":
            # For non-Python, just show first lines and structure
            header = lines[:20]
            return ReadResult(
                content="\n".join(f"{i+1}: {line}" for i, line in enumerate(header))
                + f"\n... ({len(lines) - 20} more lines)",
                strategy=ReadStrategy.SUMMARY,
                lines_read=20,
                total_lines=len(lines),
                truncated=True,
            )

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return self._read_chunk(lines, 1, len(lines))

        outline: list[str] = [f"# File: {path.name} ({len(lines)} lines)"]

        # Module docstring
        docstring = ast.get_docstring(tree)
        if docstring:
            outline.append(f'"""{docstring.split(chr(10))[0]}"""')

        # List all top-level definitions
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                outline.append(f"\nclass {node.name}:")
                class_doc = ast.get_docstring(node)
                if class_doc:
                    outline.append(f'    """{class_doc.split(chr(10))[0]}"""')
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        prefix = "async " if isinstance(item, ast.AsyncFunctionDef) else ""
                        args = ", ".join(a.arg for a in item.args.args[:4])
                        if len(item.args.args) > 4:
                            args += ", ..."
                        outline.append(f"    {prefix}def {item.name}({args}): ...")

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
                args = ", ".join(a.arg for a in node.args.args[:4])
                if len(node.args.args) > 4:
                    args += ", ..."
                outline.append(f"\n{prefix}def {node.name}({args}):")
                func_doc = ast.get_docstring(node)
                if func_doc:
                    outline.append(f'    """{func_doc.split(chr(10))[0]}"""')
                outline.append("    ...")

        return ReadResult(
            content="\n".join(outline),
            strategy=ReadStrategy.SUMMARY,
            lines_read=len(outline),
            total_lines=len(lines),
            truncated=True,
            sections=[],
        )

    def read_multiple(
        self, paths: list[Path], budget: int = 2000, focus: str | None = None
    ) -> dict[Path, ReadResult]:
        """Read multiple files within a line budget."""
        results: dict[Path, ReadResult] = {}
        remaining = budget
        per_file = budget // max(len(paths), 1)

        for path in paths:
            if remaining <= 0:
                break

            # Adjust strategy based on remaining budget
            if per_file < 50:
                strategy = ReadStrategy.SUMMARY
            elif per_file < 200:
                strategy = ReadStrategy.SMART
            else:
                strategy = None  # Auto-select

            result = self.read(path, strategy=strategy, focus=focus)
            results[path] = result
            remaining -= result.lines_read

        return results
