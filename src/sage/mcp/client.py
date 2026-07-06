from __future__ import annotations
"""Minimal real MCP client for connecting SAGE to external MCP servers.

Supports two transports:

- stdio: launch a command (e.g. ``npx -y @modelcontextprotocol/server-filesystem``)
  and speak JSON-RPC 2.0 over its stdin/stdout.
- http:  POST JSON-RPC to an HTTP(S) endpoint (streamable-http / JSON-RPC).

``connect_and_list`` performs the real ``initialize`` handshake and a
``tools/list`` call, returning the discovered tools so the caller can prove
the connection is live — no mocking, no placeholders.
"""

import logging

import json
import queue
import shlex
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)

PROTOCOL_VERSION = "2024-11-05"
CLIENT_INFO = {"name": "psycgod-sage", "version": "2.0.0"}

@dataclass
class MCPConnectionResult:
    ok: bool
    transport: str
    target: str
    server_name: str = ""
    server_version: str = ""
    tools: list[dict[str, Any]] = field(default_factory=list)
    error: str = ""

    @property
    def tool_names(self) -> list[str]:
        return [str(tool.get("name", "")) for tool in self.tools]

def detect_transport(target: str) -> str:
    """Infer transport from the target string."""
    stripped = target.strip()
    if stripped.startswith(("http://", "https://")):
        return "http"
    return "stdio"

def connect_and_list(target: str, *, timeout: float = 25.0) -> MCPConnectionResult:
    """Connect to an MCP server and list its tools. Never raises."""
    transport = detect_transport(target)
    if timeout <= 0:
        timeout = 25.0
    try:
        if transport == "http":
            return _connect_http(target, timeout=timeout)
        return _connect_stdio(target, timeout=timeout)
    except Exception as exc:  # pragma: no cover - defensive
        return MCPConnectionResult(ok=False, transport=transport, target=target, error=_friendly_error(exc))

def _rpc(method: str, request_id: int | None, params: dict | None = None) -> dict:
    message: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
    if request_id is not None:
        message["id"] = request_id
    if params is not None:
        message["params"] = params
    return message

def _initialize_params() -> dict:
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {},
        "clientInfo": CLIENT_INFO,
    }

def _connect_stdio(command: str, *, timeout: float) -> MCPConnectionResult:
    argv = shlex.split(command, posix=(sys.platform != "win32"))
    if not argv:
        return MCPConnectionResult(ok=False, transport="stdio", target=command, error="empty command")

    creationflags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
    try:
        proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=creationflags,
        )
    except FileNotFoundError:
        return MCPConnectionResult(
            ok=False,
            transport="stdio",
            target=command,
            error=f"Command not found: {argv[0]}. Install that MCP server or check the command path.",
        )

    stdout_queue: queue.Queue[str | None] = queue.Queue()

    def pump_stdout() -> None:
        try:
            assert proc.stdout is not None
            for line in iter(proc.stdout.readline, ""):
                stdout_queue.put(line)
        finally:
            stdout_queue.put(None)

    stdout_thread = threading.Thread(target=pump_stdout, daemon=True)
    stdout_thread.start()

    def send(message: dict) -> None:
        assert proc.stdin is not None
        proc.stdin.write(json.dumps(message) + "\n")
        proc.stdin.flush()

    def read_response(expect_id: int) -> dict:
        deadline_lines = 200
        deadline = time.monotonic() + timeout
        while deadline_lines > 0:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    f"MCP server did not answer {expect_id} within {timeout:.0f}s. "
                    "The command may not be an MCP stdio server, or the selected AI client may not support this MCP connection."
                )
            try:
                line = stdout_queue.get(timeout=min(0.25, remaining))
            except queue.Empty:
                if proc.poll() is not None:
                    raise RuntimeError(_stderr_tail(proc) or "MCP server exited before responding.")
                continue
            if line is None:
                raise RuntimeError(_stderr_tail(proc) or "MCP server closed the connection before completing the handshake.")
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue  # skip non-JSON log lines
            if payload.get("id") == expect_id:
                return payload
            deadline_lines -= 1
        raise RuntimeError("no matching JSON-RPC response")

    try:
        send(_rpc("initialize", 1, _initialize_params()))
        init = read_response(1)
        if "error" in init:
            return MCPConnectionResult(ok=False, transport="stdio", target=command, error=str(init["error"]))
        server_info = (init.get("result") or {}).get("serverInfo") or {}

        send(_rpc("notifications/initialized", None))
        send(_rpc("tools/list", 2, {}))
        listed = read_response(2)
        tools = ((listed.get("result") or {}).get("tools")) or []

        return MCPConnectionResult(
            ok=True,
            transport="stdio",
            target=command,
            server_name=str(server_info.get("name", "")),
            server_version=str(server_info.get("version", "")),
            tools=list(tools),
        )
    finally:
        try:
            if proc.stdin:
                proc.stdin.close()
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                log.debug("suppressed", exc_info=True)

def _stderr_tail(proc: subprocess.Popen) -> str:
    try:
        if proc.stderr is not None:
            chunks: list[str] = []
            while True:
                line = proc.stderr.readline()
                if not line:
                    break
                chunks.append(line)
                if sum(len(chunk) for chunk in chunks) > 1000:
                    break
            return "".join(chunks).strip()[-400:]
    except Exception:
        log.debug("suppressed", exc_info=True)
    return ""

def _connect_http(url: str, *, timeout: float) -> MCPConnectionResult:
    def post(message: dict) -> dict:
        body = json.dumps(message).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace").strip()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace").strip()[:400]
            raise RuntimeError(f"HTTP MCP server returned {exc.code}: {detail or exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Could not reach HTTP MCP server: {exc.reason}") from exc
        return _parse_http_payload(raw)

    init = post(_rpc("initialize", 1, _initialize_params()))
    if "error" in init:
        return MCPConnectionResult(ok=False, transport="http", target=url, error=str(init["error"]))
    server_info = (init.get("result") or {}).get("serverInfo") or {}

    listed = post(_rpc("tools/list", 2, {}))
    tools = ((listed.get("result") or {}).get("tools")) or []
    return MCPConnectionResult(
        ok=True,
        transport="http",
        target=url,
        server_name=str(server_info.get("name", "")),
        server_version=str(server_info.get("version", "")),
        tools=list(tools),
    )

def _parse_http_payload(raw: str) -> dict:
    """Parse a JSON or SSE (text/event-stream) JSON-RPC response body."""
    if not raw:
        raise RuntimeError("MCP HTTP server returned an empty response.")
    if raw.lstrip().startswith("{"):
        return json.loads(raw)
    # SSE: pull the last `data:` line that parses as JSON.
    last: dict = {}
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            candidate = line[len("data:"):].strip()
            try:
                last = json.loads(candidate)
            except json.JSONDecodeError:
                continue
    if not last:
        raise RuntimeError("MCP HTTP server did not return JSON-RPC or SSE data.")
    return last

def _friendly_error(exc: Exception) -> str:
    text = str(exc).strip() or exc.__class__.__name__
    if isinstance(exc, TimeoutError):
        return text
    if "json" in text.lower() and "rpc" not in text.lower():
        return f"Server responded, but not with MCP JSON-RPC: {text}"
    return text
