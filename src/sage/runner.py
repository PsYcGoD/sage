from __future__ import annotations

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


def _configure_stdio() -> None:
    """Keep Windows terminals from crashing or corrupting UTF-8 AI output."""
    for stream in (sys.stdout, sys.stderr):
        try:
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

    if predict:
        from .ml import FailurePredictor

        will_fail, confidence, reason = FailurePredictor().predict(command_text)
        outcome = "likely to fail" if will_fail else "likely to succeed"
        print(f"[sage] prediction: {outcome} ({confidence:.0%}) - {reason}")

    started = time.perf_counter()
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    use_shell = sys.platform.startswith("win")
    process = subprocess.Popen(
        command_text if use_shell else command_parts,
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
            _print_stream(line)
        else:
            stderr_parts.append(line)
            _print_stream(line, stderr=True)

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
        # Check if this is an AI-related command
        is_ai_related = any(marker in command_text for marker in ["--claude", "--codex"]) or caller in ["mcp", "agent"]
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

            agent_results = execute_agents_for_run(
                run_id=run_id,
                command=command_text,
                stdout=stdout_redacted.text,
                stderr=stderr_redacted.text,
                exit_code=returncode,
                summary=summary_redacted.text,
            )
        except Exception as e:
            agent_results = []
            print(f"[sage] warning: failed to execute agents: {e}")

    suppress_footer = os.environ.get("SAGE_SUPPRESS_FOOTER") == "1"
    suppress_summary = os.environ.get("SAGE_SUPPRESS_SUMMARY") == "1"
    clean_mode = os.environ.get("SAGE_CLEAN_MODE") == "1"

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

        if agent_results:
            agent_names = ", ".join(str(item.get("agent", "agent")) for item in agent_results)
            print(f"[sage] agents: {len(agent_results)} completed ({agent_names})")

        # Save compression stats to database
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
            # Don't crash if DB write fails
            print(f"[sage] warning: failed to save compression stats: {e}")

        # Auto-queue telemetry event (respects level 0 local-only policy).
        # Only spawn the sender from an interactive terminal. When stdout/stderr
        # are captured by tests, GUIs, or agent wrappers on Windows, detached
        # helper processes can keep the capture pipe alive past process exit.
        try:
            from . import telemetry
            telemetry.queue_event(run_id)

            if (
                os.environ.get("SAGE_AUTO_SEND_TELEMETRY", "1") == "1"
                and sys.stdout.isatty()
                and sys.stderr.isatty()
            ):
                # Spawn background sender immediately when cloud sync is connected.
                from .telemetry_sender import spawn_background_sender
                spawn_background_sender()
        except Exception:
            # Telemetry failures are silent
            pass

    if not suppress_summary:
        print("[sage] summary:")
        print(summary)

    return returncode
