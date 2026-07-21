"""Validate tool - deep AST, security, quality validation."""
from __future__ import annotations

from pathlib import Path

from .base import BaseTool


class ValidateTool(BaseTool):
    """Deep code validation tool."""

    @property
    def name(self) -> str:
        return "sage_validate"

    @property
    def description(self) -> str:
        return "Deep validation: AST errors, security issues (hardcoded secrets), code quality (TODO/debug code)"

    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self._parameters(),
            },
        }

    def _parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to validate"},
                "content": {"type": "string", "description": "Optional content to validate instead of reading file"},
            },
            "required": ["path"],
        }

    async def execute(self, input_data: dict) -> dict:
        path = Path(input_data.get("path", ""))
        content = input_data.get("content")

        if content is None:
            if not path.exists():
                return {"error": f"File not found: {path}"}
            content = path.read_text(encoding="utf-8", errors="replace")

        try:
            from sage.codegen import create_default_registry

            registry = create_default_registry()
            result = registry.validate(path, content)

            return {
                "success": True,
                "valid": result.valid,
                "summary": result.summary(),
                "issues": [
                    {
                        "line": i.line,
                        "severity": i.severity,
                        "category": i.category,
                        "message": i.message,
                        "suggestion": i.suggestion,
                    }
                    for i in result.issues[:15]
                ],
            }
        except Exception as e:
            return {"error": f"Validation failed: {e}"}
