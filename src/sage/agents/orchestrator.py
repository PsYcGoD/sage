"""Agent orchestrator for task distribution."""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from .base_agent import BaseAgent, Task
from .registry import select_agents_for_command


class Orchestrator:
    """Coordinates multiple agents and distributes tasks."""

    def __init__(self):
        self.agents: dict[str, BaseAgent] = {}
        self.task_counter = 0

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the orchestrator."""
        self.agents[agent.name] = agent
        print(f"[SAGE] Registered agent: {agent.name} ({agent.agent_type})")

    async def spawn_agent(
        self,
        agent_class: type[BaseAgent],
        name: str,
    ) -> BaseAgent:
        """Spawn a new agent."""
        agent = agent_class(name)
        await agent.start()
        self.register_agent(agent)
        
        # Start agent run loop in background
        asyncio.create_task(agent.run())
        
        return agent

    async def assign_task(
        self,
        agent_name: str,
        description: str,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Assign a task to a specific agent."""
        if agent_name not in self.agents:
            raise ValueError(f"Agent {agent_name} not found")

        agent = self.agents[agent_name]
        self.task_counter += 1
        
        task = Task(
            id=self.task_counter,
            description=description,
            context=context or {},
        )
        
        await agent.task_queue.put(task)
        print(f"[SAGE] Task #{task.id} assigned to {agent_name}")

    async def broadcast_task(
        self,
        description: str,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Broadcast a task to all idle agents."""
        self.task_counter += 1
        task = Task(
            id=self.task_counter,
            description=description,
            context=context or {},
        )

        assigned_count = 0
        for agent in self.agents.values():
            if agent.status == "idle":
                await agent.task_queue.put(task)
                assigned_count += 1

        print(f"[SAGE] Task #{task.id} broadcast to {assigned_count} agents")

    def get_agent_by_capability(self, capability: str) -> Optional[BaseAgent]:
        """Find an idle agent with specific capability."""
        for agent in self.agents.values():
            if capability in agent.capabilities and agent.status == "idle":
                return agent
        return None

    def plan_for_command(self, command: str) -> list[dict[str, Any]]:
        """Return agent roles that should participate in a command."""
        return [
            {
                "type": spec.type,
                "name": spec.name,
                "capabilities": list(spec.capabilities),
                "description": spec.description,
            }
            for spec in select_agents_for_command(command)
        ]

    async def shutdown(self) -> None:
        """Shutdown all agents."""
        print("[SAGE] Shutting down orchestrator...")
        for agent in self.agents.values():
            await agent.stop()
        self.agents.clear()
