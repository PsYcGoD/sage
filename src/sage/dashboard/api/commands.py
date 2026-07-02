"""Commands API endpoints."""

from __future__ import annotations

try:
    from fastapi import APIRouter
except ImportError:
    APIRouter = None

from ...store import connect, recent_runs


if APIRouter:
    router = APIRouter()

    @router.get("/commands/recent")
    async def get_recent_commands(limit: int = 20):
        """Get recent commands."""
        records = recent_runs(limit=limit)
        return {
            "commands": [
                {
                    "id": r.id,
                    "command": r.command,
                    "exit_code": r.exit_code,
                    "duration_ms": r.duration_ms,
                    "created_at": r.created_at,
                    "summary": r.summary,
                }
                for r in records
            ]
        }

    @router.get("/commands/{command_id}")
    async def get_command(command_id: int):
        """Get specific command details."""
        with connect() as conn:
            row = conn.execute(
                """
                SELECT id, command, exit_code, duration_ms, 
                       stdout, stderr, summary, created_at
                FROM runs
                WHERE id = ?
                """,
                (command_id,),
            ).fetchone()
            
            if not row:
                return {"error": "Command not found"}
            
            return {
                "id": row["id"],
                "command": row["command"],
                "exit_code": row["exit_code"],
                "duration_ms": row["duration_ms"],
                "stdout": row["stdout"],
                "stderr": row["stderr"],
                "summary": row["summary"],
                "created_at": row["created_at"],
            }
else:
    router = None
