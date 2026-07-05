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

AGENT_SKILL_PROFILES: dict[str, tuple[str, ...]] = {
    "code": ("repo pattern reading", "scoped implementation", "safe edits", "focused verification"),
    "debug": ("root-cause tracing", "first-error isolation", "failure reproduction", "fix planning"),
    "test": ("regression design", "pytest/unittest/jest signals", "coverage risk", "narrow reruns"),
    "research": ("primary-source evidence", "current-fact checks", "comparison", "source synthesis"),
    "security": ("secrets handling", "auth review", "dependency risk", "permission boundaries"),
    "performance": ("baseline measurement", "bottleneck detection", "benchmark discipline", "latency signals"),
    "docs": ("claim verification", "release notes", "user-facing clarity", "README accuracy"),
    "dependency": ("package managers", "environment diagnosis", "version pinning", "install failures"),
    "workflow": ("CI steps", "YAML validation", "automation safety", "pipeline debugging"),
    "database": ("SQLite/schema safety", "migration review", "query compatibility", "data preservation"),
    "frontend": ("interface taste", "layout polish", "accessibility", "animation craft", "Framer Motion/Motion patterns"),
    "release": ("packaging", "version readiness", "metadata checks", "shipping risk"),
    "architecture": ("module boundaries", "contracts", "system design", "ownership lines"),
    "review": ("bug finding", "behavioral regression", "missing tests", "risk prioritization"),
    "refactor": ("deduplication", "behavior preservation", "migration sequencing", "simplification"),
    "devops": ("runtime environment", "ports/services", "deployment assumptions", "ops checks"),
    "api": ("HTTP contracts", "JSON/schema shape", "client compatibility", "status semantics"),
    "ml": ("feature validation", "model thresholds", "prediction quality", "training data hygiene"),
    "memory": ("session persistence", "context reuse", "history hydration", "token waste control"),
    "telemetry": ("proof counters", "privacy-safe metrics", "queue behavior", "sync reliability"),
    "privacy": ("redaction", "retention", "local-only guarantees", "PII minimization"),
    "redteam": ("abuse paths", "prompt injection", "exploit thinking", "attacker-controlled inputs"),
    "blueteam": ("mitigation", "hardening", "least privilege", "control verification"),
    "auditor": ("evidence synthesis", "severity ranking", "assumption separation", "final triage"),
}

_UNIVERSAL_PRIORITY = {
    "code": 24,
    "debug": 23,
    "test": 22,
    "review": 21,
    "auditor": 20,
    "architecture": 19,
    "security": 18,
    "frontend": 17,
}


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
            "skill_profile": list(agent_skill_profile(spec.type)),
            "skill_file": agent_skill_file(spec.type),
        }
        for spec in DEFAULT_AGENT_SPECS
    ]


def agent_skill_profile(agent_type: str) -> tuple[str, ...]:
    """Return the built-in specialist training profile for an agent type."""
    return AGENT_SKILL_PROFILES.get(agent_type, ())


def agent_skill_file(agent_type: str) -> str | None:
    """Return the bundled SKILL.md folder bound to an agent type, if any.

    Bindings live in ``sage.skills.AGENT_SKILL_FILES`` (code -> coding-master-pro,
    research -> research-master-pro, frontend -> design-master-pro). The skill is
    auto-installed into the Claude Code / Codex skill folders so the CLI that
    drives the run loads it and routes by the skill's description.
    """
    try:
        from ..skills import agent_skill_file as _lookup

        return _lookup(agent_type)
    except Exception:
        return None


def select_agents_for_command(command: str, limit: int | None = None) -> list[AgentSpec]:
    """Return all agents, relevance-sorted, so every run gets full fan-out."""
    text = command.lower()
    scored: list[tuple[int, AgentSpec]] = []
    for spec in DEFAULT_AGENT_SPECS:
        trigger_score = sum(100 for trigger in spec.triggers if trigger in text)
        capability_score = sum(3 for capability in spec.capabilities if capability.replace("_", " ") in text)
        skill_score = sum(2 for skill in agent_skill_profile(spec.type) if skill.lower() in text)
        score = trigger_score + capability_score + skill_score + _UNIVERSAL_PRIORITY.get(spec.type, 0)
        scored.append((score, spec))

    scored.sort(key=lambda item: (-item[0], item[1].type))
    if limit is None or limit <= 0:
        limit = len(DEFAULT_AGENT_SPECS)
    return [spec for _, spec in scored[:limit]]
