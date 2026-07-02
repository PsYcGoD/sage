"""Base agent class and protocols."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class AgentRecord:
    """Agent record from database."""
    id: int
    name: str
    type: str
    status: str
    last_active: Optional[str]


@dataclass
class Task:
    """Task for an agent to execute."""
    id: int
    description: str
    context: dict[str, Any]


class BaseAgent:
    """Base class for all specialized agents."""

    def __init__(self, name: str, agent_type: str, capabilities: list[str]):
        self.name = name
        self.agent_type = agent_type
        self.capabilities = capabilities
        self.status = "idle"
        self.task_queue: asyncio.Queue[Task] = asyncio.Queue()
        self.db_id: Optional[int] = None

    async def start(self) -> None:
        """Start the agent."""
        from ..store import connect
        
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO agents (name, type, status, capabilities, created_at, last_active)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (self.name, self.agent_type, self.status, str(self.capabilities), now, now),
            )
            self.db_id = cursor.lastrowid
            conn.commit()

        print(f"[SAGE] Agent {self.name} started (ID: {self.db_id})")

    async def execute_task(self, task: Task) -> Any:
        """
        Execute a task.
        
        Override this method in specialized agents.
        """
        raise NotImplementedError("Subclasses must implement execute_task")

    async def update_status(self, new_status: str) -> None:
        """Update agent status in database."""
        if not self.db_id:
            return

        from ..store import connect
        
        self.status = new_status
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        
        with connect() as conn:
            conn.execute(
                """
                UPDATE agents
                SET status = ?, last_active = ?
                WHERE id = ?
                """,
                (new_status, now, self.db_id),
            )
            conn.commit()

    async def run(self) -> None:
        """Main agent loop - process tasks from queue."""
        while True:
            try:
                task = await self.task_queue.get()
                await self.update_status("busy")
                
                result = await self.execute_task(task)
                
                # Save task result
                await self._save_task_result(task, result)
                
                await self.update_status("idle")
                self.task_queue.task_done()
            except Exception as e:
                print(f"[SAGE] Agent {self.name} error: {e}")
                await self.update_status("error")

    async def _save_task_result(self, task: Task, result: Any) -> None:
        """Save task execution result."""
        if not self.db_id:
            return

        from ..store import connect
        
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO agent_tasks
                (agent_id, task_description, status, result, started_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (self.db_id, task.description, "completed", str(result), now, now),
            )
            conn.commit()

    async def stop(self) -> None:
        """Stop the agent."""
        await self.update_status("stopped")
        print(f"[SAGE] Agent {self.name} stopped")
