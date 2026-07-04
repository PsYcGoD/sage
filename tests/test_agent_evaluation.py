"""Tests for the deterministic agent evaluation harness."""

import json

from sage.agents.evaluation import (
    DEFAULT_SCENARIOS,
    SCORE_DIMENSIONS,
    evaluate_agents,
    write_eval_report,
)
from sage.agents.executor import llm_backend


def test_default_scenarios_cover_core_agents():
    covered = {scenario.agent_type for scenario in DEFAULT_SCENARIOS}
    assert {"debug", "test", "dependency", "security", "code"} <= covered


def test_evaluation_report_shape():
    report = evaluate_agents()
    assert report["harness_version"] == "agent-eval-v1"
    assert report["scenario_count"] == len(DEFAULT_SCENARIOS)
    assert report["dimensions"] == list(SCORE_DIMENSIONS)
    for scenario in report["scenarios"]:
        assert set(scenario["checks"]) == set(SCORE_DIMENSIONS)


def test_agents_meet_quality_floor():
    """Every agent must score >= 80% and overall >= 90% on fixtures."""
    report = evaluate_agents()
    assert report["overall_score"] >= 0.9, report
    for agent_type, data in report["agents"].items():
        assert data["score"] >= 0.8, (agent_type, data)


def test_contract_validity_is_universal():
    report = evaluate_agents()
    for scenario in report["scenarios"]:
        assert scenario["checks"]["contract"] is True, scenario


def test_agent_type_filter():
    report = evaluate_agents(agent_types={"debug"})
    assert set(report["agents"]) == {"debug"}
    assert report["scenario_count"] == sum(
        1 for scenario in DEFAULT_SCENARIOS if scenario.agent_type == "debug"
    )


def test_write_eval_report(tmp_path):
    report = evaluate_agents(agent_types={"test"})
    path = write_eval_report(report, tmp_path / "eval.json")
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["overall_score"] == report["overall_score"]


def test_llm_backend_defaults_off(monkeypatch):
    monkeypatch.delenv("SAGE_AGENT_LLM", raising=False)
    assert llm_backend() == ""
    monkeypatch.setenv("SAGE_AGENT_LLM", "claude")
    assert llm_backend() == "claude"


def test_llm_enrich_falls_back_on_missing_cli(monkeypatch):
    """Enabling a broken LLM backend must never corrupt deterministic results."""
    from sage.agents.executor import _maybe_llm_enrich
    from sage.agents.registry import DEFAULT_AGENT_SPECS

    monkeypatch.setenv("SAGE_AGENT_LLM", "definitely-not-a-real-cli-xyz")
    spec = next(spec for spec in DEFAULT_AGENT_SPECS if spec.type == "debug")
    baseline = {"finding": "failure needs investigation", "severity": "high"}
    enriched = _maybe_llm_enrich(spec, {"command": "python x.py", "output": "boom", "exit_code": 1, "summary": ""}, dict(baseline))
    assert enriched == baseline
