"""Verification system — confirms fixes actually work by re-running and comparing."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from enum import Enum


class VerifyStatus(Enum):
    """Result of fix verification."""
    FIXED = "fixed"          # Original command now succeeds
    PARTIAL = "partial"      # Different error (some progress)
    UNCHANGED = "unchanged"  # Same error as before
    WORSE = "worse"          # New/worse error introduced


@dataclass
class VerifyResult:
    """Result of verifying a fix."""
    status: VerifyStatus
    exit_code: int
    original_error: str
    new_output: str
    message: str


def verify_fix(
    command: str,
    original_stderr: str,
    shell: bool = True,
    cwd: str | None = None,
    timeout: int = 300,
) -> VerifyResult:
    """Re-run the original command and check if the fix worked."""
    try:
        result = subprocess.run(
            command,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
    except subprocess.TimeoutExpired:
        return VerifyResult(
            status=VerifyStatus.WORSE,
            exit_code=-1,
            original_error=original_stderr[:500],
            new_output="Command timed out",
            message="Fix may have caused a hang",
        )
    except Exception as e:
        return VerifyResult(
            status=VerifyStatus.WORSE,
            exit_code=-1,
            original_error=original_stderr[:500],
            new_output=str(e),
            message=f"Verification failed: {e}",
        )

    # Success — fix worked
    if result.returncode == 0:
        return VerifyResult(
            status=VerifyStatus.FIXED,
            exit_code=0,
            original_error=original_stderr[:500],
            new_output=result.stdout[-1000:],
            message="Fix verified — command now succeeds",
        )

    # Still failing — compare errors
    new_stderr = result.stderr[-2000:]
    original_snippet = original_stderr[:200].strip()
    new_snippet = new_stderr[:200].strip()

    if original_snippet and original_snippet in new_stderr:
        return VerifyResult(
            status=VerifyStatus.UNCHANGED,
            exit_code=result.returncode,
            original_error=original_stderr[:500],
            new_output=new_stderr,
            message="Same error persists — fix did not help",
        )

    # Different error — partial progress or regression
    if result.returncode > 0:
        return VerifyResult(
            status=VerifyStatus.PARTIAL,
            exit_code=result.returncode,
            original_error=original_stderr[:500],
            new_output=new_stderr,
            message="Different error — fix made partial progress",
        )

    return VerifyResult(
        status=VerifyStatus.WORSE,
        exit_code=result.returncode,
        original_error=original_stderr[:500],
        new_output=new_stderr,
        message="Fix may have introduced a new problem",
    )
