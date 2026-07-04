"""Sync patterns between local and global databases."""

from __future__ import annotations

from ..store import connect
from .database import GlobalDatabase


def sync_patterns(upload: bool = True, download: bool = True) -> dict:
    """Sync local successful fixes into the global database."""
    global_db = GlobalDatabase()

    if upload:
        with connect() as local_conn:
            rows = local_conn.execute(
                """
                SELECT error_pattern, fix_template, language, times_succeeded
                FROM fixes
                WHERE times_applied > 0
                """
            ).fetchall()

        for row in rows:
            global_db.add_pattern(
                error_pattern=row["error_pattern"],
                language=row["language"] or "",
                fix_template=row["fix_template"],
                success=int(row["times_succeeded"]) > 0,
            )

    # Download can later merge remote/team patterns. For now the global DB is local.
    return global_db.get_stats()
