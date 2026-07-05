from __future__ import annotations
"""Embedded PowerShell terminal widget for the SAGE desktop GUI."""

import logging

import queue
import json
import re
import threading
import tkinter as tk
from pathlib import Path
from typing import Callable, Optional

import customtkinter as ctk
from sage.gui.ascii_art import SAGE_WELCOME

log = logging.getLogger(__name__)

try:
    import winpty
    from winpty import PtyProcess

    HAS_WINPTY = True
except ImportError:
    winpty = None
    PtyProcess = None
    HAS_WINPTY = False

class PowerShellTerminal(ctk.CTkTextbox):
    """A real PowerShell session rendered inside a CustomTkinter textbox."""

    def __init__(
        self,
        parent,
        on_reply_to_selection: Optional[Callable[[str], None]] = None,
        on_ai_response_complete: Optional[Callable[[str], None]] = None,
        on_ai_stream_finished: Optional[Callable[[str | None], None]] = None,
        **kwargs,
    ):
        super().__init__(
            parent,
            wrap="word",
            font=ctk.CTkFont(family="Consolas", size=13),
            undo=False,
            **kwargs,
        )
        try:
            self._textbox.configure(wrap="word")
        except Exception:
            log.debug("suppressed", exc_info=True)
        self.on_reply_to_selection = on_reply_to_selection
        self.on_ai_response_complete = on_ai_response_complete
        self.on_ai_stream_finished = on_ai_stream_finished
        self.pty = None
        self.reader_thread: threading.Thread | None = None
        self.output_queue: queue.Queue[str | None] = queue.Queue()
        self._drain_scheduled = False
        self._drain_lock = threading.Lock()
        self.running = False
        self._closed = False
        self.light_mode = False
        self.max_visible_chars = 120000
        self._visible_chars = 0
        self._hidden_echoes: list[str] = []
        self._suppress_sage_footer = False
        self._last_inserted_text = ""
        self._ai_stream_format: str | None = None
        self._json_line_buffer = ""
        self._current_block: str | None = None
        self._tool_name = ""
        self._tool_json = ""
        self._answer_parts: list[str] = []
        self._capture_active = False
        self._captured_response_parts: list[str] = []
        self._finish_capture_after_append = False
        self._ai_error_reported = False

        self.configure(fg_color="#050505", text_color="#d1d5db")
        self.tag_config("info", foreground="#7dd3fc")
        self.tag_config("error", foreground="#ff6b6b")
        self.tag_config("success", foreground="#4ade80")
        self.tag_config("dim", foreground="#6b7280")
        self.tag_config("thinking", foreground="#8b8b9e")
        self.tag_config("thinking_header", foreground="#9b87f5")
        self.tag_config("tool", foreground="#e0af68")
        self.tag_config("prompt", foreground="#ffffff")
        self.tag_config("routing", foreground="#2dd4bf")
        self.configure(state="disabled")

        self.bind("<Key>", self._on_key)
        self.bind("<Control-v>", lambda event: "break")
        self.bind("<Control-V>", lambda event: "break")
        self.bind("<Control-c>", self._copy_or_interrupt)
        self.bind("<Control-C>", self._copy_or_interrupt)
        self.bind("<Button-3>", self._show_context_menu)

    def start_powershell(
        self,
        project: str,
        ai_name: str = "Claude",
        mode: str = "Full Access",
    ) -> bool:
        """Start PowerShell in a Windows ConPTY and show the SAGE banner."""
        if self.running:
            return True

        self._closed = False
        if not HAS_WINPTY:
            self.append_text(
                "ERROR: pywinpty is required for the embedded PowerShell terminal.\n"
                "Install it with: pip install pywinpty\n",
                "error",
            )
            return False

        try:
            startup_script = self._startup_script(project, ai_name, mode)
            self.pty = PtyProcess.spawn(
                [
                    "powershell.exe",
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-NoExit",
                    "-Command",
                    startup_script,
                ],
                cwd=project,
                dimensions=(32, 120),
            )
            self.running = True
            self.reader_thread = threading.Thread(target=self._read_output, daemon=True)
            self.reader_thread.start()
            self._safe_after(100, lambda: self.show_welcome_screen(ai_name, mode))
            return True
        except Exception as exc:
            self.running = False
            self.append_text(f"ERROR: Failed to start PowerShell terminal: {exc}\n", "error")
            return False

    def _startup_script(self, project: str, ai_name: str, mode: str) -> str:
        """PowerShell startup script. Runs before the visible prompt, so no setup commands are echoed."""
        return (
            "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new(); "
            "$env:PYTHONIOENCODING = 'utf-8'; "
            "$env:PYTHONUTF8 = '1'; "
            "$env:SAGE_SUPPRESS_SUMMARY = '1'; "
            "$env:SAGE_SUPPRESS_FOOTER = '1'; "
            "$env:SAGE_CLEAN_MODE = '1'; "
            "Remove-Module PSReadLine -ErrorAction SilentlyContinue; "
            "if (Get-Variable PSStyle -ErrorAction SilentlyContinue) { $PSStyle.OutputRendering = 'PlainText' }; "
            "function prompt { \"PS $($executionContext.SessionState.Path.CurrentLocation)> \" }; "
            f"Set-Location -LiteralPath {self._ps_quote(project)}; "
        )

    def _read_output(self) -> None:
        """Read PowerShell output in the background and enqueue UI updates."""
        while self.running and self.pty is not None:
            try:
                if hasattr(self.pty, "isalive") and not self.pty.isalive():
                    break
                output = self.pty.read(4096)
            except (TimeoutError, EOFError):
                continue
            except Exception as exc:
                self.output_queue.put(f"\n[Terminal error: {exc}]\n")
                break

            if output:
                self.output_queue.put(output)
                self._schedule_drain()

        self.running = False

    def _schedule_drain(self) -> None:
        """Coalesce UI drains: at most one pending drain regardless of read rate.

        Two terminals each reading 4 KB chunks would otherwise schedule a flood
        of after(0) callbacks and starve the Tk event loop. One pending drain
        per terminal keeps the UI smooth even with several tabs streaming.
        """
        with self._drain_lock:
            if self._drain_scheduled:
                return
            self._drain_scheduled = True
        self._safe_after(16, self._drain_output_queue)

    def _safe_after(self, delay_ms: int, callback) -> None:
        """Schedule a UI callback only while the widget still exists."""
        try:
            if not self._closed and self.winfo_exists():
                self.after(delay_ms, callback)
        except Exception:
            log.debug("suppressed", exc_info=True)

    def _drain_output_queue(self) -> None:
        with self._drain_lock:
            self._drain_scheduled = False
        # Combine everything queued so far into one render pass. Fewer state
        # toggles and one see("end") per frame instead of one per read.
        chunks: list[str] = []
        while True:
            try:
                item = self.output_queue.get_nowait()
            except queue.Empty:
                break
            if item is not None:
                chunks.append(item)
        if chunks:
            self.append_text("".join(chunks))
        # If more arrived while we were draining, schedule the next pass.
        if not self.output_queue.empty():
            self._schedule_drain()

    def write(self, text: str) -> None:
        """Write raw text to the PowerShell PTY."""
        if not self.running or self.pty is None:
            self.append_text("\n[PowerShell terminal is not running]\n", "error")
            return
        try:
            self.pty.write(text)
        except Exception as exc:
            self.append_text(f"\n[Terminal write failed: {exc}]\n", "error")

    def send_command(self, command: str, wrap_with_sage: bool = True) -> None:
        """Send a command line to PowerShell, optionally enforcing sage run."""
        command = command.strip()
        if not command:
            return
        if wrap_with_sage and not command.lower().startswith("sage run --"):
            command = f"sage run -- {command}"
        self._hide_echo(command)
        self.write(command + "\r\n")

    def begin_ai_stream(self, ai_name: str, route_label: str | None = None) -> None:
        """Prepare the output renderer for a structured AI stream."""
        self._capture_active = True
        self._captured_response_parts = []
        self._answer_parts = []
        self._ai_error_reported = False
        if route_label:
            self._append_raw(self._tk_safe(f"-> {route_label}\n"), "routing")
        if ai_name.lower() == "claude":
            self._ai_stream_format = "claude"
            self._json_line_buffer = ""
            self._current_block = None
            self._tool_name = ""
            self._tool_json = ""
        else:
            self._ai_stream_format = None

    def interrupt(self) -> None:
        """Send Ctrl+C to the embedded PowerShell session without killing SAGE."""
        if self.pty is not None and hasattr(self.pty, "sendintr"):
            try:
                self.pty.sendintr()
            except Exception:
                log.debug("suppressed", exc_info=True)

        # Write Ctrl+C character
        try:
            self.write("\x03")
        except Exception:
            log.debug("suppressed", exc_info=True)

        # Show cancellation message after a tiny delay
        self._safe_after(100, lambda: self._show_stop_message())

    def _show_stop_message(self) -> None:
        """Show 'Stopped by user' message in terminal."""
        try:
            self.configure(state="normal")
            self.insert("end", "\n[STOPPED BY USER - Esc/Ctrl+C pressed]\n", "error")
            self.see("end")
            self.configure(state="disabled")
        except Exception:
            log.debug("suppressed", exc_info=True)

    def stop(self) -> None:
        """Close the embedded terminal."""
        self._closed = True
        self.running = False
        if self.pty is not None:
            try:
                if hasattr(self.pty, "close"):
                    self.pty.close(force=True)
                elif hasattr(self.pty, "cancel_io"):
                    self.pty.cancel_io()
            except Exception:
                log.debug("suppressed", exc_info=True)
            self.pty = None
        while not self.output_queue.empty():
            try:
                self.output_queue.get_nowait()
            except Exception:
                break

    def append_text(self, text: str, tag: str | bool | None = None) -> None:
        """Append terminal output while keeping scrollback bounded."""
        if self._ai_stream_format == "claude":
            segments = self._render_claude_stream_text(text)
        else:
            cleaned = self._clean_terminal_text(text)
            segments = [(cleaned, tag if isinstance(tag, str) else None)] if cleaned else []
        if not segments:
            if self._finish_capture_after_append:
                self._finish_capture_after_append = False
                self._finish_ai_capture()
            return
        combined = "".join(part for part, _ in segments)
        if self._last_inserted_text and not self._last_inserted_text.endswith(("\n", " ")) and combined.startswith(("[", "Claude", "Sensei")):
            first_text, first_tag = segments[0]
            segments[0] = ("\n\n" + first_text, first_tag)
            combined = "\n\n" + combined
        self._capture_response_text(combined)
        should_follow = self._is_scrolled_to_bottom()
        self.configure(state="normal")
        try:
            for part, part_tag in segments:
                self.insert("end", self._tk_safe(part), part_tag)
            self._last_inserted_text = combined[-80:]
            self._visible_chars += len(combined)
            self._prune_if_needed()
            if should_follow:
                self.see("end")
        finally:
            self.configure(state="disabled")
        if self._finish_capture_after_append:
            self._finish_capture_after_append = False
            self._finish_ai_capture()

    def append_terminal_text(self, text: str) -> None:
        self.append_text(text)

    def append_stream(self, chunk: str) -> None:
        self.append_text(chunk)

    def append_user_message(self, text: str) -> None:
        self.append_text(f"\n# User\n{text.strip()}\n", "info")

    def append_user_prompt(self, text: str) -> None:
        """Echo the user's prompt as a CLI-style `>` line before the run starts."""
        text = text.strip()
        if not text:
            return
        lines = text.splitlines()
        rendered = "\n> " + lines[0]
        for extra in lines[1:]:
            rendered += "\n  " + extra
        self._append_raw(self._tk_safe(rendered) + "\n", "prompt")

    def append_assistant_start(self, name: str = "SAGE") -> None:
        self.append_text(f"\n# {name}\n", "info")

    def append_assistant_text(self, text: str) -> None:
        self.append_text(text)

    def append_status_text(self, text: str) -> None:
        """Append GUI status text without adding it to captured AI memory."""
        self._append_raw(self._tk_safe(text), "info")

    def append_expandable_section(
        self,
        title: str,
        content: str,
        tag: str | None = None,
        collapsed: bool = False,
    ) -> None:
        """Compatibility renderer for OutputView-style structured sections."""
        content = str(content or "").strip()
        if not content:
            return
        section_tag = {
            "thinking_text": "thinking",
            "code": "tool",
            "running": "dim",
        }.get(str(tag or ""), tag or "info")
        self.append_text(f"\n{title}\n", "info")
        self.append_text(content + "\n", section_tag)

    def clear(self) -> None:
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.configure(state="disabled")
        self._visible_chars = 0
        self._last_inserted_text = ""

    def get_text(self) -> str:
        return self.get("1.0", "end-1c")

    def get_selected_text(self) -> str:
        try:
            return self.get("sel.first", "sel.last").strip()
        except Exception:
            return ""

    def set_terminal_mode(self, enabled: bool) -> None:
        return None

    def set_light_mode(self, enabled: bool) -> None:
        self.light_mode = enabled
        if enabled:
            self.configure(fg_color="#ffffff", text_color="#111827")
        else:
            self.configure(fg_color="#050505", text_color="#d1d5db")

    def show_welcome_screen(
        self,
        ai_name: str = "Claude",
        mode: str = "Full Access",
        tokens_used: int = 0,
        tokens_saved: int = 0,
        compression_ratio: str = "0%",
        run_count: int = 0,
    ) -> None:
        self.clear()
        self._append_raw(
            SAGE_WELCOME
            + f"\nConnected to: {ai_name} | Mode: {mode}\n"
            + "\n",
            "info",
        )

    def _show_context_menu(self, event) -> None:
        menu = tk.Menu(self, tearoff=0)
        has_selection = bool(self.get_selected_text())
        menu.add_command(
            label="Reply to selection",
            state="normal" if has_selection and self.on_reply_to_selection else "disabled",
            command=self._reply_to_selection,
        )
        menu.add_command(
            label="Copy selection",
            state="normal" if has_selection else "disabled",
            command=self._copy_selected_text,
        )
        menu.add_separator()
        menu.add_command(label="Copy all", command=self._copy_all_text)
        menu.add_command(label="Interrupt", command=self.interrupt)
        menu.tk_popup(event.x_root, event.y_root)

    def _reply_to_selection(self) -> None:
        selected = self.get_selected_text()
        if selected and self.on_reply_to_selection:
            self.on_reply_to_selection(selected)

    def _copy_selected_text(self) -> None:
        selected = self.get_selected_text()
        if selected:
            self.clipboard_clear()
            self.clipboard_append(selected)

    def _copy_all_text(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.get_text())

    def _copy_or_interrupt(self, event):
        if self.get_selected_text():
            self._copy_selected_text()
        else:
            self.interrupt()
        return "break"

    def _on_key(self, event):
        """Keep the output screen read-only. Commands go through the prompt box."""
        return "break"

    def _prune_if_needed(self) -> None:
        if self._visible_chars <= self.max_visible_chars + 10000:
            return
        cutoff = self.index(f"end - {self.max_visible_chars} chars")
        self.delete("1.0", cutoff)
        self.insert(
            "1.0",
            "[Older terminal scrollback trimmed for GUI speed.]\n\n",
            "info",
        )
        self._visible_chars = len(self.get_text())

    def _append_raw(self, text: str, tag: str | None = None) -> None:
        """Append trusted GUI-rendered text without terminal cleanup."""
        if not text:
            return
        should_follow = self._is_scrolled_to_bottom()
        self.configure(state="normal")
        try:
            self.insert("end", text, tag)
            self._last_inserted_text = text[-80:]
            self._visible_chars += len(text)
            self._prune_if_needed()
            if should_follow:
                self.see("end")
        finally:
            self.configure(state="disabled")

    def _is_scrolled_to_bottom(self) -> bool:
        """Return true when the user has not intentionally scrolled up."""
        try:
            _, bottom = self.yview()
            return bottom >= 0.995
        except Exception:
            return True

    def _hide_echo(self, command: str) -> None:
        """Remember a command that should execute but not render as terminal text."""
        normalized = self._normalize_line(command)
        if normalized:
            self._hidden_echoes.append(normalized)
            self._hidden_echoes = self._hidden_echoes[-12:]

    @staticmethod
    def _ps_quote(value: str | Path) -> str:
        return "'" + str(value).replace("'", "''") + "'"

    def _clean_terminal_text(self, text: str) -> str:
        text = self._clean_ansi(text)
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        kept: list[str] = []
        ended_with_newline = text.endswith("\n")
        for raw_line in text.split("\n"):
            line = raw_line
            normalized = self._normalize_line(line)

            if self._should_hide_line(normalized):
                continue

            kept.append(line)

        cleaned = "\n".join(kept)
        # Collapse long runs of blank lines so answers read cleanly instead of
        # scrolling through dead space left by suppressed wrapper/echo lines.
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        if cleaned and ended_with_newline:
            cleaned += "\n"
        return cleaned

    def _should_hide_line(self, normalized: str) -> bool:
        if not normalized:
            return False

        if self._is_prompt_line(normalized):
            if self._capture_active:
                self._finish_capture_after_append = True
            return True

        if normalized.startswith("[Checking ") or normalized.startswith("[OK] Connected"):
            return True

        if any(hidden and hidden in normalized for hidden in self._hidden_echoes):
            return True

        lower = normalized.lower()
        if lower.startswith("[sage]"):
            if "summary:" in lower:
                self._suppress_sage_footer = True
            return True

        if self._suppress_sage_footer:
            if self._is_prompt_line(normalized):
                self._suppress_sage_footer = False
            return True

        return False

    @staticmethod
    def _is_prompt_line(normalized: str) -> bool:
        return bool(re.match(r"^PS [^>]*>\s*$", normalized))

    def _capture_response_text(self, text: str) -> None:
        if self._capture_active and text:
            self._captured_response_parts.append(text)

    def _finish_ai_capture(self) -> None:
        if not self._capture_active:
            return
        self._capture_active = False
        self._ai_stream_format = None
        self._json_line_buffer = ""
        if self._answer_parts:
            response = "".join(self._answer_parts).strip()
        else:
            response = self._memory_text_from_rendered("".join(self._captured_response_parts))
        self._captured_response_parts = []
        self._answer_parts = []
        if response and self.on_ai_response_complete:
            self.on_ai_response_complete(response)
        if self.on_ai_stream_finished:
            self.on_ai_stream_finished(None)

    def _abort_ai_capture(self, message: str) -> None:
        """Stop the current AI capture after a terminal CLI failure."""
        self._capture_active = False
        self._ai_stream_format = None
        self._json_line_buffer = ""
        self._current_block = None
        self._tool_name = ""
        self._tool_json = ""
        self._captured_response_parts = []
        self._answer_parts = []
        if self.on_ai_stream_finished:
            self.on_ai_stream_finished(message)

    @staticmethod
    def _memory_text_from_rendered(text: str) -> str:
        text = text.strip()
        match = re.search(r"(?:^|\n)Answer\n(?P<answer>.*)\Z", text, re.DOTALL)
        if match:
            return match.group("answer").strip()
        return re.sub(r"^(Thinking|Answer)\n", "", text).strip()

    @staticmethod
    def _normalize_line(text: str) -> str:
        return " ".join(text.strip().split())

    @staticmethod
    def _clean_ansi(text: str) -> str:
        text = re.sub(r"\x1b\[[0-9;?]*[ -/]*[@-~]", "", text)
        text = re.sub(r"\x1b\].*?(\x07|\x1b\\)", "", text)
        return text

    @staticmethod
    def _tk_safe(text: str) -> str:
        """Tk text widgets only accept BMP characters; replace the rest."""
        return re.sub(r"[\U00010000-\U0010FFFF]", "□", text)

    def _render_claude_stream_text(self, text: str) -> list[tuple[str, str | None]]:
        """Render Claude stream-json events the way the Claude CLI presents them."""
        text = self._clean_ansi(text).replace("\r\n", "\n").replace("\r", "\n")
        self._json_line_buffer += text

        segments: list[tuple[str, str | None]] = []
        lines = self._json_line_buffer.split("\n")
        if self._json_line_buffer.endswith("\n"):
            self._json_line_buffer = ""
            complete_lines = lines
        else:
            self._json_line_buffer = lines.pop() if lines else ""
            complete_lines = lines
            if self._is_prompt_line(self._normalize_line(self._json_line_buffer)):
                if self._capture_active:
                    self._finish_capture_after_append = True
                self._json_line_buffer = ""

        for line in complete_lines:
            normalized = self._normalize_line(line)
            if self._should_hide_line(normalized):
                continue
            stripped = line.strip()
            if not stripped:
                continue
            if not stripped.startswith("{"):
                if self._is_claude_retry_limit_error(stripped):
                    if self._ai_error_reported:
                        continue
                    self._ai_error_reported = True
                    message = self._format_claude_retry_limit_error(stripped)
                    self._abort_ai_capture(message)
                    self.interrupt()
                    segments.append((f"\nERROR: {message}\n", "error"))
                    continue
                cleaned = self._clean_terminal_text(line + "\n")
                if cleaned:
                    segments.append((cleaned, None))
                continue

            segments.extend(self._render_claude_event(stripped))

        return segments

    @staticmethod
    def _is_claude_retry_limit_error(text: str) -> bool:
        lower = text.lower()
        return (
            "429" in lower
            and (
                "too many tokens per day" in lower
                or "too many requests" in lower
                or "rate limit" in lower
            )
        )

    @staticmethod
    def _format_claude_retry_limit_error(text: str) -> str:
        clean = " ".join(str(text or "").split())
        if "too many tokens per day" in clean.lower():
            return "Claude API limit hit: too many tokens per day. Wait before trying again."
        if clean:
            return f"Claude API limit hit: {clean[:300]}"
        return "Claude API limit hit. Wait before trying again."

    def _render_claude_event(self, line: str) -> list[tuple[str, str | None]]:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return []

        event_type = event.get("type")

        if event_type == "system":
            if event.get("subtype") == "init":
                model = event.get("model") or "Claude"
                return [(f"· session started · {model}\n", "dim")]
            return []

        if event_type == "stream_event":
            stream_event = event.get("event", {})
            stream_type = stream_event.get("type")

            if stream_type == "content_block_start":
                block = stream_event.get("content_block", {})
                block_type = block.get("type")
                if block_type == "thinking":
                    self._current_block = "thinking"
                    return [("\n✻ Thinking…\n", "thinking_header")]
                if block_type == "text":
                    self._current_block = "text"
                    return [("\n● ", None)]
                if block_type == "tool_use":
                    self._current_block = "tool_use"
                    self._tool_name = block.get("name", "tool")
                    self._tool_json = ""
                return []

            if stream_type == "content_block_delta":
                delta = stream_event.get("delta", {})
                delta_type = delta.get("type")
                if delta_type == "thinking_delta":
                    thinking = delta.get("thinking", "")
                    return [(thinking, "thinking")] if thinking else []
                if delta_type == "text_delta":
                    answer = delta.get("text", "")
                    if answer:
                        self._answer_parts.append(answer)
                        return [(answer, None)]
                    return []
                if delta_type == "input_json_delta":
                    self._tool_json += delta.get("partial_json", "")
                    return []
                return []

            if stream_type == "content_block_stop":
                if self._current_block == "tool_use":
                    summary = self._tool_call_summary(self._tool_name, self._tool_json)
                    self._current_block = None
                    self._tool_name = ""
                    self._tool_json = ""
                    return [(f"\n● {summary}\n", "tool")]
                self._current_block = None
                return []

            if stream_type == "message_stop":
                return [("\n", None)]
            return []

        if event_type == "user":
            return self._render_tool_results(event)

        if event_type in {"assistant", "result"}:
            if event_type == "result":
                return self._render_result(event)
            return []

        text = event.get("text") or event.get("content")
        if isinstance(text, str) and text:
            self._answer_parts.append(text)
            return [(text, None)]
        return []

    @staticmethod
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
            detail = detail[:77] + "…"
        return f"{name}({detail})"

    def _render_tool_results(self, event: dict) -> list[tuple[str, str | None]]:
        """Render tool results as indented `⎿` lines under the tool call."""
        message = event.get("message", {})
        content = message.get("content", [])
        if not isinstance(content, list):
            return []
        segments: list[tuple[str, str | None]] = []
        for item in content:
            if not isinstance(item, dict) or item.get("type") != "tool_result":
                continue
            text = self._tool_result_text(item.get("content"))
            lines = [part.strip() for part in text.splitlines() if part.strip()]
            if lines:
                summary = lines[0]
                if len(summary) > 100:
                    summary = summary[:97] + "…"
                if len(lines) > 1:
                    summary += f" … +{len(lines) - 1} lines"
            else:
                summary = "(no output)"
            tag = "error" if item.get("is_error") else "dim"
            segments.append((f"  ⎿  {summary}\n", tag))
        return segments

    @staticmethod
    def _tool_result_text(content) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict) and isinstance(block.get("text"), str):
                    parts.append(block["text"])
            return "\n".join(parts)
        return ""

    def _render_result(self, event: dict) -> list[tuple[str, str | None]]:
        """Render the final result event as a completion footer."""
        segments: list[tuple[str, str | None]] = []
        subtype = event.get("subtype")
        if event.get("is_error") or subtype not in (None, "success"):
            error_text = event.get("result") or event.get("error") or subtype or "unknown error"
            if isinstance(error_text, str):
                segments.append((f"\n✗ {error_text.strip()}\n", "error"))
                if "not logged in" in error_text.lower():
                    segments.append((
                        "  ⎿  The Claude CLI has no login on this machine. "
                        "Type /login in the prompt box to open a login window, finish there, then resend.\n",
                        "info",
                    ))
        parts = []
        duration_ms = event.get("duration_ms")
        if duration_ms:
            parts.append(f"{int(duration_ms) / 1000:.1f}s")
        cost = event.get("total_cost_usd")
        if isinstance(cost, (int, float)) and cost > 0:
            parts.append(f"${cost:.4f}")
        usage = event.get("usage") or {}
        output_tokens = usage.get("output_tokens")
        if output_tokens:
            parts.append(f"{output_tokens} tokens")
        if parts:
            segments.append((f"\n─ done · {' · '.join(parts)}\n", "dim"))
        return segments
