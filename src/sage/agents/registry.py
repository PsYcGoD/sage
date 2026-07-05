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
    AgentSpec("code", "Code Agent", ("implement", "refactor", "review"), ("code", "coding", "implement", "implementation", "refactor", "rewrite", "function", "class", "module", "method", "bugfix", "patch", "edit", "modify", "compile", "syntax", "python", "javascript", "typescript", "node", "api", "endpoint", "logic", "algorithm", "repository"), "Inspects code changes: syntax, scoped edits, leaked secrets."),
    AgentSpec("debug", "Debug Agent", ("trace", "root_cause", "fix_plan"), ("debug", "error", "traceback", "failed", "failure", "exception", "crash", "stacktrace", "stack trace", "broken", "hang", "freeze", "timeout", "regression", "root cause", "diagnose", "issue", "bug", "fix", "panic", "fatal", "cannot", "missing", "invalid", "slow"), "Investigates failures and root causes."),
    AgentSpec("test", "Test Agent", ("pytest", "coverage", "regression"), ("test", "tests", "testing", "pytest", "unittest", "jest", "vitest", "playwright", "coverage", "regression", "assert", "assertion", "fixture", "mock", "snapshot", "ci", "failing test", "passed", "failed", "rerun", "spec", "e2e", "unit", "integration", "benchmark"), "Runs and improves tests."),
    AgentSpec("research", "Research Agent", ("research", "compare", "summarize"), ("research", "find", "compare", "latest", "current", "source", "sources", "citation", "citations", "verify", "fact check", "look up", "market", "competitor", "paper", "study", "docs", "documentation", "release notes", "changelog", "pricing", "law", "regulation", "news", "evidence", "benchmark"), "Checks sources and flags stale/unsourced claims."),
    AgentSpec("security", "Security Agent", ("audit", "secrets", "dependency_risk"), ("security", "secure", "secret", "secrets", "token", "password", "auth", "oauth", "credential", "credentials", "api key", "vulnerability", "exploit", "injection", "xss", "csrf", "permission", "permissions", "privacy", "redact", "pii", "encrypt", "decrypt", "audit", "malware"), "Checks security-sensitive changes."),
    AgentSpec("dependency", "Dependency Agent", ("install", "package", "env"), ("dependency", "dependencies", "package", "packages", "install", "pip", "npm", "pnpm", "yarn", "poetry", "uv", "requirements", "package.json", "lockfile", "version", "upgrade", "downgrade", "module not found", "importerror", "environment", "venv", "node_modules", "build tool", "wheel", "resolver"), "Handles packages and environment issues."),
    AgentSpec("frontend", "Frontend Agent", ("ui", "accessibility"), ("frontend", "ui", "ux", "window", "layout", "css", "html", "react", "vue", "component", "button", "card", "modal", "responsive", "mobile", "desktop", "accessibility", "a11y", "animation", "framer", "tailwind", "style", "render", "overflow"), "Checks UI render errors, accessibility, and layout."),
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
    """Return an optional bundled SKILL.md folder bound to an agent type, if any."""
    try:
        from ..skills import agent_skill_file as _lookup

        return _lookup(agent_type)
    except Exception:
        return None


def select_agents_for_command(command: str, limit: int | None = None) -> list[AgentSpec]:
    """Return only agents whose triggers/capabilities match the command."""
    text = command.lower()
    scored: list[tuple[int, AgentSpec]] = []
    for spec in DEFAULT_AGENT_SPECS:
        trigger_score = sum(100 for trigger in spec.triggers if trigger in text)
        capability_score = sum(3 for capability in spec.capabilities if capability.replace("_", " ") in text)
        skill_score = sum(2 for skill in agent_skill_profile(spec.type) if skill.lower() in text)
        if trigger_score + capability_score + skill_score <= 0:
            continue
        score = trigger_score + capability_score + skill_score + _UNIVERSAL_PRIORITY.get(spec.type, 0)
        scored.append((score, spec))

    scored.sort(key=lambda item: (-item[0], item[1].type))
    if limit is None or limit <= 0:
        limit = len(DEFAULT_AGENT_SPECS)
    return [spec for _, spec in scored[:limit]]
