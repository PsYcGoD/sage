from __future__ import annotations
"""CLI client for SAGE Desktop GUI."""

import logging

import os
import json
import queue
import re
import shlex
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Generator, Optional

log = logging.getLogger(__name__)

WINDOWS_SCRIPT_EXTENSIONS = {".bat", ".cmd", ".ps1"}

def _split_command(command: str) -> list[str]:
    """Split a configured command without breaking Windows paths."""
    return shlex.split(command, posix=False)

def resolve_cli_command(command: str) -> Optional[list[str]]:
    """Resolve the executable in a configured CLI command."""
    parts = _split_command(command)
    if not parts:
        return None

    executable = shutil.which(parts[0])
    if not executable:
        return None

    return [executable, *parts[1:]]

def _needs_shell(executable: str) -> bool:
    """Windows needs a shell for npm .cmd shims and batch files."""
    return os.name == "nt" and Path(executable).suffix.lower() in WINDOWS_SCRIPT_EXTENSIONS

def _clean_for_display(text: str) -> str:
    """Normalize common mojibake/error symbols for the GUI output."""
    replacements = {
        "\u2713": "[OK]",
        "\u2705": "[OK]",
        "\u2717": "[X]",
        "\u274c": "[ERROR]",
        "\u26a0\ufe0f": "[WARNING]",
        "\ud83d\udcad": ">>",
        "\u26a1": ">>",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", text)
    text = re.sub(r"\s*\?{3,}\s*", " ", text)
    text = re.sub(r" {2,}", " ", text)
    return text

def _tool_call_summary(name: str, raw_json: str) -> str:
    """Build a `Tool(main argument)` label like the Claude CLI shows."""
    args = {}
    if raw_json:
        try:
            args = json.loads(raw_json)
        except json.JSONDecodeError:
            args = {}
    detail = ""
    if isinstance(args, dict):
        for key in ("command", "file_path", "path", "pattern", "url", "query", "prompt", "description"):
            value = args.get(key)
            if isinstance(value, str) and value.strip():
                detail = " ".join(value.strip().split())
                break
    if len(detail) > 80:
        detail = detail[:77] + "..."
    return f"{name}({detail})"

def _tool_result_summary(content) -> str:
    """Summarize a tool result the way the Claude CLI collapses it."""
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
        text = "\n".join(parts)
    else:
        text = ""

    lines = [part.strip() for part in text.splitlines() if part.strip()]
    if not lines:
        return "(no output)"
    summary = lines[0]
    if len(summary) > 100:
        summary = summary[:97] + "..."
    if len(lines) > 1:
        summary += f" ... +{len(lines) - 1} lines"
    return summary

class CLIClient:
    """Client that streams responses from local CLI commands."""

    DEFAULT_COMMANDS = {
        "claude": "sage run -- claude",
        "codex": "sage run -- codex exec --skip-git-repo-check",
        "ollama": "sage run -- ollama run qwen2.5-coder:7b",
        "gemini": "sage run -- aichat -m gemini",
        "llama": "sage run -- aichat -m llama",
        "mistral": "sage run -- aichat -m mistral",
    }

    def __init__(self, ai_name: str, system_prompts: list | None = None, custom_command: str | None = None):
        self.ai_name = ai_name.lower()
        self.system_prompts = system_prompts or []
        self.process = None
        self.last_run_id = None
        self.command = custom_command or self.DEFAULT_COMMANDS.get(self.ai_name, "sage run -- claude")
        self._seen_thinking = False
        self._seen_answer = False
        self._last_thinking_bucket = 0
        self._current_block: str | None = None
        self._tool_name = ""
        self._tool_json = ""

    def stop(self) -> None:
        """Stop the active CLI process tree for this client only."""
        process = self.process
        if not process or process.poll() is not None:
            return
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(process.pid), "/T"],
                    capture_output=True,
                    timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
                )
            else:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
        except Exception:
            try:
                process.terminate()
            except Exception:
                log.debug("suppressed", exc_info=True)

    def stream_response(self, prompt: str) -> Generator[str, None, None]:
        """Stream CLI response lines for a prompt."""
        self._seen_thinking = False
        self._seen_answer = False
        self._last_thinking_bucket = 0
        self._current_block = None
        self._tool_name = ""
        self._tool_json = ""

        cmd = resolve_cli_command(self.command)
        if cmd is None:
            missing = _split_command(self.command)[0] if self.command else self.ai_name
            yield f"\n[ERROR] Command '{missing}' not found. Make sure it is installed and in PATH.\n"
            return

        full_prompt = prompt
        use_stdin = True

        if self.ai_name == "claude":
            # Claude loads CLAUDE-FABLE-5.md + SAGE-INTEGRATION.md globally via
            # ~/.claude/CLAUDE.md, so no --append-system-prompt-file needed here.
            pass
        elif self.ai_name == "codex" and "exec" in self.command:
            full_prompt = prompt
        else:
            full_prompt = self._prompt_with_system_content(prompt)

        try:
            use_shell = _needs_shell(cmd[0])

            if use_stdin:
                popen_command = subprocess.list2cmdline(cmd) if use_shell else cmd
                self.process = subprocess.Popen(
                    popen_command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    encoding="utf-8",
                    errors="replace",
                    shell=use_shell,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
                )
                if self.process.stdin:
                    self.process.stdin.write(full_prompt + "\n")
                    self.process.stdin.flush()
                    self.process.stdin.close()
            else:
                cmd.append(full_prompt)
                popen_command = subprocess.list2cmdline(cmd) if use_shell else cmd
                self.process = subprocess.Popen(
                    popen_command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    encoding="utf-8",
                    errors="replace",
                    shell=use_shell,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
                )

            output_queue: queue.Queue[tuple[str, str | None]] = queue.Queue()

            def enqueue_stream(stream, stream_name: str):
                try:
                    if stream:
                        while True:
                            chunk = stream.read(1)
                            if chunk == "":
                                break
                            output_queue.put((stream_name, chunk))
                finally:
                    output_queue.put((stream_name, None))

            threading.Thread(
                target=enqueue_stream,
                args=(self.process.stdout, "stdout"),
                daemon=True,
            ).start()
            threading.Thread(
                target=enqueue_stream,
                args=(self.process.stderr, "stderr"),
                daemon=True,
            ).start()

            stdout_done = False
            stderr_done = False
            skip_sage_footer = False
            stdout_line_start = True
            stdout_prefix_buffer = ""
            json_line_buffer = ""
            stream_json = self.ai_name == "claude" and "--output-format stream-json" in self.command

            while not (stdout_done and stderr_done):
                stream_name, chunk = output_queue.get()
                if chunk is None:
                    if stream_name == "stdout":
                        if stdout_prefix_buffer and not skip_sage_footer:
                            if stream_json:
                                for parsed in self._parse_claude_json_chunk(stdout_prefix_buffer, final=True):
                                    yield parsed
                            else:
                                yield _clean_for_display(stdout_prefix_buffer)
                            stdout_prefix_buffer = ""
                        if stream_json and json_line_buffer:
                            for parsed in self._parse_claude_json_chunk(json_line_buffer, final=True):
                                yield parsed
                            json_line_buffer = ""
                        stdout_done = True
                    else:
                        stderr_done = True
                    continue

                # Leave stream-json stdout untouched so JSON parses cleanly;
                # the parser cleans rendered text itself.
                if not (stream_json and stream_name == "stdout"):
                    chunk = _clean_for_display(chunk)
                if stream_name == "stdout":
                    if skip_sage_footer:
                        continue

                    if stdout_line_start or stdout_prefix_buffer:
                        stdout_prefix_buffer += chunk
                        if "[sage]".startswith(stdout_prefix_buffer) and len(stdout_prefix_buffer) < len("[sage]"):
                            continue

                        match = None
                        if stdout_prefix_buffer.startswith("[sage]"):
                            if "\n" not in stdout_prefix_buffer:
                                continue
                            footer_line = stdout_prefix_buffer.split("\n", 1)[0]
                            match = re.search(r"#(\d+)", footer_line)
                        if match:
                            self.last_run_id = int(match.group(1))
                            skip_sage_footer = True
                            stdout_prefix_buffer = ""
                            continue

                        if stream_json:
                            json_line_buffer += stdout_prefix_buffer
                            while "\n" in json_line_buffer:
                                raw_line, json_line_buffer = json_line_buffer.split("\n", 1)
                                for parsed in self._parse_claude_json_line(raw_line):
                                    yield parsed
                        else:
                            yield stdout_prefix_buffer
                        stdout_line_start = stdout_prefix_buffer.endswith("\n")
                        stdout_prefix_buffer = ""
                        continue

                    stdout_line_start = chunk.endswith("\n")
                    if stream_json:
                        json_line_buffer += chunk
                        while "\n" in json_line_buffer:
                            raw_line, json_line_buffer = json_line_buffer.split("\n", 1)
                            for parsed in self._parse_claude_json_line(raw_line):
                                yield parsed
                    else:
                        yield chunk
                elif chunk:
                    yield chunk

            self.process.wait()

            if self.process.returncode != 0:
                yield f"\n[ERROR] Process exited with code {self.process.returncode}\n"

        except FileNotFoundError:
            yield f"\n[ERROR] Command '{cmd[0] if cmd else self.ai_name}' not found. Make sure it is installed and in PATH.\n"
        except Exception as exc:
            yield f"\n[ERROR] Error: {exc}\n"

    def _parse_claude_json_chunk(self, text: str, final: bool = False) -> Generator[str, None, None]:
        """Parse one or more Claude stream-json lines."""
        lines = text.splitlines()
        if final and text and not text.endswith(("\n", "\r")):
            lines = [text]
        for line in lines:
            for parsed in self._parse_claude_json_line(line):
                yield parsed

    def _parse_claude_json_line(self, line: str) -> Generator[str, None, None]:
        """Convert Claude stream-json events into Claude CLI-style text."""
        line = line.strip()
        if not line:
            return

        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            yield _clean_for_display(line + "\n")
            return

        event_type = payload.get("type")

        if event_type == "system":
            subtype = payload.get("subtype")
            if subtype == "init":
                model = payload.get("model") or "Claude"
                yield f"· session started · {model}\n"
            elif subtype == "status":
                status = payload.get("status")
                if status:
                    yield f"· {status}…\n"
            elif subtype == "thinking_tokens":
                tokens = int(payload.get("estimated_tokens") or 0)
                bucket = tokens // 50
                if not self._seen_thinking:
                    self._seen_thinking = True
                    yield "\n* Thinking...\n"
                elif bucket > self._last_thinking_bucket:
                    self._last_thinking_bucket = bucket
            return

        if event_type == "stream_event":
            event = payload.get("event", {})
            event_name = event.get("type")

            if event_name == "content_block_start":
                block = event.get("content_block", {})
                block_type = block.get("type")
                if block_type == "thinking":
                    self._current_block = "thinking"
                    if not self._seen_thinking:
                        self._seen_thinking = True
                    yield "\n* Thinking...\n"
                elif block_type == "text":
                    self._current_block = "text"
                    self._seen_answer = True
                    yield "\n● "
                elif block_type == "tool_use":
                    self._current_block = "tool_use"
                    self._tool_name = block.get("name", "tool")
                    self._tool_json = ""
                return

            if event_name == "content_block_delta":
                delta = event.get("delta", {})
                delta_type = delta.get("type")
                if delta_type == "text_delta":
                    yield _clean_for_display(delta.get("text", ""))
                elif delta_type == "thinking_delta":
                    thinking_text = delta.get("thinking", "")
                    if thinking_text:
                        yield _clean_for_display(thinking_text)
                elif delta_type == "input_json_delta":
                    self._tool_json += delta.get("partial_json", "")
                return

            if event_name == "content_block_stop":
                if self._current_block == "tool_use":
                    summary = _tool_call_summary(self._tool_name, self._tool_json)
                    self._tool_name = ""
                    self._tool_json = ""
                    self._current_block = None
                    yield f"\n● {summary}\n"
                else:
                    self._current_block = None
                return

            if event_name == "message_stop":
                yield "\n"
                return
            return

        if event_type == "user":
            message = payload.get("message", {})
            content = message.get("content", [])
            if isinstance(content, list):
                for item in content:
                    if not isinstance(item, dict) or item.get("type") != "tool_result":
                        continue
                    summary = _tool_result_summary(item.get("content"))
                    if item.get("is_error"):
                        summary = f"[ERROR] {summary}"
                    yield f"  L  {summary}\n"
            return

        if event_type == "result":
            if payload.get("is_error") or payload.get("subtype") not in (None, "success"):
                error_text = payload.get("result") or payload.get("error") or payload.get("subtype")
                if isinstance(error_text, str) and error_text.strip():
                    yield f"\n[ERROR] {error_text.strip()}\n"
            duration_ms = payload.get("duration_ms")
            cost = payload.get("total_cost_usd")
            parts = []
            if duration_ms:
                parts.append(f"{int(duration_ms) / 1000:.1f}s")
            if isinstance(cost, (int, float)) and cost > 0:
                parts.append(f"${cost:.4f}")
            if parts:
                yield f"\n- done · {' · '.join(parts)}\n"
            return

    def _prompt_with_system_content(self, prompt: str) -> str:
        """Prepend prompt file content for CLIs without system-prompt-file support."""
        system_content = []
        for prompt_file in self.system_prompts:
            prompt_path = Path(prompt_file)
            if prompt_path.exists():
                try:
                    system_content.append(prompt_path.read_text(encoding="utf-8"))
                except OSError:
                    pass

        if not system_content:
            return prompt

        return "\n\n".join(system_content) + "\n\n---\n\nUser: " + prompt

def check_cli_available(ai_name: str, custom_command: Optional[str] = None) -> bool:
    """Return true if the configured CLI command can be resolved."""
    command = custom_command or CLIClient.DEFAULT_COMMANDS.get(ai_name.lower(), ai_name)
    try:
        return resolve_cli_command(command) is not None
    except Exception:
        return False
