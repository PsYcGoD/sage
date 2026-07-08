"""Circuit breaker — prevents infinite retry loops and runaway automation."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class BreakerState:
    """Per-command circuit breaker state."""
    failures: int = 0
    last_failure: float = 0.0
    last_error: str = ""
    tripped: bool = False


class CircuitBreaker:
    """Prevents infinite retry loops with exponential backoff and loop detection."""

    def __init__(
        self,
        max_failures: int = 3,
        cooldown_base: float = 1.0,
        cooldown_max: float = 30.0,
        reset_after: float = 300.0,
    ):
        self.max_failures = max_failures
        self.cooldown_base = cooldown_base
        self.cooldown_max = cooldown_max
        self.reset_after = reset_after
        self._breakers: dict[str, BreakerState] = {}

    def check(self, command: str) -> bool:
        """Check if the circuit is open (should NOT proceed). Returns True if blocked."""
        state = self._breakers.get(command)
        if state is None:
            return False

        # Auto-reset after cooldown period
        if state.tripped and (time.time() - state.last_failure) > self.reset_after:
            self._breakers.pop(command, None)
            return False

        return state.tripped

    def record_failure(self, command: str, error: str = "") -> bool:
        """Record a failure. Returns True if circuit just tripped."""
        state = self._breakers.get(command)
        if state is None:
            state = BreakerState()
            self._breakers[command] = state

        state.failures += 1
        state.last_failure = time.time()
        state.last_error = error[:500]

        if state.failures >= self.max_failures:
            state.tripped = True
            return True
        return False

    def record_success(self, command: str):
        """Record success — reset the breaker for this command."""
        self._breakers.pop(command, None)

    def get_cooldown(self, command: str) -> float:
        """Get the current cooldown duration for a command."""
        state = self._breakers.get(command)
        if state is None:
            return 0.0
        delay = self.cooldown_base * (2 ** (state.failures - 1))
        return min(delay, self.cooldown_max)

    def is_loop(self, command: str, error: str) -> bool:
        """Detect if we're stuck in a loop (same error repeating)."""
        state = self._breakers.get(command)
        if state is None:
            return False
        return (
            state.failures >= 2
            and error[:100] == state.last_error[:100]
            and (time.time() - state.last_failure) < 60.0
        )

    def reset(self, command: str | None = None):
        """Reset breaker state."""
        if command:
            self._breakers.pop(command, None)
        else:
            self._breakers.clear()

    def status(self) -> dict[str, dict]:
        """Return status of all breakers for diagnostics."""
        return {
            cmd: {
                "failures": s.failures,
                "tripped": s.tripped,
                "last_error": s.last_error[:100],
                "cooldown": self.get_cooldown(cmd),
            }
            for cmd, s in self._breakers.items()
        }
