from __future__ import annotations
"""Background telemetry sender - non-blocking, best-effort sync.

Runs in a separate process to avoid slowing down sage run.
"""

import logging

import sys
import time

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

def spawn_background_sender() -> bool:
    """Keep telemetry local; the hosted sender service has been retired."""
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
