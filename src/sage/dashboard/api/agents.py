"""Agents API endpoints."""

from __future__ import annotations

try:
    from fastapi import APIRouter
except ImportError:
    APIRouter = None

from ...store import connect


if APIRouter:
    router = APIRouter()

    @router.get("/agents")
    async def get_agents():
        """Get all agents."""
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT id, type, name, status, created_at
                FROM agents
                ORDER BY created_at DESC
                """
            ).fetchall()

            return [
                {
                    "id": row["id"],
                    "type": row["type"],
                    "name": row["name"],
                    "status": row["status"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

    @router.get("/agents/{agent_id}")
    async def get_agent(agent_id: int):
        """Get specific agent details."""
        with connect() as conn:
            # Agent info
            agent_row = conn.execute(
                """
                SELECT id, type, name, status, created_at
                FROM agents
                WHERE id = ?
                """,
                (agent_id,),
            ).fetchone()

            if not agent_row:
                return {"error": "Agent not found"}

            # Agent tasks
            tasks = conn.execute(
                """
                SELECT id, description, status, created_at, completed_at
                FROM agent_tasks
                WHERE agent_id = ?
                ORDER BY created_at DESC
                """,
                (agent_id,),
            ).fetchall()

            return {
                "id": agent_row["id"],
                "type": agent_row["type"],
                "name": agent_row["name"],
                "status": agent_row["status"],
                "created_at": agent_row["created_at"],
                "tasks": [
                    {
                        "id": t["id"],
                        "description": t["description"],
                        "status": t["status"],
                        "created_at": t["created_at"],
                        "completed_at": t["completed_at"],
                    }
                    for t in tasks
                ],
            }
else:
    router = None
