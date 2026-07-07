from __future__ import annotations

from typing import Any


MODEL_SAVINGS_PROFILES: dict[str, dict[str, Any]] = {
    "claude-sonnet": {
        "label": "Claude Sonnet",
        "provider": "Anthropic",
        "input_rate_per_million": 3.0,
    },
    "codex": {
        "label": "OpenAI Codex",
        "provider": "OpenAI",
        "input_rate_per_million": 1.5,
    },
    "gemini-pro": {
        "label": "Gemini 2.5 Pro",
        "provider": "Google",
        "input_rate_per_million": 1.25,
    },
}

AGENT_SAVINGS_PROFILES: dict[str, dict[str, Any]] = {
    "claude-cli": {
        "label": "Claude CLI",
        "provider": "Anthropic",
        "model": "Claude Sonnet",
        "input_rate_per_million": 3.0,
    },
    "codex-cli": {
        "label": "Codex CLI",
        "provider": "OpenAI",
        "model": "OpenAI Codex",
        "input_rate_per_million": 1.5,
    },
    "sage-desktop": {
        "label": "SAGE Desktop",
        "provider": "SAGE",
        "model": "Desktop app",
        "input_rate_per_million": 0.0,
    },
    "claude-code": {
        "label": "Claude Code",
        "provider": "Anthropic",
        "model": "Claude Sonnet",
        "input_rate_per_million": 3.0,
    },
    "opencode": {
        "label": "OpenCode",
        "provider": "OpenCode",
        "model": "Claude Sonnet",
        "input_rate_per_million": 3.0,
    },
    "cursor": {
        "label": "Cursor",
        "provider": "Cursor",
        "model": "OpenAI Codex",
        "input_rate_per_million": 1.5,
    },
    "windsurf": {
        "label": "Windsurf",
        "provider": "Codeium",
        "model": "Claude Sonnet",
        "input_rate_per_million": 3.0,
    },
    "aider": {
        "label": "Aider",
        "provider": "Aider",
        "model": "Claude Sonnet",
        "input_rate_per_million": 3.0,
    },
    "copilot": {
        "label": "GitHub Copilot coding agent",
        "provider": "GitHub",
        "model": "GitHub Copilot",
        "input_rate_per_million": 0.0,
    },
}

# Backwards-compatible name used by the CLI.
SAVINGS_PROFILES = MODEL_SAVINGS_PROFILES


def _estimate(saved_tokens: int, input_rate_per_million: float) -> float:
    return round((int(saved_tokens or 0) / 1_000_000) * input_rate_per_million, 4)


def estimate_savings_usd(saved_tokens: int, agent: str) -> float:
    profile = MODEL_SAVINGS_PROFILES[agent]
    input_rate = float(profile.get("input_rate_per_million", 0) or 0)
    return _estimate(saved_tokens, input_rate)


def build_model_savings(saved_tokens: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for model, profile in MODEL_SAVINGS_PROFILES.items():
        input_rate = float(profile.get("input_rate_per_million", 0) or 0)
        rows.append(
            {
                "model": model,
                "label": str(profile["label"]),
                "provider": str(profile["provider"]),
                "saved_tokens": int(saved_tokens or 0),
                "input_rate_per_million": input_rate,
                "estimated_savings_usd": _estimate(saved_tokens, input_rate),
            }
        )
    return rows


def estimate_total_model_savings_usd(saved_tokens: int) -> float:
    return round(sum(row["estimated_savings_usd"] for row in build_model_savings(saved_tokens)), 4)


def default_agent_usage(saved_tokens: int) -> dict[str, int]:
    """Current public proof has model-level totals, not historical editor attribution."""
    saved = max(0, int(saved_tokens or 0))
    if not saved:
        return {}
    return {
        "claude-cli": saved,
        "codex-cli": saved,
    }


def build_agent_savings(saved_tokens: int, used_agents: dict[str, int] | None = None) -> list[dict[str, Any]]:
    usage = default_agent_usage(saved_tokens) if used_agents is None else used_agents
    rows: list[dict[str, Any]] = []
    for agent, profile in AGENT_SAVINGS_PROFILES.items():
        agent_saved = int(usage.get(agent, 0) or 0)
        input_rate = float(profile.get("input_rate_per_million", 0) or 0)
        rows.append(
            {
                "agent": agent,
                "label": str(profile["label"]),
                "provider": str(profile["provider"]),
                "model": str(profile["model"]),
                "saved_tokens": max(0, agent_saved),
                "input_rate_per_million": input_rate,
                "estimated_savings_usd": _estimate(agent_saved, input_rate),
            }
        )
    return rows
