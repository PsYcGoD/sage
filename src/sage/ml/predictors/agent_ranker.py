"""Agent Priority Ranker - selects which agents to run for a command."""

from __future__ import annotations

import re
from typing import List, Optional

from .base import BasePredictor, Prediction

AGENT_RELEVANCE = {
    "Security Agent": [
        r"^git (push|commit|add)",
        r"^docker",
        r"^ssh",
        r"^curl",
        r"^wget",
        r"env|secret|token|key|password|cred",
    ],
    "Test Agent": [
        r"^pytest",
        r"^python -m pytest",
        r"^jest",
        r"^vitest",
        r"^cargo test",
        r"^go test",
        r"^npm test",
        r"test",
    ],
    "Code Agent": [
        r"^python",
        r"^node",
        r"^cargo",
        r"^go (run|build)",
        r"^gcc|^g\+\+|^clang",
        r"^javac",
        r"^tsc",
    ],
    "Debug Agent": [
        r"^python.*-m (pdb|debugpy)",
        r"exit_code.*!=.*0",
        r"error|fail|exception|traceback",
    ],
    "Dependency Agent": [
        r"^pip",
        r"^npm",
        r"^yarn",
        r"^cargo add",
        r"^go get",
        r"install|update|upgrade",
    ],
    "Frontend Agent": [
        r"^npm (run|start|build)",
        r"^yarn (dev|build|start)",
        r"^vite",
        r"^webpack",
        r"^next",
        r"\.tsx?$|\.jsx?$|\.vue$|\.svelte$",
    ],
    "Research Agent": [
        r"^curl",
        r"^wget",
        r"^gh (api|search)",
        r"search|find|query|lookup",
    ],
}

# Always include Code Agent as baseline
ALWAYS_RUN = ["Code Agent"]
MAX_AGENTS = 4


class AgentRanker(BasePredictor):
    """Ranks which agents are most relevant for a command."""

    CATEGORY = "agent_selection"

    def predict(self, command: str, **context) -> Optional[Prediction]:
        cmd_lower = command.lower().strip()
        if not cmd_lower:
            return None

        scores: dict[str, float] = {}

        for agent, patterns in AGENT_RELEVANCE.items():
            score = 0.0
            for pattern in patterns:
                if re.search(pattern, cmd_lower):
                    score += 1.0
            if score > 0:
                scores[agent] = score

        # Always include baseline agents
        for agent in ALWAYS_RUN:
            if agent not in scores:
                scores[agent] = 0.5

        # Rank by score and take top N
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        selected = [name for name, _ in ranked[:MAX_AGENTS]]

        return Prediction(
            category=self.CATEGORY,
            probability=0.85,
            will_trigger=True,
            reason=f"Run: {selected}",
            suggestion=",".join(selected),
        )

    def rank_agents(self, command: str) -> List[str]:
        """Return ordered list of agents to run for this command."""
        result = self.predict(command)
        if result and result.suggestion:
            return result.suggestion.split(",")
        return ALWAYS_RUN
