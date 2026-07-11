"""Grep content search tool."""
from __future__ import annotations
import re
from pathlib import Path
from typing import Any

from .base import BaseTool


class GrepTool(BaseTool):
    """Search file contents using regex."""

    @property
    def name(self) -> str:
        return "grep"

    @property
    def description(self) -> str:
        return "Search for text patterns in files using regex"

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
                            "description": "Regex pattern to search for",
                        },
                        "paths": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of paths to search (files or directories)",
                        },
                        "glob_filter": {
                            "type": "string",
                            "description": "Optional glob pattern to filter files (e.g., '*.py')",
                        },
                        "ignore_case": {
                            "type": "boolean",
                            "description": "Case-insensitive search",
                        },
                    },
                    "required": ["pattern"],
                },
            },
        }

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute grep search."""
        pattern_str = input_data.get("pattern", "")
        paths = input_data.get("paths", ["."])
        glob_filter = input_data.get("glob_filter", "*")
        ignore_case = input_data.get("ignore_case", False)

        if not pattern_str:
            return {"error": "No pattern provided"}

        try:
            # Compile regex
            flags = re.IGNORECASE if ignore_case else 0
            pattern = re.compile(pattern_str, flags)

            matches = []

            # Search each path
            for path_str in paths:
                path = Path(path_str)

                if not path.exists():
                    continue

                # Get files to search
                if path.is_file():
                    files = [path]
                else:
                    # Directory - glob for files
                    files = list(path.rglob(glob_filter))
                    files = [f for f in files if f.is_file()]

                # Search each file
                for file_path in files:
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="replace")
                        for line_num, line in enumerate(content.splitlines(), start=1):
                            if pattern.search(line):
                                matches.append({
                                    "file": str(file_path),
                                    "line": line_num,
                                    "text": line.strip(),
                                })
                    except Exception:
                        # Skip files that can't be read
                        continue

            return {
                "matches": matches,
                "count": len(matches),
                "pattern": pattern_str,
            }

        except re.error as e:
            return {"error": f"Invalid regex pattern: {str(e)}"}
        except Exception as e:
            return {"error": str(e)}
