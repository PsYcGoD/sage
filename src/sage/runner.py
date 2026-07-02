from __future__ import annotations

import subprocess
import time
from pathlib import Path

from .detectors import summarize_output
from .store import save_run
from .context import ContextManager


def run_command(command_parts: list[str]) -> int:
    if not command_parts:
        print("No command was provided. Example: sage run -- python --version")
        return 2

    command_text = subprocess.list2cmdline(command_parts)
    started = time.perf_counter()
    completed = subprocess.run(
        command_text,
        shell=True,
        capture_output=True,
        text=True,
        errors="replace",
    )
    duration_ms = int((time.perf_counter() - started) * 1000)

    summary = summarize_output(completed.stdout, completed.stderr, completed.returncode)
    run_id = save_run(
        project=str(Path.cwd()),
        command=command_text,
        exit_code=completed.returncode,
        duration_ms=duration_ms,
        stdout=completed.stdout,
        stderr=completed.stderr,
        summary=summary,
    )

    # Process output through context manager
    context_mgr = ContextManager()
    result = context_mgr.process_command_output(
        stdout=completed.stdout,
        stderr=completed.stderr,
        exit_code=completed.returncode,
        run_id=run_id,
    )

    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="")

    print()
    print(f"[sage] saved run #{run_id} exit={completed.returncode} time={duration_ms}ms")

    # Show token savings
    if result['token_savings'] > 0:
        print(f"[sage] context: saved {result['token_savings']} tokens ({result['compression_ratio']} compression)")

    print("[sage] summary:")
    print(summary)

    return completed.returncode
