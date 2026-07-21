"""Context builder for SAGE codegen - import/class/function analysis."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ImportInfo:
    """Information about an import statement."""

    module: str
    names: list[str]  # Imported names (empty for `import x`)
    alias: str | None = None
    is_relative: bool = False
    level: int = 0  # For relative imports
    line: int = 0


@dataclass
class FunctionInfo:
    """Information about a function/method."""

    name: str
    line: int
    end_line: int
    args: list[str]
    return_type: str | None = None
    decorators: list[str] = field(default_factory=list)
    docstring: str | None = None
    is_async: bool = False
    is_method: bool = False


@dataclass
class ClassInfo:
    """Information about a class."""

    name: str
    line: int
    end_line: int
    bases: list[str]
    methods: list[FunctionInfo] = field(default_factory=list)
    docstring: str | None = None
    decorators: list[str] = field(default_factory=list)


@dataclass
class FileContext:
    """Complete context for a single file."""

    path: Path
    imports: list[ImportInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)  # Top-level only
    constants: list[tuple[str, int]] = field(default_factory=list)  # (name, line)
    docstring: str | None = None

    def get_public_api(self) -> list[str]:
        """Get public API names (no leading underscore)."""
        names: list[str] = []
        for f in self.functions:
            if not f.name.startswith("_"):
                names.append(f.name)
        for c in self.classes:
            if not c.name.startswith("_"):
                names.append(c.name)
        for name, _ in self.constants:
            if not name.startswith("_") and name.isupper():
                names.append(name)
        return names


class ContextBuilder:
    """Build rich context from source files."""

    def __init__(self, root: Path):
        self.root = root
        self._cache: dict[str, FileContext] = {}

    def build_file_context(self, path: Path, content: str | None = None) -> FileContext:
        """Build context for a single file."""
        cache_key = str(path)
        if cache_key in self._cache and content is None:
            return self._cache[cache_key]

        if content is None:
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return FileContext(path=path)

        ctx = FileContext(path=path)

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return ctx

        # Module docstring
        ctx.docstring = ast.get_docstring(tree)

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    ctx.imports.append(
                        ImportInfo(
                            module=alias.name,
                            names=[],
                            alias=alias.asname,
                            line=node.lineno,
                        )
                    )

            elif isinstance(node, ast.ImportFrom):
                ctx.imports.append(
                    ImportInfo(
                        module=node.module or "",
                        names=[a.name for a in node.names],
                        is_relative=node.level > 0,
                        level=node.level,
                        line=node.lineno,
                    )
                )

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                ctx.functions.append(self._extract_function_info(node))

            elif isinstance(node, ast.ClassDef):
                ctx.classes.append(self._extract_class_info(node))

            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        ctx.constants.append((target.id, node.lineno))

            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name) and node.target.id.isupper():
                    ctx.constants.append((node.target.id, node.lineno))

        self._cache[cache_key] = ctx
        return ctx

    def _extract_function_info(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_method: bool = False
    ) -> FunctionInfo:
        """Extract function information from AST node."""
        args: list[str] = []
        for arg in node.args.args:
            args.append(arg.arg)

        return_type = None
        if node.returns:
            return_type = ast.unparse(node.returns)

        decorators = [ast.unparse(d) for d in node.decorator_list]

        return FunctionInfo(
            name=node.name,
            line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            args=args,
            return_type=return_type,
            decorators=decorators,
            docstring=ast.get_docstring(node),
            is_async=isinstance(node, ast.AsyncFunctionDef),
            is_method=is_method,
        )

    def _extract_class_info(self, node: ast.ClassDef) -> ClassInfo:
        """Extract class information from AST node."""
        bases = [ast.unparse(b) for b in node.bases]
        methods: list[FunctionInfo] = []

        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(self._extract_function_info(item, is_method=True))

        decorators = [ast.unparse(d) for d in node.decorator_list]

        return ClassInfo(
            name=node.name,
            line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            bases=bases,
            methods=methods,
            docstring=ast.get_docstring(node),
            decorators=decorators,
        )

    def find_related_files(self, path: Path) -> list[Path]:
        """Find files related to the given file (tests, same dir, importers)."""
        related: list[Path] = []
        name = path.stem

        # Find test file
        test_patterns = [
            f"test_{name}.py",
            f"{name}_test.py",
            f"tests/test_{name}.py",
            f"tests/{name}_test.py",
        ]
        for pattern in test_patterns:
            test_path = self.root / pattern
            if test_path.exists():
                related.append(test_path)

        # Find __init__.py in same directory
        init_path = path.parent / "__init__.py"
        if init_path.exists() and init_path != path:
            related.append(init_path)

        # Find files in same directory
        if path.parent.exists():
            for sibling in path.parent.glob("*.py"):
                if sibling != path and sibling not in related:
                    related.append(sibling)
                    if len(related) >= 10:
                        break

        return related[:10]

    def build_import_graph(self, paths: list[Path] | None = None) -> dict[str, list[str]]:
        """Build a graph of imports between files."""
        if paths is None:
            paths = list(self.root.rglob("*.py"))[:50]

        graph: dict[str, list[str]] = {}

        for path in paths:
            ctx = self.build_file_context(path)
            deps: list[str] = []

            for imp in ctx.imports:
                if imp.is_relative:
                    deps.append(f".{imp.module}")
                else:
                    deps.append(imp.module)

            graph[str(path.relative_to(self.root))] = deps

        return graph

    def summarize_file(self, path: Path, content: str | None = None) -> str:
        """Generate a summary of a file for LLM context."""
        ctx = self.build_file_context(path, content)
        lines: list[str] = [f"File: {path.name}"]

        if ctx.docstring:
            lines.append(f"Description: {ctx.docstring.split(chr(10))[0]}")

        if ctx.imports:
            main_imports = [i.module for i in ctx.imports if not i.is_relative][:5]
            if main_imports:
                lines.append(f"Imports: {', '.join(main_imports)}")

        if ctx.classes:
            class_names = [c.name for c in ctx.classes]
            lines.append(f"Classes: {', '.join(class_names)}")
            for c in ctx.classes:
                method_names = [m.name for m in c.methods if not m.name.startswith("_")]
                if method_names:
                    lines.append(f"  {c.name} methods: {', '.join(method_names[:5])}")

        if ctx.functions:
            func_names = [f.name for f in ctx.functions if not f.name.startswith("_")]
            if func_names:
                lines.append(f"Functions: {', '.join(func_names[:10])}")

        return "\n".join(lines)

    def get_symbol_location(self, symbol: str, paths: list[Path] | None = None) -> tuple[Path, int] | None:
        """Find where a symbol is defined."""
        if paths is None:
            paths = list(self.root.rglob("*.py"))[:100]

        for path in paths:
            ctx = self.build_file_context(path)

            for func in ctx.functions:
                if func.name == symbol:
                    return path, func.line

            for cls in ctx.classes:
                if cls.name == symbol:
                    return path, cls.line
                for method in cls.methods:
                    if method.name == symbol:
                        return path, method.line

            for name, line in ctx.constants:
                if name == symbol:
                    return path, line

        return None
