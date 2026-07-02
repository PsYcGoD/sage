"""WebSocket support for real-time updates."""

from __future__ import annotations

try:
    from fastapi import WebSocket
except ImportError:
    WebSocket = None


class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self):
        self.active_connections: list = []

    async def connect(self, websocket):
        """Connect a new client."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket):
        """Disconnect a client."""
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Broadcast message to all clients."""
        for connection in self.active_connections:
            await connection.send_json(message)


manager = ConnectionManager()
