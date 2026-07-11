"""Glob file search tool."""
from __future__ import annotations
from pathlib import Path
from typing import Any

from .base import BaseTool


class GlobTool(BaseTool):
    """Search for files using glob patterns."""

    @property
    def name(self) -> str:
        return "glob"

    @property
    def description(self) -> str:
        return "Find files matching a glob pattern (e.g., '**/*.py')"

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Glob pattern (e.g., '**/*.py', 'src/**/*.ts')",
                        },
                        "root": {
                            "type": "string",
                            "description": "Root directory to search from (default: '.')",
                        },
                    },
                    "required": ["pattern"],
                },
            },
        }

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute glob search."""
        pattern = input_data.get("pattern", "")
        root = input_data.get("root", ".")

        if not pattern:
            return {"error": "No pattern provided"}

        try:
            root_path = Path(root)
            if not root_path.exists():
                return {"error": f"Root directory not found: {root}"}

            # Find matching files
            matches = list(root_path.glob(pattern))
            
            # Filter to files only, convert to strings
            files = [str(p.resolve()) for p in matches if p.is_file()]
            
            # Sort by name
            files.sort()

            return {
                "files": files,
                "count": len(files),
                "pattern": pattern,
                "root": str(root_path.resolve()),
            }

        except Exception as e:
            return {"error": str(e)}
