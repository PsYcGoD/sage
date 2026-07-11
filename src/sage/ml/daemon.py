"""SAGE ML Prediction Daemon — loads model once, serves predictions via local socket."""

from __future__ import annotations

import json
import logging
import gc
import os
import signal
import socket
import sys
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

DAEMON_HOST = "127.0.0.1"
DAEMON_PORT = 19472
_DATA_DIR = Path(os.environ.get("SAGE_DATA_DIR", "")) if os.environ.get("SAGE_DATA_DIR") else Path.home() / ".sage"
PID_FILE = _DATA_DIR / "ml-daemon.pid"
START_LOCK_FILE = _DATA_DIR / "ml-daemon-start.lock"
MAX_REQUEST_SIZE = 8192
IDLE_TIMEOUT = 10  # seconds before daemon sleeps


class MLDaemon:
    """Background prediction server using V2 embeddings + heuristics."""

    def __init__(self):
        self._server: socket.socket | None = None
        self._running = False
        self._predictor = None
        self._ready = threading.Event()
        self._last_activity = time.time()
        self._sleeping = False
        self._sleep_lock = threading.Lock()

    def start(self):
        """Start the daemon — blocks until shutdown."""
        self._running = True
        self._write_pid()
        self._setup_signals()

        # Warm the model in a thread so we can accept connections immediately
        warm_thread = threading.Thread(target=self._warm_model, daemon=True)
        warm_thread.start()

        # Idle watchdog — puts daemon to sleep after IDLE_TIMEOUT
        idle_thread = threading.Thread(target=self._idle_watchdog, daemon=True)
        idle_thread.start()

        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self._server.bind((DAEMON_HOST, DAEMON_PORT))
        except OSError as e:
            logger.error(f"Cannot bind to {DAEMON_HOST}:{DAEMON_PORT}: {e}")
            self._cleanup()
            sys.exit(1)

        self._server.listen(8)
        self._server.settimeout(1.0)
        logger.info(f"ML daemon listening on {DAEMON_HOST}:{DAEMON_PORT}")
        print(f"[sage-ml] daemon ready on {DAEMON_HOST}:{DAEMON_PORT} (pid {os.getpid()})")

        while self._running:
            try:
                conn, _addr = self._server.accept()
                threading.Thread(
                    target=self._handle_client, args=(conn,), daemon=True
                ).start()
            except socket.timeout:
                continue
            except OSError:
                if self._running:
                    logger.exception("Accept error")
                break

        self._cleanup()

    def _warm_model(self):
        """Load the prediction pipeline — heuristics first (instant), then V2 (slow)."""
        from .predictor import FailurePredictor
        predictor = FailurePredictor()
        predictor._v2_failed = True  # Start with heuristics only
        self._predictor = predictor
        self._ready.set()  # Accept predictions immediately
        logger.info("ML daemon ready (heuristics mode)")

        # Now try loading V2 embeddings in the background
        if self._sleeping or not self._running:
            return
        try:
            predictor._v2_failed = False
            store = predictor._get_vector_store()
            if store:
                logger.info(f"V2 model loaded: {store.size} commands indexed")
            else:
                predictor._v2_failed = True
                logger.info("V2 not available, staying in heuristics mode")
        except Exception as e:
            if self._predictor is predictor:
                predictor._v2_failed = True
            logger.info(f"V2 warmup failed ({e}), staying in heuristics mode")

    def _idle_watchdog(self):
        """Monitor activity and sleep the daemon after IDLE_TIMEOUT of inactivity."""
        while self._running:
            time.sleep(1)
            if self._sleeping:
                continue
            elapsed = time.time() - self._last_activity
            if elapsed >= IDLE_TIMEOUT:
                self._sleep()

    def _sleep(self):
        """Unload the model and enter sleep state."""
        with self._sleep_lock:
            if self._sleeping:
                return
            self._sleeping = True
            self._ready.clear()
            self._predictor = None
            gc.collect()
            logger.info("ML daemon sleeping (idle timeout)")

    def _wake(self):
        """Reload the model and resume serving predictions."""
        with self._sleep_lock:
            if not self._sleeping:
                return
            self._sleeping = False
            logger.info("ML daemon waking up")
        self._warm_model()

    def _handle_client(self, conn: socket.socket):
        """Handle a single prediction request."""
        conn.settimeout(5.0)
        try:
            data = conn.recv(MAX_REQUEST_SIZE)
            if not data:
                return
            request = json.loads(data.decode("utf-8"))
            command = request.get("command", "")

            if request.get("action") == "health":
                response = {"ok": True, "ready": self._ready.is_set(), "pid": os.getpid(), "sleeping": self._sleeping}
            elif request.get("action") == "shutdown":
                self._running = False
                response = {"ok": True, "action": "shutdown"}
            elif command:
                self._last_activity = time.time()
                if self._sleeping:
                    self._wake()
                response = self._predict(command)
            else:
                response = {"ok": False, "error": "no command"}

            conn.sendall(json.dumps(response).encode("utf-8"))
        except Exception as e:
            try:
                conn.sendall(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))
            except Exception:
                pass
        finally:
            conn.close()

    def _predict(self, command: str) -> dict:
        """Run prediction and return result dict."""
        if not self._ready.wait(timeout=15):
            return {"ok": False, "error": "model still loading"}

        try:
            will_fail, confidence, reason = self._predictor.predict(command)
            return {
                "ok": True,
                "will_fail": will_fail,
                "confidence": round(confidence, 4),
                "reason": reason,
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _setup_signals(self):
        """Handle graceful shutdown."""
        def _shutdown(signum, frame):
            self._running = False

        signal.signal(signal.SIGTERM, _shutdown)
        signal.signal(signal.SIGINT, _shutdown)

    def _write_pid(self):
        """Write PID file for auto-start detection."""
        PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(os.getpid()))

    def _cleanup(self):
        """Clean up on shutdown."""
        if self._server:
            self._server.close()
        if PID_FILE.exists():
            try:
                PID_FILE.unlink()
            except OSError:
                pass
        logger.info("ML daemon stopped")


def is_daemon_running() -> bool:
    """Check if the ML daemon is alive."""
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            # Check if process exists
            if sys.platform == "win32":
                import ctypes
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.OpenProcess(0x1000, False, pid)
                if handle:
                    kernel32.CloseHandle(handle)
                    return _check_socket()
            else:
                os.kill(pid, 0)
                return _check_socket()
        except (ValueError, OSError, ProcessLookupError):
            # Stale PID file
            try:
                PID_FILE.unlink()
            except OSError:
                pass
    return False


def _check_socket() -> bool:
    """Quick check if daemon port is responding."""
    return _check_socket_status().get("ok", False)


def _check_socket_status() -> dict:
    """Health check returning the full status dict."""
    try:
        with socket.create_connection((DAEMON_HOST, DAEMON_PORT), timeout=0.5) as s:
            s.sendall(json.dumps({"action": "health"}).encode("utf-8"))
            data = s.recv(1024)
            return json.loads(data.decode("utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def start_daemon_background() -> bool:
    """Spawn the ML daemon as a detached background process."""
    if is_daemon_running():
        return True
    lock = _acquire_start_lock()
    if lock is None:
        for _ in range(10):
            time.sleep(0.3)
            if is_daemon_running():
                return True
        return False

    import subprocess

    try:
        if is_daemon_running():
            return True

        python = sys.executable
        cmd = [python, "-m", "sage.ml.daemon"]

        if sys.platform == "win32":
            CREATE_NO_WINDOW = 0x08000000
            DETACHED_PROCESS = 0x00000008
            subprocess.Popen(
                cmd,
                creationflags=CREATE_NO_WINDOW | DETACHED_PROCESS,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
        else:
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )

        # Wait briefly for daemon to bind
        for _ in range(10):
            time.sleep(0.3)
            if _check_socket():
                return True
        return False
    finally:
        _release_start_lock(lock)


def _acquire_start_lock():
    START_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    handle = START_LOCK_FILE.open("a+b")
    try:
        if sys.platform == "win32":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        handle.seek(0)
        handle.truncate()
        handle.write(str(os.getpid()).encode("ascii", errors="ignore") or b"0")
        handle.flush()
        return handle
    except OSError:
        handle.close()
        return None


def _release_start_lock(handle) -> None:
    try:
        if sys.platform == "win32":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass
    finally:
        handle.close()


def stop_daemon() -> bool:
    """Stop the running daemon."""
    try:
        with socket.create_connection((DAEMON_HOST, DAEMON_PORT), timeout=2) as s:
            s.sendall(json.dumps({"action": "shutdown"}).encode("utf-8"))
            s.recv(1024)
        return True
    except OSError:
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    daemon = MLDaemon()
    daemon.start()
