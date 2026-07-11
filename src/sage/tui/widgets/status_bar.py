"""Status bar widget for SAGE TUI."""

from textual.widgets import Static


class StatusBar(Static):
    """Footer status bar showing model, session, and token info."""

    DEFAULT_CSS = """"""

    def __init__(self) -> None:
        super().__init__()
        self.model = ""
        self.session_name = "New Chat"
        self.tokens = 0
        self.streaming = False
        self.daemon_status = "unknown"
        self._update_display()

    def _update_display(self) -> None:
        """Update the status bar text."""
        parts = ["SAGE TUI"]
        
        # Model
        parts.append(f"Model: {self.model}")
        
        # Session
        parts.append(f"Session: {self.session_name}")
        
        # Tokens
        parts.append(f"Tokens: {self.tokens}")
        
        # Streaming indicator
        if self.streaming:
            parts.append("⟳ Streaming...")
        
        # ML daemon status
        if self.daemon_status == "active":
            parts.append("ML: active")
        elif self.daemon_status == "sleeping":
            parts.append("ML: sleeping")
        elif self.daemon_status == "off":
            parts.append("ML: off")
        
        self.update(" | ".join(parts))

    def set_model(self, model: str) -> None:
        """Update the model name."""
        self.model = model
        self._update_display()

    def set_session(self, session_name: str) -> None:
        """Update the session name."""
        self.session_name = session_name
        self._update_display()

    def set_tokens(self, tokens: int) -> None:
        """Update the token count."""
        self.tokens = tokens
        self._update_display()

    def set_streaming(self, active: bool) -> None:
        """Update the streaming indicator.
        
        Args:
            active: True if currently streaming, False otherwise
        """
        self.streaming = active
        self._update_display()

    def set_daemon_status(self, status: str) -> None:
        """Update the ML daemon status.
        
        Args:
            status: Status string - 'active', 'sleeping', 'off', or 'unknown'
        """
        self.daemon_status = status
        self._update_display()
