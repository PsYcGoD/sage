"""
AI Selector Widget for SAGE Desktop GUI.

Provides a dropdown to select between Claude, Codex, GPT-4, Gemini, and Custom AI.
"""

import customtkinter as ctk
from typing import Callable, Optional


class AISelector(ctk.CTkFrame):
    """AI selection dropdown widget."""

    AI_OPTIONS = ["Claude", "Bedrock", "Codex", "Ollama", "Gemini"]

    def __init__(
        self,
        parent,
        default_ai: str = "Claude",
        callback: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        """
        Initialize AI selector widget.

        Args:
            parent: Parent widget
            default_ai: Default AI to select (default: "Claude")
            callback: Function to call when AI selection changes
            **kwargs: Additional arguments for CTkFrame
        """
        super().__init__(parent, **kwargs)

        # Store callback
        self.callback = callback

        # Create label
        self.label = ctk.CTkLabel(
            self,
            text="AI:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.label.pack(side="left", padx=(0, 10))

        # Create dropdown
        self.dropdown = ctk.CTkComboBox(
            self,
            values=self.AI_OPTIONS,
            command=self._on_selection_changed,
            width=150,
            state="readonly"
        )
        self.dropdown.set(default_ai)
        self.dropdown.pack(side="left")

    def _on_selection_changed(self, choice: str):
        """Handle AI selection change."""
        if self.callback:
            # Convert display name to internal format (lowercase)
            ai_key = choice.lower().replace("-", "")
            self.callback(ai_key)

    def get_selected_ai(self) -> str:
        """
        Get the currently selected AI.

        Returns:
            Selected AI in internal format (e.g., "claude", "gpt4")
        """
        choice = self.dropdown.get()
        return choice.lower().replace("-", "")

    def set_selected_ai(self, ai: str):
        """
        Set the selected AI.

        Args:
            ai: AI to select (internal format like "claude" or "gpt4")
        """
        # Convert internal format to display format
        ai_map = {
            "claude": "Claude",
            "bedrock": "Bedrock",
            "codex": "Codex",
            "ollama": "Ollama",
            "gemini": "Gemini"
        }
        display_name = ai_map.get(ai.lower(), "Claude")
        self.dropdown.set(display_name)

    def set_callback(self, callback: Callable[[str], None]):
        """
        Set or update the callback function.

        Args:
            callback: Function to call when AI selection changes
        """
        self.callback = callback
