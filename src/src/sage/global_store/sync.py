"""Sync patterns between local and global databases."""

from __future__ import annotations

from ..store import connect
from .database import GlobalDatabase


def sync_patterns(upload: bool = True, download: bool = True):
    """
    Sync patterns between local and global databases.
    
    Args:
        upload: Upload local patterns to global DB
        download: Download global patterns to local DB
    """
    global_db = GlobalDatabase()

    if upload:
        # Upload local successful fixes to global
        with connect() as local_conn:
            local_conn.row_factory = None
            fixes = local_conn.execute(
                """
                SELECT error_pattern, fix_template, language,
                       times_succeeded, times_applied
                FROM fixes
                WHERE times_applied > 0
                """
            ).fetchall()

            for fix in fixes:
                error_pattern, fix_template, language, succeeded, applied = fix
                success = succeeded > 0
                
                global_db.add_pattern(
                    error_pattern=error_pattern,
                    language=language,
                    fix_template=fix_template,
                    success=success,
                )

    if download:
        # Download global patterns that don't exist locally
        # (Placeholder for now)
        pass

    return global_db.get_stats()
