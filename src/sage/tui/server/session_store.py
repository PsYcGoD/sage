"""Session storage for the chat server."""
from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sage.store import connect
from .models import Session, Message, ToolCall


class SessionStore:
    """CRUD for sessions and messages using the existing sage.db."""

    def __init__(self):
        self._ensure_tables()

    def _ensure_tables(self):
        """Create chat tables if they don't exist."""
        conn = connect()
        try:
            # Sessions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    model TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Messages table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tool_calls TEXT DEFAULT '[]',
                    tokens_in INTEGER DEFAULT 0,
                    tokens_out INTEGER DEFAULT 0,
                    cost REAL DEFAULT 0.0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
                )
            """)

            # Tool calls table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_tool_calls (
                    id TEXT PRIMARY KEY,
                    message_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    input_json TEXT NOT NULL,
                    output_json TEXT NOT NULL,
                    duration_ms INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    FOREIGN KEY (message_id) REFERENCES chat_messages(id) ON DELETE CASCADE
                )
            """)

            # Index for faster lookups
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session 
                ON chat_messages(session_id, created_at)
            """)

            conn.commit()
        finally:
            conn.close()

    def create_session(self, model: str, agent: str, title: str = "New Chat") -> Session:
        """Create a new chat session."""
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        conn = connect()
        try:
            conn.execute(
                """
                INSERT INTO chat_sessions (id, title, model, agent, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, title, model, agent, now, now),
            )
            conn.commit()
        finally:
            conn.close()

        return Session(
            id=session_id,
            title=title,
            model=model,
            agent=agent,
            created_at=now,
            updated_at=now,
        )

    def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID."""
        conn = connect()
        try:
            row = conn.execute(
                "SELECT * FROM chat_sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if not row:
                return None
            return Session(
                id=row["id"],
                title=row["title"],
                model=row["model"],
                agent=row["agent"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        finally:
            conn.close()

    def list_sessions(self, limit: int = 50) -> list[Session]:
        """List recent sessions."""
        conn = connect()
        try:
            rows = conn.execute(
                "SELECT * FROM chat_sessions ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [
                Session(
                    id=row["id"],
                    title=row["title"],
                    model=row["model"],
                    agent=row["agent"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]
        finally:
            conn.close()

    def delete_session(self, session_id: str):
        """Delete a session and all its messages."""
        conn = connect()
        try:
            conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            conn.commit()
        finally:
            conn.close()

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_calls: list[dict[str, Any]] | None = None,
        tokens_in: int = 0,
        tokens_out: int = 0,
        cost: float = 0.0,
    ) -> Message:
        """Add a message to a session."""
        message_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        tool_calls_json = json.dumps(tool_calls or [])

        conn = connect()
        try:
            conn.execute(
                """
                INSERT INTO chat_messages 
                (id, session_id, role, content, tool_calls, tokens_in, tokens_out, cost, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    session_id,
                    role,
                    content,
                    tool_calls_json,
                    tokens_in,
                    tokens_out,
                    cost,
                    now,
                ),
            )

            # Update session updated_at
            conn.execute(
                "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
                (now, session_id),
            )

            conn.commit()
        finally:
            conn.close()

        return Message(
            id=message_id,
            session_id=session_id,
            role=role,
            content=content,
            tool_calls=tool_calls or [],
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost=cost,
            created_at=now,
        )

    def get_messages(self, session_id: str) -> list[Message]:
        """Get all messages for a session."""
        conn = connect()
        try:
            rows = conn.execute(
                "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY created_at ASC",
                (session_id,),
            ).fetchall()
            return [
                Message(
                    id=row["id"],
                    session_id=row["session_id"],
                    role=row["role"],
                    content=row["content"],
                    tool_calls=json.loads(row["tool_calls"]),
                    tokens_in=row["tokens_in"],
                    tokens_out=row["tokens_out"],
                    cost=row["cost"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]
        finally:
            conn.close()

    def update_session_title(self, session_id: str, title: str):
        """Update a session's title."""
        now = datetime.now(timezone.utc).isoformat()
        conn = connect()
        try:
            conn.execute(
                "UPDATE chat_sessions SET title = ?, updated_at = ? WHERE id = ?",
                (title, now, session_id),
            )
            conn.commit()
        finally:
            conn.close()
