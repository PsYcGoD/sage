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

_auto_registered_this_session = False

def _try_silent_register() -> bool:
    global _auto_registered_this_session
    if _auto_registered_this_session:
        return True
    from . import telemetry
    ok = telemetry.auto_register_silent()
    if ok:
        _auto_registered_this_session = True
    return ok

def send_batch_background(limit: int = 200) -> None:
    """Publish one daily aggregate snapshot without uploading per-run events."""
    try:
        from . import telemetry

        config = telemetry.load_config()
        if not config.get("api_endpoint") or not telemetry.resolve_api_key(config):
            if _try_silent_register():
                config = telemetry.load_config()
            else:
                return

        snapshot_result = None
        # Per-run telemetry remains local. Only the privacy-safe aggregate proof
        # is sent automatically, reducing each active installation to one API
        # request per day. Explicit `sage telemetry sync-all --for-real` remains
        # available for users who deliberately opt into a full history upload.
        result = {
            "sent": 0,
            "queued": telemetry.queue_status().get("queued", 0),
        }
        snapshot_result = None
        try:
            snapshot_result = telemetry.send_proof_snapshot()
        except Exception as exc:
            snapshot_result = {"ok": False, "error": str(exc)}

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

# The normal caller schedules at most one sender every 24 hours. This lock is
# a second line of defence for direct callers and prevents detached processes
# from accumulating when the network is slow or offline.
_SENDER_DEBOUNCE_SECONDS = 24 * 60 * 60


def _sender_lock_path() -> Path:
    from .store import data_dir

    return Path(data_dir()) / "telemetry_sender.lock"


def spawn_background_sender() -> bool:
    """Spawn a background process to send telemetry. Returns True if spawned.

    Debounced: if a sender was spawned within the last _SENDER_DEBOUNCE_SECONDS,
    this is a no-op so detached python processes cannot accumulate.
    """
    try:
        # Quick check: only spawn if we have events to send
        from . import telemetry

        status = telemetry.queue_status()
        if status.get("queued", 0) == 0:
            return False

        # Debounce: skip if a recent sender is still within its window.
        lock = _sender_lock_path()
        try:
            if lock.exists() and (time.time() - lock.stat().st_mtime) < _SENDER_DEBOUNCE_SECONDS:
                return False
        except OSError:
            pass
        try:
            lock.parent.mkdir(parents=True, exist_ok=True)
            lock.write_text(str(time.time()), encoding="utf-8")
        except OSError:
            pass

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
