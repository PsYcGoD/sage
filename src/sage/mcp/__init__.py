"""MCP server integration for SAGE.

The package keeps imports lazy so ``python -m sage.mcp.server`` starts with a
clean module state. Eagerly importing ``sage.mcp.server`` from here causes
Python's runpy module to emit a RuntimeWarning before the MCP stdio server
starts, which is noisy for strict MCP registry and Glama checks.
"""

from __future__ import annotations

from typing import Any

__all__ = ["MCPServer", "SAGE_TOOLS"]


def __getattr__(name: str) -> Any:
    if name == "MCPServer":
        from .server import MCPServer

        return MCPServer
    if name == "SAGE_TOOLS":
        from .tools import SAGE_TOOLS

        return SAGE_TOOLS
    raise AttributeError(name)
