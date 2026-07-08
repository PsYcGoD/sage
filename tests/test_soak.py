"""
SAGE 6-Hour Soak Test — Run before sleep, check results when you wake up.

Usage:
    python tests/test_soak.py

What happens:
    - Runs 10 test batteries in a loop for 6 hours
    - Live output to terminal so you can see it's working
    - Full report saved to tests/soak_report.json every cycle
    - Graceful exit: Ctrl+C stops cleanly at next checkpoint
    - On completion: final summary printed + saved to tests/soak_report.txt

Duration: 6 hours (auto-exits cleanly after)
"""

from __future__ import annotations

import gc
import io
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import traceback
from dataclasses import dataclass, field, asdict
from pathlib import Path

# Force UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------

STOP = False

def _signal_handler(sig, frame):
    global STOP
    STOP = True
    print("\n\n  [CTRL+C] Stopping after current test finishes...\n", flush=True)

signal.signal(signal.SIGINT, _signal_handler)
if hasattr(signal, "SIGTERM"):
    signal.signal(signal.SIGTERM, _signal_handler)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DURATION_HOURS = 6
REPORT_DIR = Path(__file__).parent
JSON_REPORT = REPORT_DIR / "soak_report.json"
TXT_REPORT = REPORT_DIR / "soak_report.txt"

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

@dataclass
class CycleResult:
    cycle: int
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    duration_s: float = 0.0
    failures: list = field(default_factory=list)

@dataclass
class SoakState:
    started: str = ""
    last_update: str = ""
    total_cycles: int = 0
    total_tests: int = 0
    total_passed: int = 0
    total_failed: int = 0
    cycles: list = field(default_factory=list)
    current_status: str = "running"
    elapsed_hours: float = 0.0

state = SoakState()

def now():
    return time.strftime("%Y-%m-%d %H:%M:%S")

def log(msg: str):
    ts = time.strftime("%H:%M:%S")
    print(f"  [{ts}] {msg}", flush=True)

def save_report():
    """Save report to disk (called every cycle so you always have results)."""
    state.last_update = now()
    with open(JSON_REPORT, "w", encoding="utf-8") as f:
        json.dump(asdict(state), f, indent=2, default=str)

    with open(TXT_REPORT, "w", encoding="utf-8") as f:
        f.write("SAGE SOAK TEST REPORT\n")
        f.write(f"{'=' * 50}\n")
        f.write(f"Started:      {state.started}\n")
        f.write(f"Last update:  {state.last_update}\n")
        f.write(f"Status:       {state.current_status}\n")
        f.write(f"Elapsed:      {state.elapsed_hours:.1f} hours\n")
        f.write(f"Cycles:       {state.total_cycles}\n")
        f.write(f"Total tests:  {state.total_tests}\n")
        f.write(f"Passed:       {state.total_passed}\n")
        f.write(f"Failed:       {state.total_failed}\n")
        f.write(f"{'=' * 50}\n\n")
        for c in state.cycles:
            status = "ALL PASS" if c["tests_failed"] == 0 else f"{c['tests_failed']} FAILED"
            f.write(f"Cycle {c['cycle']}: {status} ({c['duration_s']:.1f}s)\n")
            for fail in c["failures"]:
                f.write(f"  X {fail}\n")
        f.write(f"\n{'=' * 50}\n")
        if state.total_failed == 0:
            f.write("RESULT: ALL TESTS PASSED ACROSS ALL CYCLES\n")
        else:
            f.write(f"RESULT: {state.total_failed} FAILURES TOTAL\n")

# ---------------------------------------------------------------------------
# Test functions (each returns True/False + appends to failures list)
# ---------------------------------------------------------------------------

def t_rapid_fire(failures: list) -> bool:
    """1000 commands through the engine."""
    from sage.agentic.session import SessionState
    from sage.agentic.engine import AgenticEngine, Autonomy

    session = SessionState()
    engine = AgenticEngine(autonomy=Autonomy.SUGGEST, max_retries=3)
    commands = [
        ("ls -la", 0, ""),
        ("python app.py", 1, "ModuleNotFoundError: No module named 'flask'"),
        ("npm start", 1, "Error: address already in use port 3000"),
        ("pytest", 1, "FAILED test_main.py - AssertionError"),
        ("cat /etc/shadow", 1, "Permission denied"),
        ("git push", 0, ""),
        ("docker build .", 0, ""),
        ("rustc main.rs", 1, "rustc: command not found"),
    ]

    for i in range(1000):
        cmd, code, stderr = commands[i % len(commands)]
        session.record(cmd, code, stderr_tail=stderr)
        if i % 100 == 0:
            engine = AgenticEngine(autonomy=Autonomy.SUGGEST, max_retries=3)
        engine.decide(cmd, code, stderr=stderr)

    if len(session.history) > 100:
        failures.append(f"rapid_fire: history unbounded ({len(session.history)})")
        return False
    return True


def t_circuit_breaker(failures: list) -> bool:
    """Circuit breaker trips, resets, detects loops."""
    from sage.agentic.circuit_breaker import CircuitBreaker

    cb = CircuitBreaker(max_failures=3, cooldown_base=0.05, reset_after=0.5)

    # Trip
    for i in range(3):
        cb.record_failure("bad", "err")
    if not cb.check("bad"):
        failures.append("circuit_breaker: didn't trip after 3 failures")
        return False

    # Reset on success
    cb.record_success("bad")
    if cb.check("bad"):
        failures.append("circuit_breaker: didn't reset on success")
        return False

    # Auto-reset after timeout
    cb2 = CircuitBreaker(max_failures=2, reset_after=0.3)
    cb2.record_failure("x", "e")
    cb2.record_failure("x", "e")
    time.sleep(0.4)
    if cb2.check("x"):
        failures.append("circuit_breaker: didn't auto-reset")
        return False

    # Loop detection
    cb3 = CircuitBreaker()
    cb3.record_failure("loop", "same")
    cb3.record_failure("loop", "same")
    if not cb3.is_loop("loop", "same"):
        failures.append("circuit_breaker: missed loop")
        return False

    return True


def t_fix_patterns(failures: list) -> bool:
    """All fix patterns match correctly."""
    from sage.agentic.fixer import suggest_fix

    cases = [
        ("python app.py", "ModuleNotFoundError: No module named 'requests'", "install_module"),
        ("python main.py", "ImportError: cannot import name 'Foo' from 'bar'", "check_import"),
        ("cat /root/secret", "Permission denied", "permission"),
        ("node server.js", "EADDRINUSE: address already in use port 3000", "port_in_use"),
        ("git merge feat", "CONFLICT (content): Merge conflict in app.py", "git_conflict"),
        ("pytest tests/", "FAILED tests/test_auth.py - AssertionError", "test_failure"),
        ("helm install", "helm: command not found", "command_not_found"),
        ("npm install", "ENOSPC: no space left on device", "disk_space"),
        ("curl localhost:8080", "Connection refused", "connection_refused"),
        ("wget http://slow.test", "Connection timed out", "timeout"),
    ]

    for cmd, stderr, expected in cases:
        fix = suggest_fix(cmd, stderr)
        if not fix or fix.strategy != expected:
            actual = fix.strategy if fix else "None"
            failures.append(f"fix_patterns: '{stderr[:40]}' expected={expected} got={actual}")
            return False
    return True


def t_session_memory(failures: list) -> bool:
    """10K commands, memory stays bounded."""
    from sage.agentic.session import SessionState

    session = SessionState()
    for i in range(10_000):
        session.record(f"cmd_{i}", i % 5, stdout_tail="x" * 200, stderr_tail="y" * 200)

    if len(session.history) > 100:
        failures.append(f"session_memory: history={len(session.history)} (should be <=100)")
        return False
    gc.collect()
    return True


def t_engine_decisions(failures: list) -> bool:
    """Engine makes correct decisions for all action types."""
    from sage.agentic.engine import AgenticEngine, Action, Autonomy
    from sage.agentic.session import reset_session

    reset_session()
    engine = AgenticEngine(autonomy=Autonomy.AUTO, max_retries=2)

    # Success -> LOG_SUCCESS
    d = engine.decide("echo hi", 0)
    if d.action != Action.LOG_SUCCESS:
        failures.append(f"engine: success should be LOG_SUCCESS, got {d.action}")
        return False

    # Failure with pattern -> AUTO_FIX (auto mode)
    d = engine.decide("python x.py", 1, stderr="ModuleNotFoundError: No module named 'foo'")
    if d.action != Action.AUTO_FIX:
        failures.append(f"engine: pattern match should AUTO_FIX, got {d.action}")
        return False

    # Destructive -> never auto-fix
    reset_session()
    engine2 = AgenticEngine(autonomy=Autonomy.AUTO)
    d = engine2.decide("cat /etc/shadow", 1, stderr="Permission denied")
    if d.action == Action.AUTO_FIX:
        failures.append("engine: destructive fix should NOT be AUTO_FIX")
        return False

    # Pre-check destructive
    d = engine2.pre_check("rm -rf /")
    if not d or d.action != Action.WARN_DESTRUCTIVE:
        failures.append("engine: rm -rf should warn")
        return False

    return True


def t_intent_detection(failures: list) -> bool:
    """Intent detection finds workflows."""
    from sage.agentic.intent import detect_intent

    intent = detect_intent("npm run deploy", history=["npm run build", "npm test"])
    if not intent or intent.name != "deploy":
        failures.append(f"intent: deploy not detected, got {intent}")
        return False

    intent = detect_intent("echo hello")
    if intent is not None:
        failures.append(f"intent: simple cmd should be None, got {intent.name}")
        return False

    return True


def t_lsp_server(failures: list) -> bool:
    """LSP server handles 200 request cycles without error."""
    from sage.lsp.server import SageLSPServer

    class FakeTransport:
        def __init__(self, msgs):
            self.inbox = list(msgs)
            self.outbox = []
        def read_message(self):
            return self.inbox.pop(0) if self.inbox else None
        def write_message(self, msg):
            self.outbox.append(msg)

    for i in range(200):
        msgs = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "sage/predict", "params": {"command": f"test_{i}"}},
            {"jsonrpc": "2.0", "id": 3, "method": "shutdown", "params": {}},
        ]
        t = FakeTransport(msgs)
        srv = SageLSPServer(transport=t)
        srv._transport = t
        srv._message_loop()
        if len(t.outbox) != 3:
            failures.append(f"lsp: cycle {i} got {len(t.outbox)} responses, expected 3")
            return False
    return True


def t_concurrent(failures: list) -> bool:
    """5 threads hammering engine simultaneously."""
    from sage.agentic.engine import AgenticEngine, Autonomy
    from sage.agentic.session import SessionState

    errors = []
    lock = threading.Lock()

    def worker(tid):
        session = SessionState()
        engine = AgenticEngine(autonomy=Autonomy.SUGGEST, max_retries=3)
        for i in range(300):
            try:
                session.record(f"t{tid}_{i}", i % 3, stderr_tail="err" if i % 3 else "")
                engine.decide(f"t{tid}_{i}", i % 3, stderr="ModuleNotFoundError: No module named 'x'" if i % 3 == 1 else "")
                if i % 60 == 0:
                    engine = AgenticEngine(autonomy=Autonomy.SUGGEST, max_retries=3)
            except Exception as e:
                with lock:
                    errors.append(f"T{tid}#{i}: {e}")

    threads = [threading.Thread(target=worker, args=(t,), daemon=True) for t in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    if errors:
        failures.append(f"concurrent: {len(errors)} errors — {errors[0]}")
        return False
    return True


def t_agentic_loop(failures: list) -> bool:
    """Agentic loop runs 20 iterations without crash."""
    from sage.agentic.loop import AgenticLoop, LoopState
    from sage.agentic.engine import Autonomy
    from sage.agentic.session import reset_session

    successes = 0
    for i in range(20):
        reset_session()
        loop = AgenticLoop(autonomy=Autonomy.AUTO, max_retries=1, cooldown_base=0.01)
        if i % 2 == 0:
            result = loop.run("echo ok", shell=True)
            if result.state == LoopState.DONE:
                successes += 1
        else:
            result = loop.run("python -c \"import sys; sys.exit(1)\"", shell=True)

    if successes < 8:
        failures.append(f"agentic_loop: only {successes}/10 echo commands succeeded")
        return False
    return True


def t_ml_predict(failures: list) -> bool:
    """ML predictor runs without crash (heuristic mode)."""
    from sage.ml.predictor import FailurePredictor

    p = FailurePredictor()
    p._v2_failed = True  # Force heuristic mode for speed

    commands = ["ls", "rm -rf /", "pytest", "npm start", "git push --force", "echo hello",
                "docker compose up", "pip install flask", "curl localhost", "make build"]

    for cmd in commands:
        will_fail, confidence, reason = p.predict(cmd)
        if not isinstance(will_fail, bool):
            failures.append(f"ml_predict: '{cmd}' returned non-bool: {will_fail}")
            return False
        if not (0 <= confidence <= 1):
            failures.append(f"ml_predict: '{cmd}' confidence out of range: {confidence}")
            return False
    return True


# All tests in order
ALL_TESTS = [
    ("rapid_fire_1000", t_rapid_fire),
    ("circuit_breaker", t_circuit_breaker),
    ("fix_patterns", t_fix_patterns),
    ("session_memory_10k", t_session_memory),
    ("engine_decisions", t_engine_decisions),
    ("intent_detection", t_intent_detection),
    ("lsp_server_200", t_lsp_server),
    ("concurrent_5threads", t_concurrent),
    ("agentic_loop_20x", t_agentic_loop),
    ("ml_predict", t_ml_predict),
]

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run_cycle(cycle_num: int) -> CycleResult:
    """Run one full cycle of all tests."""
    result = CycleResult(cycle=cycle_num)
    start = time.time()

    for name, fn in ALL_TESTS:
        if STOP:
            break
        failures = []
        try:
            passed = fn(failures)
        except Exception as e:
            passed = False
            failures.append(f"{name}: EXCEPTION {e}")

        result.tests_run += 1
        if passed:
            result.tests_passed += 1
        else:
            result.tests_failed += 1
            result.failures.extend(failures)

    result.duration_s = round(time.time() - start, 1)
    return result


def main():
    global STOP

    start_time = time.time()
    end_time = start_time + (DURATION_HOURS * 3600)

    state.started = now()
    print(f"\n{'=' * 60}", flush=True)
    print(f"  SAGE SOAK TEST — {DURATION_HOURS} HOUR RUN", flush=True)
    print(f"  Started: {state.started}", flush=True)
    print(f"  Stop cleanly: Ctrl+C", flush=True)
    print(f"  Reports: {JSON_REPORT}", flush=True)
    print(f"{'=' * 60}\n", flush=True)

    cycle = 0
    while time.time() < end_time and not STOP:
        cycle += 1
        elapsed_h = (time.time() - start_time) / 3600
        remaining_h = DURATION_HOURS - elapsed_h
        state.elapsed_hours = round(elapsed_h, 2)

        print(f"\n--- Cycle {cycle} | {elapsed_h:.1f}h elapsed | {remaining_h:.1f}h remaining ---", flush=True)

        result = run_cycle(cycle)
        state.total_cycles = cycle
        state.total_tests += result.tests_run
        state.total_passed += result.tests_passed
        state.total_failed += result.tests_failed
        state.cycles.append(asdict(result))

        # Print cycle result
        if result.tests_failed == 0:
            print(f"  Cycle {cycle}: ALL {result.tests_run} PASS ({result.duration_s}s)", flush=True)
        else:
            print(f"  Cycle {cycle}: {result.tests_failed} FAILED / {result.tests_run} ({result.duration_s}s)", flush=True)
            for f in result.failures:
                print(f"    X {f}", flush=True)

        # Save after every cycle
        save_report()

        # Wait between cycles (30s breather, also makes 6h achievable)
        if not STOP and time.time() < end_time:
            wait = 30
            log(f"Next cycle in {wait}s...")
            for _ in range(wait):
                if STOP:
                    break
                time.sleep(1)

    # Final
    state.current_status = "stopped_by_user" if STOP else "completed"
    state.elapsed_hours = round((time.time() - start_time) / 3600, 2)
    save_report()

    print(f"\n\n{'=' * 60}", flush=True)
    print(f"  SOAK TEST COMPLETE", flush=True)
    print(f"{'=' * 60}", flush=True)
    print(f"  Status:   {state.current_status}", flush=True)
    print(f"  Duration: {state.elapsed_hours:.1f} hours", flush=True)
    print(f"  Cycles:   {state.total_cycles}", flush=True)
    print(f"  Tests:    {state.total_tests}", flush=True)
    print(f"  Passed:   {state.total_passed}", flush=True)
    print(f"  Failed:   {state.total_failed}", flush=True)
    print(f"\n  JSON: {JSON_REPORT}", flush=True)
    print(f"  TXT:  {TXT_REPORT}", flush=True)
    print(f"{'=' * 60}\n", flush=True)

    return 0 if state.total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
