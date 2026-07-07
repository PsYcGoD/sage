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
        
        # ML and agent activity stats
        ml_result = conn.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM ml_training_examples) as ml_examples,
                (SELECT COUNT(*) FROM agent_runs) as agent_runs,
                (SELECT COUNT(*) FROM agent_quality_metrics) as quality_metrics,
                (SELECT COUNT(*) FROM agent_tasks) as agent_tasks
            """
        ).fetchone()

    total = int(cmd_result["total"] or 0)
    successful = int(cmd_result["successful"] or 0)
    total_saved = int(compression_result["total_saved"] or 0)
    total_compressed = int(compression_result["total_compressed"] or 0)
    total_estimated = int(compression_result["total_estimated"] or 0)
    active_agents = int(agent_result["active"] or 0)
    total_agents = int(agent_result["total"] or 0)
    
    # ML stats
    ml_examples = int(ml_result["ml_examples"] or 0)
    agent_runs_count = int(ml_result["agent_runs"] or 0)
    quality_metrics = int(ml_result["quality_metrics"] or 0)
    agent_tasks_count = int(ml_result["agent_tasks"] or 0)

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
            "ml_training_examples": ml_examples,
            "agent_runs_completed": agent_runs_count,
            "agent_quality_metrics": quality_metrics,
            "agent_tasks_processed": agent_tasks_count,
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
