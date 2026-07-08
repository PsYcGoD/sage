"""Phase 5: Agentic Loop Tests."""

import pytest

from sage.agentic.session import SessionState, get_session, reset_session
from sage.agentic.fixer import suggest_fix, suggest_fixes, FixSuggestion
from sage.agentic.intent import detect_intent, DetectedIntent
from sage.agentic.engine import AgenticEngine, Action, Autonomy, is_destructive
from sage.agentic.circuit_breaker import CircuitBreaker
from sage.agentic.loop import AgenticLoop, LoopState


class TestSession:
    def setup_method(self):
        reset_session()

    def test_record_and_retrieve(self):
        session = get_session()
        session.record("ls", 0)
        session.record("cat missing.txt", 1, stderr_tail="No such file")

        assert len(session.history) == 2
        assert session.last.exit_code == 1
        assert session.failure_streak == 1

    def test_success_resets_streak(self):
        session = get_session()
        session.record("bad", 1)
        session.record("bad", 1)
        assert session.failure_streak == 2
        session.record("good", 0)
        assert session.failure_streak == 0

    def test_detect_loop(self):
        session = get_session()
        for _ in range(4):
            session.record("npm start", 1, stderr_tail="EADDRINUSE port 3000")
        assert session.detect_loop("npm start", "EADDRINUSE port 3000")

    def test_no_loop_different_errors(self):
        session = get_session()
        session.record("npm start", 1, stderr_tail="error A")
        session.record("npm start", 1, stderr_tail="error B")
        session.record("npm start", 1, stderr_tail="error C")
        assert not session.detect_loop("npm start", "error D")


class TestFixer:
    def test_missing_module(self):
        fix = suggest_fix("python app.py", "ModuleNotFoundError: No module named 'flask'")
        assert fix is not None
        assert fix.strategy == "install_module"
        assert "pip install flask" in fix.fix_command

    def test_port_in_use(self):
        fix = suggest_fix("npm start", "Error: address already in use port 3000")
        assert fix is not None
        assert fix.strategy == "port_in_use"

    def test_permission_denied(self):
        fix = suggest_fix("cat /etc/shadow", "Permission denied")
        assert fix is not None
        assert fix.strategy == "permission"
        assert fix.destructive is True

    def test_command_not_found(self):
        fix = suggest_fix("rustc main.rs", "rustc: command not found")
        assert fix is not None
        assert fix.strategy == "command_not_found"

    def test_no_match(self):
        fix = suggest_fix("echo hello", "some random output")
        assert fix is None

    def test_suggest_fixes_returns_sorted(self):
        stderr = "ModuleNotFoundError: No module named 'foo'\nPermission denied"
        fixes = suggest_fixes("python app.py", stderr)
        assert len(fixes) >= 2
        assert fixes[0].confidence >= fixes[1].confidence


class TestIntent:
    def test_detect_deploy_intent(self):
        intent = detect_intent("npm run deploy", history=["npm run build", "npm test"])
        assert intent is not None
        assert intent.name == "deploy"
        assert intent.confidence >= 0.4

    def test_detect_fix_bug_intent(self):
        intent = detect_intent("pytest -v", history=["git log", "pytest", "vim fix.py"])
        assert intent is not None

    def test_no_intent_for_simple_command(self):
        intent = detect_intent("echo hello")
        assert intent is None


class TestEngine:
    def setup_method(self):
        reset_session()

    def test_success_logs(self):
        engine = AgenticEngine()
        decision = engine.decide("ls", 0)
        assert decision.action == Action.LOG_SUCCESS

    def test_failure_suggests_fix(self):
        engine = AgenticEngine(autonomy=Autonomy.SUGGEST)
        decision = engine.decide(
            "python app.py", 1,
            stderr="ModuleNotFoundError: No module named 'flask'"
        )
        assert decision.action == Action.SUGGEST_FIX
        assert decision.fix is not None

    def test_auto_mode_auto_fixes(self):
        engine = AgenticEngine(autonomy=Autonomy.AUTO)
        decision = engine.decide(
            "python app.py", 1,
            stderr="ModuleNotFoundError: No module named 'flask'"
        )
        assert decision.action == Action.AUTO_FIX
        assert decision.next_command is not None

    def test_destructive_never_auto_fixed(self):
        engine = AgenticEngine(autonomy=Autonomy.AUTO)
        decision = engine.decide(
            "cat /etc/shadow", 1,
            stderr="Permission denied"
        )
        assert decision.action == Action.SUGGEST_FIX  # Not AUTO_FIX

    def test_max_retries_escalates(self):
        engine = AgenticEngine(autonomy=Autonomy.AUTO, max_retries=2)
        # Use different stderr each time to avoid loop detection
        engine.decide("bad", 1, stderr="ModuleNotFoundError: No module named 'x1'")
        engine.decide("bad", 1, stderr="ModuleNotFoundError: No module named 'x2'")
        decision = engine.decide("bad", 1, stderr="ModuleNotFoundError: No module named 'x3'")
        assert decision.action == Action.ESCALATE

    def test_pre_check_destructive(self):
        engine = AgenticEngine()
        decision = engine.pre_check("rm -rf /")
        assert decision is not None
        assert decision.action == Action.WARN_DESTRUCTIVE

    def test_pre_check_safe(self):
        engine = AgenticEngine()
        decision = engine.pre_check("ls -la")
        assert decision is None


class TestCircuitBreaker:
    def test_trips_after_max_failures(self):
        cb = CircuitBreaker(max_failures=3)
        cb.record_failure("bad cmd", "error")
        cb.record_failure("bad cmd", "error")
        tripped = cb.record_failure("bad cmd", "error")
        assert tripped is True
        assert cb.check("bad cmd") is True

    def test_success_resets(self):
        cb = CircuitBreaker(max_failures=3)
        cb.record_failure("cmd", "err")
        cb.record_failure("cmd", "err")
        cb.record_success("cmd")
        assert cb.check("cmd") is False

    def test_loop_detection(self):
        cb = CircuitBreaker()
        cb.record_failure("npm start", "EADDRINUSE")
        cb.record_failure("npm start", "EADDRINUSE")
        assert cb.is_loop("npm start", "EADDRINUSE") is True

    def test_no_loop_different_errors(self):
        cb = CircuitBreaker()
        cb.record_failure("cmd", "error A")
        cb.record_failure("cmd", "error B")
        assert cb.is_loop("cmd", "error C") is False


class TestIsDestructive:
    def test_rm_rf(self):
        assert is_destructive("rm -rf /tmp/stuff") is True

    def test_force_push(self):
        assert is_destructive("git push --force origin main") is True

    def test_safe_commands(self):
        assert is_destructive("ls -la") is False
        assert is_destructive("git status") is False
        assert is_destructive("pytest") is False
