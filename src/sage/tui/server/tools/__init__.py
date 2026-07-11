"""Tool registry for the chat server."""
from __future__ import annotations
from typing import Any

from .base import BaseTool
from .bash import BashTool
from .read_file import ReadFileTool
from .write_file import WriteFileTool
from .edit_file import EditFileTool
from .glob import GlobTool
from .grep import GrepTool


class ToolRegistry:
    """Registry of available tools."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._register_defaults()

    def _register_defaults(self):
        """Register default tools."""
        for tool in [
            BashTool(),
            ReadFileTool(),
            WriteFileTool(),
            EditFileTool(),
            GlobTool(),
            GrepTool(),
        ]:
            self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def schemas(self) -> list[dict]:
        """Get all tool schemas in OpenAI format."""
        return [t.schema() for t in self._tools.values()]

    async def execute(self, name: str, input_data: dict) -> dict:
        """Execute a tool by name."""
        tool = self._tools.get(name)
        if not tool:
            return {"error": f"Unknown tool: {name}"}
        try:
            return await tool.execute(input_data)
        except Exception as e:
            return {"error": str(e)}


__all__ = ["ToolRegistry", "BaseTool"]
