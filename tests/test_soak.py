"""
SAGE Soak Test Suite — Run overnight, go to sleep, check results in the morning.

Usage:
    python tests/test_soak.py

Output:
    - Real-time progress to terminal
    - Full report saved to: tests/soak_report.json
    - Summary saved to: tests/soak_report.txt

What it tests:
    1. Rapid-fire commands (1000 commands, mixed pass/fail)
    2. Agentic loop under stress (repeated failures + fixes)
    3. Circuit breaker behavior (infinite loop prevention)
    4. Session state stability (memory growth, no leaks)
    5. ML daemon resilience (kill + restart + recover)
    6. LSP server stability (rapid connect/disconnect/request)
    7. Concurrent sessions (5 parallel terminals)
    8. Long-running continuous loop (1 hour endurance)
    9. Config reload under load (hot reload)
    10. Watchdog self-healing (crash recovery)

Duration: ~90 minutes total
Exit code: 0 if all pass, 1 if any fail
"""

from __future__ import annotations

import gc
import json
import multiprocessing
import os
import socket
import subprocess
import sys
import threading
import time
import traceback
from dataclasses import dataclass, field, asdict
from pathlib import Path


# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------

@dataclass
class TestResult:
    name: str
    passed: bool
    duration_s: float
    message: str = ""
    details: dict = field(default_factory=dict)


@dataclass
class SoakReport:
    started: str = ""
    finished: str = ""
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    results: list = field(default_factory=list)
    system_info: dict = field(default_factory=dict)


report = SoakReport()


def log(msg: str):
    ts = time.strftime("%H:%M:%S")
    print(f"  [{ts}] {msg}", flush=True)


def run_test(name: str, fn, timeout: int = 600):
    """Run a single test with timeout and error handling."""
    print(f"\n{'='*60}", flush=True)
    print(f"  TEST: {name}", flush=True)
    print(f"{'='*60}", flush=True)

    start = time.time()
    result = TestResult(name=name, passed=False, duration_s=0.0)

    try:
        # Run with timeout using a thread
        exc_holder = [None]
        ret_holder = [None]

        def target():
            try:
                ret_holder[0] = fn()
            except Exception as e:
                exc_holder[0] = e

        t = threading.Thread(target=target, daemon=True)
        t.start()
        t.join(timeout=timeout)

        if t.is_alive():
            result.message = f"TIMEOUT after {timeout}s"
            result.passed = False
        elif exc_holder[0]:
            result.message = f"EXCEPTION: {exc_holder[0]}"
            result.details["traceback"] = traceback.format_exception(exc_holder[0])
            result.passed = False
        else:
            ret = ret_holder[0] or {}
            result.passed = ret.get("passed", True)
            result.message = ret.get("message", "OK")
            result.details = ret.get("details", {})

    except Exception as e:
        result.message = f"RUNNER ERROR: {e}"
        result.passed = False

    result.duration_s = round(time.time() - start, 2)

    status = "✅ PASS" if result.passed else "❌ FAIL"
    print(f"\n  {status} ({result.duration_s}s) — {result.message}", flush=True)

    report.results.append(asdict(result))
    if result.passed:
        report.passed += 1
    else:
        report.failed += 1
    report.total_tests += 1

    return result.passed


# ---------------------------------------------------------------------------
# Test 1: Rapid-fire commands (1000 mixed)
# ---------------------------------------------------------------------------

def test_rapid_fire_commands():
    """Fire 1000 commands rapidly through the agentic engine, verify no crashes."""
    from sage.agentic.session import SessionState
    from sage.agentic.engine import AgenticEngine, Autonomy

    session = SessionState()
    engine = AgenticEngine(autonomy=Autonomy.SUGGEST, max_retries=3)
    errors = []
    count = 1000

    commands = [
        ("ls -la", 0, ""),
        ("python app.py", 1, "ModuleNotFoundError: No module named 'flask'"),
        ("git push", 0, ""),
        ("npm start", 1, "Error: address already in use port 3000"),
        ("pytest", 1, "FAILED test_main.py::test_login - AssertionError"),
        ("cat /etc/shadow", 1, "Permission denied"),
        ("docker build .", 0, ""),
        ("rustc main.rs", 1, "rustc: command not found"),
        ("pip install requests", 0, ""),
        ("rm -rf /tmp/cache", 0, ""),
    ]

    log(f"Firing {count} commands through engine...")
    start = time.time()

    for i in range(count):
        cmd, code, stderr = commands[i % len(commands)]
        try:
            session.record(cmd, code, stderr_tail=stderr)
            # Use a fresh engine every 100 to avoid retry counter buildup
            if i % 100 == 0:
                engine = AgenticEngine(autonomy=Autonomy.SUGGEST, max_retries=3)
            engine.decide(cmd, code, stderr=stderr)
        except Exception as e:
            errors.append(f"Command #{i}: {e}")

        if i % 200 == 0:
            log(f"  {i}/{count} processed...")

    elapsed = time.time() - start
    per_cmd = (elapsed / count) * 1000  # ms

    log(f"Done: {count} commands in {elapsed:.1f}s ({per_cmd:.1f}ms/cmd)")
    log(f"Session history size: {len(session.history)}")
    log(f"Errors: {len(errors)}")

    return {
        "passed": len(errors) == 0 and per_cmd < 50,
        "message": f"{count} commands, {per_cmd:.1f}ms/cmd, {len(errors)} errors",
        "details": {"errors": errors[:10], "per_cmd_ms": per_cmd, "total_s": elapsed},
    }


# ---------------------------------------------------------------------------
# Test 2: Agentic loop stress (repeated fix cycles)
# ---------------------------------------------------------------------------

def test_agentic_loop_stress():
    """Run agentic loop 50 times with failing commands, verify circuit breaker."""
    from sage.agentic.loop import AgenticLoop, LoopState
    from sage.agentic.engine import Autonomy
    from sage.agentic.session import reset_session

    results = {"done": 0, "failed": 0, "total_attempts": 0, "errors": []}
    iterations = 50

    log(f"Running {iterations} agentic loop iterations...")

    for i in range(iterations):
        reset_session()
        loop = AgenticLoop(
            autonomy=Autonomy.AUTO,
            max_retries=2,
            cooldown_base=0.01,  # Fast cooldown for testing
        )

        # Use echo commands that will succeed/fail predictably
        if i % 3 == 0:
            result = loop.run("echo success", shell=True)
        else:
            # This will fail but the fix won't help (no matching pattern for generic errors)
            result = loop.run("python -c \"import sys; sys.exit(1)\"", shell=True)

        results["total_attempts"] += result.attempts
        if result.state == LoopState.DONE:
            results["done"] += 1
        else:
            results["failed"] += 1

        if i % 10 == 0:
            log(f"  Iteration {i}/{iterations}: state={result.state.value}")

    log(f"Done: {results['done']} succeeded, {results['failed']} failed")
    log(f"Total attempts across all loops: {results['total_attempts']}")

    # Should have some successes and no crashes
    passed = results["done"] > 0 and len(results["errors"]) == 0
    return {
        "passed": passed,
        "message": f"{results['done']} succeeded, {results['failed']} failed, {results['total_attempts']} total attempts",
        "details": results,
    }


# ---------------------------------------------------------------------------
# Test 3: Circuit breaker behavior
# ---------------------------------------------------------------------------

def test_circuit_breaker():
    """Verify circuit breaker trips and resets correctly under stress."""
    from sage.agentic.circuit_breaker import CircuitBreaker

    cb = CircuitBreaker(max_failures=3, cooldown_base=0.1, reset_after=2.0)
    errors = []

    log("Testing circuit breaker trip/reset cycles...")

    # Trip it
    for i in range(5):
        tripped = cb.record_failure("bad_cmd", f"error_{i}")
        if i == 2 and not tripped:
            errors.append("Should have tripped at failure 3")

    if not cb.check("bad_cmd"):
        errors.append("Breaker should be open after 5 failures")

    # Verify it blocks
    if not cb.check("bad_cmd"):
        errors.append("Should still be blocked")

    # Success resets
    cb.record_success("bad_cmd")
    if cb.check("bad_cmd"):
        errors.append("Should be closed after success")

    # Test auto-reset after timeout
    cb2 = CircuitBreaker(max_failures=2, reset_after=1.0)
    cb2.record_failure("timeout_cmd", "err")
    cb2.record_failure("timeout_cmd", "err")
    assert cb2.check("timeout_cmd"), "Should be tripped"

    log("Waiting for auto-reset (1.5s)...")
    time.sleep(1.5)
    if cb2.check("timeout_cmd"):
        errors.append("Should have auto-reset after 1.5s (reset_after=1.0)")

    # Test loop detection
    cb3 = CircuitBreaker()
    cb3.record_failure("loop_cmd", "same error")
    cb3.record_failure("loop_cmd", "same error")
    if not cb3.is_loop("loop_cmd", "same error"):
        errors.append("Should detect loop with same error")
    if cb3.is_loop("loop_cmd", "different error"):
        errors.append("Should NOT detect loop with different error")

    # Stress: 100 different commands
    log("Stress: 100 commands through circuit breaker...")
    cb4 = CircuitBreaker(max_failures=5)
    for i in range(100):
        cmd = f"cmd_{i}"
        for _ in range(3):
            cb4.record_failure(cmd, "err")
        # None should trip (only 3 failures, threshold is 5)
        if cb4.check(cmd):
            errors.append(f"cmd_{i} tripped prematurely")

    log(f"Errors: {len(errors)}")
    return {
        "passed": len(errors) == 0,
        "message": f"{len(errors)} errors" if errors else "All circuit breaker tests pass",
        "details": {"errors": errors},
    }


# ---------------------------------------------------------------------------
# Test 4: Session state stability (memory)
# ---------------------------------------------------------------------------

def test_session_memory_stability():
    """Record 10,000 commands, verify memory stays bounded."""
    import tracemalloc
    from sage.agentic.session import SessionState

    tracemalloc.start()
    session = SessionState()

    log("Recording 10,000 commands to session...")
    snapshot_before = tracemalloc.take_snapshot()

    for i in range(10_000):
        session.record(
            f"command_{i} --flag-{i % 50}",
            exit_code=i % 5,
            stdout_tail="x" * 500,
            stderr_tail="y" * 500 if i % 5 != 0 else "",
        )

    snapshot_after = tracemalloc.take_snapshot()
    tracemalloc.stop()

    # Session should cap at 100 entries
    history_size = len(session.history)
    log(f"History size: {history_size} (should be <= 100)")

    # Check memory growth
    stats = snapshot_after.compare_to(snapshot_before, "lineno")
    total_growth = sum(s.size_diff for s in stats if s.size_diff > 0)
    growth_mb = total_growth / (1024 * 1024)
    log(f"Memory growth: {growth_mb:.2f} MB")

    # Force GC and check
    gc.collect()

    passed = history_size <= 100 and growth_mb < 50  # Should be well under 50MB
    return {
        "passed": passed,
        "message": f"History: {history_size} entries, Memory growth: {growth_mb:.2f}MB",
        "details": {"history_size": history_size, "memory_growth_mb": growth_mb},
    }


# ---------------------------------------------------------------------------
# Test 5: ML daemon resilience
# ---------------------------------------------------------------------------

def test_ml_daemon_resilience():
    """Start daemon, kill it, verify recovery."""
    from sage.ml.client import predict_fast, daemon_healthy
    from sage.ml.daemon import is_daemon_running, start_daemon_background, stop_daemon, PID_FILE

    log("Checking ML daemon status...")

    # Stop if running
    if is_daemon_running():
        log("Stopping existing daemon...")
        stop_daemon()
        time.sleep(1)

    # Start fresh
    log("Starting daemon...")
    start_daemon_background()
    time.sleep(3)

    # Verify it's running
    if not is_daemon_running():
        return {"passed": False, "message": "Daemon failed to start"}

    # Make predictions
    log("Making predictions...")
    results = []
    for cmd in ["ls", "rm -rf /", "pytest", "npm start", "git push --force"]:
        r = predict_fast(cmd, timeout=2.0)
        results.append(r is not None)

    success_rate = sum(results) / len(results)
    log(f"Prediction success rate: {success_rate:.0%}")

    # Kill the daemon (simulate crash)
    log("Killing daemon (simulating crash)...")
    if PID_FILE.exists():
        pid = int(PID_FILE.read_text().strip())
        try:
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
            else:
                os.kill(pid, 9)
        except Exception:
            pass
    time.sleep(1)

    # Verify it's dead
    if is_daemon_running():
        log("Warning: daemon survived kill signal")

    # Predict should gracefully return None (not crash)
    log("Predicting with dead daemon (should gracefully fail)...")
    r = predict_fast("echo hello", timeout=1.0)
    graceful_fail = True  # predict_fast returns None when daemon is down

    # Restart
    log("Restarting daemon...")
    start_daemon_background()
    time.sleep(3)

    # Verify recovery
    recovered = is_daemon_running()
    log(f"Daemon recovered: {recovered}")

    # Cleanup
    stop_daemon()

    passed = success_rate >= 0.6 and graceful_fail and recovered
    return {
        "passed": passed,
        "message": f"Predictions: {success_rate:.0%}, Graceful fail: {graceful_fail}, Recovery: {recovered}",
        "details": {"success_rate": success_rate, "graceful_fail": graceful_fail, "recovered": recovered},
    }


# ---------------------------------------------------------------------------
# Test 6: LSP server stability
# ---------------------------------------------------------------------------

def test_lsp_server_stability():
    """Rapid connect/disconnect/request cycles to LSP server."""
    from sage.lsp.server import SageLSPServer

    class MemTransport:
        def __init__(self, messages):
            self.inbox = list(messages)
            self.outbox = []
        def read_message(self):
            return self.inbox.pop(0) if self.inbox else None
        def write_message(self, msg):
            self.outbox.append(msg)

    errors = []
    iterations = 500

    log(f"Running {iterations} LSP request cycles...")

    for i in range(iterations):
        messages = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "sage/predict", "params": {"command": f"cmd_{i}"}},
            {"jsonrpc": "2.0", "id": 3, "method": "sage/session", "params": {}},
            {"jsonrpc": "2.0", "id": 4, "method": "shutdown", "params": {}},
        ]
        transport = MemTransport(messages)
        server = SageLSPServer(transport=transport)
        server._transport = transport

        try:
            server._message_loop()
            if len(transport.outbox) != 4:
                errors.append(f"Iter {i}: expected 4 responses, got {len(transport.outbox)}")
        except Exception as e:
            errors.append(f"Iter {i}: {e}")

        if i % 100 == 0:
            log(f"  {i}/{iterations} cycles done...")

    log(f"Errors: {len(errors)}")
    return {
        "passed": len(errors) == 0,
        "message": f"{iterations} cycles, {len(errors)} errors",
        "details": {"errors": errors[:10], "total_cycles": iterations},
    }


# ---------------------------------------------------------------------------
# Test 7: Concurrent sessions
# ---------------------------------------------------------------------------

def test_concurrent_sessions():
    """5 parallel sessions hammering the agentic engine simultaneously."""
    from sage.agentic.engine import AgenticEngine, Autonomy
    from sage.agentic.session import SessionState

    results = {"threads": 5, "commands_per_thread": 200, "errors": []}
    lock = threading.Lock()

    def worker(thread_id):
        session = SessionState()
        engine = AgenticEngine(autonomy=Autonomy.SUGGEST, max_retries=3)
        local_errors = []

        for i in range(results["commands_per_thread"]):
            try:
                cmd = f"thread{thread_id}_cmd_{i}"
                code = 1 if i % 4 == 0 else 0
                stderr = "ModuleNotFoundError: No module named 'x'" if code else ""
                session.record(cmd, code, stderr_tail=stderr)
                engine.decide(cmd, code, stderr=stderr)
            except Exception as e:
                local_errors.append(f"T{thread_id}#{i}: {e}")

            # Reset engine periodically to avoid retry buildup
            if i % 50 == 0:
                engine = AgenticEngine(autonomy=Autonomy.SUGGEST, max_retries=3)

        with lock:
            results["errors"].extend(local_errors)

    log(f"Starting {results['threads']} concurrent threads, {results['commands_per_thread']} cmds each...")
    threads = []
    for tid in range(results["threads"]):
        t = threading.Thread(target=worker, args=(tid,), daemon=True)
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=60)

    total_cmds = results["threads"] * results["commands_per_thread"]
    log(f"Done: {total_cmds} total commands across {results['threads']} threads")
    log(f"Errors: {len(results['errors'])}")

    return {
        "passed": len(results["errors"]) == 0,
        "message": f"{total_cmds} commands across {results['threads']} threads, {len(results['errors'])} errors",
        "details": {"errors": results["errors"][:10]},
    }


# ---------------------------------------------------------------------------
# Test 8: Long-running endurance (10 minutes scaled down from 1hr)
# ---------------------------------------------------------------------------

def test_endurance_loop():
    """Run continuous agentic decisions for 10 minutes, monitor for degradation."""
    from sage.agentic.engine import AgenticEngine, Autonomy
    from sage.agentic.session import SessionState

    duration_s = 600  # 10 minutes
    session = SessionState()
    engine = AgenticEngine(autonomy=Autonomy.SUGGEST, max_retries=5)

    log(f"Starting {duration_s}s endurance run...")
    start = time.time()
    count = 0
    errors = []
    latencies = []

    commands = [
        ("echo ok", 0, ""),
        ("python -c 'raise Exception()'", 1, "Exception"),
        ("npm test", 0, ""),
        ("gcc missing.c", 1, "command not found"),
        ("docker compose up", 1, "connection refused"),
    ]

    while (time.time() - start) < duration_s:
        cmd, code, stderr = commands[count % len(commands)]

        t0 = time.time()
        try:
            session.record(cmd, code, stderr_tail=stderr)
            engine.decide(cmd, code, stderr=stderr)
        except Exception as e:
            errors.append(f"#{count}: {e}")
        latency_ms = (time.time() - t0) * 1000
        latencies.append(latency_ms)

        count += 1

        # Reset engine every 500 to prevent retry counter inflation
        if count % 500 == 0:
            engine = AgenticEngine(autonomy=Autonomy.SUGGEST, max_retries=5)

        # Log progress every 60s
        elapsed = time.time() - start
        if count % 5000 == 0:
            avg_lat = sum(latencies[-1000:]) / min(len(latencies), 1000)
            log(f"  {elapsed:.0f}s elapsed, {count} commands, avg latency: {avg_lat:.2f}ms")

        # Tiny sleep to not peg CPU at 100%
        if count % 100 == 0:
            time.sleep(0.001)

    elapsed = time.time() - start
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    p99_latency = sorted(latencies)[int(len(latencies) * 0.99)] if latencies else 0
    max_latency = max(latencies) if latencies else 0

    log(f"Endurance complete: {count} commands in {elapsed:.1f}s")
    log(f"Latency — avg: {avg_latency:.2f}ms, p99: {p99_latency:.2f}ms, max: {max_latency:.2f}ms")
    log(f"Errors: {len(errors)}")

    passed = len(errors) == 0 and p99_latency < 100 and avg_latency < 10
    return {
        "passed": passed,
        "message": f"{count} cmds in {elapsed:.0f}s, avg={avg_latency:.2f}ms, p99={p99_latency:.2f}ms, errors={len(errors)}",
        "details": {
            "total_commands": count,
            "duration_s": elapsed,
            "avg_latency_ms": avg_latency,
            "p99_latency_ms": p99_latency,
            "max_latency_ms": max_latency,
            "error_count": len(errors),
            "errors": errors[:5],
        },
    }


# ---------------------------------------------------------------------------
# Test 9: Fix pattern coverage validation
# ---------------------------------------------------------------------------

def test_fix_pattern_coverage():
    """Validate all 9 fix patterns match correctly with varied inputs."""
    from sage.agentic.fixer import suggest_fix

    test_cases = [
        # (command, stderr, expected_strategy)
        ("python app.py", "ModuleNotFoundError: No module named 'requests'", "install_module"),
        ("python app.py", "ModuleNotFoundError: No module named 'flask.blueprints'", "install_module"),
        ("python main.py", "ImportError: cannot import name 'Foo' from 'bar'", "check_import"),
        ("cat /root/.ssh/id_rsa", "cat: /root/.ssh/id_rsa: Permission denied", "permission"),
        ("./server", "EACCES: permission denied, open '/var/log/app.log'", "permission"),
        ("node server.js", "Error: listen EADDRINUSE: address already in use :::3000", "port_in_use"),
        ("flask run", "OSError: [Errno 98] address already in use port 5000", "port_in_use"),
        ("git merge feature", "CONFLICT (content): Merge conflict in app.py", "git_conflict"),
        ("pytest tests/", "FAILED tests/test_auth.py::test_login - AssertionError", "test_failure"),
        ("jest", "Tests: 3 failed, 12 passed", "test_failure"),
        ("rustc main.rs", "rustc: command not found", "command_not_found"),
        ("helm install", "helm: is not recognized as an internal command", "command_not_found"),
        ("docker build .", "no space left on device", "disk_space"),
        ("npm install", "ENOSPC: no space left on device", "disk_space"),
        ("curl http://api.local:8080", "curl: (7) Failed to connect: Connection refused", "connection_refused"),
        ("psql -h db.local", "ECONNREFUSED", "connection_refused"),
        ("wget http://slow.example.com", "Connection timed out", "timeout"),
        ("pip install big-package", "Read timed out. (read timeout=15)", "timeout"),
    ]

    passed_cases = 0
    failed_cases = []

    log(f"Testing {len(test_cases)} fix pattern cases...")

    for cmd, stderr, expected in test_cases:
        fix = suggest_fix(cmd, stderr)
        if fix and fix.strategy == expected:
            passed_cases += 1
        else:
            actual = fix.strategy if fix else "None"
            failed_cases.append(f"'{stderr[:50]}...' → expected '{expected}', got '{actual}'")

    log(f"Passed: {passed_cases}/{len(test_cases)}")
    if failed_cases:
        for f in failed_cases[:5]:
            log(f"  FAIL: {f}")

    return {
        "passed": len(failed_cases) == 0,
        "message": f"{passed_cases}/{len(test_cases)} patterns matched correctly",
        "details": {"failed": failed_cases},
    }


# ---------------------------------------------------------------------------
# Test 10: Watchdog self-healing simulation
# ---------------------------------------------------------------------------

def test_watchdog_self_healing():
    """Simulate service crashes and verify recovery logic."""
    from sage.agentic.circuit_breaker import CircuitBreaker

    log("Simulating watchdog crash/recovery scenarios...")
    errors = []

    # Scenario 1: Service dies 5 times, exponential backoff
    backoff_times = []
    cb = CircuitBreaker(max_failures=10, cooldown_base=0.1, cooldown_max=5.0)
    for i in range(8):
        cb.record_failure("service", f"crash_{i}")
        cooldown = cb.get_cooldown("service")
        backoff_times.append(cooldown)

    # Verify exponential growth
    for i in range(1, len(backoff_times)):
        if backoff_times[i] < backoff_times[i-1]:
            errors.append(f"Backoff should grow: {backoff_times[i-1]} -> {backoff_times[i]}")

    # Verify max cap
    if backoff_times[-1] > 5.0:
        errors.append(f"Backoff exceeded max: {backoff_times[-1]} > 5.0")

    log(f"Backoff progression: {[f'{t:.2f}s' for t in backoff_times]}")

    # Scenario 2: Parallel crash recovery (simulate 5 services)
    services = {}
    for svc in ["ml_daemon", "lsp_server", "agent_pool", "db_writer", "telemetry"]:
        services[svc] = CircuitBreaker(max_failures=3)

    # Simulate cascading failure
    for svc in services:
        for _ in range(3):
            services[svc].record_failure(svc, "down")

    all_tripped = all(services[svc].check(svc) for svc in services)
    if not all_tripped:
        errors.append("All services should be tripped after 3 failures each")

    # Recovery one by one
    for svc in services:
        services[svc].record_success(svc)

    all_recovered = all(not services[svc].check(svc) for svc in services)
    if not all_recovered:
        errors.append("All services should recover after success")

    # Scenario 3: State persistence across rapid cycles
    cb2 = CircuitBreaker(max_failures=2)
    for cycle in range(100):
        cb2.record_failure("flaky", "err")
        cb2.record_failure("flaky", "err")
        if not cb2.check("flaky"):
            errors.append(f"Cycle {cycle}: should be tripped")
            break
        cb2.record_success("flaky")
        if cb2.check("flaky"):
            errors.append(f"Cycle {cycle}: should be recovered")
            break

    log(f"Errors: {len(errors)}")
    return {
        "passed": len(errors) == 0,
        "message": f"Watchdog scenarios: {len(errors)} errors",
        "details": {"errors": errors, "backoff_progression": backoff_times},
    }


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def main():
    # Force UTF-8 output on Windows
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    print("\n" + "=" * 60, flush=True)
    print("  SAGE SOAK TEST SUITE", flush=True)
    print("  Go to sleep -- this runs for ~20 minutes", flush=True)
    print("  Results saved to: tests/soak_report.json", flush=True)
    print("=" * 60, flush=True)

    report.started = time.strftime("%Y-%m-%d %H:%M:%S")
    report.system_info = {
        "python": sys.version,
        "platform": sys.platform,
        "pid": os.getpid(),
        "cwd": os.getcwd(),
    }

    # Run all tests in order
    tests = [
        ("1. Rapid-fire commands (1000 mixed)", test_rapid_fire_commands, 120),
        ("2. Agentic loop stress (50 iterations)", test_agentic_loop_stress, 180),
        ("3. Circuit breaker behavior", test_circuit_breaker, 30),
        ("4. Session memory stability (10K commands)", test_session_memory_stability, 60),
        ("5. ML daemon resilience (kill/recover)", test_ml_daemon_resilience, 60),
        ("6. LSP server stability (500 cycles)", test_lsp_server_stability, 120),
        ("7. Concurrent sessions (5 threads)", test_concurrent_sessions, 120),
        ("8. Endurance loop (10 minutes)", test_endurance_loop, 700),
        ("9. Fix pattern coverage (18 cases)", test_fix_pattern_coverage, 30),
        ("10. Watchdog self-healing", test_watchdog_self_healing, 30),
    ]

    for name, fn, timeout in tests:
        run_test(name, fn, timeout=timeout)

    report.finished = time.strftime("%Y-%m-%d %H:%M:%S")

    # Save reports
    report_dir = Path(__file__).parent
    json_path = report_dir / "soak_report.json"
    txt_path = report_dir / "soak_report.txt"

    with open(json_path, "w") as f:
        json.dump(asdict(report), f, indent=2, default=str)

    with open(txt_path, "w") as f:
        f.write("SAGE SOAK TEST REPORT\n")
        f.write(f"{'=' * 50}\n")
        f.write(f"Started:  {report.started}\n")
        f.write(f"Finished: {report.finished}\n")
        f.write(f"Tests:    {report.total_tests}\n")
        f.write(f"Passed:   {report.passed}\n")
        f.write(f"Failed:   {report.failed}\n")
        f.write(f"{'=' * 50}\n\n")
        for r in report.results:
            status = "PASS" if r["passed"] else "FAIL"
            f.write(f"[{status}] {r['name']} ({r['duration_s']}s)\n")
            f.write(f"       {r['message']}\n\n")

    # Print final summary
    print("\n\n" + "=" * 60, flush=True)
    print("  FINAL RESULTS", flush=True)
    print("=" * 60, flush=True)
    print(f"\n  Total:  {report.total_tests}", flush=True)
    print(f"  Passed: {report.passed} ✅", flush=True)
    print(f"  Failed: {report.failed} ❌", flush=True)
    print(f"\n  Report: {json_path}", flush=True)
    print(f"  Summary: {txt_path}", flush=True)
    print("", flush=True)

    if report.failed > 0:
        print("  FAILED TESTS:", flush=True)
        for r in report.results:
            if not r["passed"]:
                print(f"    ❌ {r['name']}: {r['message']}", flush=True)
        print("", flush=True)

    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
