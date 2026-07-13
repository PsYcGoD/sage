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
        "description": "Explain why a previous SAGE command failed. Use after a non-zero command exit before editing code or retrying. Input is an optional SAGE run id; when omitted, the most recent failed run is analyzed. Returns a structured object with error_type, summary, root_cause, affected_files, and suggestions. Read-only: does not run commands, edit files, or contact external services.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command_id": {
                    "type": "integer",
                    "description": "Optional SAGE run id to analyze. Omit to analyze the most recent failed command.",
                    "minimum": 1
                }
            }
        }
    },
    {
        "name": "sage_suggest_fix",
        "description": "Suggest safe next steps for a failed SAGE command. Use after sage_explain_error when you want possible fixes but do not want them executed automatically. Returns a list of fix suggestions with explanation, confidence, and candidate command when available. Read-only: it never applies patches and never runs the suggested command.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command_id": {
                    "type": "integer",
                    "description": "Optional SAGE run id. Omit to use the most recent failed command.",
                    "minimum": 1
                }
            }
        }
    },
    {
        "name": "sage_spawn_agent",
        "description": "Run one focused local SAGE specialist for a bounded development task. Use only when a task clearly matches one specialization: code, test, debug, security, or performance. Returns agent_type, task, status, and a compact result. Side effects depend on the task: the specialist may inspect files, run local commands through SAGE, or propose edits. Do not use for open-ended chat, secrets, credentials, or tasks requiring external account access.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_type": {
                    "type": "string",
                    "enum": ["code", "test", "debug", "security", "performance"],
                    "description": "Specialization: code (implement), test (verify), debug (investigate), security (scan), performance (optimize)"
                },
                "task": {
                    "type": "string",
                    "description": "Concrete bounded task for the specialist, including target files or command context when known.",
                    "minLength": 8,
                    "maxLength": 1000
                }
            },
            "required": ["agent_type", "task"]
        }
    },
    {
        "name": "sage_run_workflow",
        "description": "Run a named local workflow through SAGE, such as test, lint, build, or ci. Use when the project has a repeatable workflow and you want one structured result instead of several separate shell calls. The workflow must be local/project-defined. Returns success, per-step status, duration, and compact output. Side effects: runs the workflow's local commands and may change files if the workflow commands do. Do not use for deployment unless the user explicitly requested deployment.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workflow_name": {
                    "type": "string",
                    "description": "Local workflow name, for example test, lint, build, or ci.",
                    "minLength": 1,
                    "maxLength": 80
                },
                "workflow_path": {
                    "type": "string",
                    "description": "Optional path to a local workflow YAML file. Omit to use the default project workflow file."
                }
            },
            "required": ["workflow_name"]
        }
    },
    {
        "name": "sage_get_history",
        "description": "List recent local SAGE command runs. Use to find a run_id for sage_show_raw, sage_explain_error, or sage_suggest_fix. Returns compact metadata such as run_id, command summary, exit_code, duration, timestamp, and compression ratio. Read-only: reads the local SAGE database only and does not execute commands.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of recent commands to retrieve (most recent first)",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 100
                },
                "failed_only": {
                    "type": "boolean",
                    "description": "Filter to commands with non-zero exit code only",
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
        "description": "Run one local shell command through SAGE with a purpose label. Use when you need command execution and want the result categorized as read, search, test, build, deploy, audit, or unknown. Returns exit_code, compact output, run_id, purpose, and agent metadata. Side effects are exactly the side effects of the command itself. Do not use for secrets, credential prompts, or deployment unless explicitly requested.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Single local shell command to execute through SAGE.", "minLength": 1, "maxLength": 4000},
                "purpose": {"type": "string", "enum": ["read", "search", "test", "build", "deploy", "audit", "unknown"], "description": "Why this command is being run - improves ML failure prediction", "default": "unknown"},
                "agent": {"type": "string", "description": "Name of the calling agent for multi-agent tracking", "default": "mcp"}
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
    },
    {
        "name": "sage_agentic_run",
        "description": "Run one local command with SAGE's failure-recovery loop. Use for development commands where automatic diagnosis and retry may help, such as tests or builds. Autonomy controls behavior: suggest reports fixes only, ask requires confirmation, auto may apply safe fixes and retry. Returns command result, recovery attempts, and verification status. Do not use for destructive commands, credential entry, production deploys, or external account changes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Single local command to execute with recovery enabled.", "minLength": 1, "maxLength": 4000},
                "max_retries": {"type": "integer", "description": "Maximum recovery attempts.", "default": 3, "minimum": 0, "maximum": 5},
                "autonomy": {"type": "string", "enum": ["suggest", "ask", "auto"], "description": "How autonomous: suggest (report only), ask (confirm), auto (fix automatically)", "default": "auto"}
            },
            "required": ["command"]
        }
    },
    {
        "name": "sage_agentic_fix",
        "description": "Return the single best fix candidate for a failed SAGE command. Use when you need one actionable repair plan, not a list of alternatives. Input is an optional SAGE run id; when omitted, the most recent failed run is analyzed. Returns fix_command, strategy, confidence, and explanation, or null when no safe fix is known. Read-only: does not execute the fix and does not edit files.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command_id": {"type": "integer", "description": "Optional SAGE run id of the failed command. Omit to use the most recent failed command.", "minimum": 1}
            }
        }
    },
    {
        "name": "sage_agentic_session",
        "description": "Get the current agentic session state — failure streak, recent errors, intent chain. Useful for understanding context before deciding next action.",
        "inputSchema": {
            "type": "object",
            "properties": {}
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

    # Inherit session_id from environment (set by parent AI process)
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
    
    result = {
        "success": exit_code == 0,
        "exit_code": exit_code,
        "run_id": record.id if record else None,
        "purpose": purpose,
        "agent": agent,
    }
    
    # Enhance with telemetry that terminal users see but MCP clients were missing
    if record is not None:
        with connect() as conn:
            # Query compression stats
            compression = conn.execute(
                """
                SELECT original_tokens, compressed_tokens, saved_tokens, strategy
                FROM context_compression
                WHERE run_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (record.id,)
            ).fetchone()
            
            if compression:
                saved = compression["saved_tokens"]
                original = compression["original_tokens"]
                compression_pct = f"{(saved / original * 100):.1f}%" if original > 0 else "0%"
                result["compression"] = {
                    "original_tokens": original,
                    "compressed_tokens": compression["compressed_tokens"],
                    "saved_tokens": saved,
                    "compression_ratio": compression_pct,
                    "strategy": compression["strategy"],
                }
            
            # Query agent execution results
            agents = conn.execute(
                """
                SELECT name, type, status
                FROM agents
                WHERE last_active >= datetime('now', '-5 seconds')
                ORDER BY last_active DESC
                """,
            ).fetchall()
            
            if agents:
                result["agents"] = {
                    "count": len(agents),
                    "completed": [dict(row) for row in agents],
                    "names": [row["name"] for row in agents],
                }
            
            # Add summary and duration
            result["duration_ms"] = record.duration_ms
            result["summary"] = record.summary
    
    return result


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


# --- Agentic Loop Tools ---

def sage_agentic_run(command: str, max_retries: int = 3, autonomy: str = "auto") -> dict[str, Any]:
    """Run a command with the full agentic loop (auto-retry and fix on failure)."""
    from ..agentic.engine import Autonomy
    from ..agentic.loop import AgenticLoop

    autonomy_map = {"suggest": Autonomy.SUGGEST, "ask": Autonomy.ASK, "auto": Autonomy.AUTO}
    level = autonomy_map.get(autonomy, Autonomy.AUTO)

    loop = AgenticLoop(autonomy=level, max_retries=max_retries)
    result = loop.run(command)
    return {
        "success": result.final_exit_code == 0,
        "command": result.original_command,
        "exit_code": result.final_exit_code,
        "state": result.state.value,
        "attempts": result.attempts,
        "fixes_applied": result.fixes_applied,
        "message": result.message,
    }


def sage_agentic_fix(command_id: int = None) -> dict[str, Any]:
    """Auto-fix the last failed command using the agentic fixer."""
    from ..agentic.fixer import suggest_fix
    from ..store import connect, latest_run

    if command_id:
        from ..store import connect
        with connect() as conn:
            row = conn.execute("SELECT * FROM runs WHERE id = ?", (command_id,)).fetchone()
    else:
        record = latest_run()
        if record is None:
            return {"success": False, "error": "No command history."}
        from ..store import connect
        with connect() as conn:
            row = conn.execute("SELECT * FROM runs WHERE id = ?", (record.id,)).fetchone()

    if not row:
        return {"success": False, "error": "Command not found."}
    if row["exit_code"] == 0:
        return {"success": False, "error": "Command succeeded — nothing to fix."}

    stderr = row.get("summary", "") or ""
    fix = suggest_fix(row["command"], stderr)
    if fix is None:
        return {"success": False, "error": "No known fix pattern matched this error."}

    return {
        "success": True,
        "strategy": fix.strategy,
        "fix_command": fix.fix_command,
        "explanation": fix.explanation,
        "confidence": fix.confidence,
        "destructive": fix.destructive,
    }


def sage_agentic_session() -> dict[str, Any]:
    """Get the current agentic session state (history, patterns, intent)."""
    from ..agentic.session import get_session

    session = get_session()
    return {
        "success": True,
        "failure_streak": session.failure_streak,
        "total_commands": len(session.history),
        "total_fixes_applied": session.total_fixes_applied,
        "total_fixes_succeeded": session.total_fixes_succeeded,
        "recent_failures": [
            {"command": r.command, "exit_code": r.exit_code, "error": r.stderr_tail[:200]}
            for r in session.recent_errors(5)
        ],
        "intent_chain": session.intent_chain,
    }
