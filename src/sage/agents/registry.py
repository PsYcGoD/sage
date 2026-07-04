"""Default SAGE agent catalog and command routing."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class AgentSpec:
    """A built-in SAGE agent role."""

    type: str
    name: str
    capabilities: tuple[str, ...]
    triggers: tuple[str, ...]
    description: str


DEFAULT_AGENT_SPECS: tuple[AgentSpec, ...] = (
    AgentSpec("code", "Code Agent", ("implement", "refactor", "review"), ("python", "node", "code", "refactor", "implement"), "Writes and reviews code changes."),
    AgentSpec("debug", "Debug Agent", ("trace", "root_cause", "fix_plan"), ("error", "traceback", "failed", "exception"), "Investigates failures and root causes."),
    AgentSpec("test", "Test Agent", ("pytest", "coverage", "regression"), ("test", "pytest", "unittest", "jest"), "Runs and improves tests."),
    AgentSpec("research", "Research Agent", ("research", "compare", "summarize"), ("research", "find", "compare", "latest"), "Gathers and synthesizes external or local evidence."),
    AgentSpec("security", "Security Agent", ("audit", "secrets", "dependency_risk"), ("security", "secret", "token", "auth", "vulnerability"), "Checks security-sensitive changes."),
    AgentSpec("performance", "Performance Agent", ("profile", "optimize", "benchmark"), ("slow", "performance", "profile", "optimize"), "Finds bottlenecks and optimizations."),
    AgentSpec("docs", "Docs Agent", ("readme", "docs", "release_notes"), ("readme", "docs", "document", "changelog"), "Keeps docs and user-facing text accurate."),
    AgentSpec("dependency", "Dependency Agent", ("install", "package", "env"), ("pip", "npm", "yarn", "install", "requirements"), "Handles packages and environment issues."),
    AgentSpec("workflow", "Workflow Agent", ("ci", "automation", "yaml"), ("workflow", "ci", "pipeline", "yaml"), "Builds and validates workflows."),
    AgentSpec("database", "Database Agent", ("schema", "migration", "queries"), ("database", "sqlite", "schema", "migration", "db"), "Protects data, schemas, and migrations."),
    AgentSpec("frontend", "Frontend Agent", ("gui", "ui", "accessibility"), ("gui", "ui", "frontend", "window", "card"), "Improves interface reliability and polish."),
    AgentSpec("release", "Release Agent", ("version", "package", "ship"), ("release", "build", "version", "package"), "Checks packaging and release readiness."),
    AgentSpec("architecture", "Architecture Agent", ("boundaries", "contracts", "system_design"), ("architecture", "design", "boundary", "contract", "system"), "Checks module boundaries and system design."),
    AgentSpec("review", "Review Agent", ("code_review", "risk", "regression"), ("review", "pr", "diff", "regression", "risk"), "Reviews changes for bugs and regressions."),
    AgentSpec("refactor", "Refactor Agent", ("simplify", "deduplicate", "migration"), ("refactor", "cleanup", "dedupe", "simplify"), "Plans safe refactors without changing behavior."),
    AgentSpec("devops", "DevOps Agent", ("deploy", "runtime", "ops"), ("deploy", "docker", "server", "runtime", "ops"), "Checks deployment and runtime operations."),
    AgentSpec("api", "API Agent", ("contracts", "http", "schema"), ("api", "endpoint", "http", "json", "schema"), "Protects API contracts and integrations."),
    AgentSpec("ml", "ML Agent", ("prediction", "validation", "features"), ("ml", "model", "predict", "training", "feature"), "Checks model, feature, and validation behavior."),
    AgentSpec("memory", "Memory Agent", ("session", "persistence", "context"), ("memory", "session", "history", "context", "persistent"), "Protects session memory and context reuse."),
    AgentSpec("telemetry", "Telemetry Agent", ("metrics", "sync", "proof"), ("telemetry", "metrics", "sync", "proof", "dashboard"), "Checks metrics, sync, and proof counters."),
    AgentSpec("privacy", "Privacy Agent", ("redaction", "retention", "local_data"), ("privacy", "redact", "retention", "pii", "local-only"), "Checks privacy, retention, and redaction behavior."),
    AgentSpec("redteam", "Red Team Agent", ("attack_paths", "abuse_cases", "threats"), ("red-team", "attack", "exploit", "abuse", "threat"), "Finds plausible abuse paths and exploit chains."),
    AgentSpec("blueteam", "Blue Team Agent", ("mitigation", "hardening", "controls"), ("blue-team", "mitigate", "harden", "control", "defense"), "Evaluates mitigations and hardening controls."),
    AgentSpec("auditor", "Auditor Agent", ("synthesis", "priorities", "evidence"), ("audit", "auditor", "evidence", "priority", "risk assessment"), "Synthesizes findings into prioritized evidence."),
)


def ensure_default_agents() -> int:
    """Ensure all built-in agents exist as idle DB records."""
    from ..store import connect

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    created = 0
    with connect() as conn:
        for spec in DEFAULT_AGENT_SPECS:
            existing = conn.execute(
                "SELECT id FROM agents WHERE type = ? AND name = ?",
                (spec.type, spec.name),
            ).fetchone()
            if existing:
                continue
            conn.execute(
                """
                INSERT INTO agents (name, type, status, capabilities, created_at, last_active)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (spec.name, spec.type, "idle", json.dumps(list(spec.capabilities)), now, now),
            )
            created += 1
        conn.commit()
    return created


def list_default_agent_specs() -> list[dict]:
    """Return the built-in agent catalog for UI/API display."""
    return [
        {
            "type": spec.type,
            "name": spec.name,
            "capabilities": list(spec.capabilities),
            "triggers": list(spec.triggers),
            "description": spec.description,
        }
        for spec in DEFAULT_AGENT_SPECS
    ]


def select_agents_for_command(command: str, limit: int = 4) -> list[AgentSpec]:
    """Pick the most relevant agents for a command or user request."""
    text = command.lower()
    scored: list[tuple[int, AgentSpec]] = []
    for spec in DEFAULT_AGENT_SPECS:
        score = sum(1 for trigger in spec.triggers if trigger in text)
        if score:
            scored.append((score, spec))

    if not scored:
        scored = [(1, DEFAULT_AGENT_SPECS[0]), (1, DEFAULT_AGENT_SPECS[1])]

    scored.sort(key=lambda item: (-item[0], item[1].type))
    return [spec for _, spec in scored[:limit]]
