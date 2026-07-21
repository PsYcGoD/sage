"""AST-based Python code validator."""

from __future__ import annotations

import ast
from pathlib import Path

from .base import ValidationIssue


class ASTValidator:
    """Python-specific AST validation for code quality issues."""

    def can_validate(self, path: Path) -> bool:
        return path.suffix.lower() in (".py", ".pyi")

    def validate(self, path: Path, content: str) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return issues  # Syntax errors handled by py_compile elsewhere

        for node in ast.walk(tree):
            # Empty functions
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                issue = self._check_empty_function(path, node)
                if issue:
                    issues.append(issue)

                # Missing return in non-void functions
                issue = self._check_missing_return(path, node, content)
                if issue:
                    issues.append(issue)

            # Bare except clauses
            if isinstance(node, ast.ExceptHandler):
                issue = self._check_bare_except(path, node)
                if issue:
                    issues.append(issue)

            # Mutable default arguments
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                issues.extend(self._check_mutable_defaults(path, node))

            # Assert in non-test files
            if isinstance(node, ast.Assert) and "test" not in str(path).lower():
                issues.append(
                    ValidationIssue(
                        file=str(path),
                        line=node.lineno,
                        severity="warning",
                        category="assert_in_production",
                        message="Assert statement in non-test code may be disabled with -O",
                        suggestion="Use explicit if/raise for production checks",
                    )
                )

        return issues

    def _check_empty_function(
        self, path: Path, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> ValidationIssue | None:
        """Check if function body is effectively empty."""
        body = node.body
        if not body:
            return ValidationIssue(
                file=str(path),
                line=node.lineno,
                severity="warning",
                category="empty_function",
                message=f"Function '{node.name}' has no body",
                suggestion="Add implementation or use 'pass' with a TODO comment",
            )

        # Check for just pass or just docstring or just ...
        if len(body) == 1:
            stmt = body[0]
            if isinstance(stmt, ast.Pass):
                return ValidationIssue(
                    file=str(path),
                    line=node.lineno,
                    severity="warning",
                    category="empty_function",
                    message=f"Function '{node.name}' contains only 'pass'",
                    suggestion="Add implementation or document why it's empty",
                )
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                if stmt.value.value is ...:
                    return ValidationIssue(
                        file=str(path),
                        line=node.lineno,
                        severity="warning",
                        category="empty_function",
                        message=f"Function '{node.name}' contains only '...'",
                        suggestion="Add implementation - this is a stub",
                    )

        # Check for docstring + pass only
        if len(body) == 2:
            first, second = body
            has_docstring = isinstance(first, ast.Expr) and isinstance(
                first.value, ast.Constant
            )
            has_pass = isinstance(second, ast.Pass)
            if has_docstring and has_pass:
                return ValidationIssue(
                    file=str(path),
                    line=node.lineno,
                    severity="info",
                    category="stub_function",
                    message=f"Function '{node.name}' is a documented stub",
                    suggestion=None,
                )

        return None

    def _check_bare_except(
        self, path: Path, node: ast.ExceptHandler
    ) -> ValidationIssue | None:
        """Check for bare except: clauses."""
        if node.type is None:
            return ValidationIssue(
                file=str(path),
                line=node.lineno,
                severity="warning",
                category="bare_except",
                message="Bare 'except:' catches all exceptions including KeyboardInterrupt and SystemExit",
                suggestion="Use 'except Exception:' to catch only standard exceptions",
            )
        return None

    def _check_mutable_defaults(
        self, path: Path, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> list[ValidationIssue]:
        """Check for mutable default arguments."""
        issues = []
        defaults = node.args.defaults + node.args.kw_defaults
        for default in defaults:
            if default is None:
                continue
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                issues.append(
                    ValidationIssue(
                        file=str(path),
                        line=default.lineno,
                        severity="warning",
                        category="mutable_default",
                        message=f"Mutable default argument in function '{node.name}'",
                        suggestion="Use None as default and initialize inside the function",
                    )
                )
        return issues

    def _check_missing_return(
        self, path: Path, node: ast.FunctionDef | ast.AsyncFunctionDef, content: str
    ) -> ValidationIssue | None:
        """Check for functions that should return but don't."""
        # Skip __init__, __del__, etc.
        if node.name.startswith("__") and node.name.endswith("__"):
            return None

        # Skip if has type annotation showing None/void
        if node.returns:
            if isinstance(node.returns, ast.Constant) and node.returns.value is None:
                return None
            if isinstance(node.returns, ast.Name) and node.returns.id == "None":
                return None

        # Check if function has any return statement with a value
        has_return_value = False
        has_return_none = False

        for child in ast.walk(node):
            if isinstance(child, ast.Return):
                if child.value is not None:
                    has_return_value = True
                else:
                    has_return_none = True

        # If some paths return values and others don't, that's suspicious
        if has_return_value and has_return_none:
            return ValidationIssue(
                file=str(path),
                line=node.lineno,
                severity="warning",
                category="inconsistent_return",
                message=f"Function '{node.name}' has inconsistent return statements",
                suggestion="Ensure all code paths return a value or None explicitly",
            )

        return None
