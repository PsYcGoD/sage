"""Sidebar widget for session management."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Static, Button, ListView, ListItem, Label
from textual.message import Message
from textual.binding import Binding


class SessionSelected(Message):
    """Posted when a session is selected."""

    def __init__(self, session_id: str) -> None:
        super().__init__()
        self.session_id = session_id


class NewSessionRequested(Message):
    """Posted when the user requests a new session."""


class SessionDeleteRequested(Message):
    """Posted when the user requests to delete a session."""

    def __init__(self, session_id: str) -> None:
        super().__init__()
        self.session_id = session_id


class SettingsRequested(Message):
    """Posted when user clicks settings."""


class Sidebar(Container):
    """Sidebar panel for session management."""

    DEFAULT_CSS = """"""

    BINDINGS = [
        Binding("delete", "delete_session", "Delete Session", show=False),
    ]

    def __init__(self, project_name: str = "SAGE") -> None:
        super().__init__()
        self.project_name = project_name
        self._sessions: list[dict] = []
        self._active_session_id: str | None = None

    def compose(self) -> ComposeResult:
        """Compose the sidebar layout."""
        with Vertical():
            yield Static(f"⚡ {self.project_name}", classes="header")
            yield Button("+ New Chat", id="new-chat-btn")
            yield ListView(id="session-list")
            yield Button("⚙ Settings", id="settings-btn")

    def set_sessions(self, sessions: list[dict], active_session_id: str | None = None):
        """Update the session list.
        
        Args:
            sessions: List of session dicts with keys: id, title, updated_at, preview
            active_session_id: ID of the currently active session
        """
        self._sessions = sessions
        self._active_session_id = active_session_id
        self._refresh_list()

    def set_active_session(self, session_id: str):
        """Mark a session as active."""
        self._active_session_id = session_id
        self._refresh_list()

    def _refresh_list(self):
        """Refresh the session list view."""
        list_view = self.query_one("#session-list", ListView)

        # Remove all existing children
        for child in list(list_view.children):
            child.remove()

        if not self._sessions:
            list_view.mount(Static("No sessions yet.\nClick 'New Chat' to start!", classes="empty-state"))
            return

        for session in self._sessions:
            session_id = session["id"]
            title = session.get("title", "Untitled Chat")[:40]
            date = session.get("updated_at", "")
            date_short = date.split("T")[0] if "T" in date else date

            label_text = f"[b]{title}[/b]\n[dim]{date_short}[/dim]"

            item = ListItem(Label(label_text, markup=True))
            item.session_id = session_id

            if session_id == self._active_session_id:
                item.add_class("--active")

            list_view.mount(item)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "new-chat-btn":
            self.post_message(NewSessionRequested())
        elif event.button.id == "settings-btn":
            self.post_message(SettingsRequested())

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle session selection."""
        session_id = getattr(event.item, "session_id", None)
        if session_id:
            self.post_message(SessionSelected(session_id))

    def action_delete_session(self) -> None:
        """Delete the currently selected session."""
        list_view = self.query_one("#session-list", ListView)
        if list_view.index is not None and list_view.highlighted_child:
            session_id = getattr(list_view.highlighted_child, "session_id", None)
            if session_id:
                self.post_message(SessionDeleteRequested(session_id))
