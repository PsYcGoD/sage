"""LSP transport layer — handles JSON-RPC framing over stdio and TCP."""

from __future__ import annotations

import json
import sys
import threading
from typing import Any, Callable


class StdioTransport:
    """LSP transport over stdin/stdout with Content-Length framing."""

    def __init__(self):
        self._lock = threading.Lock()

    def read_message(self) -> dict | None:
        """Read one JSON-RPC message from stdin."""
        headers = {}
        while True:
            line = sys.stdin.buffer.readline()
            if not line:
                return None
            line = line.decode("utf-8").strip()
            if not line:
                break
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip().lower()] = value.strip()

        content_length = int(headers.get("content-length", 0))
        if content_length == 0:
            return None

        body = sys.stdin.buffer.read(content_length)
        return json.loads(body.decode("utf-8"))

    def write_message(self, msg: dict) -> None:
        """Write one JSON-RPC message to stdout."""
        body = json.dumps(msg, ensure_ascii=False).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
        with self._lock:
            sys.stdout.buffer.write(header + body)
            sys.stdout.buffer.flush()


class TCPTransport:
    """LSP transport over TCP socket with Content-Length framing."""

    def __init__(self, reader, writer):
        self._reader = reader
        self._writer = writer
        self._lock = threading.Lock()

    def read_message(self) -> dict | None:
        """Read one JSON-RPC message from the socket."""
        headers = {}
        while True:
            line = self._reader.readline()
            if not line:
                return None
            line = line.decode("utf-8").strip()
            if not line:
                break
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip().lower()] = value.strip()

        content_length = int(headers.get("content-length", 0))
        if content_length == 0:
            return None

        body = self._reader.read(content_length)
        return json.loads(body.decode("utf-8"))

    def write_message(self, msg: dict) -> None:
        """Write one JSON-RPC message to the socket."""
        body = json.dumps(msg, ensure_ascii=False).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
        with self._lock:
            self._writer.write(header + body)
            self._writer.flush()
