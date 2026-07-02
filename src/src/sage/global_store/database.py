"""Global database for cross-project pattern sharing."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


def global_db_path() -> Path:
    """Get global database path."""
    from ..store import data_dir
    return data_dir() / "global.db"


class GlobalDatabase:
    """Manage global cross-project pattern database."""

    def __init__(self):
        self.db_path = global_db_path()
        self._ensure_schema()

    def _ensure_schema(self):
        """Create global database schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS global_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    error_hash TEXT UNIQUE NOT NULL,
                    error_pattern TEXT NOT NULL,
                    language TEXT,
                    fix_templates TEXT NOT NULL,
                    occurrences INTEGER DEFAULT 1,
                    success_count INTEGER DEFAULT 0,
                    last_seen TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def add_pattern(
        self,
        error_pattern: str,
        language: str,
        fix_template: str,
        success: bool = False,
    ):
        """Add or update a global pattern."""
        # Anonymize the error pattern (remove file paths, line numbers)
        anonymous_pattern = self._anonymize(error_pattern)
        error_hash = hashlib.sha256(anonymous_pattern.encode()).hexdigest()[:16]

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Check if pattern exists
            existing = conn.execute(
                "SELECT id, fix_templates, occurrences, success_count FROM global_patterns WHERE error_hash = ?",
                (error_hash,)
            ).fetchone()

            if existing:
                # Update existing
                fixes = json.loads(existing['fix_templates'])
                if fix_template not in fixes:
                    fixes.append(fix_template)

                new_occurrences = existing['occurrences'] + 1
                new_success = existing['success_count'] + (1 if success else 0)

                conn.execute(
                    """
                    UPDATE global_patterns
                    SET fix_templates = ?, occurrences = ?, success_count = ?, last_seen = ?
                    WHERE error_hash = ?
                    """,
                    (json.dumps(fixes), new_occurrences, new_success, now, error_hash)
                )
            else:
                # Insert new
                conn.execute(
                    """
                    INSERT INTO global_patterns
                    (error_hash, error_pattern, language, fix_templates, occurrences, success_count, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        error_hash,
                        anonymous_pattern,
                        language,
                        json.dumps([fix_template]),
                        1,
                        1 if success else 0,
                        now
                    )
                )
            conn.commit()

    def find_similar(self, error_pattern: str, language: str) -> Optional[Dict]:
        """Find similar error patterns globally."""
        anonymous_pattern = self._anonymize(error_pattern)
        error_hash = hashlib.sha256(anonymous_pattern.encode()).hexdigest()[:16]

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            row = conn.execute(
                """
                SELECT error_pattern, fix_templates, occurrences, success_count
                FROM global_patterns
                WHERE error_hash = ? OR (language = ? AND error_pattern LIKE ?)
                ORDER BY occurrences DESC
                LIMIT 1
                """,
                (error_hash, language, f"%{anonymous_pattern[:50]}%")
            ).fetchone()

            if row:
                fixes = json.loads(row['fix_templates'])
                success_rate = row['success_count'] / row['occurrences'] if row['occurrences'] > 0 else 0.0

                return {
                    'error_pattern': row['error_pattern'],
                    'fix_templates': fixes,
                    'occurrences': row['occurrences'],
                    'success_rate': success_rate,
                }

        return None

    def _anonymize(self, text: str) -> str:
        """Anonymize error pattern by removing file paths and line numbers."""
        import re
        
        # Remove file paths
        text = re.sub(r'[/\\][\w/\\.-]+\.py', '/path/to/file.py', text)
        text = re.sub(r'[/\\][\w/\\.-]+\.js', '/path/to/file.js', text)
        
        # Remove line numbers
        text = re.sub(r'line \d+', 'line N', text)
        text = re.sub(r':\d+:', ':N:', text)
        
        # Remove usernames/directories
        text = re.sub(r'[/\\]Users[/\\]\w+', '/Users/user', text)
        text = re.sub(r'[/\\]home[/\\]\w+', '/home/user', text)
        text = re.sub(r'C:\\Users\\\w+', 'C:\\Users\\user', text)
        
        return text

    def get_stats(self) -> Dict:
        """Get global database statistics."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            stats = conn.execute(
                """
                SELECT 
                    COUNT(*) as total_patterns,
                    SUM(occurrences) as total_occurrences,
                    SUM(success_count) as total_successes
                FROM global_patterns
                """
            ).fetchone()

            return {
                'total_patterns': stats['total_patterns'] or 0,
                'total_occurrences': stats['total_occurrences'] or 0,
                'total_successes': stats['total_successes'] or 0,
            }
