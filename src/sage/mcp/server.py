"""MCP Server implementation for SAGE (JSON-RPC 2.0 over stdio)."""

from __future__ import annotations
import logging

import json
import os
import sys
import threading
import time
import uuid
from pathlib import Path
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
DEFAULT_IDLE_TIMEOUT_SECONDS = 300
MIN_IDLE_TIMEOUT_SECONDS = 10


def _verbose_stderr_enabled() -> bool:
    return os.getenv("SAGE_MCP_VERBOSE", "").strip().lower() in {"1", "true", "yes", "on"}


def _mcp_idle_timeout() -> int:
    """Return the MCP stdio idle timeout.

    MCP clients usually restart stdio servers on demand, so idle MCP servers
    should not sit around forever when an AI client crashes or forgets to close
    stdin. MCP clients such as Claude Code often keep a stdio server open
    between tool calls, so the default must be long enough not to look like a
    flaky server while still cleaning truly abandoned processes. Set
    SAGE_MCP_IDLE_TIMEOUT_SECONDS for stricter or longer local policy.
    """
    raw = os.getenv("SAGE_MCP_IDLE_TIMEOUT_SECONDS", "").strip()
    if not raw:
        return DEFAULT_IDLE_TIMEOUT_SECONDS
    try:
        timeout = int(raw)
    except ValueError:
        return DEFAULT_IDLE_TIMEOUT_SECONDS
    return max(MIN_IDLE_TIMEOUT_SECONDS, timeout)


def _session_dir() -> Path:
    base = os.getenv("SAGE_DATA_DIR")
    if base:
        root = Path(base)
    elif os.name == "nt" and os.getenv("LOCALAPPDATA"):
        root = Path(os.environ["LOCALAPPDATA"]) / "SAGE"
    else:
        root = Path.home() / ".sage"
    return root / "mcp-sessions"

def command_tools_enabled() -> bool:
    """Return whether MCP clients may execute local commands through SAGE."""
    return os.getenv("SAGE_MCP_ENABLE_COMMANDS", "").strip().lower() in {"1", "true", "yes", "on"}

class MCPServer:
    """MCP protocol server exposing SAGE tools to MCP clients like Claude Code."""

    def __init__(self):
        self.command_tools_enabled = command_tools_enabled()
        self.idle_timeout = _mcp_idle_timeout()
        self._last_activity = time.monotonic()
        self._started_at = time.time()
        self._running = True
        self._session_id = f"{os.getpid()}-{uuid.uuid4().hex[:8]}"
        self._session_file = _session_dir() / f"{self._session_id}.json"
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

    def _touch_activity(self) -> None:
        self._last_activity = time.monotonic()
        self._write_session()

    def _write_session(self) -> None:
        """Write a small session heartbeat for diagnostics and stale cleanup."""
        try:
            self._session_file.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "pid": os.getpid(),
                "session_id": self._session_id,
                "cwd": os.getcwd(),
                "started_at": self._started_at,
                "last_activity": time.time(),
                "idle_timeout_seconds": self.idle_timeout,
            }
            tmp = self._session_file.with_suffix(f".{uuid.uuid4().hex}.tmp")
            tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            tmp.replace(self._session_file)
        except Exception:
            log.debug("suppressed", exc_info=True)

    def _remove_session(self) -> None:
        try:
            self._session_file.unlink(missing_ok=True)
        except Exception:
            log.debug("suppressed", exc_info=True)

    def _cleanup_session_records(self) -> None:
        """Remove old MCP heartbeat files.

        This intentionally does not kill arbitrary PIDs from old files because
        PIDs can be reused. Live processes now self-exit via the idle watchdog;
        this cleanup keeps diagnostics from filling with stale session records.
        """
        cutoff = time.time() - max(self.idle_timeout * 4, 300)
        try:
            directory = _session_dir()
            if not directory.exists():
                return
            for path in directory.glob("*.json"):
                try:
                    stat = path.stat()
                    if stat.st_mtime < cutoff:
                        path.unlink(missing_ok=True)
                except Exception:
                    log.debug("suppressed", exc_info=True)
        except Exception:
            log.debug("suppressed", exc_info=True)

    def _start_idle_watchdog(self) -> None:
        thread = threading.Thread(target=self._idle_watchdog, name="sage-mcp-idle-watchdog", daemon=True)
        thread.start()

    def _idle_watchdog(self) -> None:
        while self._running:
            time.sleep(1)
            if time.monotonic() - self._last_activity < self.idle_timeout:
                continue
            if _verbose_stderr_enabled():
                print(
                    f"[SAGE MCP Server] idle for {self.idle_timeout}s; exiting",
                    file=sys.stderr,
                    flush=True,
                )
            self._running = False
            self._remove_session()
            os._exit(0)

    def handle_request(self, request: dict) -> Optional[dict]:
        """Handle one JSON-RPC request. Returns None for notifications."""
        self._touch_activity()
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
        self._cleanup_session_records()
        self._write_session()
        self._start_idle_watchdog()
        if _verbose_stderr_enabled():
            print(
                f"[SAGE MCP Server] stdio ready (idle timeout {self.idle_timeout}s)",
                file=sys.stderr,
                flush=True,
            )

        try:
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
        finally:
            self._running = False
            self._remove_session()

def main():
    """MCP server entry point."""
    server = MCPServer()
    server.run()

if __name__ == "__main__":
    main()
