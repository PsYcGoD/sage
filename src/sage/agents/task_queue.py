"""Task queue management."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class QueuedTask:
    """Task in the queue."""
    id: int
    description: str
    priority: int
    context: dict[str, Any]


class TaskQueue:
    """Priority task queue for agent work distribution."""

    def __init__(self):
        self.queue: asyncio.PriorityQueue[tuple[int, QueuedTask]] = asyncio.PriorityQueue()
        self.task_counter = 0

    async def add_task(
        self,
        description: str,
        priority: int = 5,
        context: Optional[dict[str, Any]] = None,
    ) -> int:
        """Add a task to the queue."""
        self.task_counter += 1
        task = QueuedTask(
            id=self.task_counter,
            description=description,
            priority=priority,
            context=context or {},
        )
        await self.queue.put((priority, task))
        return task.id

    async def get_task(self) -> QueuedTask:
        """Get highest priority task from queue."""
        _, task = await self.queue.get()
        return task

    def task_done(self) -> None:
        """Mark task as complete."""
        self.queue.task_done()

    def size(self) -> int:
        """Get queue size."""
        return self.queue.qsize()
