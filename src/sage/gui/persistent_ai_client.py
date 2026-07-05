"""
Persistent AI Client - REAL conversation sessions that maintain context.

This replaces one-shot subprocess calls with persistent SDK-backed sessions.
that keep conversation history and don't burn credits on repeated context.
"""

import json
import logging
import os
import queue
import re
import shutil
import subprocess
import threading
import tempfile
from pathlib import Path
from typing import Optional, Generator, Tuple
from datetime import datetime

from sage.gui.model_defaults import bedrock_claude_model, claude_model, ollama_model


LOG = logging.getLogger(__name__)


class PersistentAIClient:
    """Maintains a persistent conversation session with an AI provider."""

    def __init__(
        self,
        ai_name: str,
        system_prompts: list[str] | None = None,
        permission_mode: str = "ask",
        project_cwd: str | None = None,
    ):
        self.ai_name = ai_name.lower()
        self.system_prompts = system_prompts or []
        self.permission_mode = permission_mode
        self.project_cwd = str(project_cwd or os.getcwd())
        self.conversation_history = []
        self.session_active = False
        self.codex_has_session = False
        self.codex_command = ""
        self.last_error = ""
        self._lock = threading.Lock()

    def _record_error(self, message: str, exc: Exception | None = None) -> None:
        self.last_error = message
        if exc:
            LOG.warning("%s: %s", message, exc, exc_info=LOG.isEnabledFor(logging.DEBUG))
        else:
            LOG.warning("%s", message)

    def _compact_text(self, text: str, max_chars: int = 4000) -> str:
        text = str(text or "")
        if len(text) <= max_chars:
            return text
        half = max_chars // 2
        return text[:half] + "\n[Middle trimmed for persistent session speed]\n" + text[-half:]

    def _add_history(self, role: str, content: str) -> None:
        self.conversation_history.append({
            "role": role,
            "content": self._compact_text(content),
        })
        self.conversation_history = self.conversation_history[-8:]

    def load_history(self, messages: list[dict]) -> None:
        """Hydrate provider history from saved GUI session messages."""
        with self._lock:
            self.conversation_history = []
            for message in messages[-8:]:
                role = str(message.get("role", "user")).lower()
                content = str(message.get("text") or message.get("content") or "").strip()
                if not content:
                    continue
                provider_role = "user" if role == "user" else "assistant"
                self._add_history(provider_role, content)

    def start_session(self) -> bool:
        """Initialize persistent session with the AI."""
        if self.session_active:
            return True

        try:
            if self.ai_name == "claude":
                return self._start_claude_session()
            elif self.ai_name == "codex":
                return self._start_codex_session()
            elif self.ai_name == "ollama":
                return self._start_ollama_session()
            else:
                return self._start_generic_session()
        except Exception as e:
            self._record_error(f"Failed to start {self.ai_name} session", e)
            return False

    def _start_claude_session(self) -> bool:
        """Start persistent Claude session using AWS Bedrock or Anthropic API."""
        try:
            import anthropic

            # AUTO-DETECT: Bedrock if AWS creds exist, else direct API
            aws_region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
            has_aws_creds = bool(os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("AWS_PROFILE"))

            # Check AWS credentials location
            aws_creds_file = Path.home() / ".aws" / "credentials"
            if not has_aws_creds and aws_creds_file.exists():
                has_aws_creds = True

            # Default to Bedrock if AWS is configured
            use_bedrock = has_aws_creds or os.getenv("USE_BEDROCK", "").lower() in ("true", "1", "yes")

            LOG.info("Claude session region=%s bedrock=%s", aws_region, use_bedrock)

            # Create client - match Claude Code's exact setup
            try:
                api_key = os.getenv("ANTHROPIC_API_KEY")
                base_url = os.getenv("ANTHROPIC_BASE_URL")

                if use_bedrock or os.getenv("CLAUDE_CODE_USE_BEDROCK") == "1":
                    # AWS Bedrock client - uses boto3 credentials
                    self.client = anthropic.AnthropicBedrock(aws_region=aws_region)
                    LOG.info("AWS Bedrock client created for region %s", aws_region)
                    self.is_bedrock = True
                elif base_url:
                    # Custom base URL (like cc.freemodel.dev proxy)
                    self.client = anthropic.Anthropic(api_key=api_key, base_url=base_url)
                    LOG.info("Anthropic API client created with custom base URL")
                    self.is_bedrock = False
                else:
                    # Direct Anthropic API
                    if not api_key:
                        # Try Claude CLI auth
                        try:
                            result = subprocess.run(
                                [shutil.which("claude") or "claude", "auth", "status"],
                                capture_output=True,
                                text=True,
                                encoding="utf-8",
                                errors="replace",
                                timeout=5,
                                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
                            )
                            if '"loggedin": true' not in result.stdout.lower():
                                self._record_error("No Anthropic API key and Claude CLI is not logged in")
                                return False
                        except Exception as exc:
                            self._record_error("Could not verify Claude CLI auth", exc)
                            return False

                    self.client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
                    LOG.info("Anthropic API client created")
                    self.is_bedrock = False

            except Exception as e:
                self._record_error("Failed to create Claude client", e)
                return False

            # Verify client
            if not self.client:
                self._record_error("Claude client is None after creation")
                return False

            self.conversation_history = []

            # Build system prompt from files
            system_content = []
            for prompt_file in self.system_prompts:
                p = Path(prompt_file)
                if p.exists():
                    try:
                        content = p.read_text(encoding="utf-8")
                        system_content.append(content)
                        LOG.info("Loaded system prompt %s (%s chars)", p.name, len(content))
                    except Exception as e:
                        LOG.warning("Could not read system prompt %s: %s", prompt_file, e)

            self.system_message = "\n\n".join(system_content) if system_content else None
            self.session_active = True

            LOG.info("Claude session started with %s system prompts", len(system_content))
            return True

        except ImportError as e:
            self._record_error(f"Missing Claude package: {e}. Install with: pip install sage[ai]")
            return False
        except Exception as e:
            self._record_error("Claude session failed", e)
            return False

    def _start_codex_session(self) -> bool:
        """Start a CLI-backed Codex session using the user's `codex login` auth."""
        try:
            codex_command = self._resolve_codex_command()
            if not codex_command:
                self.last_error = "Codex CLI was not found in PATH or known Windows install locations."
                LOG.warning("%s", self.last_error)
                return False

            env = self._codex_cli_env()
            result = subprocess.run(
                [codex_command, "login", "status"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
            combined_output = f"{result.stdout}\n{result.stderr}"
            if result.returncode != 0 or "Logged in" not in combined_output:
                self.last_error = (
                    "Codex CLI login check failed.\n"
                    f"Command: {codex_command} login status\n"
                    f"Exit code: {result.returncode}\n"
                    f"Output:\n{combined_output.strip() or '(no output)'}"
                )
                LOG.warning("%s", self.last_error)
                return False

            self.codex_command = codex_command
            self.conversation_history = []
            self.codex_has_session = False
            self.session_active = True
            return True

        except Exception as e:
            self.last_error = f"Codex session failed: {e}"
            LOG.warning("%s", self.last_error)
            return False

    def _resolve_codex_command(self) -> str:
        """Resolve Codex CLI robustly for GUI processes with incomplete PATH."""
        names = ["codex.cmd", "codex.exe", "codex"] if os.name == "nt" else ["codex"]
        for name in names:
            found = shutil.which(name)
            if found:
                return found

        if os.name == "nt":
            candidates: list[Path] = []
            appdata = os.environ.get("APPDATA")
            if appdata:
                candidates.append(Path(appdata) / "npm" / "codex.cmd")
            localappdata = os.environ.get("LOCALAPPDATA")
            if localappdata:
                candidates.extend(Path(localappdata).glob("Microsoft/WindowsApps/codex*.exe"))
            program_files = os.environ.get("ProgramFiles")
            if program_files:
                candidates.extend(Path(program_files).glob("WindowsApps/OpenAI.Codex_*/*/resources/codex.exe"))
                candidates.extend(Path(program_files).glob("WindowsApps/OpenAI.Codex_*/app/resources/codex.exe"))
            for candidate in candidates:
                if candidate.exists():
                    return str(candidate)
        return ""

    def _codex_cli_env(self) -> dict:
        """Return an environment that forces Codex CLI auth instead of env API keys."""
        env = os.environ.copy()
        env.pop("OPENAI_API_KEY", None)
        return env

    def _start_ollama_session(self) -> bool:
        """Start persistent Ollama session."""
        try:
            # Ollama runs locally via HTTP API
            import requests

            # Test Ollama connection
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code != 200:
                return False

            self.conversation_history = []
            self.session_active = True
            self.ollama_model = ollama_model()
            return True

        except Exception as e:
            self._record_error("Ollama session failed", e)
            return False

    def _start_generic_session(self) -> bool:
        """Fallback for other AIs."""
        self.conversation_history = []
        self.session_active = True
        return True

    def send_message(self, prompt: str) -> Generator[Tuple[str, str], None, None]:
        """
        Send message and stream response while maintaining conversation history.

        Yields: (event_type, content) tuples
        - ("thinking", text) - reasoning/thinking content
        - ("text", text) - actual response text
        - ("error", text) - error messages
        - ("complete", "") - response finished
        """
        if not self.session_active:
            yield ("error", "Session not active. Call start_session() first.")
            return

        with self._lock:
            try:
                if self.ai_name == "claude":
                    yield from self._stream_claude(prompt)
                elif self.ai_name == "codex":
                    yield from self._stream_codex(prompt)
                elif self.ai_name == "ollama":
                    yield from self._stream_ollama(prompt)
                else:
                    yield from self._stream_generic(prompt)
            except Exception as e:
                yield ("error", f"Error: {str(e)}")

    def _stream_claude(self, prompt: str) -> Generator[Tuple[str, str], None, None]:
        """Stream Claude response with conversation history."""
        try:
            # Add user message to history
            self._add_history("user", prompt)

            # Use env-specified model IDs if available (Claude Code style)
            if hasattr(self, 'is_bedrock') and self.is_bedrock:
                model = bedrock_claude_model()
            else:
                model = claude_model()

            LOG.debug("Using Claude model: %s", model)

            # Prepare system message (Bedrock requires list format)
            system_param = None
            if self.system_message:
                if hasattr(self, 'is_bedrock') and self.is_bedrock:
                    # Bedrock requires list format
                    system_param = [{"type": "text", "text": self.system_message}]
                else:
                    # Direct API accepts string
                    system_param = self.system_message

            # Call Claude API with full conversation history
            kwargs = {
                "model": model,
                "max_tokens": 8192,
                "messages": self.conversation_history[-8:]
            }
            if system_param:
                kwargs["system"] = system_param

            with self.client.messages.stream(**kwargs) as stream:
                assistant_text = []
                current_tool = {}  # Track current tool_use block

                for event in stream:
                    if hasattr(event, 'type'):
                        if event.type == 'content_block_start':
                            block = getattr(event, 'content_block', None)
                            if block and hasattr(block, 'type'):
                                if block.type == 'thinking':
                                    yield ("thinking", "[Thinking...]\n")
                                elif block.type == 'tool_use':
                                    # Start tracking a new tool call
                                    current_tool = {
                                        'id': getattr(block, 'id', ''),
                                        'name': getattr(block, 'name', ''),
                                        'input': {}
                                    }

                        elif event.type == 'content_block_delta':
                            delta = getattr(event, 'delta', None)
                            if delta:
                                if hasattr(delta, 'type'):
                                    if delta.type == 'thinking_delta':
                                        text = getattr(delta, 'thinking', '')
                                        if text:
                                            yield ("thinking", text)
                                    elif delta.type == 'text_delta':
                                        text = getattr(delta, 'text', '')
                                        if text:
                                            assistant_text.append(text)
                                            yield ("text", text)
                                    elif delta.type == 'input_json_delta':
                                        # Accumulate tool input JSON
                                        json_chunk = getattr(delta, 'partial_json', '')
                                        if json_chunk and current_tool:
                                            current_tool.setdefault('input_json', '')
                                            current_tool['input_json'] += json_chunk

                        elif event.type == 'content_block_stop':
                            # Tool call complete - parse and format it
                            if current_tool and current_tool.get('name'):
                                tool_name = current_tool['name']

                                # Parse accumulated JSON input
                                try:
                                    import json
                                    tool_input = json.loads(current_tool.get('input_json', '{}'))

                                    # Format Edit() calls as visual diffs
                                    if tool_name == 'Edit':
                                        from sage.gui.diff_formatter import format_edit_diff
                                        file_path = tool_input.get('file_path', 'unknown')
                                        old_string = tool_input.get('old_string', '')
                                        new_string = tool_input.get('new_string', '')
                                        diff_output = format_edit_diff(file_path, old_string, new_string)
                                        yield ("tool", diff_output)

                                    # Format Write() calls showing preview
                                    elif tool_name == 'Write':
                                        from sage.gui.diff_formatter import format_write_diff
                                        file_path = tool_input.get('file_path', 'unknown')
                                        content = tool_input.get('content', '')
                                        write_output = format_write_diff(file_path, content)
                                        yield ("tool", write_output)

                                    # Other tools - show compact summary
                                    else:
                                        summary = f"\n🔧 {tool_name}({', '.join(f'{k}={repr(v)[:50]}' for k, v in tool_input.items())})\n"
                                        yield ("tool", summary)

                                except Exception as e:
                                    # Fallback to raw tool info on parse error
                                    yield ("tool", f"\n🔧 {tool_name}(...)\n")

                                # Reset for next tool
                                current_tool = {}

                # Save assistant response to history
                full_response = "".join(assistant_text)
                self._add_history("assistant", full_response)

                yield ("complete", "")

        except Exception as e:
            yield ("error", f"Claude API error: {str(e)}")

    def _stream_codex(self, prompt: str) -> Generator[Tuple[str, str], None, None]:
        """Stream Codex through its CLI so it uses `codex login` credentials."""
        try:
            output_path = Path(tempfile.gettempdir()) / f"sage-codex-last-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.txt"
            if self.codex_has_session:
                cmd = self._codex_command(resume=True, output_path=output_path)
                cli_prompt = prompt
            else:
                cmd = self._codex_command(resume=False, output_path=output_path)
                cli_prompt = self._build_initial_codex_prompt(prompt)

            self._add_history("user", prompt)
            assistant_text = []
            visible_started = False
            suppress_rest = False
            saw_error = False

            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=self._codex_cli_env(),
                cwd=self.project_cwd if os.path.isdir(self.project_cwd) else None,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )

            if process.stdin:
                process.stdin.write(cli_prompt)
                process.stdin.close()

            output_queue: queue.Queue[tuple[str, str | None]] = queue.Queue()

            def read_stream(stream, stream_name: str):
                try:
                    for line in iter(stream.readline, ""):
                        output_queue.put((stream_name, line))
                finally:
                    output_queue.put((stream_name, None))

            stdout_thread = threading.Thread(target=read_stream, args=(process.stdout, "stdout"), daemon=True)
            stderr_thread = threading.Thread(target=read_stream, args=(process.stderr, "stderr"), daemon=True)
            stdout_thread.start()
            stderr_thread.start()

            streams_done = {"stdout": False, "stderr": False}
            while not all(streams_done.values()):
                stream_name, line = output_queue.get()
                if line is None:
                    streams_done[stream_name] = True
                    continue

                event_type, visible = self._classify_codex_stream_item(
                    line,
                    stream_name,
                    visible_started,
                    suppress_rest,
                )
                visible_started = visible_started or visible == "__START__"
                suppress_rest = suppress_rest or visible == "__STOP__"

                if visible and visible not in {"__START__", "__STOP__"}:
                    if event_type in {None, "text"}:
                        assistant_text.append(visible)
                    elif event_type == "error":
                        saw_error = True
                    yield (event_type or "text", visible)

            exit_code = process.wait()
            if exit_code != 0:
                if not saw_error:
                    yield ("error", f"Codex CLI exited with code {exit_code}")
                return

            self.codex_has_session = True
            if not assistant_text and output_path.exists():
                final_text = output_path.read_text(encoding="utf-8", errors="replace").strip()
                if final_text:
                    assistant_text.append(final_text + "\n")
                    yield ("text", final_text + "\n")

            full_response = "".join(assistant_text)
            self._add_history("assistant", full_response)

            yield ("complete", "")

        except Exception as e:
            yield ("error", f"Codex CLI error: {str(e)}")

    def _build_initial_codex_prompt(self, prompt: str) -> str:
        """Return the user's prompt without injecting large system files."""
        return prompt

    def _codex_command(self, *, resume: bool, output_path: Path) -> list[str]:
        # CRITICAL FIX: Run codex directly to prevent cmd.exe spawn
        cmd = [
            self.codex_command or self._resolve_codex_command() or "codex",
            "exec",
            "--json",
            "--color",
            "never",
        ]
        if resume:
            cmd.extend(["resume", "--last"])

        cmd.extend(["--skip-git-repo-check", "-o", str(output_path)])

        mode = self.permission_mode if self.permission_mode in {"ask", "approve", "full"} else "ask"
        if mode == "full":
            cmd.append("--dangerously-bypass-approvals-and-sandbox")
        elif mode == "approve":
            cmd.extend(["-c", 'approval_policy="never"', "-c", 'sandbox_mode="workspace-write"'])
        else:
            cmd.extend(["-c", 'approval_policy="on-request"', "-c", 'sandbox_mode="workspace-write"'])

        cmd.append("-")
        return cmd

    def _filter_codex_line(
        self,
        line: str,
        stream_name: str,
        visible_started: bool,
        suppress_rest: bool,
    ) -> str | None:
        """Hide Codex transcript/header noise without suppressing useful output."""
        if stream_name != "stdout":
            stripped_err = line.strip()
            if stripped_err.lower().startswith(("error", "[error]", "codex api error")):
                return line
            if not stripped_err or suppress_rest:
                return None
            return line

        stripped = line.strip()
        if not stripped:
            return "\n" if visible_started and not suppress_rest else None

        lowered = stripped.lower()
        if lowered == "codex":
            return "__START__"
        if lowered.startswith("tokens used"):
            return "__STOP__"
        if suppress_rest:
            return None

        # KEEP reasoning/thinking output visible - only hide connection metadata
        header_prefixes = (
            "openaI codex",
            "openai codex",
            "workdir:",
            "model:",
            "provider:",
            "approval:",
            "sandbox:",
            "session id:",
        )
        if lowered == "--------" or any(lowered.startswith(prefix.lower()) for prefix in header_prefixes):
            return None
        if lowered in {"user", "assistant"}:
            return "__START__" if lowered == "assistant" else None

        # Older Codex CLI builds printed a literal "codex" marker before the
        # assistant text. Newer builds may not, so show non-header lines rather
        # than leaving the GUI blank until the final output file is written.
        if not visible_started:
            return line
        return line

    def _classify_codex_stream_item(
        self,
        line: str,
        stream_name: str,
        visible_started: bool,
        suppress_rest: bool,
    ) -> tuple[str | None, str | None]:
        """Classify Codex JSONL when available, falling back to text output."""
        normalized_error = self._normalize_provider_error(line)
        if stream_name != "stdout" and normalized_error:
            return "error", normalized_error + "\n"

        if stream_name == "stdout":
            stripped = line.strip()
            if stripped.startswith("{") and stripped.endswith("}"):
                try:
                    payload = json.loads(stripped)
                except json.JSONDecodeError:
                    pass
                else:
                    return self._classify_codex_json_event(payload)

        return self._classify_codex_line(line, stream_name, visible_started, suppress_rest)

    def _classify_codex_json_event(self, payload: dict) -> tuple[str | None, str | None]:
        """Convert `codex exec --json` events into GUI event types."""
        raw_type = str(payload.get("type") or payload.get("event") or "").lower()
        item = payload.get("item") if isinstance(payload.get("item"), dict) else {}
        item_type = str(item.get("type") or payload.get("item_type") or "").lower()
        combined_type = f"{raw_type} {item_type}"
        status = str(item.get("status") or payload.get("status") or "").lower()

        if "token" in combined_type or raw_type in {"turn.completed", "thread.completed"}:
            return None, None

        if "error" in combined_type:
            text = self._extract_codex_text(payload)
            text = self._normalize_provider_error(text) or text
            return ("error", text + "\n") if text else (None, None)

        if "reason" in combined_type or "thinking" in combined_type:
            text = self._extract_codex_text(payload)
            return ("thinking", self._ensure_trailing_newline(text)) if text else (None, None)

        if any(marker in combined_type for marker in ("exec", "command", "tool", "function_call", "local_shell")):
            text = self._format_codex_tool_event(payload)
            return ("tool", self._ensure_trailing_newline(text)) if text else (None, None)

        if status in {"in_progress", "running", "pending"}:
            text = self._extract_codex_text(payload, status_only=True) or status
            return "thinking", self._ensure_trailing_newline(text)

        if any(marker in combined_type for marker in ("patch", "edit", "file_change", "diff")):
            text = self._extract_codex_text(payload)
            return ("coding", self._ensure_trailing_newline(text)) if text else (None, None)

        if any(marker in combined_type for marker in ("message", "output_text", "answer")):
            text = self._extract_codex_text(payload)
            return ("text", text) if text else (None, None)

        if raw_type.endswith(".started"):
            label = raw_type.removesuffix(".started").replace("_", " ").replace(".", " ")
            if label and label not in {"thread", "turn"}:
                return "thinking", f"{label}...\n"

        text = self._extract_codex_text(payload, status_only=True)
        return ("thinking", self._ensure_trailing_newline(text)) if text else (None, None)

    def _format_codex_tool_event(self, payload: dict) -> str:
        item = payload.get("item") if isinstance(payload.get("item"), dict) else {}
        source = item or payload
        status = str(source.get("status") or payload.get("status") or "").lower()
        item_type = str(source.get("type") or payload.get("type") or "").lower()
        name = (
            source.get("name")
            or source.get("tool_name")
            or source.get("command")
            or source.get("cmd")
            or source.get("type")
            or payload.get("type")
        )

        command_text = self._clean_codex_tool_text(self._codex_tool_command_text(source))
        result_text = self._codex_tool_result_text(source) or self._codex_tool_result_text(payload)

        # Codex emits tool output as a separate event. Show that output as output,
        # not as "Ran <the output>".
        if "output" in item_type and not command_text:
            return result_text or str(name or "")

        if not command_text and result_text:
            return result_text
        if not command_text:
            return str(name or "")

        exit_code = self._codex_tool_exit_code(source)
        if exit_code not in (None, 0):
            prefix = f"Failed ({exit_code})"
        elif status in {"in_progress", "running", "pending"}:
            prefix = "Running"
        elif status in {"completed", "success", "succeeded"}:
            prefix = "Ran"
        else:
            prefix = ""

        text = f"{prefix} {command_text}".strip()
        if result_text:
            text = f"{text}\n\n{result_text}" if text else result_text
        return text

    def _codex_tool_exit_code(self, source: dict) -> int | None:
        for key in ("exit_code", "exitCode", "returncode", "return_code"):
            value = source.get(key)
            if value is None:
                continue
            try:
                return int(value)
            except (TypeError, ValueError):
                return None
        return None

    def _codex_tool_result_text(self, source: dict) -> str:
        """Extract tool output/result text without repeating command arguments."""
        parts: list[str] = []
        for key in ("stdout", "stderr", "output", "result", "content", "message", "summary", "error"):
            if key not in source:
                continue
            text = self._extract_codex_text(source.get(key))
            if text:
                parts.append(text)
        return "\n".join(dict.fromkeys(parts)).strip()

    def _codex_tool_command_text(self, source: dict) -> str:
        """Extract the command-like part of Codex tool JSON without status noise."""
        for key in ("arguments", "command", "cmd"):
            value = source.get(key)
            if not value:
                continue
            if isinstance(value, str):
                stripped = value.strip()
                if stripped.startswith("{") and stripped.endswith("}"):
                    try:
                        decoded = json.loads(stripped)
                    except json.JSONDecodeError:
                        return stripped
                    nested = self._codex_tool_command_text(decoded)
                    return nested or stripped
                return stripped
            if isinstance(value, dict):
                nested = self._codex_tool_command_text(value)
                if nested:
                    return nested
        return ""

    def _clean_codex_tool_text(self, text: str) -> str:
        text = str(text or "").strip()
        if not text:
            return ""
        match = re.search(r"(sage\s+run\s+--\s+.+?)(?:['\"]\s*$|$)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return text

    def _extract_codex_text(self, payload, *, status_only: bool = False) -> str:
        """Pull human-readable text out of common Codex JSON event shapes."""
        if isinstance(payload, str):
            return payload.strip()
        if isinstance(payload, list):
            parts = [self._extract_codex_text(item, status_only=status_only) for item in payload]
            return "\n".join(part for part in parts if part).strip()
        if not isinstance(payload, dict):
            return ""

        if status_only:
            keys = ("status", "message", "summary")
        else:
            keys = (
                "text",
                "delta",
                "message",
                "summary",
                "reasoning",
                "thinking",
                "content",
                "error",
                "output",
                "result",
                "command",
                "cmd",
                "arguments",
                "status",
            )

        parts: list[str] = []
        for key in keys:
            value = payload.get(key)
            text = self._extract_codex_text(value, status_only=status_only)
            if text:
                parts.append(text)

        item = payload.get("item")
        if isinstance(item, dict):
            text = self._extract_codex_text(item, status_only=status_only)
            if text:
                parts.append(text)

        return "\n".join(dict.fromkeys(parts)).strip()

    def _ensure_trailing_newline(self, text: str) -> str:
        if not text:
            return ""
        return text if text.endswith("\n") else text + "\n"

    def _classify_codex_line(
        self,
        line: str,
        stream_name: str,
        visible_started: bool,
        suppress_rest: bool,
    ) -> tuple[str | None, str | None]:
        """Return a GUI event type plus filtered Codex output."""
        visible = self._filter_codex_line(line, stream_name, visible_started, suppress_rest)
        if not visible or visible in {"__START__", "__STOP__"}:
            return None, visible

        stripped = visible.strip()
        lowered = stripped.lower()
        if not stripped:
            return "text", visible
        normalized_error = self._normalize_provider_error(stripped)
        if normalized_error:
            return "error", normalized_error + "\n"
        if lowered.startswith(("reasoning", "thinking", "analysis")):
            return "thinking", visible
        if lowered.startswith(("tool:", "exec:", "command:", "running:", "apply_patch")):
            return "tool", visible
        if (
            stripped.startswith(("```", "$", "diff --git", "@@", "+++", "---"))
            or lowered.startswith(("coding", "editing", "modified", "created file", "updated file"))
        ):
            return "coding", visible
        return "text", visible

    def _normalize_provider_error(self, text: str) -> str:
        """Return a concise GUI error for common API/provider failures."""
        text = str(text or "").strip()
        if not text:
            return ""
        lowered = text.lower()
        token_limit_markers = (
            "context_length_exceeded",
            "maximum context length",
            "too many tokens",
            "token limit",
            "exceeds the model",
            "exceeded the model",
        )
        if any(marker in lowered for marker in token_limit_markers):
            detail = " ".join(text.split())
            if len(detail) > 500:
                detail = detail[:497] + "..."
            return (
                "API error: prompt is over the model context/token limit. "
                f"{detail}"
            )

        api_error_markers = ("api error", "openai error", "anthropic error", "provider error")
        if any(marker in lowered for marker in api_error_markers):
            detail = " ".join(text.split())
            return detail[:500]

        return ""

    def _stream_ollama(self, prompt: str) -> Generator[Tuple[str, str], None, None]:
        """Stream Ollama response with conversation history."""
        try:
            import requests

            self._add_history("user", prompt)

            # Build context from history
            context_messages = []
            for msg in self.conversation_history[-8:]:
                context_messages.append(f"{msg['role']}: {msg['content']}")

            full_prompt = "\n\n".join(context_messages)

            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": full_prompt,
                    "stream": True
                },
                stream=True,
                timeout=120
            )

            assistant_text = []
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    if "response" in data:
                        text = data["response"]
                        assistant_text.append(text)
                        yield ("text", text)

            full_response = "".join(assistant_text)
            self._add_history("assistant", full_response)

            yield ("complete", "")

        except Exception as e:
            yield ("error", f"Ollama error: {str(e)}")

    def _stream_generic(self, prompt: str) -> Generator[Tuple[str, str], None, None]:
        """Fallback to subprocess for unsupported AIs."""
        yield ("error", f"No persistent streaming backend is configured for {self.ai_name}.")

    def clear_history(self):
        """Clear conversation history and start fresh."""
        with self._lock:
            self.conversation_history = []
            self.codex_has_session = False

    def get_history_summary(self) -> str:
        """Get a summary of conversation history."""
        return f"{len(self.conversation_history)} messages in history"

    def stop_session(self):
        """Clean up session resources."""
        self.session_active = False
        self.conversation_history = []

    def stop(self):
        """Stop the active persistent session from the GUI cancel path."""
        self.stop_session()
