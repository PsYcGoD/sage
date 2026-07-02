"""MCP Server implementation for SAGE."""

from __future__ import annotations

import json
import sys
from typing import Any

from .tools import (
    SAGE_TOOLS,
    sage_run_command,
    sage_explain_error,
    sage_suggest_fix,
    sage_spawn_agent,
    sage_run_workflow,
    sage_get_history,
)


class MCPServer:
    """MCP Protocol server for SAGE."""

    def __init__(self):
        self.tools = {
            "sage_run_command": sage_run_command,
            "sage_explain_error": sage_explain_error,
            "sage_suggest_fix": sage_suggest_fix,
            "sage_spawn_agent": sage_spawn_agent,
            "sage_run_workflow": sage_run_workflow,
            "sage_get_history": sage_get_history,
        }

    def handle_request(self, request: dict) -> dict:
        """Handle MCP protocol request."""
        method = request.get("method")
        
        if method == "tools/list":
            return {
                "tools": SAGE_TOOLS
            }
        
        elif method == "tools/call":
            tool_name = request.get("params", {}).get("name")
            arguments = request.get("params", {}).get("arguments", {})
            
            if tool_name not in self.tools:
                return {"error": f"Tool {tool_name} not found"}
            
            try:
                result = self.tools[tool_name](**arguments)
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }
            except Exception as e:
                return {"error": str(e)}
        
        return {"error": "Unknown method"}

    def run(self):
        """Run MCP server (stdio mode)."""
        print("[SAGE MCP Server] Starting in stdio mode", file=sys.stderr)
        
        for line in sys.stdin:
            try:
                request = json.loads(line)
                response = self.handle_request(request)
                print(json.dumps(response))
                sys.stdout.flush()
            except Exception as e:
                error_response = {"error": str(e)}
                print(json.dumps(error_response))
                sys.stdout.flush()


def main():
    """MCP server entry point."""
    server = MCPServer()
    server.run()


if __name__ == "__main__":
    main()
