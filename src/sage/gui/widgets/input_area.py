"""
Input Area Widget for SAGE Desktop GUI.

Provides a multi-line text input with Send, Clear, and Settings buttons.
Supports keyboard shortcuts: Ctrl+Enter to send, Shift+Enter for newline.
"""

import customtkinter as ctk
from typing import Callable, Optional


class InputArea(ctk.CTkFrame):
    """Multi-line text input area with control buttons."""

    def __init__(
        self,
        parent,
        on_send: Optional[Callable[[str], None]] = None,
        on_clear: Optional[Callable[[], None]] = None,
        on_settings: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        """
        Initialize input area widget.

        Args:
            parent: Parent widget
            on_send: Callback when Send button is clicked or Ctrl+Enter pressed
            on_clear: Callback when Clear button is clicked
            on_settings: Callback when Settings button is clicked
            **kwargs: Additional arguments for CTkFrame
        """
        super().__init__(parent, **kwargs)

        # Store callbacks
        self.on_send = on_send
        self.on_clear = on_clear
        self.on_settings = on_settings

        # Create text input area
        self.text_input = ctk.CTkTextbox(
            self,
            height=100,
            wrap="word",
            font=ctk.CTkFont(size=13)
        )
        self.text_input.grid(row=0, column=0, columnspan=4, padx=5, pady=5, sticky="ew")

        # Bind keyboard shortcuts
        self.text_input.bind("<Control-Return>", self._on_send_shortcut)
        self.text_input.bind("<Shift-Return>", self._on_newline_shortcut)

        # Create button frame for alignment
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=1, column=0, columnspan=4, padx=5, pady=(0, 5), sticky="e")

        # Create Send button
        self.send_button = ctk.CTkButton(
            button_frame,
            text="Send",
            command=self._on_send_clicked,
            width=80,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.send_button.pack(side="right", padx=5)

        # Create Clear button
        self.clear_button = ctk.CTkButton(
            button_frame,
            text="Clear",
            command=self._on_clear_clicked,
            width=80,
            fg_color="gray40",
            hover_color="gray30"
        )
        self.clear_button.pack(side="right", padx=5)

        # Create Settings button
        self.settings_button = ctk.CTkButton(
            button_frame,
            text="⚙",
            command=self._on_settings_clicked,
            width=40,
            font=ctk.CTkFont(size=16)
        )
        self.settings_button.pack(side="right", padx=5)

        # Configure grid weights
        self.grid_columnconfigure(0, weight=1)

        # Add placeholder text
        self._add_placeholder()

    def _add_placeholder(self):
        """Add placeholder text to the input area."""
        if not self.get_text():
            self.text_input.insert("1.0", "Type your command or prompt...")
            self.text_input.configure(text_color="gray50")
            self.text_input.bind("<FocusIn>", self._on_focus_in)

    def _on_focus_in(self, event):
        """Clear placeholder text when focused."""
        if self.get_text() == "Type your command or prompt...":
            self.text_input.delete("1.0", "end")
            self.text_input.configure(text_color=("gray10", "gray90"))
        self.text_input.unbind("<FocusIn>")
        self.text_input.bind("<FocusOut>", self._on_focus_out)

    def _on_focus_out(self, event):
        """Restore placeholder if empty."""
        if not self.get_text():
            self._add_placeholder()

    def _on_send_shortcut(self, event):
        """Handle Ctrl+Enter shortcut."""
        self._on_send_clicked()
        return "break"  # Prevent default behavior

    def _on_newline_shortcut(self, event):
        """Handle Shift+Enter shortcut."""
        # Allow default behavior (insert newline)
        return None

    def _on_send_clicked(self):
        """Handle Send button click."""
        text = self.get_text()
        if text and text != "Type your command or prompt...":
            if self.on_send:
                self.on_send(text)

    def _on_clear_clicked(self):
        """Handle Clear button click."""
        self.clear()
        if self.on_clear:
            self.on_clear()

    def _on_settings_clicked(self):
        """Handle Settings button click."""
        if self.on_settings:
            self.on_settings()

    def get_text(self) -> str:
        """
        Get the current text from the input area.

        Returns:
            Text content (stripped of trailing whitespace)
        """
        text = self.text_input.get("1.0", "end-1c")
        return text.strip()

    def set_text(self, text: str):
        """
        Set the text in the input area.

        Args:
            text: Text to set
        """
        self.text_input.delete("1.0", "end")
        self.text_input.insert("1.0", text)
        self.text_input.configure(text_color=("gray10", "gray90"))

    def clear(self):
        """Clear the input area."""
        self.text_input.delete("1.0", "end")
        self._add_placeholder()

    def set_enabled(self, enabled: bool):
        """
        Enable or disable the input area and buttons.

        Args:
            enabled: True to enable, False to disable
        """
        state = "normal" if enabled else "disabled"
        self.text_input.configure(state=state)
        self.send_button.configure(state=state)
        self.clear_button.configure(state=state)

    def focus(self):
        """Set focus to the text input area."""
        self.text_input.focus()
