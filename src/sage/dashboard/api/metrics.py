"""Metrics API endpoints."""

from __future__ import annotations

try:
    from fastapi import APIRouter
except ImportError:
    APIRouter = None

from ..data import dashboard_snapshot
from ...store import connect


if APIRouter:
    router = APIRouter()

    @router.get("/metrics")
    async def get_all_metrics():
        """Get all metrics for dashboard."""
        return dashboard_snapshot()["metrics"]

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

    @router.get("/metrics/ml")
    async def get_ml_metrics():
        """Get ML and agent activity metrics."""
        with connect() as conn:
            result = conn.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM ml_training_examples) as ml_examples,
                    (SELECT COUNT(*) FROM agent_runs) as agent_runs,
                    (SELECT COUNT(*) FROM agent_quality_metrics) as quality_metrics,
                    (SELECT COUNT(*) FROM agent_tasks) as agent_tasks,
                    (SELECT COUNT(*) FROM agents) as total_agents
                """
            ).fetchone()
            
            return {
                "ml_training_examples": result["ml_examples"] or 0,
                "agent_runs_completed": result["agent_runs"] or 0,
                "agent_quality_metrics": result["quality_metrics"] or 0,
                "agent_tasks_processed": result["agent_tasks"] or 0,
                "total_agents": result["total_agents"] or 0,
            }

    @router.get("/metrics/ml/v2")
    async def get_ml_v2_status():
        """Get ML V2 embedding model status and metrics."""
        try:
            from ...ml.embeddings import _HAS_ML_DEPS
        except ImportError:
            _HAS_ML_DEPS = False

        if not _HAS_ML_DEPS:
            return {
                "available": False,
                "reason": "ML dependencies not installed (pip install psycgod-sage[ml])",
            }

        result = {
            "available": True,
            "model": "all-MiniLM-L6-v2",
            "embedding_dim": 384,
            "index_cached": False,
            "index_size": 0,
            "embeddings_stored": 0,
        }

        from ...store import db_path as get_db_path
        import sqlite3
        from pathlib import Path

        db = get_db_path()

        # Check cached index
        index_path = db.parent / "ml_v2_index.faiss"
        result["index_cached"] = index_path.exists()

        # Count commands in DB
        with sqlite3.connect(db) as conn:
            row = conn.execute(
                "SELECT COUNT(DISTINCT command) FROM runs WHERE command IS NOT NULL AND command != ''"
            ).fetchone()
            result["index_size"] = row[0] if row else 0

            # Check embeddings table
            try:
                row = conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()
                result["embeddings_stored"] = row[0] if row else 0
            except sqlite3.OperationalError:
                result["embeddings_stored"] = 0

        return result

else:
    router = None
