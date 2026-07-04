"""Tests for run-linked agent task execution."""

from sage.agents import execute_agents_for_run, get_agent_runs_for_run, get_agent_tasks_for_run
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
    assert len(results) == 24
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


def test_execute_agents_for_run_exercises_expanded_agents(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    run_id = save_run(
        project=str(tmp_path),
        command="audit persistent session memory telemetry privacy red-team blue-team",
        exit_code=0,
        duration_ms=45,
        stdout="context retention, metrics proof, redaction, attack mitigation evidence",
        stderr="",
        summary="expanded agent catalog smoke",
    )

    execute_agents_for_run(
        run_id=run_id,
        command="audit persistent session memory telemetry privacy red-team blue-team",
        stdout="context retention, metrics proof, redaction, attack mitigation evidence",
        stderr="",
        exit_code=0,
        summary="expanded agent catalog smoke",
        limit=8,
    )

    agent_types = {task["agent_type"] for task in get_agent_tasks_for_run(run_id)}

    assert {"memory", "telemetry", "privacy"} <= agent_types
    assert {"redteam", "blueteam"} & agent_types


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
