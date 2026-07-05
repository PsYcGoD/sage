from __future__ import annotations
"""Background telemetry sender - non-blocking, best-effort sync.

Runs in a separate process to avoid slowing down sage run.
"""

import logging

import sys
import subprocess
import time
from pathlib import Path

log = logging.getLogger(__name__)

def send_batch_background(limit: int = 200) -> None:
    """Send a batch of queued telemetry events in background."""
    try:
        from . import telemetry

        # Quick check: if no API configured, exit immediately
        config = telemetry.load_config()
        if not config.get("api_endpoint") or not config.get("api_key"):
            return

        snapshot_result = None
        try:
            # Push aggregate proof first so the 15-second dashboard refresh sees
            # current local totals even if the event backlog needs more batches.
            snapshot_result = telemetry.send_proof_snapshot()
        except Exception as exc:
            snapshot_result = {"ok": False, "error": str(exc)}

        # Send batch (non-dry-run)
        result = telemetry.send_queued(dry_run=False, limit=limit)
        try:
            post_batch_snapshot = telemetry.send_proof_snapshot()
            if not snapshot_result or not snapshot_result.get("ok"):
                snapshot_result = post_batch_snapshot
        except Exception as exc:
            if not snapshot_result or not snapshot_result.get("ok"):
                snapshot_result = {"ok": False, "error": str(exc)}
            pass

        # Log to file for debugging (optional)
        log_path = telemetry.data_dir() / "telemetry_sender.log"
        try:
            with log_path.open("a", encoding="utf-8") as f:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                f.write(
                    f"{timestamp} | Sent: {result['sent']}, Queued: {result['queued']}, "
                    f"Snapshot: {snapshot_result}\n"
                )
        except Exception:
            log.debug("suppressed", exc_info=True)

    except Exception:
        # Silent failure - telemetry is best-effort
        pass

def spawn_background_sender() -> bool:
    """Spawn a background process to send telemetry. Returns True if spawned."""
    try:
        # Quick check: only spawn if we have events to send
        from . import telemetry

        status = telemetry.queue_status()
        if status.get("queued", 0) == 0:
            return False

        cmd = [sys.executable, "-m", "sage.telemetry_sender", "--limit", "200"]
        kwargs = {
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "close_fds": True,
        }
        if sys.platform.startswith("win"):
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
        subprocess.Popen(cmd, **kwargs)
        return True
    except Exception:
        return False

def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint used by detached background sender processes."""
    argv = argv or sys.argv[1:]
    limit = 200
    if "--limit" in argv:
        try:
            limit = int(argv[argv.index("--limit") + 1])
        except (ValueError, IndexError):
            limit = 200
    send_batch_background(limit=limit)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
