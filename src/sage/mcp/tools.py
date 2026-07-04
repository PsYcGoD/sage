"""SAGE MCP Tools definitions."""

from __future__ import annotations

import shlex
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
    },
    {
        "name": "sage_read_file",
        "description": "Read a file with SAGE compression: small files exact, large files as outline + head with line references. Prefer this over cat/type/Get-Content to save context.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to read"},
                "lines": {"type": "string", "description": "Optional exact range START:END, e.g. 120:220"},
                "max_tokens": {"type": "integer", "description": "Token budget for large files", "default": 1500},
                "raw": {"type": "boolean", "description": "Return exact full content", "default": False},
                "symbols": {"type": "boolean", "description": "Return only the symbol outline", "default": False}
            },
            "required": ["path"]
        }
    },
    {
        "name": "sage_grep",
        "description": "Search files with compressed, grouped results (exact paths and line numbers kept). Prefer this over rg/grep when output may be large.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Regex pattern"},
                "paths": {"type": "array", "items": {"type": "string"}, "description": "Paths to search", "default": ["."]},
                "glob": {"type": "string", "description": "Filename filter, e.g. *.py"},
                "ignore_case": {"type": "boolean", "default": False}
            },
            "required": ["pattern"]
        }
    },
    {
        "name": "sage_call",
        "description": "Run a command as an explicit agent tool-call with purpose metadata (tracked for tool-quality metrics).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Command to execute"},
                "purpose": {"type": "string", "enum": ["read", "search", "test", "build", "deploy", "audit", "unknown"], "default": "unknown"},
                "agent": {"type": "string", "description": "Calling agent name", "default": "mcp"}
            },
            "required": ["command"]
        }
    },
    {
        "name": "sage_show_raw",
        "description": "Recover the exact stored output of a previous run by ID (compression never destroys the original).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "integer", "description": "Run ID (omit for latest run)"}
            }
        }
    },
    {
        "name": "sage_write_file",
        "description": "Create or update a file. Returns bytes/lines/sha256 confirmation instead of echoing the content back — saves the whole file's tokens. Existing files require overwrite=true (a snapshot is taken first so it is reversible).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to write"},
                "content": {"type": "string", "description": "Full file content"},
                "overwrite": {"type": "boolean", "description": "Allow replacing an existing file", "default": False},
                "append": {"type": "boolean", "description": "Append instead of replace", "default": False}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "sage_edit_file",
        "description": "Exact string replacement in a file. Returns a compact change preview instead of the whole file, and snapshots the pre-edit content for undo. old must match exactly and be unique unless replace_all=true.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File to edit"},
                "old": {"type": "string", "description": "Exact string to replace"},
                "new": {"type": "string", "description": "Replacement (empty deletes)"},
                "replace_all": {"type": "boolean", "default": False}
            },
            "required": ["path", "old", "new"]
        }
    },
    {
        "name": "sage_glob",
        "description": "Find files by pattern, newest first, junk directories ignored, capped output. Prefer over recursive directory listings.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Pattern, e.g. **/*.py"},
                "root": {"type": "string", "description": "Root directory", "default": "."},
                "limit": {"type": "integer", "description": "Max files returned", "default": 50}
            },
            "required": ["pattern"]
        }
    },
    {
        "name": "sage_tree",
        "description": "Compact depth-limited directory overview instead of ls -R noise.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {"type": "string", "description": "Root directory", "default": "."},
                "depth": {"type": "integer", "default": 3},
                "limit": {"type": "integer", "default": 200}
            }
        }
    }
]


def sage_run_command(command: str, auto_fix: bool = False, predict: bool = False) -> dict[str, Any]:
    """Execute SAGE run command."""
    from ..runner import run_command
    prediction = None

    if predict:
        from ..ml import FailurePredictor

        will_fail, confidence, reason = FailurePredictor().predict(command)
        prediction = {
            "will_fail": will_fail,
            "confidence": confidence,
            "reason": reason,
        }

    exit_code = run_command(shlex.split(command), predict=predict)
    
    return {
        "success": exit_code == 0,
        "exit_code": exit_code,
        "message": "Command executed via SAGE",
        "prediction": prediction,
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
    """Run one deterministic SAGE agent analysis task through the DB worker."""
    from pathlib import Path

    from ..classify import workspace_hash
    from ..security import command_hash, retention_expiry
    from ..store import save_run
    from ..agents.executor import enqueue_agent_runs, get_agent_tasks_for_run, run_agent_worker_once
    from ..agents.registry import DEFAULT_AGENT_SPECS, ensure_default_agents

    ensure_default_agents()
    matching = [spec for spec in DEFAULT_AGENT_SPECS if spec.type == agent_type]
    if not matching:
        return {
            "success": False,
            "agent_type": agent_type,
            "task": task,
            "error": f"Unknown agent type: {agent_type}",
        }

    command_text = f"sage agent {agent_type}: {task}"
    run_id = save_run(
        project=str(Path.cwd()),
        command=command_text,
        exit_code=0,
        duration_ms=0,
        stdout="",
        stderr="",
        summary=task,
        command_sha256=command_hash(command_text),
        retention_expires_at=retention_expiry(),
        command_kind="agent",
        command_family=agent_type,
        caller="mcp",
        workspace_hash=workspace_hash(str(Path.cwd())),
        is_ai_session=1,
    )
    queued = enqueue_agent_runs(
        run_id=run_id,
        specs=[matching[0]],
        command=command_text,
        output="",
        exit_code=0,
        summary=task,
    )
    run_agent_worker_once(run_id=run_id, max_workers=1)
    tasks = get_agent_tasks_for_run(run_id)
    return {
        "success": bool(tasks),
        "run_id": run_id,
        "queued": queued,
        "agent_type": agent_type,
        "task": task,
        "results": tasks,
    }


def sage_run_workflow(workflow_name: str = None, workflow_path: str = None) -> dict[str, Any]:
    """Run a workflow by template name or YAML path."""
    import asyncio
    from pathlib import Path

    from ..workflows import WorkflowExecutor, WorkflowParser

    if workflow_path:
        path = Path(workflow_path)
    elif workflow_name:
        requested = Path(workflow_name)
        if requested.exists():
            path = requested
        else:
            path = Path(__file__).resolve().parents[1] / "workflows" / "templates" / f"{workflow_name}.yml"
    else:
        return {"success": False, "error": "workflow_name or workflow_path is required"}

    if not path.exists():
        return {"success": False, "error": f"Workflow not found: {workflow_path or workflow_name}"}

    parser = WorkflowParser()
    workflow = parser.parse_file(path)
    errors = parser.validate(workflow)
    if errors:
        return {"success": False, "workflow": workflow.name, "errors": errors}

    executor = WorkflowExecutor()
    success = asyncio.run(executor.execute(workflow))
    return {
        "success": success,
        "workflow": workflow.name,
        "workflow_run_id": executor.run_id,
        "path": str(path),
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


def sage_read_file(
    path: str,
    lines: str = "",
    max_tokens: int = 1500,
    raw: bool = False,
    symbols: bool = False,
) -> dict[str, Any]:
    """Read a file with compression; stored as a run for token proof."""
    from ..reader import read_file, save_read_run

    result = read_file(path, lines=lines, max_tokens=max_tokens, raw=raw, symbols_only=symbols)
    run_id = save_read_run(result, caller="mcp")
    if not result.exists:
        return {"success": False, "error": result.error, "run_id": run_id}
    return {
        "success": True,
        "run_id": run_id,
        "mode": result.mode,
        "language": result.language,
        "lines": result.lines,
        "original_tokens": result.original_tokens,
        "shown_tokens": result.shown_tokens,
        "saved_tokens": result.saved_tokens,
        "content": result.output,
    }


def sage_grep(
    pattern: str,
    paths: list[str] | None = None,
    glob: str = "",
    ignore_case: bool = False,
) -> dict[str, Any]:
    """Search with compressed grouped output; stored as a run."""
    from ..searcher import render, save_grep_run, search

    result = search(pattern, paths or ["."], glob=glob, ignore_case=ignore_case)
    rendered = render(result)
    raw_output = "\n".join(
        f"{file}:{line_no}:{text}" for file, hits in result.matches.items() for line_no, text in hits
    )
    run_id = save_grep_run(result, rendered, raw_output, caller="mcp")
    return {
        "success": result.exit_code != 2,
        "run_id": run_id,
        "match_count": result.match_count,
        "matched_files": result.matched_files,
        "hidden_matches": result.hidden_matches,
        "engine": result.engine,
        "content": rendered,
    }


def sage_call(command: str, purpose: str = "unknown", agent: str = "mcp") -> dict[str, Any]:
    """Execute a command as a tracked agent tool-call."""
    import os
    from ..runner import run_command
    from ..store import connect, latest_run

    # Inherit session_id from environment (set by GUI or parent AI process)
    session_id = os.environ.get("SAGE_SESSION_ID", "")
    is_ai_session = 1 if session_id else 0

    exit_code = run_command(
        shlex.split(command),
        caller="mcp",
        kind_override="call",
        session_id=session_id,
        is_ai_session=is_ai_session,
    )
    record = latest_run()
    if record is not None:
        with connect() as conn:
            conn.execute("UPDATE runs SET command_family = ? WHERE id = ?", (purpose, record.id))
            conn.commit()
    return {
        "success": exit_code == 0,
        "exit_code": exit_code,
        "run_id": record.id if record else None,
        "purpose": purpose,
        "agent": agent,
    }


def sage_write_file(path: str, content: str, overwrite: bool = False, append: bool = False) -> dict[str, Any]:
    """Write a file; confirm with metadata instead of echoing content."""
    from ..fileops import save_fileop_run, write_file

    result = write_file(path, content, overwrite=overwrite, append=append)
    summary = (
        f"{'created' if result.created else 'updated'} {result.path}: {result.lines} lines, {result.bytes} bytes"
        if result.ok
        else result.error
    )
    run_id = save_fileop_run(
        kind="write",
        command_text=f"sage write {path}",
        output=summary,
        exit_code=0 if result.ok else 1,
        summary=summary,
        caller="mcp",
    )
    return {
        "success": result.ok,
        "run_id": run_id,
        "created": result.created,
        "bytes": result.bytes,
        "lines": result.lines,
        "sha256": result.sha256,
        "content_tokens_not_echoed": result.content_tokens,
        "snapshot": result.snapshot,
        "error": result.error,
    }


def sage_edit_file(path: str, old: str, new: str, replace_all: bool = False) -> dict[str, Any]:
    """Exact string replacement with compact preview and undo snapshot."""
    from ..fileops import edit_file, save_fileop_run

    result = edit_file(path, old, new, replace_all=replace_all)
    summary = (
        f"edited {result.path}: {result.replacements} replacement(s) on lines {result.changed_lines[:10]}"
        if result.ok
        else result.error
    )
    run_id = save_fileop_run(
        kind="edit",
        command_text=f"sage edit {path}",
        output=f"{summary}\n{result.preview}" if result.ok else summary,
        exit_code=0 if result.ok else 1,
        summary=summary,
        caller="mcp",
    )
    return {
        "success": result.ok,
        "run_id": run_id,
        "replacements": result.replacements,
        "changed_lines": result.changed_lines,
        "preview": result.preview,
        "snapshot": result.snapshot,
        "error": result.error,
    }


def sage_glob(pattern: str, root: str = ".", limit: int = 50) -> dict[str, Any]:
    """Find files by pattern, newest first."""
    from ..fileops import glob_files, render_glob, save_fileop_run

    result = glob_files(pattern, root, limit=limit)
    rendered = render_glob(result)
    run_id = save_fileop_run(
        kind="glob",
        command_text=f"sage glob {pattern} {root}",
        output=rendered,
        exit_code=0 if not result.error else 2,
        summary=f"glob {pattern!r}: {result.total_found} files",
        caller="mcp",
    )
    return {
        "success": not result.error,
        "run_id": run_id,
        "total_found": result.total_found,
        "files": [path for path, _, _ in result.files],
        "content": rendered,
        "error": result.error,
    }


def sage_tree(root: str = ".", depth: int = 3, limit: int = 200) -> dict[str, Any]:
    """Compact directory overview."""
    from ..fileops import save_fileop_run, tree_view

    rendered = tree_view(root, depth=depth, limit=limit)
    ok = not rendered.startswith("sage tree error")
    run_id = save_fileop_run(
        kind="tree",
        command_text=f"sage tree {root}",
        output=rendered,
        exit_code=0 if ok else 2,
        summary=f"tree {root} depth={depth}",
        caller="mcp",
    )
    return {"success": ok, "run_id": run_id, "content": rendered}


def sage_show_raw(run_id: int | None = None) -> dict[str, Any]:
    """Recover exact stored output for a run."""
    from ..artifacts import load_raw_output
    from ..store import latest_run

    if run_id is None:
        record = latest_run()
        if record is None:
            return {"success": False, "error": "No command history yet."}
        run_id = record.id
    raw = load_raw_output(run_id)
    if raw is None:
        return {"success": False, "error": f"Run #{run_id} not found."}
    return {
        "success": True,
        "run_id": run_id,
        "source": raw["source"],
        "integrity": raw["verified"],
        "stdout": raw["stdout"],
        "stderr": raw["stderr"],
    }
