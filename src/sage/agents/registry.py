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
    # Seven deterministic specialists — real pattern-based analysis, zero tokens.
    # code/research/frontend embody their bound skills (coding/research/design)
    # as heuristic checklists; debug/test/dependency/security do proven parsing.
    AgentSpec("code", "Code Agent", ("implement", "refactor", "review"), ("python", "node", "code", "refactor", "implement"), "Inspects code changes: syntax, scoped edits, leaked secrets."),
    AgentSpec("debug", "Debug Agent", ("trace", "root_cause", "fix_plan"), ("error", "traceback", "failed", "exception"), "Investigates failures and root causes."),
    AgentSpec("test", "Test Agent", ("pytest", "coverage", "regression"), ("test", "pytest", "unittest", "jest"), "Runs and improves tests."),
    AgentSpec("research", "Research Agent", ("research", "compare", "summarize"), ("research", "find", "compare", "latest"), "Checks sources and flags stale/unsourced claims."),
    AgentSpec("security", "Security Agent", ("audit", "secrets", "dependency_risk"), ("security", "secret", "token", "auth", "vulnerability"), "Checks security-sensitive changes."),
    AgentSpec("dependency", "Dependency Agent", ("install", "package", "env"), ("pip", "npm", "yarn", "install", "requirements"), "Handles packages and environment issues."),
    AgentSpec("frontend", "Frontend Agent", ("gui", "ui", "accessibility"), ("gui", "ui", "frontend", "window", "card"), "Checks UI render errors, accessibility, and layout."),
)

AGENT_SKILL_PROFILES: dict[str, tuple[str, ...]] = {
    "code": ("repo pattern reading", "scoped implementation", "safe edits", "focused verification"),
    "debug": ("root-cause tracing", "first-error isolation", "failure reproduction", "fix planning"),
    "test": ("regression design", "pytest/unittest/jest signals", "coverage risk", "narrow reruns"),
    "research": ("primary-source evidence", "current-fact checks", "comparison", "source synthesis"),
    "security": ("secrets handling", "auth review", "dependency risk", "permission boundaries"),
    "dependency": ("package managers", "environment diagnosis", "version pinning", "install failures"),
    "frontend": ("interface taste", "layout polish", "accessibility", "animation craft", "Framer Motion/Motion patterns"),
}

_UNIVERSAL_PRIORITY = {
    "code": 24,
    "debug": 23,
    "test": 22,
    "security": 21,
    "frontend": 20,
    "research": 19,
    "dependency": 18,
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
