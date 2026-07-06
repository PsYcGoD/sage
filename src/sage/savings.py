from __future__ import annotations

from typing import Any


SAVINGS_PROFILES: dict[str, dict[str, Any]] = {
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
    "copilot": {
        "label": "GitHub Copilot coding agent",
        "provider": "GitHub",
        "input_rate_per_million": 0.0,
    },
}


def estimate_savings_usd(saved_tokens: int, agent: str) -> float:
    profile = SAVINGS_PROFILES[agent]
    input_rate = float(profile.get("input_rate_per_million", 0) or 0)
    return round((int(saved_tokens or 0) / 1_000_000) * input_rate, 4)


def build_agent_savings(saved_tokens: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for agent, profile in SAVINGS_PROFILES.items():
        input_rate = float(profile.get("input_rate_per_million", 0) or 0)
        rows.append(
            {
                "agent": agent,
                "label": str(profile["label"]),
                "provider": str(profile["provider"]),
                "saved_tokens": int(saved_tokens or 0),
                "input_rate_per_million": input_rate,
                "estimated_savings_usd": estimate_savings_usd(saved_tokens, agent),
            }
        )
    return rows

