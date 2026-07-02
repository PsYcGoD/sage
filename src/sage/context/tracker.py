"""Token usage tracking."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ..store import connect


class TokenTracker:
    """Track token usage across commands."""

    def __init__(self):
        self._ensure_table()

    def _ensure_table(self):
        """Ensure token tracking table exists."""
        with connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS token_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    estimated_tokens INTEGER,
                    compressed_tokens INTEGER,
                    savings INTEGER,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES runs(id)
                )
                """
            )
            conn.commit()

    def record_usage(
        self,
        run_id: int,
        estimated_tokens: int,
        compressed_tokens: int,
    ) -> None:
        """Record token usage for a command."""
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        savings = estimated_tokens - compressed_tokens

        with connect() as conn:
            conn.execute(
                """
                INSERT INTO token_usage
                (run_id, estimated_tokens, compressed_tokens, savings, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (run_id, estimated_tokens, compressed_tokens, savings, now)
            )
            conn.commit()

    def get_stats(self) -> dict:
        """Get token usage statistics."""
        with connect() as conn:
            result = conn.execute(
                """
                SELECT 
                    COUNT(*) as total_commands,
                    SUM(estimated_tokens) as total_estimated,
                    SUM(compressed_tokens) as total_compressed,
                    SUM(savings) as total_savings
                FROM token_usage
                """
            ).fetchone()

            if result and result['total_commands']:
                total_est = result['total_estimated'] or 0
                total_comp = result['total_compressed'] or 0
                total_sav = result['total_savings'] or 0

                return {
                    'total_commands': result['total_commands'],
                    'total_estimated': total_est,
                    'total_compressed': total_comp,
                    'total_savings': total_sav,
                    'savings_percent': (total_sav / total_est * 100) if total_est > 0 else 0,
                }

        return {
            'total_commands': 0,
            'total_estimated': 0,
            'total_compressed': 0,
            'total_savings': 0,
            'savings_percent': 0,
        }

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count.
        
        Rough estimation: ~4 chars per token for English.
        """
        if not text:
            return 0
        
        # Simple estimation
        # More accurate: use tiktoken library
        return len(text) // 4
