"""Input bar widget for SAGE TUI."""

from textual.widgets import TextArea
from textual.message import Message


class InputSubmitted(Message):
    """Message posted when user submits input."""

    def __init__(self, text: str) -> None:
        super().__init__()
        self.text = text


class InputBar(TextArea):
    """Multi-line input bar with submission on Enter."""

    DEFAULT_CSS = """"""

    def __init__(self) -> None:
        super().__init__(
            text="",
            language="markdown",
            theme="monokai",
            show_line_numbers=False,
        )
        self.placeholder = "Type a message... (Enter to send, Shift+Enter for newline, Escape to clear)"
        self._history: list[str] = []
        self._history_index: int = -1
        self._current_draft: str = ""

    def on_mount(self) -> None:
        """Set placeholder after mount."""
        # Textual TextArea doesn't have built-in placeholder support in all versions
        # We'll show it in the border title instead
        self.border_title = "Message"

    def _on_key(self, event) -> None:
        """Handle key events."""
        # Don't allow input if disabled
        if self.read_only:
            return
        
        # Check for Enter without Shift (in Textual, shift+enter is a separate key name)
        if event.key == "enter":
            event.prevent_default()
            event.stop()
            text = self.text.strip()
            if text:
                # Add to history
                self._history.append(text)
                self._history_index = len(self._history)
                self._current_draft = ""
                
                self.post_message(InputSubmitted(text))
                self.clear()
        # Escape clears input
        elif event.key == "escape":
            event.prevent_default()
            event.stop()
            self.clear()
            self._history_index = len(self._history)
            self._current_draft = ""
        # Up arrow - navigate history backwards
        elif event.key == "up":
            cursor = self.cursor_location
            if cursor[0] == 0 and self._history:  # At first line
                event.prevent_default()
                event.stop()
                
                # Save current draft if at end of history
                if self._history_index == len(self._history):
                    self._current_draft = self.text
                
                # Navigate backwards
                if self._history_index > 0:
                    self._history_index -= 1
                    self.text = self._history[self._history_index]
        # Down arrow - navigate history forwards
        elif event.key == "down":
            cursor = self.cursor_location
            line_count = len(self.text.split('\n'))
            if cursor[0] == line_count - 1 and self._history:  # At last line
                event.prevent_default()
                event.stop()
                
                # Navigate forwards
                if self._history_index < len(self._history):
                    self._history_index += 1
                    
                    if self._history_index == len(self._history):
                        # Restore draft
                        self.text = self._current_draft
                    else:
                        self.text = self._history[self._history_index]

    async def action_submit(self) -> None:
        """Submit the current input."""
        if self.read_only:
            return
        
        text = self.text.strip()
        if text:
            # Add to history
            self._history.append(text)
            self._history_index = len(self._history)
            self._current_draft = ""
            
            self.post_message(InputSubmitted(text))
            self.clear()

    def disable(self) -> None:
        """Disable input (during response processing)."""
        self.read_only = True
        self.add_class("disabled")

    def enable(self) -> None:
        """Enable input (after response completes)."""
        self.read_only = False
        self.remove_class("disabled")
