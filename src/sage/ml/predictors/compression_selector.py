"""Compression Strategy Selector - picks the best output compression for a command."""

from __future__ import annotations

import re
from typing import Optional

from .base import BasePredictor, Prediction

STRATEGY_MAP = {
    "diff": [
        r"^git diff",
        r"^git show",
        r"^diff ",
        r"^patch ",
    ],
    "stacktrace": [
        r"^python.*traceback",
        r"^node.*error",
        r"^java ",
        r"^mvn ",
        r"^gradle ",
    ],
    "test_output": [
        r"^pytest",
        r"^python -m pytest",
        r"^python3 -m pytest",
        r"^jest",
        r"^vitest",
        r"^cargo test",
        r"^go test",
        r"^npm test",
        r"^yarn test",
        r"^unittest",
        r"^mocha",
    ],
    "progress": [
        r"^pip install",
        r"^npm install",
        r"^yarn install",
        r"^cargo build",
        r"^docker build",
        r"^docker pull",
        r"^wget ",
        r"^curl.*-o",
        r"^git clone",
    ],
    "log": [
        r"^tail ",
        r"^journalctl",
        r"^docker logs",
        r"^kubectl logs",
        r"^cat.*\.log",
    ],
}


class CompressionSelector(BasePredictor):
    """Selects the best output compression strategy for a command."""

    CATEGORY = "compression_strategy"

    def predict(self, command: str, **context) -> Optional[Prediction]:
        cmd_lower = command.lower().strip()
        if not cmd_lower:
            return None

        best_strategy = "generic"
        best_confidence = 0.5

        for strategy, patterns in STRATEGY_MAP.items():
            for pattern in patterns:
                if re.search(pattern, cmd_lower):
                    best_strategy = strategy
                    best_confidence = 0.90
                    break
            if best_confidence > 0.5:
                break

        # Heuristic fallbacks
        if best_strategy == "generic":
            if any(kw in cmd_lower for kw in ("test", "spec", "check")):
                best_strategy = "test_output"
                best_confidence = 0.70
            elif any(kw in cmd_lower for kw in ("install", "update", "upgrade", "build")):
                best_strategy = "progress"
                best_confidence = 0.65
            elif any(kw in cmd_lower for kw in ("log", "tail", "journal")):
                best_strategy = "log"
                best_confidence = 0.70

        return Prediction(
            category=self.CATEGORY,
            probability=best_confidence,
            will_trigger=True,
            reason=f"Strategy: {best_strategy} ({best_confidence*100:.0f}% confidence)",
            suggestion=best_strategy,
        )
