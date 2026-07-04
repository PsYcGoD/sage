"""Multi-agent orchestration system for SAGE."""

from .base_agent import BaseAgent, AgentRecord
from .orchestrator import Orchestrator
from .registry import (
    DEFAULT_AGENT_SPECS,
    ensure_default_agents,
    list_default_agent_specs,
    select_agents_for_command,
)
from .executor import (
    AGENT_STATES,
    cancel_agent_runs,
    execute_agents_for_run,
    get_agent_runs_for_run,
    get_agent_tasks_for_run,
    llm_backend,
    run_agent_worker_once,
)
from .evaluation import DEFAULT_SCENARIOS, evaluate_agents, write_eval_report

__all__ = [
    "BaseAgent",
    "AgentRecord",
    "Orchestrator",
    "DEFAULT_AGENT_SPECS",
    "ensure_default_agents",
    "list_default_agent_specs",
    "select_agents_for_command",
    "AGENT_STATES",
    "cancel_agent_runs",
    "execute_agents_for_run",
    "get_agent_runs_for_run",
    "get_agent_tasks_for_run",
    "run_agent_worker_once",
    "llm_backend",
    "DEFAULT_SCENARIOS",
    "evaluate_agents",
    "write_eval_report",
    "list_agents",
    "get_agent_status",
]


def list_agents():
    """List all agents from database."""
    from ..store import connect

    ensure_default_agents()
    
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

    ensure_default_agents()
    
    with connect() as conn:
        result = conn.execute(
            """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status IN ('busy', 'running', 'waiting_for_tool') THEN 1 ELSE 0 END) as active,
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
            "total": result["total"] or 0,
            "total_tasks": tasks["count"] or 0,
        }
