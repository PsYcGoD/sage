"""Agentic Decision Engine — decides what to do after each command execution."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .fixer import FixSuggestion, suggest_fix
from .intent import DetectedIntent, detect_intent
from .session import CommandRecord, SessionState, get_session

logger = logging.getLogger(__name__)


class Action(Enum):
    """Actions the engine can recommend."""
    IDLE = "idle"
    LOG_SUCCESS = "log_success"
    SUGGEST_FIX = "suggest_fix"
    AUTO_FIX = "auto_fix"
    WARN_DESTRUCTIVE = "warn_destructive"
    ESCALATE = "escalate"
    ABORT = "abort"


class Autonomy(Enum):
    """How autonomous the engine should be."""
    SUGGEST = "suggest"  # Only suggest, never auto-run
    ASK = "ask"          # Ask before running fixes
    AUTO = "auto"        # Auto-run non-destructive fixes


@dataclass
class Decision:
    """Engine's decision after analyzing a command result."""
    action: Action
    fix: FixSuggestion | None = None
    intent: DetectedIntent | None = None
    message: str = ""
    should_retry: bool = False
    next_command: str | None = None


# Commands that should never be auto-fixed without confirmation
DESTRUCTIVE_PATTERNS = [
    "rm -rf", "rm -r", "drop table", "drop database",
    "git push --force", "git push -f", "git reset --hard",
    "git clean -fd", "del /s", "format ", "mkfs",
    "shutdown", "reboot", "kill -9",
]


def is_destructive(command: str) -> bool:
    """Check if a command is destructive."""
    cmd_lower = command.lower()
    return any(p in cmd_lower for p in DESTRUCTIVE_PATTERNS)


class AgenticEngine:
    """Core decision engine for the agentic loop."""

    def __init__(self, autonomy: Autonomy = Autonomy.SUGGEST, max_retries: int = 3):
        self.autonomy = autonomy
        self.max_retries = max_retries
        self._retry_count: dict[str, int] = {}

    def pre_check(self, command: str) -> Decision | None:
        """Check a command BEFORE execution. Returns warning if destructive."""
        if is_destructive(command):
            return Decision(
                action=Action.WARN_DESTRUCTIVE,
                message=f"⚠ Destructive command detected: {command}",
            )
        return None

    def decide(self, command: str, exit_code: int, stderr: str = "", stdout: str = "") -> Decision:
        """Decide what to do after a command executes."""
        session = get_session()
        session.record(command, exit_code, stdout_tail=stdout, stderr_tail=stderr)

        # Success path
        if exit_code == 0:
            self._retry_count.pop(command, None)
            intent = detect_intent(command, [r.command for r in session.history])
            return Decision(
                action=Action.LOG_SUCCESS,
                intent=intent,
                message="",
            )

        # Failure path — check for loops
        if session.detect_loop(command, stderr[:100]):
            return Decision(
                action=Action.ABORT,
                message="Loop detected: same command failing with same error repeatedly. Stopping.",
            )

        # Check retry limit
        retries = self._retry_count.get(command, 0)
        if retries >= self.max_retries:
            self._retry_count.pop(command, None)
            return Decision(
                action=Action.ESCALATE,
                message=f"Max retries ({self.max_retries}) reached for: {command}",
            )

        # Try to find a fix
        fix = suggest_fix(command, stderr)
        if fix is None:
            return Decision(
                action=Action.SUGGEST_FIX,
                message=f"Command failed (exit {exit_code}) but no known fix pattern matched.",
            )

        # Determine action based on autonomy level
        self._retry_count[command] = retries + 1

        if fix.destructive or self.autonomy == Autonomy.SUGGEST:
            return Decision(
                action=Action.SUGGEST_FIX,
                fix=fix,
                message=f"Suggested fix: {fix.fix_command}",
                should_retry=True,
                next_command=fix.fix_command,
            )

        if self.autonomy == Autonomy.ASK:
            return Decision(
                action=Action.SUGGEST_FIX,
                fix=fix,
                message=f"Fix available: {fix.fix_command}\nRun it? (requires confirmation)",
                should_retry=True,
                next_command=fix.fix_command,
            )

        # Autonomy.AUTO — run the fix automatically
        return Decision(
            action=Action.AUTO_FIX,
            fix=fix,
            message=f"Auto-fixing: {fix.explanation}",
            should_retry=True,
            next_command=fix.fix_command,
        )

    def reset_retries(self, command: str | None = None):
        """Reset retry counters."""
        if command:
            self._retry_count.pop(command, None)
        else:
            self._retry_count.clear()
