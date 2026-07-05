import sqlite3

from sage.gui.app import SAGEApp


def test_gui_context_token_totals_match_context_stats_source():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE token_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            estimated_tokens INTEGER,
            compressed_tokens INTEGER,
            savings INTEGER,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.executemany(
        """
        INSERT INTO token_usage
        (run_id, estimated_tokens, compressed_tokens, savings, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (1, 1000, 120, 880, "2026-07-05T00:00:00+00:00"),
            (2, 2500, 400, 2100, "2026-07-05T00:01:00+00:00"),
        ],
    )

    totals = SAGEApp._fetch_context_token_totals(object(), conn)

    assert tuple(totals) == (3500, 520, 2980)


def test_gui_context_token_totals_are_zero_when_table_missing():
    conn = sqlite3.connect(":memory:")

    assert SAGEApp._fetch_context_token_totals(object(), conn) == (0, 0, 0)
