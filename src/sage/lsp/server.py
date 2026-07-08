"""SAGE LSP Server — JSON-RPC 2.0 language server for terminal intelligence."""

from __future__ import annotations

import json
import logging
import socketserver
import sys
import threading
from typing import Any, Callable

from .transport import StdioTransport, TCPTransport

logger = logging.getLogger(__name__)

LSP_VERSION = "0.1.0"
DEFAULT_TCP_PORT = 19473


class SageLSPServer:
    """Language Server Protocol server for SAGE predictions and agentic features."""

    def __init__(self, transport=None):
        self._transport = transport
        self._running = False
        self._initialized = False
        self._handlers: dict[str, Callable] = {
            "initialize": self._handle_initialize,
            "initialized": self._handle_initialized,
            "shutdown": self._handle_shutdown,
            "exit": self._handle_exit,
            "sage/predict": self._handle_predict,
            "sage/explain": self._handle_explain,
            "sage/fix": self._handle_fix,
            "sage/session": self._handle_session,
        }

    def start_stdio(self):
        """Start LSP server on stdio (for editor integration)."""
        self._transport = StdioTransport()
        self._running = True
        logger.info("SAGE LSP server started (stdio)")
        self._message_loop()

    def start_tcp(self, host: str = "127.0.0.1", port: int = DEFAULT_TCP_PORT):
        """Start LSP server on TCP (for AI agent connections)."""
        server = _TCPServer((host, port), self)
        self._running = True
        logger.info(f"SAGE LSP server started (tcp://{host}:{port})")
        print(f"[sage-lsp] listening on {host}:{port}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.shutdown()

    def handle_tcp_client(self, reader, writer):
        """Handle a single TCP client connection."""
        transport = TCPTransport(reader, writer)
        self._transport = transport
        self._message_loop()

    def _message_loop(self):
        """Main message processing loop."""
        self._running = True
        while self._running:
            try:
                msg = self._transport.read_message()
                if msg is None:
                    break
                self._dispatch(msg)
            except Exception as e:
                logger.error(f"Message loop error: {e}")
                break

    def _dispatch(self, msg: dict):
        """Route a JSON-RPC message to its handler."""
        method = msg.get("method", "")
        msg_id = msg.get("id")
        params = msg.get("params", {})

        handler = self._handlers.get(method)
        if handler:
            try:
                result = handler(params)
                if msg_id is not None:
                    self._respond(msg_id, result)
            except Exception as e:
                if msg_id is not None:
                    self._respond_error(msg_id, -32603, str(e))
        elif msg_id is not None:
            self._respond_error(msg_id, -32601, f"Method not found: {method}")

    def _respond(self, msg_id: Any, result: Any):
        """Send a successful response."""
        self._transport.write_message({
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": result,
        })

    def _respond_error(self, msg_id: Any, code: int, message: str):
        """Send an error response."""
        self._transport.write_message({
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": code, "message": message},
        })

    def _notify(self, method: str, params: Any = None):
        """Send a notification (no response expected)."""
        msg = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        self._transport.write_message(msg)

    # --- LSP Lifecycle ---

    def _handle_initialize(self, params: dict) -> dict:
        """Handle initialize request — return server capabilities."""
        return {
            "capabilities": {
                "textDocumentSync": 1,
                "completionProvider": {"triggerCharacters": [" ", "-", "/"]},
                "codeActionProvider": True,
                "diagnosticProvider": {"interFileDependencies": False, "workspaceDiagnostics": False},
                "experimental": {
                    "sagePrediction": True,
                    "sageAgenticLoop": True,
                    "sageAutoFix": True,
                },
            },
            "serverInfo": {
                "name": "sage-lsp",
                "version": LSP_VERSION,
            },
        }

    def _handle_initialized(self, params: dict) -> None:
        """Handle initialized notification — server is ready."""
        self._initialized = True
        logger.info("LSP client connected and initialized")
        return None

    def _handle_shutdown(self, params: dict) -> None:
        """Handle shutdown request."""
        self._running = False
        return None

    def _handle_exit(self, params: dict) -> None:
        """Handle exit notification."""
        self._running = False
        sys.exit(0)

    # --- SAGE Custom Methods ---

    def _handle_predict(self, params: dict) -> dict:
        """Handle sage/predict — predict command failure."""
        command = params.get("command", "")
        if not command:
            return {"ok": False, "error": "no command provided"}

        try:
            from ..ml.client import predict_fast
            result = predict_fast(command)
            if result:
                return result
            # Fallback to local heuristics
            from ..ml.predictor import FailurePredictor
            predictor = FailurePredictor()
            predictor._v2_failed = True
            will_fail, confidence, reason = predictor.predict(command)
            return {
                "ok": True,
                "will_fail": will_fail,
                "confidence": round(confidence, 4),
                "reason": reason,
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _handle_explain(self, params: dict) -> dict:
        """Handle sage/explain — explain last failure."""
        run_id = params.get("run_id")
        try:
            from ..store import connect
            with connect() as conn:
                if run_id:
                    row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
                else:
                    row = conn.execute(
                        "SELECT * FROM runs WHERE exit_code != 0 ORDER BY id DESC LIMIT 1"
                    ).fetchone()
                if not row:
                    return {"ok": False, "error": "no failed command found"}
                return {
                    "ok": True,
                    "command": row["command"],
                    "exit_code": row["exit_code"],
                    "summary": row["summary"],
                }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _handle_fix(self, params: dict) -> dict:
        """Handle sage/fix — suggest fix for last failure."""
        try:
            from ..store import connect
            with connect() as conn:
                row = conn.execute(
                    "SELECT * FROM runs WHERE exit_code != 0 ORDER BY id DESC LIMIT 1"
                ).fetchone()
                if not row:
                    return {"ok": False, "error": "no failed command found"}

            from ..agentic.fixer import suggest_fix
            fix = suggest_fix(row["command"], row["summary"] or "")
            return {"ok": True, "fix": fix}
        except ImportError:
            return {"ok": False, "error": "agentic module not yet available"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _handle_session(self, params: dict) -> dict:
        """Handle sage/session — return current session state."""
        try:
            from ..store import connect
            with connect() as conn:
                recent = conn.execute(
                    "SELECT command, exit_code, summary FROM runs ORDER BY id DESC LIMIT 10"
                ).fetchall()
            return {
                "ok": True,
                "recent_commands": [
                    {"command": r["command"], "exit_code": r["exit_code"], "summary": r["summary"]}
                    for r in recent
                ],
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}


class _TCPHandler(socketserver.StreamRequestHandler):
    """Handle a single TCP LSP client."""

    def handle(self):
        self.server.lsp_server.handle_tcp_client(self.rfile, self.wfile)


class _TCPServer(socketserver.ThreadingTCPServer):
    """Threaded TCP server for multiple LSP clients."""

    allow_reuse_address = True

    def __init__(self, server_address, lsp_server: SageLSPServer):
        self.lsp_server = lsp_server
        super().__init__(server_address, _TCPHandler)
