"""Shared dashboard data helpers."""

from __future__ import annotations

from typing import Any

from ..store import connect, recent_runs


def dashboard_snapshot(limit: int = 10) -> dict[str, Any]:
    """Return local dashboard metrics, recent commands, and agents."""
    with connect() as conn:
        cmd_result = conn.execute(
            """
            SELECT
                COUNT(*) as total,
                COALESCE(SUM(CASE WHEN exit_code = 0 THEN 1 ELSE 0 END), 0) as successful
            FROM runs
            """
        ).fetchone()
        compression_result = conn.execute(
            """
            SELECT
                COALESCE(SUM(original_tokens), 0) as total_estimated,
                COALESCE(SUM(compressed_tokens), 0) as total_compressed,
                COALESCE(SUM(saved_tokens), 0) as total_saved
            FROM context_compression
            """
        ).fetchone()
        agent_result = conn.execute(
            """
            SELECT
                COUNT(*) as total,
                COALESCE(SUM(CASE WHEN status NOT IN ('idle', 'cancelled', 'failed') THEN 1 ELSE 0 END), 0) as active
            FROM agents
            """
        ).fetchone()
        agent_rows = conn.execute(
            """
            SELECT id, type, name, status, created_at
            FROM agents
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    total = int(cmd_result["total"] or 0)
    successful = int(cmd_result["successful"] or 0)
    total_saved = int(compression_result["total_saved"] or 0)
    total_compressed = int(compression_result["total_compressed"] or 0)
    total_estimated = int(compression_result["total_estimated"] or 0)
    active_agents = int(agent_result["active"] or 0)
    total_agents = int(agent_result["total"] or 0)

    return {
        "metrics": {
            "total_commands": total,
            "successful": successful,
            "failed": max(0, total - successful),
            "success_rate": (successful / total) if total else 0,
            "total_tokens_estimated": total_estimated,
            "total_tokens_compressed": total_compressed,
            "total_tokens_saved": total_saved,
            "active_agents": active_agents,
            "total_agents": total_agents,
        },
        "commands": [
            {
                "id": r.id,
                "command": r.command,
                "exit_code": r.exit_code,
                "duration_ms": r.duration_ms,
                "timestamp": r.created_at,
                "summary": r.summary,
            }
            for r in recent_runs(limit=limit)
        ],
        "agents": [
            {
                "id": row["id"],
                "type": row["type"],
                "name": row["name"],
                "status": row["status"],
                "created_at": row["created_at"],
            }
            for row in agent_rows
        ],
    }
