"""Tests for run-linked agent task execution."""

import asyncio

from sage.agents import execute_agents_for_run, get_agent_runs_for_run, get_agent_tasks_for_run
from sage.agents.specialized.code_agent import CodeAgent
from sage.runner import run_command
from sage.store import connect, save_run


def test_execute_agents_for_run_stores_tasks(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    run_id = save_run(
        project=str(tmp_path),
        command="pytest tests",
        exit_code=1,
        duration_ms=123,
        stdout="tests/test_app.py::test_one FAILED\nsqlite migration error",
        stderr="AssertionError: failed",
        summary="pytest failed with sqlite migration error",
    )

    results = execute_agents_for_run(
        run_id=run_id,
        command="pytest tests",
        stdout="tests/test_app.py::test_one FAILED\nsqlite migration error",
        stderr="AssertionError: failed",
        exit_code=1,
        summary="pytest failed with sqlite migration error",
    )
    tasks = get_agent_tasks_for_run(run_id)

    assert results
    assert len(results) == 7
    assert len(tasks) == len(results)
    assert {task["run_id"] for task in tasks} == {run_id}
    assert "test" in {task["agent_type"] for task in tasks}
    assert all(task["status"] == "completed" for task in tasks)
    assert all(task["result"].get("finding") for task in tasks)
    assert all(task["result"].get("severity") for task in tasks)
    assert all("confidence" in task["result"] for task in tasks)
    assert all(task["result"].get("actions") for task in tasks)
    assert all(task["result"].get("token_strategy") for task in tasks)
    assert all(task["result"].get("skill_profile") for task in tasks)
    assert all(task["result"].get("agent_brief") for task in tasks)
    assert all(task["result"].get("contract_valid") for task in tasks)
    assert all("evidence" in task["result"] for task in tasks)

    agent_runs = get_agent_runs_for_run(run_id)
    assert agent_runs
    assert {row["status"] for row in agent_runs} == {"completed"}
    assert all(row["duration_ms"] >= 0 for row in agent_runs)
    assert all(row["output_artifact_path"] for row in agent_runs)
    assert tasks == sorted(tasks, key=lambda item: item["rank_score"], reverse=True)


def test_agent_task_queue_rebinds_for_new_event_loop():
    agent = CodeAgent("code-agent-main")

    async def queue_id():
        return id(agent.ensure_task_queue())

    first_queue_id = asyncio.run(queue_id())
    second_queue_id = asyncio.run(queue_id())

    assert first_queue_id != second_queue_id


def test_execute_agents_for_run_covers_seven_specialists(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    run_id = save_run(
        project=str(tmp_path),
        command="python build with a missing module and a leaked token",
        exit_code=1,
        duration_ms=45,
        stdout="ModuleNotFoundError: No module named 'x'; SyntaxError: invalid syntax; secret=abc",
        stderr="",
        summary="seven specialist smoke",
    )

    execute_agents_for_run(
        run_id=run_id,
        command="python build with a missing module and a leaked token",
        stdout="ModuleNotFoundError: No module named 'x'; SyntaxError: invalid syntax; secret=abc",
        stderr="",
        exit_code=1,
        summary="seven specialist smoke",
        limit=8,
    )

    agent_types = {task["agent_type"] for task in get_agent_tasks_for_run(run_id)}

    # The trimmed roster is exactly these seven deterministic specialists.
    assert agent_types == {"code", "debug", "test", "research", "security", "dependency", "frontend"}


def test_run_command_executes_agents_for_saved_run(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("SAGE_SUPPRESS_FOOTER", "1")
    monkeypatch.delenv("SAGE_DISABLE_AGENTS", raising=False)

    exit_code = run_command(["python", "-c", "print('agent integration ok')"])

    assert exit_code == 0
    with connect() as conn:
        run = conn.execute("SELECT id FROM runs ORDER BY id DESC LIMIT 1").fetchone()
        assert run is not None
        task_count = conn.execute(
            "SELECT COUNT(*) FROM agent_tasks WHERE run_id = ?",
            (run["id"],),
        ).fetchone()[0]
        agent_run_count = conn.execute(
            "SELECT COUNT(*) FROM agent_runs WHERE run_id = ?",
            (run["id"],),
        ).fetchone()[0]

    assert task_count > 0
    assert agent_run_count > 0
