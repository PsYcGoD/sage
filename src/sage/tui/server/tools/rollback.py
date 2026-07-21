"""Rollback tool - restore files from snapshots."""
from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from .base import BaseTool


class RollbackTool(BaseTool):
    """Rollback files to previous snapshots."""

    # Shared snapshot store across all instances
    _snapshots: ClassVar[dict[str, dict]] = {}
    _counter: ClassVar[int] = 0

    @property
    def name(self) -> str:
        return "sage_rollback"

    @property
    def description(self) -> str:
        return "Rollback a file to its state before the last write/edit using snapshot ID"

    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self._parameters(),
            },
        }

    def _parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "snapshot_id": {"type": "string", "description": "Snapshot ID from previous write/edit result"},
            },
            "required": ["snapshot_id"],
        }

    @classmethod
    def create_snapshot(cls, path: Path) -> str:
        """Create a snapshot of a file. Returns snapshot ID."""
        cls._counter += 1
        import time
        snapshot_id = f"snap_{cls._counter}_{int(time.time())}"

        content = None
        if path.exists():
            content = path.read_text(encoding="utf-8", errors="replace")

        cls._snapshots[snapshot_id] = {
            "path": str(path),
            "content": content,
        }
        return snapshot_id

    @classmethod
    def get_snapshot(cls, snapshot_id: str) -> dict | None:
        """Get a snapshot by ID."""
        return cls._snapshots.get(snapshot_id)

    async def execute(self, input_data: dict) -> dict:
        snapshot_id = input_data.get("snapshot_id", "")

        if not snapshot_id:
            return {"error": "snapshot_id is required"}

        snapshot = self._snapshots.get(snapshot_id)
        if not snapshot:
            return {"error": f"Snapshot not found: {snapshot_id}"}

        path = Path(snapshot["path"])
        content = snapshot["content"]

        try:
            if content is None:
                # File was created, delete it
                if path.exists():
                    path.unlink()
            else:
                path.write_text(content, encoding="utf-8")

            del self._snapshots[snapshot_id]
            return {"success": True, "restored": str(path)}
        except Exception as e:
            return {"error": f"Rollback failed: {e}"}
