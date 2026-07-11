"""Migrate old GUI sessions from ~/.sage/sessions.json to sage.db."""
from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def migrate_if_needed(store):
    """One-time migration from old JSON sessions to SQLite.
    
    Args:
        store: SessionStore instance
    """
    old_path = Path.home() / ".sage" / "sessions.json"
    marker = Path.home() / ".sage" / ".sessions_migrated"
    
    # Skip if already migrated or no old sessions exist
    if marker.exists() or not old_path.exists():
        return
    
    log.info("Migrating old sessions from %s to sage.db", old_path)
    
    try:
        # Read old sessions
        data = json.loads(old_path.read_text(encoding="utf-8"))
        
        migrated_count = 0
        # Import each project's sessions
        for project_path, sessions in data.items():
            if not isinstance(sessions, list):
                continue
                
            for session_data in sessions:
                # Create session
                title = session_data.get("title", "Imported Chat")
                model = session_data.get("model", "claude-sonnet-4.6")
                agent = session_data.get("agent", "coder")
                
                session = store.create_session(
                    model=model,
                    agent=agent,
                    title=title,
                )
                
                # Import messages
                messages = session_data.get("messages", [])
                for msg in messages:
                    role = msg.get("role", "user")
                    text = msg.get("text", msg.get("content", ""))
                    if text:
                        store.add_message(session.id, role, text)
                
                migrated_count += 1
        
        # Mark as migrated
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(f"migrated {migrated_count} sessions")
        
        log.info("Migration complete: %d sessions imported", migrated_count)
        
    except Exception as e:
        log.error("Failed to migrate old sessions: %s", e, exc_info=True)
        # Write marker anyway to avoid repeated failures
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(f"migration failed: {e}")
