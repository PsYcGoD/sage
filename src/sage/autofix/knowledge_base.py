"""Historical fix pattern storage and retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from ..store import connect


@dataclass
class HistoricalFix:
    """A fix pattern from the knowledge base."""
    id: int
    pattern: str
    template: str
    language: str
    success_rate: float
    times_applied: int


class KnowledgeBase:
    """Manages historical fix patterns and their success rates."""

    def find_fix(self, error_pattern: str, language: str) -> Optional[HistoricalFix]:
        """Find a historical fix for this error pattern."""
        with connect() as conn:
            row = conn.execute(
                """
                SELECT id, error_pattern, fix_template, language,
                       success_rate, times_applied
                FROM fixes
                WHERE error_pattern = ? AND language = ?
                ORDER BY success_rate DESC, times_applied DESC
                LIMIT 1
                """,
                (error_pattern, language),
            ).fetchone()

            if row:
                return HistoricalFix(
                    id=row["id"],
                    pattern=row["error_pattern"],
                    template=row["fix_template"],
                    language=row["language"],
                    success_rate=row["success_rate"],
                    times_applied=row["times_applied"],
                )
            return None

    def record_fix_attempt(
        self,
        error_pattern: str,
        fix_template: str,
        language: str,
        success: bool,
    ) -> None:
        """Record a fix attempt to update success rates."""
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")

        with connect() as conn:
            existing = conn.execute(
                """
                SELECT id, times_applied, times_succeeded
                FROM fixes
                WHERE error_pattern = ? AND fix_template = ? AND language = ?
                """,
                (error_pattern, fix_template, language),
            ).fetchone()

            if existing:
                new_applied = existing["times_applied"] + 1
                new_succeeded = existing["times_succeeded"] + (1 if success else 0)
                new_rate = new_succeeded / new_applied if new_applied > 0 else 0.0

                conn.execute(
                    """
                    UPDATE fixes
                    SET times_applied = ?,
                        times_succeeded = ?,
                        success_rate = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (new_applied, new_succeeded, new_rate, now, existing["id"]),
                )
            else:
                initial_rate = 1.0 if success else 0.0
                conn.execute(
                    """
                    INSERT INTO fixes
                    (error_pattern, fix_template, language, confidence,
                     success_rate, times_applied, times_succeeded,
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        error_pattern,
                        fix_template,
                        language,
                        0.8,
                        initial_rate,
                        1,
                        1 if success else 0,
                        now,
                        now,
                    ),
                )
            conn.commit()
