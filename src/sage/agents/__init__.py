"""Multi-agent orchestration system for SAGE."""

from .base_agent import BaseAgent, AgentRecord
from .orchestrator import Orchestrator

__all__ = ["BaseAgent", "AgentRecord", "Orchestrator", "list_agents", "get_agent_status"]


def list_agents():
    """List all agents from database."""
    from ..store import connect
    
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, name, type, status, last_active
            FROM agents
            ORDER BY id DESC
            """
        ).fetchall()
        
        return [
            AgentRecord(
                id=row["id"],
                name=row["name"],
                type=row["type"],
                status=row["status"],
                last_active=row["last_active"],
            )
            for row in rows
        ]


def get_agent_status():
    """Get agent status summary."""
    from ..store import connect
    
    with connect() as conn:
        result = conn.execute(
            """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'busy' THEN 1 ELSE 0 END) as active,
                SUM(CASE WHEN status = 'idle' THEN 1 ELSE 0 END) as idle
            FROM agents
            """
        ).fetchone()
        
        tasks = conn.execute(
            "SELECT COUNT(*) as count FROM agent_tasks"
        ).fetchone()
        
        return {
            "active": result["active"] or 0,
            "idle": result["idle"] or 0,
            "total_tasks": tasks["count"] or 0,
        }
