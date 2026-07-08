"""MCP Server implementation for SAGE (JSON-RPC 2.0 over stdio)."""

from __future__ import annotations
import logging

import json
import os
import sys
from typing import Any, Optional

from .tools import (

    SAGE_TOOLS,
    sage_run_command,
    sage_explain_error,
    sage_suggest_fix,
    sage_spawn_agent,
    sage_run_workflow,
    sage_get_history,
    sage_read_file,
    sage_grep,
    sage_call,
    sage_show_raw,
    sage_write_file,
    sage_edit_file,
    sage_glob,
    sage_tree,
    sage_agentic_run,
    sage_agentic_fix,
    sage_agentic_session,
)


log = logging.getLogger(__name__)

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "sage", "version": "2.0.4"}
COMMAND_TOOL_NAMES = {"sage_run_command"}

def command_tools_enabled() -> bool:
    """Return whether MCP clients may execute local commands through SAGE."""
    return os.getenv("SAGE_MCP_ENABLE_COMMANDS", "").strip().lower() in {"1", "true", "yes", "on"}

class MCPServer:
    """MCP protocol server exposing SAGE tools to MCP clients like Claude Code."""

    def __init__(self):
        self.command_tools_enabled = command_tools_enabled()
        self.tools = {
            "sage_explain_error": sage_explain_error,
            "sage_suggest_fix": sage_suggest_fix,
            "sage_spawn_agent": sage_spawn_agent,
            "sage_run_workflow": sage_run_workflow,
            "sage_get_history": sage_get_history,
            "sage_read_file": sage_read_file,
            "sage_grep": sage_grep,
            "sage_call": sage_call,
            "sage_show_raw": sage_show_raw,
            "sage_write_file": sage_write_file,
            "sage_edit_file": sage_edit_file,
            "sage_glob": sage_glob,
            "sage_tree": sage_tree,
            "sage_agentic_run": sage_agentic_run,
            "sage_agentic_fix": sage_agentic_fix,
            "sage_agentic_session": sage_agentic_session,
        }
        if self.command_tools_enabled:
            self.tools["sage_run_command"] = sage_run_command

    def handle_request(self, request: dict) -> Optional[dict]:
        """Handle one JSON-RPC request. Returns None for notifications."""
        method = request.get("method")
        request_id = request.get("id")
        is_notification = "id" not in request

        try:
            if method == "initialize":
                params = request.get("params") or {}
                result = {
                    "protocolVersion": params.get("protocolVersion") or PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": SERVER_INFO,
                }
            elif method in ("notifications/initialized", "notifications/cancelled"):
                return None
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": self._tool_specs()}
            elif method == "tools/call":
                result = self._call_tool(request.get("params") or {})
            else:
                if is_notification:
                    return None
                return self._error(request_id, -32601, f"Method not found: {method}")
        except Exception as exc:
            if is_notification:
                return None
            return self._error(request_id, -32603, str(exc))

        if is_notification:
            return None
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def _call_tool(self, params: dict) -> dict:
        """Execute a SAGE tool and wrap the result as MCP content."""
        name = params.get("name")
        arguments = params.get("arguments") or {}

        if name not in self.tools:
            if name in COMMAND_TOOL_NAMES and not self.command_tools_enabled:
                return {
                    "content": [{
                        "type": "text",
                        "text": (
                            "Tool 'sage_run_command' is disabled by default. "
                            "Set SAGE_MCP_ENABLE_COMMANDS=1 only for trusted local MCP clients."
                        ),
                    }],
                    "isError": True,
                }
            return {
                "content": [{"type": "text", "text": f"Tool '{name}' not found."}],
                "isError": True,
            }

        try:
            output = self.tools[name](**arguments)
            return {
                "content": [
                    {"type": "text", "text": json.dumps(output, indent=2, default=str)}
                ],
                "isError": False,
            }
        except Exception as exc:
            return {
                "content": [{"type": "text", "text": f"Tool '{name}' failed: {exc}"}],
                "isError": True,
            }

    def _tool_specs(self) -> list[dict]:
        """Return the MCP tool specs that are enabled for this process."""
        enabled = set(self.tools)
        return [tool for tool in SAGE_TOOLS if tool.get("name") in enabled]

    @staticmethod
    def _error(request_id: Any, code: int, message: str) -> dict:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }

    def run(self):
        """Run MCP server (stdio mode)."""
        # MCP messages must be clean UTF-8 JSON lines on stdout.
        try:
            sys.stdout.reconfigure(encoding="utf-8", newline="\n")
            sys.stdin.reconfigure(encoding="utf-8")
        except Exception:
            log.debug("suppressed", exc_info=True)
        print("[SAGE MCP Server] stdio ready", file=sys.stderr)

        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
            except json.JSONDecodeError:
                continue

            response = self.handle_request(request)
            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

def main():
    """MCP server entry point."""
    server = MCPServer()
    server.run()

if __name__ == "__main__":
    main()
