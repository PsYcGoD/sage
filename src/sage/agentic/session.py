"""Session state manager — tracks command history, intent chains, and error patterns."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class CommandRecord:
    """Single command execution record."""
    command: str
    exit_code: int | None = None
    stdout_tail: str = ""
    stderr_tail: str = ""
    prediction: dict | None = None
    timestamp: float = field(default_factory=time.time)
    fix_applied: str | None = None


@dataclass
class SessionState:
    """Tracks state across a terminal session."""

    history: list[CommandRecord] = field(default_factory=list)
    intent_chain: list[str] = field(default_factory=list)
    failure_streak: int = 0
    total_fixes_applied: int = 0
    total_fixes_succeeded: int = 0
    session_start: float = field(default_factory=time.time)

    @property
    def last(self) -> CommandRecord | None:
        return self.history[-1] if self.history else None

    @property
    def last_failed(self) -> CommandRecord | None:
        for rec in reversed(self.history):
            if rec.exit_code and rec.exit_code != 0:
                return rec
        return None

    def record(self, command: str, exit_code: int, stdout_tail: str = "", stderr_tail: str = "", prediction: dict | None = None):
        """Record a command execution."""
        rec = CommandRecord(
            command=command,
            exit_code=exit_code,
            stdout_tail=stdout_tail[-2000:],
            stderr_tail=stderr_tail[-2000:],
            prediction=prediction,
        )
        self.history.append(rec)

        if exit_code != 0:
            self.failure_streak += 1
        else:
            self.failure_streak = 0

        # Keep history bounded
        if len(self.history) > 100:
            self.history = self.history[-100:]

    def detect_loop(self, command: str, error_snippet: str) -> bool:
        """Detect if we're in a retry loop (same command, same error, 3+ times)."""
        recent = self.history[-5:]
        matches = 0
        for rec in recent:
            if rec.command == command and error_snippet in rec.stderr_tail:
                matches += 1
        return matches >= 3

    def recent_errors(self, n: int = 5) -> list[CommandRecord]:
        """Return last N failed commands."""
        return [r for r in reversed(self.history) if r.exit_code and r.exit_code != 0][:n]


# Global session instance (per-process)
_session: SessionState | None = None


def get_session() -> SessionState:
    """Get or create the global session state."""
    global _session
    if _session is None:
        _session = SessionState()
    return _session


def reset_session():
    """Reset session state (for testing)."""
    global _session
    _session = None
