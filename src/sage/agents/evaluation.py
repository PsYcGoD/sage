"""Deterministic evaluation harness for SAGE agents.

Scores each agent's analysis quality against fixture scenarios so
"agent reasoning quality" is a measured number instead of a claim.
Each scenario defines the run context (command, output, exit code,
summary) and the expected outcome (finding keyword, severity,
evidence keyword, follow-up pattern). The harness runs the real
analyzer pipeline (analysis -> contract normalization) and grades
five dimensions per scenario:

- contract:  result passes the agent-result-v1 contract
- finding:   finding text matches the expected keyword
- severity:  severity is in the accepted set for the scenario
- evidence:  at least one evidence line contains the expected keyword
- follow_up: follow-up command matches the expected pattern (or is
             correctly empty when no action is expected)

Reports aggregate per agent and overall, and can be exported as JSON
for public proof.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..store import data_dir
from .executor import _normalize_contract, _run_agent_analysis
from .registry import DEFAULT_AGENT_SPECS, AgentSpec

SCORE_DIMENSIONS = ("contract", "finding", "severity", "evidence", "follow_up")


@dataclass(frozen=True)
class EvalScenario:
    """One deterministic agent evaluation case."""

    scenario_id: str
    agent_type: str
    command: str
    output: str
    exit_code: int
    summary: str
    expect_finding: str
    expect_severity: tuple[str, ...]
    expect_evidence: str = ""
    expect_follow_up: str = ""
    expect_no_follow_up: bool = False


@dataclass
class ScenarioResult:
    scenario_id: str
    agent_type: str
    checks: dict[str, bool] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)

    @property
    def score(self) -> float:
        if not self.checks:
            return 0.0
        return sum(1 for ok in self.checks.values() if ok) / len(self.checks)


_PY_TRACEBACK = """Traceback (most recent call last):
  File "app/main.py", line 42, in <module>
    from missing_module import helper
ModuleNotFoundError: No module named 'missing_module'
"""

_PYTEST_FAILURE = """============================= test session starts =============================
collected 12 items

tests/test_auth.py::test_login PASSED                                    [  8%]
tests/test_auth.py::test_token_refresh FAILED                            [ 16%]
tests/test_api.py::test_health PASSED                                    [ 25%]

=================================== FAILURES ===================================
_____________________________ test_token_refresh ______________________________
E       AssertionError: assert 401 == 200
========================= 1 failed, 11 passed in 3.21s =========================
"""

_NPM_FAILURE = """npm WARN deprecated request@2.88.2: request has been deprecated
npm ERR! code ERESOLVE
npm ERR! ERESOLVE unable to resolve dependency tree
npm ERR! Found: react@18.2.0
npm ERR! Could not resolve dependency: peer react@"^17.0.0" from old-lib@1.0.0
"""

_SECRET_LEAK = """Deploy config loaded
export OPENAI_API_KEY=sk-proj-abcdef1234567890abcdef1234567890abcdef123456
Authorization: Bearer ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789
Deploy finished
"""

_CLEAN_PYTEST = """============================= test session starts =============================
collected 24 items

tests/test_core.py ........................                              [100%]
========================== 24 passed in 1.85s ==========================
"""

DEFAULT_SCENARIOS: tuple[EvalScenario, ...] = (
    EvalScenario(
        scenario_id="debug-python-traceback",
        agent_type="debug",
        command="python app/main.py",
        output=_PY_TRACEBACK,
        exit_code=1,
        summary="ModuleNotFoundError: No module named 'missing_module'",
        expect_finding="failure needs investigation",
        expect_severity=("high", "medium"),
        expect_evidence="ModuleNotFoundError",
        expect_follow_up=r"sage run -- python app/main\.py",
    ),
    EvalScenario(
        scenario_id="debug-clean-run",
        agent_type="debug",
        command="python -c \"print('ok')\"",
        output="ok",
        exit_code=0,
        summary="ok",
        expect_finding="no runtime failure detected",
        expect_severity=("info",),
    ),
    EvalScenario(
        scenario_id="test-pytest-failure",
        agent_type="test",
        command="python -m pytest tests/ -q",
        output=_PYTEST_FAILURE,
        exit_code=1,
        summary="1 failed, 11 passed",
        expect_finding="test failures detected",
        expect_severity=("high", "medium"),
        expect_evidence="test_token_refresh",
        expect_follow_up=r"pytest tests/test_auth\.py::test_token_refresh",
    ),
    EvalScenario(
        scenario_id="test-pytest-clean",
        agent_type="test",
        command="python -m pytest tests/ -q",
        output=_CLEAN_PYTEST,
        exit_code=0,
        summary="24 passed",
        expect_finding="tests look clean",
        expect_severity=("info", "low"),
    ),
    EvalScenario(
        scenario_id="dependency-npm-eresolve",
        agent_type="dependency",
        command="npm install",
        output=_NPM_FAILURE,
        exit_code=1,
        summary="npm ERR! ERESOLVE unable to resolve dependency tree",
        expect_finding="dependency issue likely",
        expect_severity=("high", "medium"),
        expect_evidence="ERESOLVE",
        expect_follow_up=r"sage run -- npm install",
    ),
    EvalScenario(
        scenario_id="dependency-pip-missing-module",
        agent_type="dependency",
        command="python train.py",
        output=_PY_TRACEBACK,
        exit_code=1,
        summary="No module named 'missing_module'",
        expect_finding="dependency issue likely",
        expect_severity=("high", "medium"),
        expect_evidence="No module named",
    ),
    EvalScenario(
        scenario_id="security-secret-leak",
        agent_type="security",
        command="bash deploy.sh",
        output=_SECRET_LEAK,
        exit_code=0,
        summary="Deploy finished",
        expect_finding="security-sensitive signal found",
        expect_severity=("high", "medium", "low", "info"),
        expect_evidence="redaction_matches",
        expect_follow_up=r"sage privacy report",
    ),
    EvalScenario(
        scenario_id="security-clean-output",
        agent_type="security",
        command="git status",
        output="On branch main\nnothing to commit, working tree clean",
        exit_code=0,
        summary="working tree clean",
        expect_finding="no security signal detected",
        expect_severity=("info", "low"),
        expect_no_follow_up=True,
    ),
    EvalScenario(
        scenario_id="code-python-file-context",
        agent_type="code",
        command="python src/sage/cli.py --help",
        output="usage: sage [-h] ...",
        exit_code=0,
        summary="usage help",
        expect_finding="code command detected",
        expect_severity=("info", "low"),
        expect_follow_up=r"sage run -- python src/sage/cli\.py --help",
    ),
)


def evaluate_agents(
    scenarios: tuple[EvalScenario, ...] = DEFAULT_SCENARIOS,
    *,
    agent_types: set[str] | None = None,
) -> dict[str, Any]:
    """Run every scenario through the real analyzer pipeline and grade it."""
    specs = {spec.type: spec for spec in DEFAULT_AGENT_SPECS}
    results: list[ScenarioResult] = []

    for scenario in scenarios:
        if agent_types and scenario.agent_type not in agent_types:
            continue
        spec = specs.get(scenario.agent_type) or AgentSpec(
            scenario.agent_type, f"{scenario.agent_type.title()} Agent", (), (), ""
        )
        raw = _run_agent_analysis(
            spec,
            scenario.command,
            scenario.output,
            scenario.exit_code,
            scenario.summary,
        )
        result = _normalize_contract(raw)
        results.append(_grade(scenario, result))

    return _build_report(results)


def _grade(scenario: EvalScenario, result: dict[str, Any]) -> ScenarioResult:
    checks: dict[str, bool] = {}
    checks["contract"] = bool(result.get("contract_valid"))
    checks["finding"] = scenario.expect_finding.lower() in str(result.get("finding", "")).lower()
    checks["severity"] = str(result.get("severity")) in scenario.expect_severity

    if scenario.expect_evidence:
        evidence = " ".join(str(item) for item in result.get("evidence") or [])
        checks["evidence"] = scenario.expect_evidence.lower() in evidence.lower()
    else:
        checks["evidence"] = True

    follow_up = str(result.get("follow_up_command", ""))
    if scenario.expect_no_follow_up:
        checks["follow_up"] = follow_up == ""
    elif scenario.expect_follow_up:
        checks["follow_up"] = re.search(scenario.expect_follow_up, follow_up) is not None
    else:
        checks["follow_up"] = True

    return ScenarioResult(scenario_id=scenario.scenario_id, agent_type=scenario.agent_type, checks=checks, result=result)


def _build_report(results: list[ScenarioResult]) -> dict[str, Any]:
    per_agent: dict[str, dict[str, Any]] = {}
    for item in results:
        bucket = per_agent.setdefault(
            item.agent_type,
            {"scenarios": 0, "score_sum": 0.0, "failed_checks": []},
        )
        bucket["scenarios"] += 1
        bucket["score_sum"] += item.score
        for name, ok in item.checks.items():
            if not ok:
                bucket["failed_checks"].append(f"{item.scenario_id}:{name}")

    agents = {
        agent_type: {
            "scenarios": data["scenarios"],
            "score": round(data["score_sum"] / data["scenarios"], 4) if data["scenarios"] else 0.0,
            "failed_checks": data["failed_checks"],
        }
        for agent_type, data in sorted(per_agent.items())
    }
    overall = round(sum(item.score for item in results) / len(results), 4) if results else 0.0
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "harness_version": "agent-eval-v1",
        "dimensions": list(SCORE_DIMENSIONS),
        "scenario_count": len(results),
        "overall_score": overall,
        "agents": agents,
        "scenarios": [
            {
                "scenario_id": item.scenario_id,
                "agent_type": item.agent_type,
                "score": round(item.score, 4),
                "checks": item.checks,
                "finding": item.result.get("finding"),
                "severity": item.result.get("severity"),
                "confidence": item.result.get("confidence"),
            }
            for item in results
        ],
    }


def write_eval_report(report: dict[str, Any], output: str | Path | None = None) -> Path:
    """Persist an evaluation report as JSON proof artifact."""
    if output:
        path = Path(output)
    else:
        folder = data_dir() / "agent-eval"
        folder.mkdir(parents=True, exist_ok=True)
        stamp = report.get("generated_at", "").replace(":", "-") or "report"
        path = folder / f"agent-eval-{stamp}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
