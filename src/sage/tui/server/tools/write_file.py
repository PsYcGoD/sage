"""Write file tool."""
from __future__ import annotations
from pathlib import Path
from typing import Any

from .base import BaseTool


class WriteFileTool(BaseTool):
    """Write content to a file."""

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write content to a file, creating it if it doesn't exist"

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
                            "description": "Path to the file to write",
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write to the file",
                        },
                    },
                    "required": ["path", "content"],
                },
            },
        }

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Write a file."""
        path_str = input_data.get("path", "")
        content = input_data.get("content", "")

        if not path_str:
            return {"error": "No path provided"}

        try:
            path = Path(path_str)
            created = not path.exists()

            # Create parent directories if needed
            path.parent.mkdir(parents=True, exist_ok=True)

            # Write the file
            path.write_text(content, encoding="utf-8")

            return {
                "path": str(path),
                "bytes": len(content.encode("utf-8")),
                "lines": len(content.splitlines()),
                "created": created,
            }

        except Exception as e:
            return {"error": str(e)}
