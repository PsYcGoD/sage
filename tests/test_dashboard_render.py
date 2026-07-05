from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def test_dashboard_root_server_renders_initial_stats(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    from sage.dashboard.server import _render_dashboard_html
    from sage.store import connect, save_run

    run_id = save_run(
        project="dashboard-test",
        command="echo <ok>",
        exit_code=0,
        duration_ms=12,
        stdout="ok",
        stderr="",
        summary="ok",
    )
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO context_compression
              (run_id, created_at, original_tokens, compressed_tokens, saved_tokens, strategy, verified_tokenizer)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (run_id, now, 100, 20, 80, "test", "tiktoken"),
        )
        conn.commit()

    html = _render_dashboard_html(Path("src/sage/dashboard/static/index.html"))

    assert '<div class="stat-value" id="total-commands">1</div>' in html
    assert '<div class="stat-value" id="token-savings">80 tokens</div>' in html
    assert '<div class="stat-value" id="success-rate">100%</div>' in html
    assert "echo &lt;ok&gt;" in html
    assert "Loading commands..." not in html
