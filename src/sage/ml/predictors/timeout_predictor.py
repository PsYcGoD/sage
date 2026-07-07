"""Timeout Predictor - detects commands that are likely to hang or take very long."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from .base import BasePredictor, Prediction

KNOWN_SLOW_COMMANDS = {
    "npm install": 120,
    "yarn install": 120,
    "pip install": 60,
    "docker build": 300,
    "docker pull": 120,
    "cargo build": 180,
    "mvn install": 240,
    "gradle build": 180,
    "make": 120,
    "cmake": 60,
}

HANG_RISK_PATTERNS = (
    "tail -f",
    "watch ",
    "less ",
    "more ",
    "vim ",
    "nano ",
    "emacs ",
    "top",
    "htop",
    "python -i",
    "python3 -i",
    "node --inspect",
    "cat /dev/",
)


class TimeoutPredictor(BasePredictor):
    """Detects commands likely to hang or take a very long time."""

    CATEGORY = "timeout_risk"

    def predict(self, command: str, **context) -> Optional[Prediction]:
        cmd_lower = command.lower().strip()
        if not cmd_lower:
            return None

        reasons = []
        probability = 0.0
        suggestion = None

        # Known interactive/blocking commands
        for pattern in HANG_RISK_PATTERNS:
            if cmd_lower.startswith(pattern) or f" {pattern}" in cmd_lower:
                reasons.append(f"Interactive command '{pattern.strip()}' will block")
                probability = max(probability, 0.90)
                suggestion = "This command requires interactive input"
                break

        # Known slow commands
        for slow_cmd, avg_seconds in KNOWN_SLOW_COMMANDS.items():
            if cmd_lower.startswith(slow_cmd):
                reasons.append(f"'{slow_cmd}' typically takes {avg_seconds}s+")
                probability = max(probability, 0.50)
                suggestion = f"Average duration: {avg_seconds // 60}m {avg_seconds % 60}s"
                break

        # Check historical duration for this command
        db_path = context.get("db_path")
        if db_path:
            avg_ms = self._avg_duration(command, db_path)
            if avg_ms and avg_ms > 60000:
                minutes = avg_ms / 60000
                reasons.append(f"Historical average: {minutes:.1f} minutes")
                probability = max(probability, 0.60)
                if suggestion is None:
                    suggestion = f"Expected duration: ~{minutes:.0f} min"

        # Infinite loop risk: commands without timeout that hit network
        if "curl" in cmd_lower or "wget" in cmd_lower:
            if "--max-time" not in cmd_lower and "--timeout" not in cmd_lower and "-m " not in cmd_lower:
                if "localhost" not in cmd_lower and "127.0.0.1" not in cmd_lower:
                    reasons.append("Network request without timeout")
                    probability = max(probability, 0.40)

        if not reasons:
            return None

        return Prediction(
            category=self.CATEGORY,
            probability=probability,
            will_trigger=probability >= 0.55,
            reason="; ".join(reasons),
            suggestion=suggestion,
        )

    def _avg_duration(self, command: str, db_path: Path) -> Optional[float]:
        """Get average duration_ms for this command from history."""
        try:
            with sqlite3.connect(db_path) as conn:
                row = conn.execute(
                    """
                    SELECT AVG(duration_ms) FROM runs
                    WHERE command = ? AND duration_ms > 0
                    """,
                    (command,),
                ).fetchone()
            return row[0] if row and row[0] else None
        except Exception:
            return None
