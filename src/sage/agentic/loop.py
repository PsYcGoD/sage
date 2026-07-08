"""Agentic Loop Controller — orchestrates Start → Test → Verify → Repeat cycle."""

from __future__ import annotations

import logging
import subprocess
import time
from enum import Enum
from dataclasses import dataclass, field

from .engine import AgenticEngine, Action, Autonomy, Decision
from .session import get_session
from .verify import VerifyResult, verify_fix

logger = logging.getLogger(__name__)


class LoopState(Enum):
    """States of the agentic loop."""
    IDLE = "idle"
    RUNNING = "running"
    ANALYZING = "analyzing"
    FIXING = "fixing"
    VERIFYING = "verifying"
    DONE = "done"
    FAILED = "failed"


@dataclass
class LoopResult:
    """Result of a full agentic loop run."""
    original_command: str
    final_exit_code: int
    state: LoopState
    attempts: int = 0
    fixes_applied: list[str] = field(default_factory=list)
    message: str = ""


class AgenticLoop:
    """Main agentic control loop — runs command, analyzes, fixes, verifies."""

    def __init__(
        self,
        autonomy: Autonomy = Autonomy.SUGGEST,
        max_retries: int = 3,
        cooldown_base: float = 1.0,
        on_progress: callable = None,
    ):
        self.engine = AgenticEngine(autonomy=autonomy, max_retries=max_retries)
        self.max_retries = max_retries
        self.cooldown_base = cooldown_base
        self.on_progress = on_progress or self._default_progress
        self._state = LoopState.IDLE
        self._interrupted = False

    @property
    def state(self) -> LoopState:
        return self._state

    def interrupt(self):
        """Signal the loop to stop."""
        self._interrupted = True

    def run(self, command: str, shell: bool = True, cwd: str | None = None) -> LoopResult:
        """Run a command with full agentic loop (retry on failure)."""
        self._interrupted = False
        self._state = LoopState.RUNNING
        attempts = 0
        fixes_applied = []

        # Pre-check for destructive commands
        pre = self.engine.pre_check(command)
        if pre and pre.action == Action.WARN_DESTRUCTIVE:
            self.on_progress("warn", pre.message)
            if self.engine.autonomy != Autonomy.AUTO:
                return LoopResult(
                    original_command=command,
                    final_exit_code=-1,
                    state=LoopState.FAILED,
                    message=pre.message,
                )

        while attempts <= self.max_retries and not self._interrupted:
            attempts += 1
            self._state = LoopState.RUNNING
            self.on_progress("running", f"Attempt {attempts}: {command}")

            # Execute
            exit_code, stdout, stderr = self._execute(command, shell=shell, cwd=cwd)

            # Analyze
            self._state = LoopState.ANALYZING
            decision = self.engine.decide(command, exit_code, stderr=stderr, stdout=stdout)

            if decision.action == Action.LOG_SUCCESS:
                self._state = LoopState.DONE
                return LoopResult(
                    original_command=command,
                    final_exit_code=0,
                    state=LoopState.DONE,
                    attempts=attempts,
                    fixes_applied=fixes_applied,
                    message="Success",
                )

            if decision.action == Action.ABORT:
                self._state = LoopState.FAILED
                self.on_progress("abort", decision.message)
                return LoopResult(
                    original_command=command,
                    final_exit_code=exit_code,
                    state=LoopState.FAILED,
                    attempts=attempts,
                    fixes_applied=fixes_applied,
                    message=decision.message,
                )

            if decision.action == Action.ESCALATE:
                self._state = LoopState.FAILED
                self.on_progress("escalate", decision.message)
                return LoopResult(
                    original_command=command,
                    final_exit_code=exit_code,
                    state=LoopState.FAILED,
                    attempts=attempts,
                    fixes_applied=fixes_applied,
                    message=decision.message,
                )

            if decision.action in (Action.AUTO_FIX, Action.SUGGEST_FIX):
                if decision.action == Action.AUTO_FIX and decision.next_command:
                    # Apply fix
                    self._state = LoopState.FIXING
                    fix_cmd = decision.next_command
                    self.on_progress("fixing", f"Applying: {fix_cmd}")
                    fixes_applied.append(fix_cmd)

                    fix_exit, fix_out, fix_err = self._execute(fix_cmd, shell=shell, cwd=cwd)

                    # Verify
                    self._state = LoopState.VERIFYING
                    self.on_progress("verifying", "Re-running original command...")

                    # Cooldown before retry
                    cooldown = self.cooldown_base * (2 ** (attempts - 1))
                    time.sleep(min(cooldown, 8.0))
                    continue  # Loop back to retry the original command

                else:
                    # Suggest mode — report fix but don't auto-run
                    self._state = LoopState.FAILED
                    self.on_progress("suggest", decision.message)
                    return LoopResult(
                        original_command=command,
                        final_exit_code=exit_code,
                        state=LoopState.FAILED,
                        attempts=attempts,
                        fixes_applied=fixes_applied,
                        message=decision.message,
                    )

        # Exhausted retries or interrupted
        self._state = LoopState.FAILED
        msg = "Interrupted by user" if self._interrupted else f"Failed after {attempts} attempts"
        return LoopResult(
            original_command=command,
            final_exit_code=-1,
            state=LoopState.FAILED,
            attempts=attempts,
            fixes_applied=fixes_applied,
            message=msg,
        )

    def _execute(self, command: str, shell: bool = True, cwd: str | None = None) -> tuple[int, str, str]:
        """Execute a command and capture output."""
        try:
            result = subprocess.run(
                command,
                shell=shell,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=cwd,
            )
            return result.returncode, result.stdout[-4000:], result.stderr[-4000:]
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out after 300 seconds"
        except Exception as e:
            return -1, "", str(e)

    def _default_progress(self, event: str, message: str):
        """Default progress handler — print to terminal."""
        prefix = {
            "running": "[sage-loop]",
            "fixing": "[sage-loop] 🔧",
            "verifying": "[sage-loop] ✓",
            "suggest": "[sage-loop] 💡",
            "warn": "[sage-loop] ⚠",
            "abort": "[sage-loop] ✗",
            "escalate": "[sage-loop] ⬆",
        }.get(event, "[sage-loop]")
        print(f"{prefix} {message}")
