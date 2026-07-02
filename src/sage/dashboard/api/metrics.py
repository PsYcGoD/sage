"""Metrics API endpoints."""

from __future__ import annotations

try:
    from fastapi import APIRouter
except ImportError:
    APIRouter = None

from ...store import connect


if APIRouter:
    router = APIRouter()

    @router.get("/metrics/success-rate")
    async def get_success_rate():
        """Get command success rate."""
        with connect() as conn:
            result = conn.execute(
                """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN exit_code = 0 THEN 1 ELSE 0 END) as successful
                FROM runs
                """
            ).fetchone()
            
            total = result["total"] or 0
            successful = result["successful"] or 0
            rate = (successful / total * 100) if total > 0 else 0
            
            return {
                "total_commands": total,
                "successful": successful,
                "failed": total - successful,
                "success_rate": round(rate, 2),
            }

    @router.get("/metrics/agents")
    async def get_agent_metrics():
        """Get agent metrics."""
        with connect() as conn:
            result = conn.execute(
                """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'idle' THEN 1 ELSE 0 END) as idle,
                    SUM(CASE WHEN status = 'busy' THEN 1 ELSE 0 END) as busy
                FROM agents
                """
            ).fetchone()
            
            return {
                "total_agents": result["total"] or 0,
                "idle": result["idle"] or 0,
                "busy": result["busy"] or 0,
            }

    @router.get("/metrics/workflows")
    async def get_workflow_metrics():
        """Get workflow metrics."""
        with connect() as conn:
            result = conn.execute(
                """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running
                FROM workflow_runs
                """
            ).fetchone()
            
            return {
                "total_workflows": result["total"] or 0,
                "completed": result["completed"] or 0,
                "failed": result["failed"] or 0,
                "running": result["running"] or 0,
            }
else:
    router = None
