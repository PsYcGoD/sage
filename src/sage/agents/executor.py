"""Active, DB-backed execution for SAGE agents."""

from __future__ import annotations

import json
import os
import re
import shlex
import socket
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ..security import redact_text
from ..store import connect, data_dir
from .registry import AgentSpec, agent_skill_profile, ensure_default_agents, select_agents_for_command

AGENT_STATES = {"queued", "running", "waiting_for_tool", "completed", "failed", "cancelled"}
RESULT_CONTRACT_KEYS = {
    "finding",
    "evidence",
    "severity",
    "confidence",
    "next_action",
    "follow_up_command",
}


class AgentPlanner:
    """Select and order agents from command, output, errors, file signals, and ML prediction."""

    def plan(
        self,
        *,
        command: str,
        output: str,
        exit_code: int,
        summary: str,
        limit: int = 24,
    ) -> list[AgentSpec]:
        text = f"{command}\n{summary}\n{output}".lower()
        specs = select_agents_for_command(text, limit=limit)
        scored: list[tuple[float, AgentSpec]] = []
        ml_failed = _ml_predicts_failure(command)

        for spec in specs:
            score = 1.0
            score += sum(0.4 for trigger in spec.triggers if trigger in text)
            if exit_code and spec.type in {"debug", "test", "dependency"}:
                score += 1.0
            if ml_failed and spec.type in {"debug", "test", "code"}:
                score += 0.5
            if _extract_file_paths(command, output) and spec.type in {"code", "security", "frontend"}:
                score += 0.35
            if _looks_like_package_log(text) and spec.type == "dependency":
                score += 1.0
            if _looks_like_test_output(text) and spec.type == "test":
                score += 1.0
            scored.append((score, spec))

        scored.sort(key=lambda item: (-item[0], item[1].type))
        return [spec for _, spec in scored[:limit]]


def execute_agents_for_run(
    *,
    run_id: int,
    command: str,
    stdout: str,
    stderr: str,
    exit_code: int,
    summary: str,
    limit: int = 24,
) -> list[dict[str, Any]]:
    """Queue selected agents, process the active worker queue, and return ranked results."""
    ensure_default_agents()
    output = f"{stdout}\n{stderr}".strip()
    specs = AgentPlanner().plan(command=command, output=output, exit_code=exit_code, summary=summary, limit=limit)
    enqueue_agent_runs(
        run_id=run_id,
        specs=specs,
        command=command,
        output=output,
        exit_code=exit_code,
        summary=summary,
    )
    worker_count = _agent_worker_count(len(specs))
    run_agent_worker_once(run_id=run_id, max_workers=worker_count, limit=max(len(specs), 16))
    return [task["result"] | {"task_id": task["id"]} for task in get_agent_tasks_for_run(run_id)]


def _agent_worker_count(agent_count: int) -> int:
    configured = os.environ.get("SAGE_AGENT_WORKERS", "").strip()
    if configured.isdigit():
        return max(1, min(24, int(configured)))
    return max(1, min(24, agent_count))


def enqueue_agent_runs(
    *,
    run_id: int,
    specs: list[AgentSpec],
    command: str,
    output: str,
    exit_code: int,
    summary: str,
    max_attempts: int = 2,
) -> list[int]:
    """Create durable queued agent work items."""
    now = _now()
    queued_ids: list[int] = []
    with connect() as conn:
        for spec in specs:
            agent_id = _agent_id(spec)
            duplicate = conn.execute(
                """
                SELECT id FROM agent_runs
                WHERE run_id = ? AND agent_id = ? AND status IN ('queued', 'running', 'completed')
                """,
                (run_id, agent_id),
            ).fetchone()
            if duplicate:
                queued_ids.append(int(duplicate["id"]))
                continue
            payload = {
                "agent_type": spec.type,
                "agent_name": spec.name,
                "command": command,
                "output": output,
                "exit_code": exit_code,
                "summary": summary,
            }
            cursor = conn.execute(
                """
                INSERT INTO agent_runs
                  (run_id, agent_id, status, task_description, payload, attempts, max_attempts,
                   created_at, updated_at)
                VALUES (?, ?, 'queued', ?, ?, 0, ?, ?, ?)
                """,
                (
                    run_id,
                    agent_id,
                    f"{spec.name} analysis for run #{run_id}: {command}",
                    json.dumps(payload, ensure_ascii=False),
                    max_attempts,
                    now,
                    now,
                ),
            )
            queued_ids.append(int(cursor.lastrowid))
        conn.commit()
    return queued_ids


def run_agent_worker_once(
    *,
    run_id: int | None = None,
    max_workers: int = 4,
    lease_seconds: int = 120,
    limit: int = 16,
) -> list[dict[str, Any]]:
    """Pull queued/expired agent work from SQLite and execute it with leases."""
    claimed = _claim_agent_runs(run_id=run_id, limit=limit, lease_seconds=lease_seconds)
    if not claimed:
        return []

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, max_workers), thread_name_prefix="sage-agent") as pool:
        future_map = {pool.submit(_execute_claimed_agent_run, item): item for item in claimed}
        for future in as_completed(future_map):
            item = future_map[future]
            try:
                results.append(future.result())
            except Exception as exc:
                results.append(_fail_agent_run(item, exc))
    return results


def cancel_agent_runs(run_id: int | None = None) -> int:
    """Cancel queued/running agent work."""
    now = _now()
    sql = "UPDATE agent_runs SET status = 'cancelled', cancelled_at = ?, updated_at = ? WHERE status IN ('queued', 'running', 'waiting_for_tool')"
    params: tuple[Any, ...] = (now, now)
    if run_id is not None:
        sql += " AND run_id = ?"
        params = (now, now, run_id)
    with connect() as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return int(cur.rowcount or 0)


def get_agent_tasks_for_run(run_id: int) -> list[dict[str, Any]]:
    """Return stored agent task results for a run, ranked by usefulness."""
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                t.id,
                t.run_id,
                t.status,
                t.task_description,
                t.result,
                t.started_at,
                t.completed_at,
                t.rank_score,
                t.agent_run_id,
                a.name as agent_name,
                a.type as agent_type
            FROM agent_tasks t
            LEFT JOIN agents a ON a.id = t.agent_id
            WHERE t.run_id = ?
            ORDER BY t.rank_score DESC, t.id ASC
            """,
            (run_id,),
        ).fetchall()

    tasks = []
    for row in rows:
        try:
            result = json.loads(row["result"] or "{}")
        except json.JSONDecodeError:
            result = {"raw": row["result"]}
        tasks.append(
            {
                "id": row["id"],
                "run_id": row["run_id"],
                "agent_run_id": row["agent_run_id"],
                "agent_name": row["agent_name"],
                "agent_type": row["agent_type"],
                "status": row["status"],
                "description": row["task_description"],
                "result": result,
                "started_at": row["started_at"],
                "completed_at": row["completed_at"],
                "rank_score": row["rank_score"],
            }
        )
    return tasks


def get_agent_runs_for_run(run_id: int) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT ar.*, a.name as agent_name, a.type as agent_type
            FROM agent_runs ar
            LEFT JOIN agents a ON a.id = ar.agent_id
            WHERE ar.run_id = ?
            ORDER BY ar.id ASC
            """,
            (run_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def _claim_agent_runs(*, run_id: int | None, limit: int, lease_seconds: int) -> list[dict[str, Any]]:
    now = _now()
    lease_until = (datetime.now(timezone.utc) + timedelta(seconds=lease_seconds)).isoformat(timespec="seconds")
    owner = f"{socket.gethostname()}:{time.time_ns()}"
    where = """
        ar.status IN ('queued', 'running', 'waiting_for_tool')
        AND (ar.next_attempt_at = '' OR datetime(ar.next_attempt_at) <= datetime(?))
        AND (
            ar.status = 'queued'
            OR ar.lease_expires_at = ''
            OR datetime(ar.lease_expires_at) <= datetime(?)
        )
    """
    params: list[Any] = [now, now]
    if run_id is not None:
        where += " AND ar.run_id = ?"
        params.append(run_id)

    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT ar.*, a.name as agent_name, a.type as agent_type, a.capabilities as capabilities
            FROM agent_runs ar
            JOIN agents a ON a.id = ar.agent_id
            WHERE {where}
            ORDER BY ar.id ASC
            LIMIT ?
            """,
            (*params, limit),
        ).fetchall()
        claimed: list[dict[str, Any]] = []
        status_agent_ids: list[int] = []
        for row in rows:
            cur = conn.execute(
                """
                UPDATE agent_runs
                SET status = 'running', lease_owner = ?, lease_expires_at = ?, started_at = COALESCE(NULLIF(started_at, ''), ?),
                    attempts = attempts + 1, updated_at = ?
                WHERE id = ? AND status IN ('queued', 'running', 'waiting_for_tool')
                """,
                (owner, lease_until, now, now, row["id"]),
            )
            if cur.rowcount:
                item = dict(row)
                item["lease_owner"] = owner
                claimed.append(item)
                status_agent_ids.append(int(row["agent_id"]))
        for agent_id in status_agent_ids:
            conn.execute(
                "UPDATE agents SET status = ?, last_active = ? WHERE id = ?",
                ("running", now, agent_id),
            )
        conn.commit()
    return claimed


def _execute_claimed_agent_run(item: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    payload = json.loads(item.get("payload") or "{}")
    spec = AgentSpec(
        type=str(item["agent_type"]),
        name=str(item["agent_name"]),
        capabilities=tuple(json.loads(item.get("capabilities") or "[]")),
        triggers=(),
        description="",
    )
    result = _run_agent_analysis(
        spec,
        str(payload.get("command", "")),
        str(payload.get("output", "")),
        int(payload.get("exit_code", 0)),
        str(payload.get("summary", "")),
    )
    result = _maybe_llm_enrich(spec, payload, result)
    result = _normalize_contract(result)
    result = _add_handoff_and_conflicts(result, run_id=int(item["run_id"]))
    duration_ms = int((time.perf_counter() - started) * 1000)
    artifact = _write_agent_artifact(int(item["run_id"]), int(item["id"]), result)
    rank_score = _rank_result(result)
    task_id = _store_agent_task(
        run_id=int(item["run_id"]),
        agent_id=int(item["agent_id"]),
        agent_run_id=int(item["id"]),
        description=str(item.get("task_description") or ""),
        status="completed",
        result=result,
        started_at=str(item.get("started_at") or _now()),
        completed_at=_now(),
        rank_score=rank_score,
    )
    now = _now()
    with connect() as conn:
        conn.execute(
            """
            UPDATE agent_runs
            SET status = 'completed', task_id = ?, result = ?, finished_at = ?, duration_ms = ?,
                confidence = ?, output_artifact_path = ?, lease_owner = '', lease_expires_at = '',
                updated_at = ?
            WHERE id = ?
            """,
            (
                task_id,
                json.dumps(result, ensure_ascii=False),
                now,
                duration_ms,
                float(result.get("confidence", 0.0)),
                str(artifact),
                now,
                int(item["id"]),
            ),
        )
        conn.commit()
    _set_agent_status(int(item["agent_id"]), "idle")
    _increment_quality_metric(int(item["agent_id"]), str(item["agent_type"]), "completed")
    return result


def _fail_agent_run(item: dict[str, Any], exc: Exception) -> dict[str, Any]:
    attempts = int(item.get("attempts") or 0) + 1
    max_attempts = int(item.get("max_attempts") or 2)
    now_dt = datetime.now(timezone.utc)
    will_retry = attempts < max_attempts
    status = "queued" if will_retry else "failed"
    backoff_seconds = min(300, 2 ** max(1, attempts))
    next_attempt = (now_dt + timedelta(seconds=backoff_seconds)).isoformat(timespec="seconds") if will_retry else ""
    result = _normalize_contract(
        {
            "agent": item.get("agent_name", "Agent"),
            "agent_type": item.get("agent_type", "generic"),
            "status": "failed",
            "finding": "agent failed while analyzing run",
            "evidence": [str(exc)],
            "severity": "medium",
            "confidence": 0.2,
            "next_action": "Retry the agent task or inspect the stored payload.",
            "follow_up_command": f"sage agents tasks --run-id {item.get('run_id')}",
            "actions": ["Inspect agent_runs.error.", "Retry after the backoff window."],
            "error": str(exc),
        }
    )
    with connect() as conn:
        conn.execute(
            """
            UPDATE agent_runs
            SET status = ?, attempts = ?, error = ?, next_attempt_at = ?, lease_owner = '',
                lease_expires_at = '', updated_at = ?
            WHERE id = ?
            """,
            (status, attempts, str(exc), next_attempt, now_dt.isoformat(timespec="seconds"), int(item["id"])),
        )
        conn.commit()
    _set_agent_status(int(item["agent_id"]), "idle")
    _increment_quality_metric(int(item["agent_id"]), str(item["agent_type"]), "failed")
    return result


def _run_agent_analysis(
    spec: AgentSpec,
    command: str,
    output: str,
    exit_code: int,
    summary: str,
) -> dict[str, Any]:
    base = {
        "agent": spec.name,
        "agent_type": spec.type,
        "status": "completed",
        "command": command,
        "exit_code": exit_code,
        "signals": _common_signals(command, output, summary),
        "severity": _severity(exit_code, output, summary),
        "confidence": _confidence(spec, command, output, summary),
        "token_strategy": _token_strategy(output),
        "skill_profile": list(agent_skill_profile(spec.type)),
        "agent_brief": _agent_brief(spec.type),
    }
    analyzers = {
        "debug": _debug_result,
        "test": _test_result,
        "dependency": _dependency_result,
        "database": _database_result,
        "frontend": _frontend_result,
        "security": _security_result,
        "performance": _performance_result,
        "docs": _docs_result,
        "workflow": _workflow_result,
        "release": _release_result,
        "research": _research_result,
        "code": _code_result,
        "architecture": _architecture_result,
        "review": _review_result,
        "refactor": _refactor_result,
        "devops": _devops_result,
        "api": _api_result,
        "ml": _ml_result,
        "memory": _memory_result,
        "telemetry": _telemetry_result,
        "privacy": _privacy_result,
        "redteam": _redteam_result,
        "blueteam": _blueteam_result,
        "auditor": _auditor_result,
    }
    base.update(analyzers.get(spec.type, _generic_result)(command, output, exit_code, summary))
    return base


def _common_signals(command: str, output: str, summary: str) -> dict[str, Any]:
    text = f"{command}\n{output}\n{summary}".lower()
    return {
        "has_error": any(token in text for token in ["error", "exception", "failed", "traceback"]),
        "has_tests": _looks_like_test_output(text),
        "has_packages": _looks_like_package_log(text),
        "output_lines": len(output.splitlines()) if output else 0,
        "summary_lines": len(summary.splitlines()) if summary else 0,
        "files": _extract_file_paths(command, output)[:12],
    }


def _agent_brief(agent_type: str) -> str:
    briefs = {
        "code": "Checks implementation shape, local patterns, and scoped edit risk.",
        "debug": "Finds the first useful failure signal and the smallest reproduction path.",
        "test": "Looks for regression coverage, failing tests, and narrow verification commands.",
        "research": "Flags when current or primary-source evidence is needed.",
        "security": "Checks secrets, auth, permissions, and dependency risk.",
        "performance": "Looks for latency, timeout, and measurement signals before optimization.",
        "docs": "Keeps user-facing claims tied to verified evidence.",
        "dependency": "Diagnoses package manager, environment, and missing-module failures.",
        "workflow": "Checks CI, automation, and YAML/pipeline behavior.",
        "database": "Protects schema compatibility, migrations, and persisted data.",
        "frontend": "Reviews UI polish, layout, accessibility, and animation craft.",
        "release": "Checks packaging, versioning, and release readiness.",
        "architecture": "Checks module boundaries, contracts, and system-level tradeoffs.",
        "review": "Looks for behavioral regressions and missing tests.",
        "refactor": "Keeps cleanup behavior-preserving and separately verifiable.",
        "devops": "Checks runtime, ports, services, and deployment assumptions.",
        "api": "Protects request/response contracts and client compatibility.",
        "ml": "Checks model features, thresholds, and validation behavior.",
        "memory": "Checks session persistence, context reuse, and token waste.",
        "telemetry": "Verifies proof counters, metrics, and sync behavior stay safe.",
        "privacy": "Checks redaction, retention, local-only handling, and PII risk.",
        "redteam": "Models plausible abuse paths and attacker-controlled inputs.",
        "blueteam": "Checks mitigations, hardening, and control effectiveness.",
        "auditor": "Ranks evidence, severity, assumptions, and next actions.",
    }
    return briefs.get(agent_type, "Performs specialist analysis for this run.")


def _debug_result(command: str, output: str, exit_code: int, summary: str) -> dict[str, Any]:
    text = output or summary
    first_error = _first_important_line(text, ["traceback", "error", "exception", "failed", "fatal"])
    traceback = _traceback_block(text)
    return {
        "finding": "failure needs investigation" if exit_code else "no runtime failure detected",
        "evidence": ([first_error] if first_error else []) + ([traceback] if traceback else []),
        "first_error": first_error,
        "traceback": traceback,
        "next_action": "Inspect the first error line and rerun the narrowest failing command." if exit_code else "No debug action needed.",
        "follow_up_command": _rerun_command(command),
        "actions": [
            "Open the earliest error line, not the final wrapper footer.",
            "Rerun the smallest failing command through sage run.",
            "Store the fix as a regression note if the same pattern repeats.",
        ] if exit_code else ["Keep this run as a clean baseline."],
    }


def _test_result(command: str, output: str, exit_code: int, summary: str) -> dict[str, Any]:
    text = f"{output}\n{summary}"
    failed_tests = _failed_tests(text)
    passed = _count_pattern(text, r"\bPASSED\b|\bpassed\b")
    skipped = _count_pattern(text, r"\bSKIPPED\b|\bskipped\b")
    follow_up = _narrow_test_command(command, failed_tests)
    return {
        "passed_mentions": passed,
        "failed_mentions": len(failed_tests),
        "skipped_mentions": skipped,
        "finding": "test failures detected" if failed_tests or exit_code else "tests look clean",
        "evidence": failed_tests[:8] or _important_lines(text, ["failed", "assert", "error"])[:6],
        "next_action": "Open the first failing test block and add a regression test after fixing." if failed_tests or exit_code else "Keep this run as baseline evidence.",
        "follow_up_command": follow_up,
        "actions": [
            "Run the narrowest failing test with -q.",
            "Capture the assertion and fixture setup before editing.",
            "After fixing, rerun this exact test and then the surrounding file.",
        ] if failed_tests or exit_code else ["Use this passing run as baseline evidence."],
    }


def _dependency_result(command: str, output: str, exit_code: int, summary: str) -> dict[str, Any]:
    text = output or summary
    important = _important_lines(text, ["modulenotfounderror", "no module named", "cannot find module", "missing", "not found", "eresolve", "enoent"])
    managers = _package_managers(command, text)
    return {
        "dependency_signals": important[:8],
        "package_managers": managers,
        "finding": "dependency issue likely" if important or managers else "no dependency issue detected",
        "evidence": important[:8] or managers,
        "next_action": "Install or pin the missing package, then rerun through SAGE." if important else "No dependency action needed.",
        "follow_up_command": _rerun_command(command),
        "actions": [
            "Check the active Python/Node environment.",
            "Prefer project manifest updates over global installs.",
            "Rerun the command after dependency resolution.",
        ] if important or managers else ["No dependency action needed."],
    }


def _database_result(command: str, output: str, exit_code: int, summary: str) -> dict[str, Any]:
    important = _important_lines(output or summary, ["sqlite", "database", "schema", "migration", "sql"])
    return {
        "finding": "database/schema path involved" if important else "no database signal detected",
        "evidence": important[:8],
        "next_action": "Check schema migration compatibility and preserve existing data." if important else "No database action needed.",
        "follow_up_command": "sage doctor" if important else "",
        "actions": ["Inspect schema changes.", "Use additive migrations.", "Verify existing rows still read."] if important else ["No database action needed."],
    }


def _frontend_result(command: str, output: str, exit_code: int, summary: str) -> dict[str, Any]:
    important = _important_lines(output or summary, ["gui", "ui", "window", "card", "render", "layout", "tkinter"])
    return {
        "finding": "frontend/gui path involved" if important else "no frontend signal detected",
        "evidence": important[:8],
        "next_action": "Smoke test visual state and check text fitting after changes." if important else "No frontend action needed.",
        "follow_up_command": "python -m sage gui" if important else "",
        "actions": ["Smoke test startup.", "Check text fitting.", "Check terminal streaming."] if important else ["No frontend action needed."],
    }


def _security_result(command: str, output: str, exit_code: int, summary: str) -> dict[str, Any]:
    text = f"{command}\n{output}\n{summary}"
    redacted = redact_text(text)
    important = _important_lines(text, ["secret", "token", "password", "auth", "permission", "vulnerability"])
    return {
        "finding": "security-sensitive signal found" if important or redacted.count else "no security signal detected",
        "evidence": important[:8] + ([f"redaction_matches={redacted.count}"] if redacted.count else []),
        "redaction_matches": redacted.count,
        "next_action": "Verify secrets are not printed or committed." if important or redacted.count else "No security action needed.",
        "follow_up_command": "sage privacy report" if important or redacted.count else "",
        "actions": ["Redact secrets before sharing.", "Check ignored env/config files.", "Avoid storing credentials."] if important or redacted.count else ["No security action needed."],
    }


def _performance_result(command: str, output: str, exit_code: int, summary: str) -> dict[str, Any]:
    lines = _important_lines(output or summary, ["slow", "timeout", "duration", "seconds", "ms"])
    return {
        "finding": "performance signal found" if lines else "no performance signal detected",
        "evidence": lines[:8],
        "next_action": "Measure before optimizing; keep benchmark output in run history." if lines else "No performance action needed.",
        "follow_up_command": _rerun_command(command) if lines else "",
        "actions": ["Record baseline duration.", "Change one bottleneck at a time.", "Rerun benchmark."] if lines else ["No performance action needed."],
    }


def _docs_result(command: str, output: str, exit_code: int, summary: str) -> dict[str, Any]:
    touched_docs = any(token in command.lower() for token in ["readme", ".md", "docs", "changelog"])
    return {
        "finding": "documentation command detected" if touched_docs else "no docs signal detected",
        "evidence": _extract_file_paths(command, output)[:8],
        "next_action": "Keep claims aligned with verified test results." if touched_docs else "No docs action needed.",
        "follow_up_command": "",
        "actions": ["Use exact tested numbers.", "Keep UTF-8 valid.", "Avoid unverified claims."] if touched_docs else ["No docs action needed."],
    }


def _workflow_result(command: str, output: str, exit_code: int, summary: str) -> dict[str, Any]:
    important = _important_lines(output or summary, ["workflow", "yaml", "ci", "pipeline"])
    return {
        "finding": "workflow path involved" if important else "no workflow signal detected",
        "evidence": important[:8],
        "next_action": "Validate YAML and execute the narrow workflow before broad CI." if important else "No workflow action needed.",
        "follow_up_command": _rerun_command(command) if important else "",
        "actions": ["Validate YAML syntax.", "Run individual workflow steps.", "Keep failure output inspectable."] if important else ["No workflow action needed."],
    }


def _release_result(command: str, output: str, exit_code: int, summary: str) -> dict[str, Any]:
    signal = any(token in command.lower() for token in ["build", "version", "package", "release"])
    return {
        "finding": "release readiness path involved" if signal else "no release signal detected",
        "evidence": _important_lines(output or summary, ["build", "wheel", "version", "package"])[:8],
        "next_action": "Run packaging checks and verify metadata before release." if signal else "No release action needed.",
        "follow_up_command": _rerun_command(command) if signal else "",
        "actions": ["Check metadata.", "Run compile/tests.", "Record verification commands."] if signal else ["No release action needed."],
    }


def _research_result(command: str, output: str, exit_code: int, summary: str) -> dict[str, Any]:
    return {
        "finding": "research requested" if "research" in command.lower() else "no research action needed",
        "evidence": _important_lines(output or summary, ["http", "source", "latest"])[:8],
        "next_action": "Use current primary sources when external facts can change.",
        "follow_up_command": "",
        "actions": ["Use primary/current sources.", "Summarize evidence.", "Store source links when relevant."],
    }


def _code_result(command: str, output: str, exit_code: int, summary: str) -> dict[str, Any]:
    files = _inspect_files(_extract_file_paths(command, output))
    return {
        "finding": "code command detected" if any(token in command.lower() for token in ["python", "node", "git", "pytest"]) else "general command",
        "evidence": files or _important_lines(output or summary, ["modified", "changed", "diff", "compile"])[:8],
        "file_inspection": files,
        "next_action": "Keep edits scoped and rerun the focused verification command.",
        "follow_up_command": _rerun_command(command),
        "actions": ["Read local patterns before editing.", "Keep unrelated dirty files untouched.", "Run focused verification."],
    }


def _keyword_agent_result(
    *,
    name: str,
    command: str,
    output: str,
    summary: str,
    keywords: list[str],
    finding_hit: str,
    finding_miss: str,
    next_action: str,
    actions: list[str],
) -> dict[str, Any]:
    evidence = _important_lines(output or summary or command, keywords)[:8]
    return {
        "finding": finding_hit if evidence or any(token in command.lower() for token in keywords) else finding_miss,
        "evidence": evidence,
        "next_action": next_action,
        "follow_up_command": _rerun_command(command) if evidence else "",
        "actions": actions,
        "agent_focus": name,
    }


def _architecture_result(command: str, output: str, exit_code: int, summary: str) -> dict[str, Any]:
    return _keyword_agent_result(name="architecture", command=command, output=output, summary=summary, keywords=["architecture", "boundary", "contract", "module", "interface"], finding_hit="architecture/design signal found", finding_miss="no architecture risk detected", next_action="Check module boundaries and public contracts before editing.", actions=["Identify ownership boundaries.", "Avoid cross-layer shortcuts.", "Keep public contracts explicit."])


def _review_result(command: str, output: str, exit_code: int, summary: str) -> dict[str, Any]:
    return _keyword_agent_result(name="review", command=command, output=output, summary=summary, keywords=["diff", "review", "regression", "risk", "changed"], finding_hit="review/regression signal found", finding_miss="no review-specific risk detected", next_action="Review behavior changes and missing tests before shipping.", actions=["Scan diff for behavioral changes.", "Look for missing regression tests.", "Prioritize user-visible risk."])


def _refactor_result(command: str, output: str, exit_code: int, summary: str) -> dict[str, Any]:
    return _keyword_agent_result(name="refactor", command=command, output=output, summary=summary, keywords=["refactor", "cleanup", "dedupe", "rename", "simplify"], finding_hit="refactor signal found", finding_miss="no refactor signal detected", next_action="Keep refactors behavior-preserving and separately verified.", actions=["Separate cleanup from feature work.", "Preserve public behavior.", "Run focused tests before broad tests."])


def _devops_result(command: str, output: str, exit_code: int, summary: str) -> dict[str, Any]:
    return _keyword_agent_result(name="devops", command=command, output=output, summary=summary, keywords=["deploy", "docker", "server", "runtime", "env", "port"], finding_hit="deployment/runtime signal found", finding_miss="no devops signal detected", next_action="Verify runtime environment, ports, and deployment assumptions.", actions=["Check env vars.", "Validate service startup.", "Record deployment command output."])


def _api_result(command: str, output: str, exit_code: int, summary: str) -> dict[str, Any]:
    return _keyword_agent_result(name="api", command=command, output=output, summary=summary, keywords=["api", "endpoint", "http", "json", "schema", "status"], finding_hit="API contract signal found", finding_miss="no API signal detected", next_action="Validate request/response shape and compatibility.", actions=["Check schema changes.", "Verify status codes.", "Keep clients backward compatible."])


def _ml_result(command: str, output: str, exit_code: int, summary: str) -> dict[str, Any]:
    return _keyword_agent_result(name="ml", command=command, output=output, summary=summary, keywords=["ml", "model", "predict", "training", "feature", "confidence"], finding_hit="ML/prediction signal found", finding_miss="no ML signal detected", next_action="Validate model thresholds and feature behavior with deterministic tests.", actions=["Check feature extraction.", "Validate thresholds.", "Compare model and heuristic behavior."])


def _memory_result(command: str, output: str, exit_code: int, summary: str) -> dict[str, Any]:
    return _keyword_agent_result(name="memory", command=command, output=output, summary=summary, keywords=["memory", "session", "history", "context", "persistent"], finding_hit="memory/session signal found", finding_miss="no memory signal detected", next_action="Verify session ids, saved turns, and context reuse.", actions=["Reuse existing session ids.", "Avoid duplicate context injection.", "Hydrate saved history on load."])


def _telemetry_result(command: str, output: str, exit_code: int, summary: str) -> dict[str, Any]:
    return _keyword_agent_result(name="telemetry", command=command, output=output, summary=summary, keywords=["telemetry", "metrics", "sync", "proof", "dashboard", "tokens"], finding_hit="telemetry/proof signal found", finding_miss="no telemetry signal detected", next_action="Verify counters stay privacy-safe and non-blocking.", actions=["Check queue behavior.", "Keep raw data local at low levels.", "Avoid blocking command completion."])


def _privacy_result(command: str, output: str, exit_code: int, summary: str) -> dict[str, Any]:
    return _keyword_agent_result(name="privacy", command=command, output=output, summary=summary, keywords=["privacy", "redact", "retention", "secret", "token", "pii"], finding_hit="privacy/redaction signal found", finding_miss="no privacy signal detected", next_action="Verify redaction, retention, and local-only guarantees.", actions=["Scan for secrets.", "Check retention policy.", "Avoid exposing paths or raw logs."])


def _redteam_result(command: str, output: str, exit_code: int, summary: str) -> dict[str, Any]:
    return _keyword_agent_result(name="redteam", command=command, output=output, summary=summary, keywords=["attack", "exploit", "abuse", "threat", "malware", "prompt injection"], finding_hit="attack-path signal found", finding_miss="no obvious attack-path signal detected", next_action="Model how this could be abused before trusting automation.", actions=["Identify attacker-controlled inputs.", "Look for unsafe execution paths.", "Preserve evidence for mitigation."])


def _blueteam_result(command: str, output: str, exit_code: int, summary: str) -> dict[str, Any]:
    return _keyword_agent_result(name="blueteam", command=command, output=output, summary=summary, keywords=["mitigate", "harden", "control", "defense", "allowlist", "denylist"], finding_hit="mitigation/hardening signal found", finding_miss="no mitigation signal detected", next_action="Check whether controls actually block the identified abuse path.", actions=["Verify deny/allow policy.", "Prefer least privilege.", "Add tests for controls."])


def _auditor_result(command: str, output: str, exit_code: int, summary: str) -> dict[str, Any]:
    return _keyword_agent_result(name="auditor", command=command, output=output, summary=summary, keywords=["audit", "evidence", "priority", "risk", "finding"], finding_hit="audit/evidence signal found", finding_miss="no audit signal detected", next_action="Synthesize findings by severity, evidence, and next action.", actions=["Rank risks.", "Tie every finding to evidence.", "Separate confirmed issues from assumptions."])


def _generic_result(command: str, output: str, exit_code: int, summary: str) -> dict[str, Any]:
    return {
        "finding": "agent completed generic analysis",
        "evidence": _important_lines(output or summary, ["error", "warning", "failed"])[:6],
        "next_action": "Review stored output and rerun if needed.",
        "follow_up_command": _rerun_command(command),
        "actions": ["Review stored output and rerun if needed."],
    }


def _normalize_contract(result: dict[str, Any]) -> dict[str, Any]:
    if "next_action" not in result and "next_step" in result:
        result["next_action"] = result["next_step"]
    if "next_step" not in result and "next_action" in result:
        result["next_step"] = result["next_action"]
    result.setdefault("finding", "agent completed analysis")
    result.setdefault("evidence", [])
    if isinstance(result["evidence"], str):
        result["evidence"] = [result["evidence"]]
    result["evidence"] = [str(item)[:500] for item in (result.get("evidence") or [])[:12]]
    result.setdefault("severity", "info")
    result.setdefault("confidence", 0.5)
    result["confidence"] = max(0.0, min(1.0, float(result.get("confidence") or 0.0)))
    result.setdefault("next_action", "Review the stored run output.")
    result.setdefault("next_step", result["next_action"])
    result.setdefault("follow_up_command", "")
    result.setdefault("actions", [result["next_action"]])
    result["contract_version"] = "agent-result-v1"
    result["contract_valid"] = all(key in result for key in RESULT_CONTRACT_KEYS)
    return result


def _add_handoff_and_conflicts(result: dict[str, Any], *, run_id: int) -> dict[str, Any]:
    agent_type = str(result.get("agent_type", ""))
    severity = str(result.get("severity", "info"))
    if agent_type == "debug" and severity in {"medium", "high"}:
        result["handoff"] = ["dependency", "test"]
    elif agent_type == "dependency":
        result["handoff"] = ["test"]
    else:
        result["handoff"] = []

    with connect() as conn:
        rows = conn.execute("SELECT result FROM agent_tasks WHERE run_id = ?", (run_id,)).fetchall()
    prior = []
    for row in rows:
        try:
            prior.append(json.loads(row["result"] or "{}"))
        except json.JSONDecodeError:
            pass
    result["conflicts"] = [
        {
            "with": item.get("agent_type"),
            "reason": "severity disagreement",
        }
        for item in prior
        if item.get("severity") and item.get("severity") != severity and item.get("finding") != result.get("finding")
    ][:3]
    return result


def _rank_result(result: dict[str, Any]) -> float:
    severity_weight = {"high": 4.0, "medium": 3.0, "low": 2.0, "info": 1.0}.get(str(result.get("severity")), 1.0)
    evidence_bonus = min(1.0, len(result.get("evidence") or []) * 0.15)
    handoff_bonus = 0.2 if result.get("handoff") else 0.0
    return severity_weight + float(result.get("confidence") or 0) + evidence_bonus + handoff_bonus


def _write_agent_artifact(run_id: int, agent_run_id: int, result: dict[str, Any]) -> Path:
    path = data_dir() / "agent-artifacts" / f"run-{run_id}"
    path.mkdir(parents=True, exist_ok=True)
    artifact = path / f"agent-run-{agent_run_id}.json"
    artifact.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return artifact


def _store_agent_task(
    *,
    run_id: int,
    agent_id: int,
    agent_run_id: int,
    description: str,
    status: str,
    result: dict[str, Any],
    started_at: str,
    completed_at: str,
    rank_score: float,
) -> int:
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO agent_tasks
            (run_id, agent_id, agent_run_id, task_description, status, result, started_at, completed_at, rank_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                agent_id,
                agent_run_id,
                description,
                status,
                json.dumps(result, ensure_ascii=False),
                started_at,
                completed_at,
                rank_score,
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def _agent_id(spec: AgentSpec) -> int:
    with connect() as conn:
        row = conn.execute("SELECT id FROM agents WHERE type = ? AND name = ?", (spec.type, spec.name)).fetchone()
        if not row:
            ensure_default_agents()
            row = conn.execute("SELECT id FROM agents WHERE type = ? AND name = ?", (spec.type, spec.name)).fetchone()
        return int(row["id"])


def _set_agent_status(agent_id: int, status: str) -> None:
    now = _now()
    with connect() as conn:
        conn.execute("UPDATE agents SET status = ?, last_active = ? WHERE id = ?", (status, now, agent_id))
        conn.commit()


def _increment_quality_metric(agent_id: int, agent_type: str, metric: str) -> None:
    now = _now()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO agent_quality_metrics (agent_id, agent_type, metric, value, updated_at)
            VALUES (?, ?, ?, 1, ?)
            ON CONFLICT(agent_id, metric) DO UPDATE SET
                value = value + 1,
                updated_at = excluded.updated_at
            """,
            (agent_id, agent_type, metric, now),
        )
        conn.commit()


def _important_lines(text: str, keywords: list[str]) -> list[str]:
    lines = []
    for line in text.splitlines():
        clean = line.strip()
        if clean and any(keyword in clean.lower() for keyword in keywords):
            lines.append(clean[:240])
    return lines


def _first_important_line(text: str, keywords: list[str]) -> str:
    lines = _important_lines(text, keywords)
    return lines[0] if lines else ""


def _traceback_block(text: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if "Traceback" in line:
            block = []
            for item in lines[index:index + 30]:
                block.append(item)
                if re.search(r"(Error|Exception):", item):
                    break
            return "\n".join(block)[:2000]
    return ""


def _failed_tests(text: str) -> list[str]:
    found = []
    for line in text.splitlines():
        if re.search(r"\bFAILED\b|\bfailed\b", line):
            clean = line.strip()
            if clean and clean not in found:
                found.append(clean[:240])
    return found


def _count_pattern(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, flags=re.IGNORECASE))


def _severity(exit_code: int, output: str, summary: str) -> str:
    text = f"{output}\n{summary}".lower()
    if "fatal" in text or "traceback" in text or "permission denied" in text:
        return "high"
    if exit_code:
        return "medium"
    if any(token in text for token in ["warning", "deprecated", "slow"]):
        return "low"
    return "info"


def _confidence(spec: AgentSpec, command: str, output: str, summary: str) -> float:
    text = f"{command}\n{output}\n{summary}".lower()
    trigger_hits = sum(1 for trigger in spec.triggers if trigger in text)
    evidence_hits = len(_important_lines(text, ["error", "failed", "warning", "traceback", "missing"]))
    return min(0.97, 0.55 + trigger_hits * 0.1 + min(0.2, evidence_hits * 0.02))


def _token_strategy(output: str) -> dict[str, Any]:
    lines = output.splitlines()
    unique = len(set(lines)) if lines else 0
    repeated = len(lines) - unique
    return {
        "output_lines": len(lines),
        "repeated_lines": repeated,
        "recommendation": "compress repeated output and keep failures" if repeated > 10 else "keep concise summary and important lines",
    }


def _extract_file_paths(command: str, output: str) -> list[str]:
    text = f"{command}\n{output}"
    candidates = re.findall(r"[\w./\\:-]+\.(?:py|js|ts|tsx|jsx|json|toml|yaml|yml|md|txt|css|html)", text)
    seen: set[str] = set()
    files = []
    for item in candidates:
        normalized = item.strip(",:;()[]{}\"'")
        if normalized and normalized not in seen:
            seen.add(normalized)
            files.append(normalized)
    return files


def _inspect_files(paths: list[str]) -> list[str]:
    details = []
    for raw in paths[:5]:
        path = Path(raw)
        if not path.exists() or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines = text.splitlines()
        interesting = [line.strip() for line in lines if re.match(r"\s*(class|def|function|export|import|from)\b", line)]
        details.append(f"{raw}: {len(lines)} lines; symbols={interesting[:5]}")
    return details


def _package_managers(command: str, text: str) -> list[str]:
    managers = []
    lowered = f"{command}\n{text}".lower()
    for manager in ["npm", "pip", "uv", "poetry", "pnpm", "yarn"]:
        if manager in lowered:
            managers.append(manager)
    return managers


def _looks_like_package_log(text: str) -> bool:
    return any(token in text for token in ["npm warn", "pip install", "uv pip", "poetry", "pnpm", "yarn", "requirements.txt", "package.json"])


def _looks_like_test_output(text: str) -> bool:
    return any(token in text for token in ["pytest", "unittest", "jest", " passed", " failed", "test session starts"])


def _rerun_command(command: str) -> str:
    return f"sage run -- {command}" if command else ""


def _narrow_test_command(command: str, failed_tests: list[str]) -> str:
    if failed_tests:
        match = re.search(r"([\w./\\-]+\.py::[\w:\[\].-]+)", failed_tests[0])
        if match:
            return f"sage run -- python -m pytest {match.group(1)} -q"
    return _rerun_command(command)


def llm_backend() -> str:
    """Opt-in LLM backend for agent analysis, e.g. SAGE_AGENT_LLM=claude.

    Empty (default) keeps agents fully deterministic and offline.
    """
    return os.environ.get("SAGE_AGENT_LLM", "").strip()


def _maybe_llm_enrich(spec: AgentSpec, payload: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """Optionally refine a deterministic result with an LLM CLI.

    Any failure (missing CLI, timeout, bad JSON) leaves the deterministic
    result untouched, so enabling the backend can never make agents worse.
    """
    backend = llm_backend()
    if not backend:
        return result
    prompt = (
        f"You are the SAGE {spec.name} ({spec.type}). Analyze this command run and respond "
        "with ONLY a JSON object with keys: finding (string), evidence (array of strings), "
        "severity (high|medium|low|info), confidence (0..1), next_action (string), "
        "follow_up_command (string), actions (array of strings).\n"
        f"Command: {payload.get('command', '')}\n"
        f"Exit code: {payload.get('exit_code', 0)}\n"
        f"Summary: {str(payload.get('summary', ''))[:1000]}\n"
        f"Output (redacted excerpt):\n{redact_text(str(payload.get('output', ''))[:4000]).text}"
    )
    try:
        completed = subprocess.run(
            [*shlex.split(backend), "-p", prompt, "--output-format", "text"],
            capture_output=True,
            text=True,
            timeout=int(os.environ.get("SAGE_AGENT_LLM_TIMEOUT", "60")),
        )
        if completed.returncode != 0:
            return result
        raw = completed.stdout.strip()
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not match:
            return result
        parsed = json.loads(match.group(0))
        if not isinstance(parsed, dict) or "finding" not in parsed:
            return result
        merged = dict(result)
        for key in ("finding", "evidence", "severity", "confidence", "next_action", "follow_up_command", "actions"):
            if parsed.get(key):
                merged[key] = parsed[key]
        merged["llm_backed"] = True
        merged["llm_backend"] = backend
        return merged
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, ValueError):
        return result


def _ml_predicts_failure(command: str) -> bool:
    lowered = command.lower()
    # Keep the agent planner fast inside `sage run`; full ML scoring remains
    # available through `sage run --predict` and `sage predict`.
    return "prediction: likely to fail" in lowered or "ml_prediction=fail" in lowered


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
