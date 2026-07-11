"""Read file tool."""
from __future__ import annotations
from pathlib import Path
from typing import Any

from .base import BaseTool


class ReadFileTool(BaseTool):
    """Read file content."""

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read the contents of a file"

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file to read",
                        },
                        "lines": {
                            "type": "string",
                            "description": "Optional line range in format 'start:end' (e.g., '10:20')",
                        },
                    },
                    "required": ["path"],
                },
            },
        }

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Read a file."""
        path_str = input_data.get("path", "")
        lines_spec = input_data.get("lines")

        if not path_str:
            return {"error": "No path provided"}

        try:
            path = Path(path_str)
            if not path.exists():
                return {"error": f"File not found: {path_str}"}

            if not path.is_file():
                return {"error": f"Not a file: {path_str}"}

            content = path.read_text(encoding="utf-8", errors="replace")
            lines_list = content.splitlines()

            # Handle line range if specified
            if lines_spec:
                try:
                    start, end = map(int, lines_spec.split(":"))
                    lines_list = lines_list[start - 1 : end]
                    content = "\n".join(lines_list)
                except (ValueError, IndexError) as e:
                    return {"error": f"Invalid line range: {lines_spec}"}

            # Detect language from extension
            language = path.suffix.lstrip(".") or "text"

            return {
                "content": content,
                "lines": len(lines_list),
                "language": language,
                "path": str(path),
            }

        except Exception as e:
            return {"error": str(e)}
