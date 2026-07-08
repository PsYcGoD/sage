"""Phase 5: LSP Protocol Tests."""

import json
import threading
import io
import pytest

from sage.lsp.transport import StdioTransport
from sage.lsp.server import SageLSPServer


class FakeTransport:
    """In-memory transport for testing."""

    def __init__(self):
        self.inbox: list[dict] = []
        self.outbox: list[dict] = []

    def read_message(self) -> dict | None:
        if not self.inbox:
            return None
        return self.inbox.pop(0)

    def write_message(self, msg: dict):
        self.outbox.append(msg)


def make_server_with_messages(messages: list[dict]) -> tuple[SageLSPServer, FakeTransport]:
    transport = FakeTransport()
    transport.inbox = list(messages)
    server = SageLSPServer(transport=transport)
    server._transport = transport
    return server, transport


class TestLSPLifecycle:
    def test_initialize_returns_capabilities(self):
        server, transport = make_server_with_messages([
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        ])
        server._message_loop()

        assert len(transport.outbox) == 1
        resp = transport.outbox[0]
        assert resp["id"] == 1
        assert "capabilities" in resp["result"]
        assert resp["result"]["serverInfo"]["name"] == "sage-lsp"

    def test_shutdown_stops_loop(self):
        server, transport = make_server_with_messages([
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "shutdown", "params": {}},
        ])
        server._message_loop()

        assert len(transport.outbox) == 2
        assert transport.outbox[1]["result"] is None

    def test_unknown_method_returns_error(self):
        server, transport = make_server_with_messages([
            {"jsonrpc": "2.0", "id": 1, "method": "nonexistent/method", "params": {}},
        ])
        server._message_loop()

        resp = transport.outbox[0]
        assert "error" in resp
        assert resp["error"]["code"] == -32601


class TestSAGEMethods:
    def test_predict_empty_command(self):
        server, transport = make_server_with_messages([
            {"jsonrpc": "2.0", "id": 1, "method": "sage/predict", "params": {"command": ""}},
        ])
        server._message_loop()

        resp = transport.outbox[0]
        assert resp["result"]["ok"] is False

    def test_predict_valid_command(self):
        server, transport = make_server_with_messages([
            {"jsonrpc": "2.0", "id": 1, "method": "sage/predict", "params": {"command": "ls"}},
        ])
        server._message_loop()

        resp = transport.outbox[0]
        result = resp["result"]
        assert result["ok"] is True
        assert "will_fail" in result
        assert "confidence" in result

    def test_session_returns_list(self):
        server, transport = make_server_with_messages([
            {"jsonrpc": "2.0", "id": 1, "method": "sage/session", "params": {}},
        ])
        server._message_loop()

        resp = transport.outbox[0]
        result = resp["result"]
        assert result["ok"] is True
        assert "recent_commands" in result
