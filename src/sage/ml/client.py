"""Fast client for the SAGE ML daemon — queries predictions in ~5ms."""

from __future__ import annotations

import json
import socket
from typing import Optional

DAEMON_HOST = "127.0.0.1"
DAEMON_PORT = 19472


def predict_fast(command: str, timeout: float = 0.5) -> Optional[dict]:
    """Query the ML daemon for a prediction. Returns None if daemon unavailable."""
    try:
        with socket.create_connection((DAEMON_HOST, DAEMON_PORT), timeout=timeout) as s:
            s.sendall(json.dumps({"command": command}).encode("utf-8"))
            data = s.recv(4096)
            result = json.loads(data.decode("utf-8"))
            if result.get("ok"):
                return result
            return None
    except (OSError, json.JSONDecodeError, TimeoutError):
        return None


def daemon_healthy(timeout: float = 0.3) -> bool:
    """Check if daemon is alive and responding."""
    try:
        with socket.create_connection((DAEMON_HOST, DAEMON_PORT), timeout=timeout) as s:
            s.sendall(json.dumps({"action": "health"}).encode("utf-8"))
            data = s.recv(1024)
            result = json.loads(data.decode("utf-8"))
            return result.get("ok", False)
    except (OSError, json.JSONDecodeError, TimeoutError):
        return False
