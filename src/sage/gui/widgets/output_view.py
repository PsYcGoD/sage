"""
Output View Widget for SAGE Desktop GUI.

Provides a scrollable text area for displaying AI responses with
streaming support and block detection (Thinking, Running, Coding, Complete).
"""

import customtkinter as ctk
import re
from typing import Optional
from enum import Enum


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

    def __init__(self, parent, **kwargs):
        """
        Initialize output view widget.

        Args:
            parent: Parent widget
            **kwargs: Additional arguments for CTkFrame
        """
        super().__init__(parent, **kwargs)

        # Create text widget with scrollbar
        self.text_widget = ctk.CTkTextbox(
            self,
            wrap="word",
            font=ctk.CTkFont(family="Consolas", size=12),
            state="disabled"
        )
        self.text_widget.pack(fill="both", expand=True, padx=5, pady=5)

        # Configure tags for different block types
        self._configure_tags()

        # Current block type
        self.current_block = BlockType.NORMAL

        # Auto-scroll enabled by default
        self.auto_scroll = True

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

        # Disable editing
        self.text_widget.configure(state="disabled")

    def append_text(self, text: str, auto_detect_block: bool = True):
        """
        Append text to the output view with optional block detection.

        Args:
            text: Text to append
            auto_detect_block: Whether to automatically detect block types
        """
        self.text_widget.configure(state="normal")

        if auto_detect_block:
            # Detect block type from text
            self._detect_and_append_with_blocks(text)
        else:
            # Append without block detection
            tag = self.current_block.value if self.current_block != BlockType.NORMAL else None
            self.text_widget.insert("end", text, tag)

        self.text_widget.configure(state="disabled")

        # Auto-scroll to bottom
        if self.auto_scroll:
            self.scroll_to_bottom()

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
                # Apply current block styling
                tag = self._determine_line_tag(line)
                self.text_widget.insert("end", line + "\n", tag)

    def _determine_line_tag(self, line: str) -> Optional[str]:
        """Determine the appropriate tag for a line of text."""
        # Check for special markers
        if line.strip().startswith("✓") or line.strip().startswith("✅"):
            return "success"
        elif line.strip().startswith("✗") or line.strip().startswith("❌"):
            return "error"
        elif line.strip().startswith("```") or line.strip().startswith("$"):
            return "code"
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

    def scroll_to_bottom(self):
        """Scroll to the bottom of the output view."""
        self.text_widget.see("end")

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
