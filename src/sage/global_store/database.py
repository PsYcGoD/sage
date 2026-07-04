"""Global database for cross-project pattern sharing."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def global_db_path() -> Path:
    """Get the global intelligence database path."""
    from ..store import data_dir

    return data_dir() / "global.db"


class GlobalDatabase:
    """Manage anonymized cross-project fix patterns."""

    def __init__(self):
        self.db_path = global_db_path()
        self._ensure_schema()

    def add_pattern(
        self,
        error_pattern: str,
        language: str,
        fix_template: str,
        success: bool = False,
    ) -> None:
        """Add or update a global pattern."""
        anonymous_pattern = self._anonymize(error_pattern)
        error_hash = hashlib.sha256(anonymous_pattern.encode("utf-8")).hexdigest()[:16]
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            existing = conn.execute(
                """
                SELECT fix_templates, occurrences, success_count
                FROM global_patterns
                WHERE error_hash = ?
                """,
                (error_hash,),
            ).fetchone()

            if existing:
                fixes = json.loads(existing["fix_templates"])
                if fix_template not in fixes:
                    fixes.append(fix_template)
                conn.execute(
                    """
                    UPDATE global_patterns
                    SET fix_templates = ?, occurrences = ?, success_count = ?, last_seen = ?
                    WHERE error_hash = ?
                    """,
                    (
                        json.dumps(fixes),
                        int(existing["occurrences"]) + 1,
                        int(existing["success_count"]) + (1 if success else 0),
                        now,
                        error_hash,
                    ),
                )
            else:
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
                        now,
                    ),
                )
            conn.commit()

    def find_similar(self, error_pattern: str, language: str) -> dict | None:
        """Find an exact anonymized pattern or a close language-local match."""
        anonymous_pattern = self._anonymize(error_pattern)
        error_hash = hashlib.sha256(anonymous_pattern.encode("utf-8")).hexdigest()[:16]

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
                (error_hash, language, f"%{anonymous_pattern[:50]}%"),
            ).fetchone()

        if not row:
            return None

        occurrences = int(row["occurrences"])
        return {
            "error_pattern": row["error_pattern"],
            "fix_templates": json.loads(row["fix_templates"]),
            "occurrences": occurrences,
            "success_rate": int(row["success_count"]) / occurrences if occurrences else 0.0,
        }

    def get_stats(self) -> dict:
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
            "total_patterns": stats["total_patterns"] or 0,
            "total_occurrences": stats["total_occurrences"] or 0,
            "total_successes": stats["total_successes"] or 0,
        }

    def _ensure_schema(self) -> None:
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

    def _anonymize(self, text: str) -> str:
        """Remove project-local paths and line numbers from an error pattern."""
        text = re.sub(r"[/\\][\w/\\.-]+\.py", "/path/to/file.py", text)
        text = re.sub(r"[/\\][\w/\\.-]+\.js", "/path/to/file.js", text)
        text = re.sub(r"line \d+", "line N", text)
        text = re.sub(r":\d+:", ":N:", text)
        text = re.sub(r"[/\\]Users[/\\]\w+", "/Users/user", text)
        text = re.sub(r"[/\\]home[/\\]\w+", "/home/user", text)
        text = re.sub(r"C:\\Users\\\w+", r"C:\Users\user", text)
        return text
