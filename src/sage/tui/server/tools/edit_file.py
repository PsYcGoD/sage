"""Edit file tool."""
from __future__ import annotations
from pathlib import Path
from typing import Any

from .base import BaseTool


class EditFileTool(BaseTool):
    """Edit file by replacing text."""

    @property
    def name(self) -> str:
        return "edit_file"

    @property
    def description(self) -> str:
        return "Edit a file by replacing exact text matches"

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
                            "description": "Path to the file to edit",
                        },
                        "old": {
                            "type": "string",
                            "description": "Exact text to find and replace",
                        },
                        "new": {
                            "type": "string",
                            "description": "New text to replace with",
                        },
                    },
                    "required": ["path", "old", "new"],
                },
            },
        }

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Edit a file."""
        path_str = input_data.get("path", "")
        old_text = input_data.get("old", "")
        new_text = input_data.get("new", "")

        if not path_str:
            return {"error": "No path provided"}

        if not old_text:
            return {"error": "No 'old' text provided"}

        try:
            path = Path(path_str)
            if not path.exists():
                return {"error": f"File not found: {path_str}"}

            if not path.is_file():
                return {"error": f"Not a file: {path_str}"}

            content = path.read_text(encoding="utf-8", errors="replace")

            # Count replacements
            replacements = content.count(old_text)
            if replacements == 0:
                return {
                    "error": f"Text not found in file: {old_text[:50]}...",
                    "replacements": 0,
                }

            # Replace and write back
            new_content = content.replace(old_text, new_text)
            path.write_text(new_content, encoding="utf-8")

            return {
                "path": str(path),
                "replacements": replacements,
                "lines": len(new_content.splitlines()),
            }

        except Exception as e:
            return {"error": str(e)}
