"""SAGE MCP Tools definitions."""

from __future__ import annotations

from typing import Any


SAGE_TOOLS = [
    {
        "name": "sage_run_command",
        "description": "Run command through SAGE with smart output filtering and storage",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Command to execute"
                },
                "auto_fix": {
                    "type": "boolean",
                    "description": "Automatically apply fixes if available",
                    "default": False
                },
                "predict": {
                    "type": "boolean",
                    "description": "Predict failure before running",
                    "default": False
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "sage_explain_error",
        "description": "Get AI-friendly explanation of command error",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command_id": {
                    "type": "integer",
                    "description": "Specific command ID (optional, defaults to last failed)"
                }
            }
        }
    },
    {
        "name": "sage_suggest_fix",
        "description": "Get suggested fixes for error",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command_id": {
                    "type": "integer",
                    "description": "Specific command ID (optional, defaults to last failed)"
                }
            }
        }
    },
    {
        "name": "sage_spawn_agent",
        "description": "Spawn specialized agent for task",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_type": {
                    "type": "string",
                    "enum": ["code", "test", "debug", "security", "performance"],
                    "description": "Type of agent to spawn"
                },
                "task": {
                    "type": "string",
                    "description": "Task description for the agent"
                }
            },
            "required": ["agent_type", "task"]
        }
    },
    {
        "name": "sage_run_workflow",
        "description": "Execute workflow pipeline",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workflow_name": {
                    "type": "string",
                    "description": "Name of workflow to run (e.g., 'test', 'ci', 'deploy')"
                },
                "workflow_path": {
                    "type": "string",
                    "description": "Path to workflow YAML file (optional)"
                }
            }
        }
    },
    {
        "name": "sage_get_history",
        "description": "Get command history",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of commands to retrieve",
                    "default": 10
                },
                "failed_only": {
                    "type": "boolean",
                    "description": "Only show failed commands",
                    "default": False
                }
            }
        }
    }
]


def sage_run_command(command: str, auto_fix: bool = False, predict: bool = False) -> dict[str, Any]:
    """Execute SAGE run command."""
    from ..runner import run_command
    
    exit_code = run_command(command.split())
    
    return {
        "success": exit_code == 0,
        "exit_code": exit_code,
        "message": "Command executed via SAGE"
    }


def sage_explain_error(command_id: int = None) -> dict[str, Any]:
    """Get error explanation."""
    from ..store import latest_run
    
    record = latest_run(only_failures=True)
    if not record:
        return {"error": "No failed commands found"}
    
    return {
        "command_id": record.id,
        "command": record.command,
        "exit_code": record.exit_code,
        "summary": record.summary,
    }


def sage_suggest_fix(command_id: int = None) -> dict[str, Any]:
    """Get fix suggestions."""
    from ..suggestions import suggest_next_steps
    from ..store import latest_run
    
    record = latest_run(only_failures=True)
    if not record:
        return {"error": "No failed commands found"}
    
    suggestions = suggest_next_steps(record)
    
    return {
        "command_id": record.id,
        "suggestions": suggestions,
    }


def sage_spawn_agent(agent_type: str, task: str) -> dict[str, Any]:
    """Spawn an agent."""
    return {
        "success": True,
        "agent_type": agent_type,
        "task": task,
        "message": "Agent spawning not yet implemented in MCP mode"
    }


def sage_run_workflow(workflow_name: str = None, workflow_path: str = None) -> dict[str, Any]:
    """Run a workflow."""
    return {
        "success": False,
        "message": "Workflow execution not yet implemented in MCP mode"
    }


def sage_get_history(limit: int = 10, failed_only: bool = False) -> dict[str, Any]:
    """Get command history."""
    from ..store import recent_runs
    
    records = recent_runs(limit=limit)
    
    if failed_only:
        records = [r for r in records if r.exit_code != 0]
    
    return {
        "count": len(records),
        "commands": [
            {
                "id": r.id,
                "command": r.command,
                "exit_code": r.exit_code,
                "duration_ms": r.duration_ms,
                "created_at": r.created_at,
            }
            for r in records
        ]
    }
