"""
Output View Widget for SAGE Desktop GUI.

Provides a scrollable text area for displaying AI responses with
streaming support and block detection (Thinking, Running, Coding, Complete).

Can switch between normal text mode and PTY terminal mode.
"""

import customtkinter as ctk
import re
import tkinter as tk
from typing import Callable, Optional
from enum import Enum
from .pty_terminal import PTYTerminal


class BlockType(Enum):
    """Types of output blocks."""
    THINKING = "thinking"
    RUNNING = "running"
    CODING = "coding"
    COMPLETE = "complete"
    NORMAL = "normal"


class OutputView(ctk.CTkFrame):
    """Scrollable output view with syntax highlighting and block detection."""

    # Block detection patterns
    THINKING_PATTERN = r"━━━ Thinking ━━━"
    RUNNING_PATTERN = r"━━━ Running ━━━"
    CODING_PATTERN = r"━━━ Coding ━━━"
    COMPLETE_PATTERN = r"━━━ Complete ━━━"

    # Color schemes for different block types
    BLOCK_COLORS = {
        BlockType.THINKING: "#9b87f5",  # Purple
        BlockType.RUNNING: "#3b82f6",   # Blue
        BlockType.CODING: "#10b981",    # Green
        BlockType.COMPLETE: "#f59e0b",  # Amber
        BlockType.NORMAL: None          # Default color
    }

    def __init__(
        self,
        parent,
        on_reply_to_selection: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        """
        Initialize output view widget.

        Args:
            parent: Parent widget
            **kwargs: Additional arguments for CTkFrame
        """
        super().__init__(parent, **kwargs)
        self.on_reply_to_selection = on_reply_to_selection
        # Sensei: Increased from 90K to 500K - GPT-4 Turbo has 128K context, Claude has 200K
        # Users expect to see full chat history when loading sessions
        self.max_visible_chars = 500000
        self.prune_enabled = True  # Can be disabled when loading history
        self._visible_chars = 0
        self._trimmed_once = False
        self.terminal_mode = False

        # Create text widget with scrollbar - FORCE word wrap, NO horizontal scroll
        self.text_widget = ctk.CTkTextbox(
            self,
            wrap="word",  # Wrap at word boundaries
            font=ctk.CTkFont(family="Consolas", size=12),
            state="disabled"
        )
        self.text_widget.pack(fill="both", expand=True, padx=5, pady=5)

        # Disable horizontal scrolling at the tk level
        self.text_widget._textbox.configure(wrap="word")  # Ensure tk.Text also wraps

        self.text_widget.bind("<Button-3>", self._show_context_menu)
        self.text_widget.bind("<Control-c>", self._copy_selection)

        # Configure tags for different block types
        self._configure_tags()

        # Current block type
        self.current_block = BlockType.NORMAL

        # Auto-scroll enabled by default
        self.auto_scroll = True
        self.light_mode = False

        # Collapsible sections tracking
        self.collapsed_sections = {}  # {section_name: (start_index, end_index, is_collapsed)}
        self._section_counter = 0

    def _show_context_menu(self, event):
        """Show selection actions for the output conversation."""
        menu = tk.Menu(self, tearoff=0)
        has_selection = bool(self.get_selected_text())

        menu.add_command(
            label="Reply to selection",
            state="normal" if has_selection else "disabled",
            command=self._reply_to_selection,
        )
        menu.add_command(
            label="Copy selection",
            state="normal" if has_selection else "disabled",
            command=self._copy_selected_text,
        )
        menu.add_separator()
        menu.add_command(label="Copy all", command=self._copy_all_text)
        menu.tk_popup(event.x_root, event.y_root)

    def get_selected_text(self) -> str:
        """Return selected text from the output screen."""
        try:
            return self.text_widget.get("sel.first", "sel.last").strip()
        except Exception:
            return ""

    def _reply_to_selection(self):
        """Send selected output text to the prompt box."""
        selected = self.get_selected_text()
        if selected and self.on_reply_to_selection:
            self.on_reply_to_selection(selected)

    def _copy_selected_text(self):
        """Copy selected text to clipboard."""
        selected = self.get_selected_text()
        if selected:
            self.clipboard_clear()
            self.clipboard_append(selected)

    def _copy_all_text(self):
        """Copy the full output conversation."""
        text = self.get_text()
        self.clipboard_clear()
        self.clipboard_append(text)

    def _copy_selection(self, event):
        """Preserve normal Ctrl+C copying inside the read-only output."""
        self._copy_selected_text()
        return "break"

    def _configure_tags(self):
        """Configure text tags for different block types and styles."""
        # Enable tag configuration
        self.text_widget.configure(state="normal")

        # Note: CTkTextbox does not support font configuration in tags
        # Only foreground color is supported
        for block_type, color in self.BLOCK_COLORS.items():
            if color:
                self.text_widget.tag_config(
                    block_type.value,
                    foreground=color
                )

        # Special tags
        self.text_widget.tag_config(
            "block_header",
            foreground="#60a5fa"
        )

        self.text_widget.tag_config(
            "success",
            foreground="#10b981"
        )

        self.text_widget.tag_config(
            "error",
            foreground="#ef4444"
        )

        self.text_widget.tag_config(
            "code",
            foreground="#a78bfa"
        )

        self.text_widget.tag_config(
            "info",
            foreground="#9ca3af"
        )

        self.text_widget.tag_config(
            "running",
            foreground="#e5e7eb",
            justify="left"
        )

        # Thinking/reasoning/coding tags
        self.text_widget.tag_config(
            "thinking_header",
            foreground="#9b87f5",
            underline=1  # Make it look clickable
        )

        self.text_widget.tag_config(
            "thinking_text",
            foreground="#c4b5fd"
        )

        self.text_widget.tag_config(
            "reasoning_header",
            foreground="#3b82f6",
            underline=1  # Make it look clickable
        )

        self.text_widget.tag_config(
            "coding_header",
            foreground="#10b981",
            underline=1  # Make it look clickable
        )

        self.text_widget.tag_config(
            "answer_header",
            foreground="#f59e0b"
        )

        # Collapsible section tags
        self.text_widget.tag_config(
            "collapsible_header",
            underline=1
        )

        # Bind click event to collapsible headers
        self.text_widget.tag_bind("thinking_header", "<Button-1>", self._toggle_section)
        self.text_widget.tag_bind("reasoning_header", "<Button-1>", self._toggle_section)
        self.text_widget.tag_bind("coding_header", "<Button-1>", self._toggle_section)

        # Diff syntax highlighting (like Claude Code)
        self.text_widget.tag_config(
            "diff_removed",
            foreground="#ef4444",  # Red
            background="#4c1d1d"    # Dark red background
        )

        self.text_widget.tag_config(
            "diff_added",
            foreground="#10b981",  # Green
            background="#1d4c34"    # Dark green background
        )

        self.text_widget.tag_config(
            "diff_context",
            foreground="#9ca3af"  # Gray
        )

        self.text_widget.tag_config(
            "code_line_num",
            foreground="#6b7280"  # Dim gray for line numbers
        )

        self.text_widget.tag_config(
            "user_label",
            foreground="#ffffff",
            justify="right",
            spacing1=10
        )

        self.text_widget.tag_config(
            "user_message",
            foreground="#c084fc",
            justify="right",
            rmargin=12,
            lmargin1=80,
            lmargin2=80,
            spacing3=8
        )

        self.text_widget.tag_config(
            "assistant_label",
            foreground="#86efac",
            justify="left",
            spacing1=10
        )

        self.text_widget.tag_config(
            "assistant_message",
            foreground="#f3f4f6",
            justify="left",
            lmargin1=12,
            lmargin2=12,
            rmargin=80,
            spacing3=4
        )

        self.text_widget.tag_config(
            "terminal",
            foreground="#d1d5db",
            justify="left",
            lmargin1=0,
            lmargin2=0,
            rmargin=0,
        )

        # Disable editing
        self.text_widget.configure(state="disabled")
        self.set_light_mode(False)

    def append_text(self, text: str, auto_detect_block: bool | str = True):
        """
        Append text to the output view with optional block detection.

        Args:
            text: Text to append
            auto_detect_block: Whether to automatically detect block types
        """
        if isinstance(auto_detect_block, str):
            self._insert_text(text, auto_detect_block)
            return

        should_follow = self._is_scrolled_to_bottom()
        self.text_widget.configure(state="normal")
        if auto_detect_block:
            # Detect block type from text
            self._detect_and_append_with_blocks(text)
        else:
            # Append without block detection
            tag = self.current_block.value if self.current_block != BlockType.NORMAL else None
            self.text_widget.insert("end", text, tag)

        self.text_widget.configure(state="disabled")
        self._visible_chars += len(text)
        self._prune_if_needed()

        # Auto-scroll to bottom
        if self.auto_scroll and should_follow:
            self.scroll_to_bottom()

    def _insert_text(self, text: str, tag: Optional[str] = None):
        """Insert raw text with a tag and preserve exact streaming text."""
        should_follow = self._is_scrolled_to_bottom()
        self.text_widget.configure(state="normal")
        self.text_widget.insert("end", text, tag)
        self.text_widget.configure(state="disabled")
        self._visible_chars += len(text)

        # Only check pruning if we've exceeded the limit (avoid lag from checking every insert)
        if self._visible_chars > self.max_visible_chars + 10000:
            self._prune_if_needed()

        if self.auto_scroll and should_follow:
            self.scroll_to_bottom()

    def _prune_if_needed(self):
        """Keep the visible textbox responsive when conversations get long."""
        if not self.prune_enabled or self._visible_chars <= self.max_visible_chars + 10000:
            return

        try:
            self.text_widget.configure(state="normal")
            cutoff = self.text_widget.index(f"end - {self.max_visible_chars} chars")
            self.text_widget.delete("1.0", cutoff)
            if not self._trimmed_once:
                self.text_widget.insert(
                    "1.0",
                    "[Older visible output trimmed for speed. Full saved runs remain in SAGE history.]\n\n",
                    "info",
                )
                self._trimmed_once = True
            self._visible_chars = len(self.text_widget.get("1.0", "end-1c"))
            self.text_widget.configure(state="disabled")
        except Exception:
            self.text_widget.configure(state="disabled")

    def append_user_message(self, text: str):
        """Append the user's prompt as a right-aligned chat message."""
        clean_text = text.strip()
        if not clean_text:
            return
        self._insert_text("\nYou\n", "user_label")
        self._insert_text(f"{clean_text}\n", "user_message")

    def append_assistant_start(self, name: str = "SAGE"):
        """Start a left-aligned assistant response."""
        self._insert_text(f"\n{name}\n", "assistant_label")

    def append_assistant_text(self, text: str):
        """Append assistant response text on the left."""
        self._insert_text(text, "assistant_message")

    def append_terminal_text(self, text: str):
        """Append raw terminal output without chat formatting."""
        self._insert_text(text, "terminal")

    def set_terminal_mode(self, enabled: bool):
        """Switch the output area into a raw CLI terminal surface."""
        self.terminal_mode = enabled
        self.text_widget.configure(state="normal")
        if enabled:
            self.configure(fg_color="#050505")
            self.text_widget.configure(
                fg_color="#050505",
                text_color="#d1d5db",
                font=ctk.CTkFont(family="Consolas", size=14),
            )
            self.text_widget.tag_config("terminal", foreground="#d1d5db")
            self.text_widget.tag_config("info", foreground="#858585")
            self.text_widget.tag_config("error", foreground="#ff6b6b")
            self.text_widget.tag_config("success", foreground="#4ade80")
        else:
            self.text_widget.configure(font=ctk.CTkFont(family="Consolas", size=12))
        self.text_widget.configure(state="disabled")
        if not enabled:
            self.set_light_mode(self.light_mode)

    def set_light_mode(self, enabled: bool):
        """Switch only the output/chat screen between dark and light mode."""
        self.light_mode = enabled
        if self.terminal_mode:
            self.text_widget.configure(state="normal")
            self.configure(fg_color="#050505")
            self.text_widget.configure(fg_color="#050505", text_color="#d1d5db")
            self.text_widget.tag_config("terminal", foreground="#d1d5db")
            self.text_widget.configure(state="disabled")
            return

        self.configure(fg_color="#ffffff" if enabled else "transparent")
        self.text_widget.configure(
            fg_color="#ffffff" if enabled else ("#f9fafb", "#1f2937"),
            text_color="#111827" if enabled else "#f3f4f6",
        )

        self.text_widget.configure(state="normal")
        self.text_widget.tag_config("info", foreground="#4b5563" if enabled else "#9ca3af")
        self.text_widget.tag_config("running", foreground="#111827" if enabled else "#e5e7eb")
        self.text_widget.tag_config("user_label", foreground="#7c3aed" if enabled else "#ffffff")
        self.text_widget.tag_config("user_message", foreground="#7e22ce" if enabled else "#c084fc")
        self.text_widget.tag_config("assistant_label", foreground="#166534" if enabled else "#86efac")
        self.text_widget.tag_config("assistant_message", foreground="#000000" if enabled else "#f3f4f6")
        self.text_widget.tag_config("code", foreground="#6d28d9" if enabled else "#a78bfa")
        self.text_widget.tag_config("error", foreground="#b91c1c" if enabled else "#ef4444")
        self.text_widget.tag_config("success", foreground="#15803d" if enabled else "#10b981")

        # Diff colors for light/dark mode
        self.text_widget.tag_config(
            "diff_removed",
            foreground="#b91c1c" if enabled else "#ef4444",
            background="#fee2e2" if enabled else "#4c1d1d"
        )
        self.text_widget.tag_config(
            "diff_added",
            foreground="#15803d" if enabled else "#10b981",
            background="#d1fae5" if enabled else "#1d4c34"
        )
        self.text_widget.tag_config(
            "code_line_num",
            foreground="#9ca3af" if enabled else "#6b7280"
        )

        self.text_widget.configure(state="disabled")

    def _detect_and_append_with_blocks(self, text: str):
        """Detect block types and append with appropriate styling."""
        lines = text.split('\n')

        for line in lines:
            # Check for block headers
            if re.search(self.THINKING_PATTERN, line):
                self.current_block = BlockType.THINKING
                self.text_widget.insert("end", line + "\n", "block_header")
            elif re.search(self.RUNNING_PATTERN, line):
                self.current_block = BlockType.RUNNING
                self.text_widget.insert("end", line + "\n", "block_header")
            elif re.search(self.CODING_PATTERN, line):
                self.current_block = BlockType.CODING
                self.text_widget.insert("end", line + "\n", "block_header")
            elif re.search(self.COMPLETE_PATTERN, line):
                self.current_block = BlockType.COMPLETE
                self.text_widget.insert("end", line + "\n", "block_header")
            else:
                # Apply diff-aware styling
                self._insert_line_with_diff_colors(line + "\n")

    def _insert_line_with_diff_colors(self, line: str):
        """Insert a line with intelligent diff coloring like Claude Code."""
        stripped = line.lstrip()

        # Detect line type and apply appropriate tag
        tag = self._determine_line_tag(line)

        # Add emoji symbols for diff lines
        if tag == "diff_removed":
            # Insert red line with ❌
            symbol_tag = ("diff_removed", "error")
            self.text_widget.insert("end", "❌ ", symbol_tag)
            self.text_widget.insert("end", line, tag)
        elif tag == "diff_added":
            # Insert green line with ✅
            symbol_tag = ("diff_added", "success")
            self.text_widget.insert("end", "✅ ", symbol_tag)
            self.text_widget.insert("end", line, tag)
        else:
            # Regular line
            self.text_widget.insert("end", line, tag)

    def _determine_line_tag(self, line: str) -> Optional[str]:
        """Determine the appropriate tag for a line of text."""
        # Check for diff patterns (like Claude Code)
        stripped = line.lstrip()

        # Detect removed lines (red with ❌)
        if stripped.startswith("-") and not stripped.startswith("---"):
            return "diff_removed"
        elif "❌" in line or "✗" in line:
            return "diff_removed"

        # Detect added lines (green with ✅)
        elif stripped.startswith("+") and not stripped.startswith("+++"):
            return "diff_added"
        elif "✅" in line or "✓" in line:
            return "diff_added"

        # Line numbers in diffs
        elif re.match(r'^\s*\d+\s*[│|]', line):
            return "code_line_num"

        # Code blocks
        elif stripped.startswith("```") or stripped.startswith("$"):
            return "code"

        # Current block styling
        elif self.current_block != BlockType.NORMAL:
            return self.current_block.value

        else:
            return None

    def append_stream(self, chunk: str):
        """
        Append a streaming chunk of text.

        This method is optimized for streaming output where text arrives
        in small chunks.

        Args:
            chunk: Text chunk to append
        """
        self.append_text(chunk, auto_detect_block=True)

    def clear(self):
        """Clear all text from the output view."""
        self.text_widget.configure(state="normal")
        self.text_widget.delete("1.0", "end")
        self.text_widget.configure(state="disabled")
        self.current_block = BlockType.NORMAL
        self._visible_chars = 0
        self._trimmed_once = False

    def show_welcome_screen(self, ai_name: str = "Claude", mode: str = "Full Access",
                            tokens_used: int = 0, tokens_saved: int = 0,
                            compression_ratio: str = "0%", run_count: int = 0):
        """Show SAGE ASCII art welcome screen with token stats"""
        from sage.gui.ascii_art import get_welcome_banner

        welcome = get_welcome_banner(ai_name, mode, tokens_used, tokens_saved,
                                     compression_ratio, run_count)
        self.clear()
        self.append_text(welcome, "info")

    def scroll_to_bottom(self):
        """Scroll to the bottom of the output view."""
        self.text_widget.see("end")

    def _is_scrolled_to_bottom(self) -> bool:
        """Return true when the user has not intentionally scrolled up."""
        try:
            _, bottom = self.text_widget.yview()
            return bottom >= 0.995
        except Exception:
            return True

    def set_auto_scroll(self, enabled: bool):
        """
        Enable or disable auto-scrolling.

        Args:
            enabled: True to enable auto-scroll, False to disable
        """
        self.auto_scroll = enabled

    def get_text(self) -> str:
        """
        Get all text from the output view.

        Returns:
            Complete text content
        """
        return self.text_widget.get("1.0", "end-1c")

    def save_to_file(self, filepath: str):
        """
        Save the output to a file.

        Args:
            filepath: Path to save the file
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.get_text())
            return True
        except IOError as e:
            print(f"Error saving output: {e}")
            return False

    def append_thinking(self, text: str):
        """Append text in Thinking block style."""
        self.current_block = BlockType.THINKING
        self.append_text(f"\n{self.THINKING_PATTERN}\n{text}\n", auto_detect_block=False)

    def append_running(self, text: str):
        """Append text in Running block style."""
        self.current_block = BlockType.RUNNING
        self.append_text(f"\n{self.RUNNING_PATTERN}\n{text}\n", auto_detect_block=False)

    def append_coding(self, text: str):
        """Append text in Coding block style."""
        self.current_block = BlockType.CODING
        self.append_text(f"\n{self.CODING_PATTERN}\n{text}\n", auto_detect_block=False)

    def append_complete(self, text: str):
        """Append text in Complete block style."""
        self.current_block = BlockType.COMPLETE
        self.append_text(f"\n{self.COMPLETE_PATTERN}\n{text}\n", auto_detect_block=False)

    def append_expandable_section(
        self,
        title: str,
        text: str,
        content_tag: str = "assistant_message",
        *,
        collapsed: bool = False,
    ) -> str:
        """Append a clickable section whose body can be collapsed or expanded."""
        if not text:
            return ""
        should_follow = self._is_scrolled_to_bottom()
        self._section_counter += 1
        section_id = f"section_{self._section_counter}"
        header_tag = f"{section_id}_header"
        body_tag = f"{section_id}_body"
        header_text = f"{'[+]' if collapsed else '[-]'} {title}\n"

        self.text_widget.configure(state="normal")
        header_start = self.text_widget.index("end-1c")
        self.text_widget.insert("end", "\n" + header_text, ("collapsible_header", header_tag))
        body_start = self.text_widget.index("end-1c")
        body_text = text if text.endswith("\n") else f"{text}\n"
        self.text_widget.insert("end", body_text, (body_tag, content_tag))
        body_end = self.text_widget.index("end-1c")
        if collapsed:
            self.text_widget.tag_config(body_tag, elide=True)
        self.text_widget.tag_bind(header_tag, "<Button-1>", lambda _event, sid=section_id: self.toggle_expandable_section(sid))
        self.collapsed_sections[section_id] = {
            "header_start": header_start,
            "body_tag": body_tag,
            "title": title,
            "collapsed": collapsed,
            "body_start": body_start,
            "body_end": body_end,
        }
        self.text_widget.configure(state="disabled")
        self._visible_chars += len(header_text) + len(body_text)
        self._prune_if_needed()
        if self.auto_scroll and should_follow:
            self.scroll_to_bottom()
        return section_id

    def toggle_expandable_section(self, section_id: str) -> None:
        """Toggle a section created by append_expandable_section."""
        section = self.collapsed_sections.get(section_id)
        if not section:
            return
        collapsed = not bool(section["collapsed"])
        section["collapsed"] = collapsed
        header_start = str(section["header_start"])
        self.text_widget.configure(state="normal")
        self.text_widget.delete(header_start, f"{header_start} lineend")
        self.text_widget.insert(header_start, f"{'[+]' if collapsed else '[-]'} {section['title']}")
        self.text_widget.tag_config(str(section["body_tag"]), elide=collapsed)
        self.text_widget.configure(state="disabled")

    def _toggle_section(self, event):
        """Toggle collapse/expand of a section when clicking its header."""
        try:
            # Get the index of the clicked text
            index = self.text_widget.index(f"@{event.x},{event.y}")
            line_num = int(index.split('.')[0])

            # Get the line text to identify the section
            line_start = f"{line_num}.0"
            line_end = f"{line_num}.end"
            header_text = self.text_widget.get(line_start, line_end).strip()

            # Identify section type
            section_name = None
            if "Thinking" in header_text or "thinking" in header_text.lower():
                section_name = f"thinking_{line_num}"
            elif "Reasoning" in header_text or "reasoning" in header_text.lower():
                section_name = f"reasoning_{line_num}"
            elif "Coding" in header_text or "coding" in header_text.lower():
                section_name = f"coding_{line_num}"

            if not section_name:
                return

            # Toggle collapsed state
            if section_name in self.collapsed_sections:
                # Expand the section
                start_idx, end_idx, _ = self.collapsed_sections[section_name]
                self.text_widget.configure(state="normal")

                # Change header text to show it's expanded
                self.text_widget.delete(line_start, line_end)
                self.text_widget.insert(line_start, header_text.replace("[+]", "[-]"))

                # Show the section content by removing the elision tag
                self.text_widget.tag_remove("collapsed", f"{line_num+1}.0", end_idx)

                self.text_widget.configure(state="disabled")
                del self.collapsed_sections[section_name]
            else:
                # Collapse the section
                self.text_widget.configure(state="normal")

                # Find the end of this section (next header or end of text)
                current_line = line_num + 1
                max_line = int(self.text_widget.index("end-1c").split('.')[0])
                end_line = current_line

                while end_line < max_line:
                    next_text = self.text_widget.get(f"{end_line}.0", f"{end_line}.end").strip()
                    if any(pattern in next_text for pattern in ["━━━", "You", "SAGE", "Claude", "Codex"]):
                        break
                    end_line += 1

                start_idx = f"{current_line}.0"
                end_idx = f"{end_line}.0"

                # Change header text to show it's collapsed
                self.text_widget.delete(line_start, line_end)
                collapsed_header = header_text.replace("[-]", "[+]") if "[-]" in header_text else f"[+] {header_text}"
                self.text_widget.insert(line_start, collapsed_header)

                # Hide the section content using elision tag
                self.text_widget.tag_add("collapsed", start_idx, end_idx)
                self.text_widget.tag_config("collapsed", elide=True)

                self.text_widget.configure(state="disabled")
                self.collapsed_sections[section_name] = (start_idx, end_idx, True)

        except Exception as e:
            print(f"[ERROR] Toggle section failed: {e}")
            self.text_widget.configure(state="disabled")
