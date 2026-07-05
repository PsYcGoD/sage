"""Chat session management for SAGE GUI - multi-session architecture."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SessionManager:
    """Manages multiple chat sessions per project."""

    def __init__(self, sessions_path: str | Path | None = None):
        self.sessions_path = Path(sessions_path) if sessions_path else Path.home() / ".sage" / "sessions.json"
        self.sessions_path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, list[dict]] = {}
        self._load()

    def _load(self):
        """Load sessions from disk."""
        if not self.sessions_path.exists():
            self._data = {}
            return
        try:
            raw = json.loads(self.sessions_path.read_text(encoding="utf-8"))
            self._data = raw if isinstance(raw, dict) else {}
        except (json.JSONDecodeError, OSError):
            self._data = {}

    def _save(self):
        """Persist sessions to disk."""
        try:
            self.sessions_path.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except OSError:
            pass

    def _normalize_path(self, project_path: str) -> str:
        """Normalize project path for cross-platform consistency."""
        return os.path.normcase(os.path.abspath(project_path))

    def create_session(self, project_path: str, title: str = "New Chat") -> str:
        """Create new session and return session ID."""
        project_key = self._normalize_path(project_path)
        session_id = str(uuid.uuid4())[:8]  # Short ID

        session = {
            "id": session_id,
            "title": title,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "messages": [],
            "pinned": False,
            "unread": False,
        }

        if project_key not in self._data:
            self._data[project_key] = []

        self._data[project_key].insert(0, session)  # Newest first
        self._save()
        return session_id

    def get_session(self, project_path: str, session_id: str) -> dict | None:
        """Get specific session by ID."""
        project_key = self._normalize_path(project_path)
        sessions = self._data.get(project_key, [])
        for session in sessions:
            if session.get("id") == session_id:
                return session
        return None

    def get_sessions(self, project_path: str) -> list[dict]:
        """Get all sessions for a project (newest first)."""
        project_key = self._normalize_path(project_path)
        return self._data.get(project_key, [])

    def get_all_projects(self) -> list[dict]:
        """Get all projects with their sessions for sidebar."""
        projects = []
        for project_path, sessions in self._data.items():
            if sessions:  # Only show projects with sessions
                projects.append({
                    "path": project_path,
                    "name": Path(project_path).name or project_path,
                    "sessions": sessions,
                    "session_count": len(sessions)
                })
        # Sort by most recent session update
        projects.sort(key=lambda p: max(
            (s.get("updated_at", "") for s in p["sessions"]),
            default=""
        ), reverse=True)
        return projects

    def add_message(self, project_path: str, session_id: str, role: str, text: str):
        """Add message to session."""
        session = self.get_session(project_path, session_id)
        if not session:
            return

        # FIXED: Keep FULL messages, don't truncate
        # Only truncate EXTREME cases (>20KB)
        if len(text) > 20000:
            text = text[:9500] + "\n[...content truncated...]\n" + text[-9500:]

        session["messages"].append({"role": role, "text": text})
        # FIXED: Store last 100 messages instead of 40
        session["messages"] = session["messages"][-100:]
        session["updated_at"] = datetime.now(timezone.utc).isoformat()
        session["unread"] = False  # Mark as read when adding message

        # FIXED: Better auto-title - keep full title (don't truncate to 50 chars)
        if not session.get("title") or session["title"] == "New Chat":
            user_messages = [m for m in session["messages"] if m.get("role") == "user"]
            if user_messages:
                first_msg = user_messages[0].get("text", "").strip()
                if first_msg:
                    # Keep first 100 chars for title (was 50)
                    session["title"] = first_msg[:100]

        self._save()

    def get_messages(self, project_path: str, session_id: str) -> list[dict]:
        """Get all messages for a session."""
        session = self.get_session(project_path, session_id)
        return session.get("messages", []) if session else []

    def delete_session(self, project_path: str, session_id: str):
        """Delete a session."""
        project_key = self._normalize_path(project_path)
        if project_key in self._data:
            self._data[project_key] = [
                s for s in self._data[project_key]
                if s.get("id") != session_id
            ]
            self._save()

    def rename_session(self, project_path: str, session_id: str, new_title: str):
        """Rename a session."""
        session = self.get_session(project_path, session_id)
        if session:
            session["title"] = new_title
            session["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._save()

    def pin_session(self, project_path: str, session_id: str, pinned: bool = True):
        """Pin/unpin a session."""
        session = self.get_session(project_path, session_id)
        if session:
            session["pinned"] = pinned
            self._save()

    def mark_unread(self, project_path: str, session_id: str, unread: bool = True):
        """Mark session as read/unread."""
        session = self.get_session(project_path, session_id)
        if session:
            session["unread"] = unread
            self._save()

    def get_or_create_session(self, project_path: str) -> str:
        """Get most recent session or create new one if none exist."""
        sessions = self.get_sessions(project_path)
        if sessions:
            return sessions[0]["id"]  # Most recent
        return self.create_session(project_path)
