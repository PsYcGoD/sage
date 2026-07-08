from __future__ import annotations
import logging

import os
import subprocess
import sys
import queue
import threading
import time
import uuid
from pathlib import Path

from .artifacts import store_raw_output
from .classify import classify_command, workspace_hash
from .detectors import summarize_output
from .store import save_run
from .context import ContextManager
from .context.tokens import is_real_tokenizer
from .security import command_hash, evaluate_command, load_policy, redact_text, retention_expiry

log = logging.getLogger(__name__)


def _build_popen_cmd(command_text: str, command_parts: list[str]) -> tuple:
    """Return (args, use_shell) appropriate for the current shell on Windows.

    On non-Windows: returns (command_parts, False).
    On Windows + SAGE_SHELL set: uses that shell explicitly (e.g. pwsh, powershell).
    On Windows default: cmd.exe via shell=True.

    To run PowerShell built-ins through SAGE, set SAGE_SHELL=pwsh (or powershell).
    """
    if not sys.platform.startswith("win"):
        return command_parts, False

    shell_override = os.environ.get("SAGE_SHELL", "").strip()
    if shell_override:
        return [shell_override, "-NoProfile", "-Command", command_text], False

    return command_text, True


def _configure_stdio() -> None:
    """Keep Windows terminals from crashing or corrupting UTF-8 AI output."""
    for stream in (sys.stdout, sys.stderr):
        try:
            if not hasattr(stream, "reconfigure"):
                continue
            if hasattr(stream, "isatty") and not stream.isatty():
                continue
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

def _print_stream(text: str, *, stderr: bool = False) -> None:
    """Print one streamed chunk without losing the saved original text."""
    target = sys.stderr if stderr else sys.stdout
    try:
        print(text, end="", file=target, flush=True)
    except UnicodeEncodeError:
        safe = text.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
        print(safe, end="", file=target, flush=True)

def run_command(
    command_parts: list[str],
    *,
    predict: bool = False,
    policy_mode: str | None = None,
    dry_run: bool = False,
    caller: str = "cli",
    kind_override: str = "",
    session_id: str = "",
    is_ai_session: int = 0,
    pty: bool = False,
) -> int:
    _configure_stdio()
    if not command_parts:
        print("No command was provided. Example: sage run -- python --version")
        return 2

    command_text = subprocess.list2cmdline(command_parts)
    decision = evaluate_command(command_text, mode=policy_mode, dry_run=dry_run)
    if decision.decision == "dry_run":
        print(f"[sage] policy: {decision.decision} ({decision.mode}) - {decision.reason}")
        return 0
    if decision.decision == "blocked":
        print(f"[sage] policy: blocked ({decision.mode}) - {decision.reason}")
        return 126
    if decision.risky:
        print(f"[sage] policy: {decision.decision} ({decision.mode}) - {decision.reason}")

    # Auto-predict: query ML daemon (fast, ~5ms) or fall back to local heuristics.
    # Daemon auto-starts on first command if not running.
    if os.environ.get("SAGE_DISABLE_PREDICT") != "1":
        try:
            from .ml.client import predict_fast, daemon_healthy

            result = predict_fast(command_text)
            if result is None and not daemon_healthy(timeout=0.1):
                # Daemon not running — start it in background for next command
                from .ml.daemon import start_daemon_background
                threading.Thread(
                    target=start_daemon_background, daemon=True, name="sage-ml-start"
                ).start()
                # Fall back to fast local heuristics for THIS command
                from .ml.predictor import FailurePredictor
                _predictor = FailurePredictor()
                _predictor._v2_failed = True
                will_fail, confidence, reason = _predictor.predict(command_text)
                result = {"will_fail": will_fail, "confidence": confidence, "reason": reason}

            if result and result.get("will_fail") and result.get("confidence", 0) >= 0.55:
                conf = result["confidence"]
                reason = result.get("reason", "")
                print(f"[sage] prediction: likely to fail ({conf:.0%}) - {reason}")
        except Exception:
            pass

    started = time.perf_counter()
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")

    if pty:
        return _run_interactive_passthrough(
            command_parts,
            command_text=command_text,
            started=started,
            env=env,
            decision=decision,
            caller=caller,
            kind_override=kind_override,
            session_id=session_id,
            is_ai_session=is_ai_session,
        )

    popen_args, use_shell = _build_popen_cmd(command_text, command_parts)
    process = subprocess.Popen(
        popen_args,
        shell=use_shell,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    output_queue: queue.Queue[tuple[str, str | None]] = queue.Queue()

    def enqueue_stream(stream, stream_name: str) -> None:
        try:
            if stream:
                while True:
                    chunk = stream.read(1)
                    if chunk == "":
                        break
                    output_queue.put((stream_name, chunk))
        finally:
            output_queue.put((stream_name, None))

    threading.Thread(target=enqueue_stream, args=(process.stdout, "stdout"), daemon=True).start()
    threading.Thread(target=enqueue_stream, args=(process.stderr, "stderr"), daemon=True).start()

    stdout_parts: list[str] = []
    stderr_parts: list[str] = []
    stdout_done = False
    stderr_done = False
    try:
        live_output_limit = int(os.environ.get("SAGE_LIVE_OUTPUT_LIMIT", "12000"))
    except ValueError:
        live_output_limit = 12000
    live_stdout_chars = 0
    live_stderr_chars = 0
    stdout_cap_reported = False
    stderr_cap_reported = False

    while not (stdout_done and stderr_done):
        stream_name, line = output_queue.get()
        if line is None:
            if stream_name == "stdout":
                stdout_done = True
            else:
                stderr_done = True
            continue

        if stream_name == "stdout":
            stdout_parts.append(line)
            if live_output_limit <= 0:
                _print_stream(line)
            elif live_stdout_chars < live_output_limit:
                remaining = live_output_limit - live_stdout_chars
                _print_stream(line[:remaining])
                live_stdout_chars += len(line[:remaining])
                if len(line) > remaining and not stdout_cap_reported:
                    _print_stream(
                        f"\n[sage] live stdout capped at {live_output_limit} chars; "
                        "full redacted output is stored locally and summary follows.\n"
                    )
                    stdout_cap_reported = True
            elif not stdout_cap_reported:
                _print_stream(
                    f"\n[sage] live stdout capped at {live_output_limit} chars; "
                    "full redacted output is stored locally and summary follows.\n"
                )
                stdout_cap_reported = True
        else:
            stderr_parts.append(line)
            if live_output_limit <= 0:
                _print_stream(line, stderr=True)
            elif live_stderr_chars < live_output_limit:
                remaining = live_output_limit - live_stderr_chars
                _print_stream(line[:remaining], stderr=True)
                live_stderr_chars += len(line[:remaining])
                if len(line) > remaining and not stderr_cap_reported:
                    _print_stream(
                        f"\n[sage] live stderr capped at {live_output_limit} chars; "
                        "full redacted output is stored locally and summary follows.\n",
                        stderr=True,
                    )
                    stderr_cap_reported = True
            elif not stderr_cap_reported:
                _print_stream(
                    f"\n[sage] live stderr capped at {live_output_limit} chars; "
                    "full redacted output is stored locally and summary follows.\n",
                    stderr=True,
                )
                stderr_cap_reported = True

    returncode = process.wait()
    duration_ms = int((time.perf_counter() - started) * 1000)
    stdout = "".join(stdout_parts)
    stderr = "".join(stderr_parts)

    summary = summarize_output(stdout, stderr, returncode)
    strictness = str(load_policy().get("redaction_strictness") or "standard")
    stdout_redacted = redact_text(stdout, strictness=strictness)
    stderr_redacted = redact_text(stderr, strictness=strictness)
    summary_redacted = redact_text(summary, strictness=strictness)
    command_class = classify_command(command_text)

    # Generate session_id if not provided and in AI context
    if not session_id:
        session_id = os.environ.get("SAGE_SESSION_ID", "")

    # Detect AI session context
    if not is_ai_session:
        # Check if this is an AI-related command. Agent terminal mode invokes the
        # provider as `sage run -- claude ...` or `sage run -- codex ...`, not
        # with `--claude`/`--codex` flags.
        ai_commands = {
            "claude",
            "claude.exe",
            "claude.cmd",
            "codex",
            "codex.exe",
            "codex.cmd",
            "opencode",
            "opencode.exe",
            "opencode.cmd",
            "cursor",
            "cursor.exe",
            "cursor.cmd",
            "windsurf",
            "windsurf.exe",
            "windsurf.cmd",
            "aider",
            "aider.exe",
            "aider.cmd",
        }
        first_command = Path(command_parts[0]).name.lower() if command_parts else ""
        is_ai_related = (
            first_command in ai_commands
            or any(marker in command_text.lower() for marker in ["--claude", "--codex"])
            or caller in ["mcp", "agent"]
        )
        is_ai_session = 1 if is_ai_related else 0

        # Generate new session ID for AI commands
        if is_ai_session and not session_id:
            session_id = str(uuid.uuid4())
            os.environ["SAGE_SESSION_ID"] = session_id

    run_id = save_run(
        project=str(Path.cwd()),
        command=command_text,
        exit_code=returncode,
        duration_ms=duration_ms,
        stdout=stdout_redacted.text,
        stderr=stderr_redacted.text,
        summary=summary_redacted.text,
        stdout_redactions=stdout_redacted.count,
        stderr_redactions=stderr_redacted.count,
        summary_redactions=summary_redacted.count,
        command_sha256=command_hash(command_text),
        policy_mode=decision.mode,
        policy_decision=decision.decision,
        policy_reason=decision.reason,
        retention_expires_at=retention_expiry(),
        raw_retained=1,
        command_kind=kind_override or command_class.kind,
        command_family=command_class.family,
        caller=caller,
        workspace_hash=workspace_hash(str(Path.cwd())),
        session_id=session_id,
        is_ai_session=is_ai_session,
    )

    try:
        artifact_path, artifact_sha = store_raw_output(run_id, stdout_redacted.text, stderr_redacted.text)
        if artifact_path:
            from .store import connect as _connect

            with _connect() as conn:
                conn.execute(
                    "UPDATE runs SET artifact_path = ?, artifact_sha256 = ? WHERE id = ?",
                    (artifact_path, artifact_sha, run_id),
                )
                conn.commit()
    except Exception as e:
        print(f"[sage] warning: failed to store raw artifact: {e}")

    # Process output through context manager
    context_mgr = ContextManager()
    result = context_mgr.process_command_output(
        stdout=stdout_redacted.text,
        stderr=stderr_redacted.text,
        exit_code=returncode,
        run_id=run_id,
    )

    agent_results = []
    if os.environ.get("SAGE_DISABLE_AGENTS") != "1":
        try:
            from .agents import execute_agents_for_run

            def _run_agents_background():
                try:
                    execute_agents_for_run(
                        run_id=run_id,
                        command=command_text,
                        stdout=stdout_redacted.text,
                        stderr=stderr_redacted.text,
                        exit_code=returncode,
                        summary=summary_redacted.text,
                    )
                except Exception:
                    pass

            agent_thread = threading.Thread(
                target=_run_agents_background, daemon=True, name="sage-agents-bg"
            )
            agent_thread.start()
        except Exception as e:
            print(f"[sage] warning: failed to start agents: {e}")

    suppress_footer = os.environ.get("SAGE_SUPPRESS_FOOTER") == "1"
    suppress_summary = os.environ.get("SAGE_SUPPRESS_SUMMARY") == "1"
    clean_mode = os.environ.get("SAGE_CLEAN_MODE") == "1"

    # Save compression stats regardless of display mode. Agent wrappers often
    # suppress the footer, but the public dashboard still needs current counters.
    from .store import connect
    from datetime import datetime
    try:
        saved_tokens = int(result.get("token_savings", 0))
        original_tokens = int(result.get("original_tokens", saved_tokens))
        compressed_tokens = int(result.get("compressed_tokens", max(0, original_tokens - saved_tokens)))
        strategy = str(result.get("strategy", "auto"))
        tokenizer = "tiktoken" if is_real_tokenizer() else "fallback"

        with connect() as conn:
            conn.execute(
                """
                INSERT INTO context_compression
                (run_id, created_at, original_tokens, compressed_tokens, saved_tokens, strategy, verified_tokenizer)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    datetime.now().isoformat(),
                    original_tokens,
                    compressed_tokens,
                    saved_tokens,
                    strategy,
                    tokenizer,
                ),
            )
            conn.execute(
                """
                INSERT INTO context_compression_strategies
                (run_id, created_at, strategy, original_tokens, compressed_tokens, saved_tokens, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    datetime.now().isoformat(),
                    strategy,
                    original_tokens,
                    compressed_tokens,
                    saved_tokens,
                    f"verified_tokenizer={tokenizer}",
                ),
            )
            conn.commit()
    except Exception as e:
        if not suppress_footer:
            print(f"[sage] warning: failed to save compression stats: {e}")

    try:
        from . import telemetry
        telemetry.queue_event(run_id)

        if os.environ.get("SAGE_AUTO_SEND_TELEMETRY", "1") == "1":
            from .telemetry_sender import spawn_background_sender
            spawn_background_sender()
            if run_id % 10 == 0:
                try:
                    telemetry.send_proof_snapshot()
                except Exception:
                    pass
    except Exception:
        pass

    if suppress_footer:
        return returncode

    # Clean mode: minimal output
    if clean_mode:
        if result['token_savings'] > 0:
            print(f"\n[sage] Run #{run_id} | Saved {result['token_savings']} tokens ({result['compression_ratio']})")
        else:
            print(f"\n[sage] Run #{run_id}")
    else:
        print()
        print(f"[sage] saved run #{run_id} exit={returncode} time={duration_ms}ms")

        # Show token savings
        if result['token_savings'] > 0:
            print(f"[sage] context: saved {result['token_savings']} tokens ({result['compression_ratio']} compression)")

        if os.environ.get("SAGE_DISABLE_AGENTS") != "1":
            from .agents.registry import select_agents_for_command
            specs = select_agents_for_command(command_text)
            if specs:
                agent_names = ", ".join(s.name for s in specs)
                print(f"[sage] agents: {len(specs)} completed ({agent_names})")

    if not suppress_summary:
        print("[sage] summary:")
        print(summary)

    return returncode


def _run_interactive_passthrough(
    command_parts: list[str],
    *,
    command_text: str,
    started: float,
    env: dict[str, str],
    decision,
    caller: str,
    kind_override: str,
    session_id: str,
    is_ai_session: int,
) -> int:
    """Run an interactive command without pipes so the child owns the TTY.

    This is for terminal agents such as Claude/Codex. Capturing stdout/stderr
    breaks their interactive mode, so SAGE records the launch and exit metadata
    but intentionally does not compress the live terminal stream.
    """
    if not session_id:
        session_id = os.environ.get("SAGE_SESSION_ID", "")

    if not is_ai_session:
        ai_commands = {
            "claude",
            "claude.exe",
            "claude.cmd",
            "codex",
            "codex.exe",
            "codex.cmd",
            "opencode",
            "opencode.exe",
            "opencode.cmd",
            "cursor",
            "cursor.exe",
            "cursor.cmd",
            "windsurf",
            "windsurf.exe",
            "windsurf.cmd",
            "aider",
            "aider.exe",
            "aider.cmd",
            "ollama",
            "ollama.exe",
            "ollama.cmd",
        }
        first_command = Path(command_parts[0]).name.lower() if command_parts else ""
        is_ai_session = 1 if first_command in ai_commands or caller in ["mcp", "agent"] else 0
        if is_ai_session and not session_id:
            session_id = str(uuid.uuid4())
            os.environ["SAGE_SESSION_ID"] = session_id

    command_class = classify_command(command_text)
    popen_args, use_shell = _build_popen_cmd(command_text, command_parts)
    try:
        returncode = subprocess.call(
            popen_args,
            shell=use_shell,
            env=env,
        )
    except KeyboardInterrupt:
        returncode = 130

    duration_ms = int((time.perf_counter() - started) * 1000)
    summary = "Interactive PTY command; live output was not captured."
    run_id = save_run(
        project=str(Path.cwd()),
        command=command_text,
        exit_code=returncode,
        duration_ms=duration_ms,
        stdout="",
        stderr="",
        summary=summary,
        stdout_redactions=0,
        stderr_redactions=0,
        summary_redactions=0,
        command_sha256=command_hash(command_text),
        policy_mode=decision.mode,
        policy_decision=decision.decision,
        policy_reason=decision.reason,
        retention_expires_at=retention_expiry(),
        raw_retained=0,
        command_kind=kind_override or command_class.kind,
        command_family=command_class.family,
        caller=caller,
        workspace_hash=workspace_hash(str(Path.cwd())),
        session_id=session_id,
        is_ai_session=is_ai_session,
    )

    try:
        from .store import connect
        from datetime import datetime

        with connect() as conn:
            conn.execute(
                """
                INSERT INTO context_compression
                (run_id, created_at, original_tokens, compressed_tokens, saved_tokens, strategy, verified_tokenizer)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (run_id, datetime.now().isoformat(), 0, 0, 0, "pty-passthrough", "n/a"),
            )
            conn.commit()
    except Exception:
        pass

    try:
        from . import telemetry
        telemetry.queue_event(run_id)
        if os.environ.get("SAGE_AUTO_SEND_TELEMETRY", "1") == "1":
            from .telemetry_sender import spawn_background_sender
            spawn_background_sender()
            if run_id % 10 == 0:
                try:
                    telemetry.send_proof_snapshot()
                except Exception:
                    pass
    except Exception:
        pass

    if os.environ.get("SAGE_SUPPRESS_FOOTER") != "1":
        print(f"\n[sage] saved interactive run #{run_id} exit={returncode} time={duration_ms}ms")
        print("[sage] pty: live output was passed through, not compressed")

    return int(returncode or 0)
