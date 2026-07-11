"""PTY-based Terminal Widget for SAGE GUI - Windows ConPTY Integration"""

import customtkinter as ctk
import threading
import queue
import re
from pathlib import Path

try:
    import winpty
    HAS_WINPTY = True
except ImportError:
    HAS_WINPTY = False


class PTYTerminal(ctk.CTkTextbox):
    """
    Embedded pseudo-terminal widget using Windows ConPTY.

    Renders AI output with proper ANSI colors, handles streaming,
    and displays ASCII art welcome screen.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            wrap="word",
            font=ctk.CTkFont(family="Consolas", size=13),
            **kwargs
        )

        self.configure(state="disabled")  # Read-only

        # PTY process (if available)
        self.pty_process = None
        self.pty_thread = None
        self.output_queue = queue.Queue()
        self.running = False

        # ANSI color tags
        self._configure_ansi_tags()

        # Current input buffer
        self.input_buffer = ""

    def _configure_ansi_tags(self):
        """Configure text tags for ANSI color codes and thinking states"""
        # Thinking/reasoning/coding tags
        self.tag_config("thinking_header", foreground="#9b87f5", font=ctk.CTkFont(family="Consolas", size=13, weight="bold"))
        self.tag_config("thinking_text", foreground="#c4b5fd")
        self.tag_config("reasoning_header", foreground="#3b82f6", font=ctk.CTkFont(family="Consolas", size=13, weight="bold"))
        self.tag_config("coding_header", foreground="#10b981", font=ctk.CTkFont(family="Consolas", size=13, weight="bold"))
        self.tag_config("answer_header", foreground="#f59e0b", font=ctk.CTkFont(family="Consolas", size=13, weight="bold"))

        # Standard colors
        self.tag_config("black", foreground="#2B2B2B")
        self.tag_config("red", foreground="#E06C75")
        self.tag_config("green", foreground="#98C379")
        self.tag_config("yellow", foreground="#E5C07B")
        self.tag_config("blue", foreground="#61AFEF")
        self.tag_config("magenta", foreground="#C678DD")
        self.tag_config("cyan", foreground="#56B6C2")
        self.tag_config("white", foreground="#ABB2BF")

        # Bright colors
        self.tag_config("bright_black", foreground="#5C6370")
        self.tag_config("bright_red", foreground="#BE5046")
        self.tag_config("bright_green", foreground="#98C379")
        self.tag_config("bright_yellow", foreground="#D19A66")
        self.tag_config("bright_blue", foreground="#61AFEF")
        self.tag_config("bright_magenta", foreground="#C678DD")
        self.tag_config("bright_cyan", foreground="#56B6C2")
        self.tag_config("bright_white", foreground="#FFFFFF")

        # Styles
        self.tag_config("bold", font=ctk.CTkFont(family="Consolas", size=13, weight="bold"))
        self.tag_config("dim", foreground="#5C6370")
        self.tag_config("info", foreground="#61AFEF")
        self.tag_config("error", foreground="#E06C75")
        self.tag_config("running", foreground="#98C379")

    def append_text(self, text: str, tag: str = None):
        """Append text with optional tag styling"""
        self.configure(state="normal")

        if tag:
            self.insert("end", text, tag)
        else:
            # Parse ANSI codes if present
            self._insert_with_ansi(text)

        self.configure(state="disabled")
        self.see("end")

    def _insert_with_ansi(self, text: str):
        """Insert text parsing ANSI escape codes"""
        # Simple ANSI parser - handles basic colors
        ansi_pattern = re.compile(r'\x1b\[([0-9;]+)m')

        current_tag = None
        last_pos = 0

        for match in ansi_pattern.finditer(text):
            # Insert text before ANSI code
            if match.start() > last_pos:
                plain_text = text[last_pos:match.start()]
                if current_tag:
                    self.insert("end", plain_text, current_tag)
                else:
                    self.insert("end", plain_text)

            # Parse ANSI code
            code = match.group(1)
            current_tag = self._ansi_code_to_tag(code)
            last_pos = match.end()

        # Insert remaining text
        if last_pos < len(text):
            remaining = text[last_pos:]
            if current_tag:
                self.insert("end", remaining, current_tag)
            else:
                self.insert("end", remaining)

    def _ansi_code_to_tag(self, code: str) -> str:
        """Convert ANSI color code to tag name"""
        code_map = {
            "0": None,  # Reset
            "1": "bold",
            "2": "dim",
            "30": "black",
            "31": "red",
            "32": "green",
            "33": "yellow",
            "34": "blue",
            "35": "magenta",
            "36": "cyan",
            "37": "white",
            "90": "bright_black",
            "91": "bright_red",
            "92": "bright_green",
            "93": "bright_yellow",
            "94": "bright_blue",
            "95": "bright_magenta",
            "96": "bright_cyan",
            "97": "bright_white",
        }
        return code_map.get(code)

    def clear(self):
        """Clear terminal content"""
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.configure(state="disabled")

    def show_welcome(self, ai_name: str = "Claude", mode: str = "Full Access"):
        """Display SAGE ASCII art welcome screen"""
        from sage.gui.ascii_art import get_welcome_banner

        welcome = get_welcome_banner(ai_name, mode)
        self.clear()
        self.append_text(welcome, "info")

    def start_pty_session(self, command: list[str]):
        """
        Start PTY session with given command.

        Args:
            command: Command parts (e.g., ['sage', 'run', '--', 'claude'])
        """
        if not HAS_WINPTY:
            self.append_text("\n[ERROR] pywinpty not installed. Using fallback mode.\n", "error")
            return False

        try:
            # Create PTY process
            self.pty_process = winpty.PTY(80, 24)  # 80 cols, 24 rows
            self.pty_process.spawn(' '.join(command))

            self.running = True

            # Start output reader thread
            self.pty_thread = threading.Thread(
                target=self._read_pty_output,
                daemon=True
            )
            self.pty_thread.start()

            return True

        except Exception as e:
            self.append_text(f"\n[ERROR] PTY failed: {e}\n", "error")
            return False

    def _read_pty_output(self):
        """Read PTY output in background thread - parse Claude stream-json AND Codex JSONL"""
        import json

        json_buffer = ""
        seen_thinking = False
        seen_reasoning = False
        seen_coding = False
        seen_answer = False

        try:
            while self.running and self.pty_process:
                try:
                    output = self.pty_process.read(1024, timeout=100)
                    if output:
                        # Try to parse as JSON stream (Claude/Codex)
                        lines = output.split('\n')
                        for line in lines:
                            line = line.strip()
                            if not line:
                                continue

                            # Check if it's JSON
                            if line.startswith('{'):
                                try:
                                    event = json.loads(line)
                                    event_type = event.get('type')

                                    # CLAUDE stream-json format
                                    if event_type == 'stream_event':
                                        stream_event = event.get('event', {})
                                        stream_type = stream_event.get('type')

                                        if stream_type == 'content_block_start':
                                            block = stream_event.get('content_block', {})
                                            block_type = block.get('type')

                                            if block_type == 'thinking' and not seen_thinking:
                                                seen_thinking = True
                                                self.output_queue.put(('thinking_header', '\n━━━ Thinking ━━━\n'))
                                            elif block_type == 'text' and not seen_answer:
                                                seen_answer = True
                                                self.output_queue.put(('answer_header', '\n━━━ Answer ━━━\n'))

                                        elif stream_type == 'content_block_delta':
                                            delta = stream_event.get('delta', {})
                                            delta_type = delta.get('type')

                                            if delta_type == 'thinking_delta':
                                                text = delta.get('thinking', '')
                                                if text:
                                                    self.output_queue.put(('thinking_text', text))
                                            elif delta_type == 'text_delta':
                                                text = delta.get('text', '')
                                                if text:
                                                    self.output_queue.put(('text', text))

                                    # CODEX JSONL format
                                    elif event_type == 'reasoning':
                                        if not seen_reasoning:
                                            seen_reasoning = True
                                            self.output_queue.put(('reasoning_header', '\n━━━ Reasoning ━━━\n'))
                                        text = event.get('text', '')
                                        if text:
                                            self.output_queue.put(('thinking_text', text))

                                    elif event_type == 'coding':
                                        if not seen_coding:
                                            seen_coding = True
                                            self.output_queue.put(('coding_header', '\n━━━ Coding ━━━\n'))
                                        text = event.get('text', '')
                                        if text:
                                            self.output_queue.put(('thinking_text', text))

                                    elif event_type == 'output' or event_type == 'message':
                                        if not seen_answer:
                                            seen_answer = True
                                            self.output_queue.put(('answer_header', '\n━━━ Answer ━━━\n'))
                                        text = event.get('text', '') or event.get('content', '')
                                        if text:
                                            self.output_queue.put(('text', text))

                                except json.JSONDecodeError:
                                    # Not JSON, just show as text
                                    self.output_queue.put(('text', line + '\n'))
                            else:
                                # Regular text output
                                self.output_queue.put(('text', line + '\n'))

                        # Update UI
                        self.after(0, self._process_pty_output)

                except TimeoutError:
                    continue
                except Exception as e:
                    self.output_queue.put(('error', f"\n[PTY Error: {e}]\n"))
                    break
        finally:
            self.running = False

    def _process_pty_output(self):
        """Process queued PTY output on main thread"""
        try:
            while not self.output_queue.empty():
                item = self.output_queue.get_nowait()

                # Handle tagged output (tag, text) or plain text
                if isinstance(item, tuple):
                    tag, text = item
                    self.append_text(text, tag)
                else:
                    self.append_text(item)

        except queue.Empty:
            pass

    def write_to_pty(self, text: str):
        """Send input to PTY process"""
        if self.pty_process and self.running:
            try:
                self.pty_process.write(text)
            except Exception as e:
                self.append_text(f"\n[Write Error: {e}]\n", "error")

    def stop_pty_session(self):
        """Stop PTY session"""
        self.running = False
        if self.pty_process:
            try:
                self.pty_process.close()
            except:
                pass
            self.pty_process = None

    def is_pty_active(self) -> bool:
        """Check if PTY session is running"""
        return self.running and self.pty_process is not None
