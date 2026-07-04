from __future__ import annotations

import sys

from sage.runner import run_command
from sage.security import evaluate_command, redact_text
from sage.store import connect


def test_redact_text_common_tokens():
    text = "token=ghp_abcdefghijklmnopqrstuvwxyz123456 and key sk-test_abcdefghijklmnopqrstuvwxyz"
    result = redact_text(text, strictness="standard")

    assert result.count >= 1
    assert "ghp_" not in result.text
    assert "[REDACTED:" in result.text


def test_policy_blocks_denylisted_command(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    decision = evaluate_command("git reset --hard", mode="company")

    assert decision.decision == "blocked"
    assert decision.risky is True


def test_policy_does_not_block_output_format_flag(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    decision = evaluate_command("claude --print --output-format stream-json", mode="personal")
    assert decision.decision == "allowed"

    blocked = evaluate_command("format D:", mode="personal")
    assert blocked.decision == "blocked"


def test_run_command_dry_run_does_not_store(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    exit_code = run_command([sys.executable, "-c", "print('should-not-run')"], dry_run=True)

    assert exit_code == 0
    with connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 0


def test_run_command_redacts_before_storage(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    secret = "ghp_abcdefghijklmnopqrstuvwxyz123456"

    exit_code = run_command([sys.executable, "-c", f"print('{secret}')"])

    assert exit_code == 0
    with connect() as conn:
        row = conn.execute("SELECT stdout, stdout_redactions, command_sha256 FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    assert secret not in row["stdout"]
    assert row["stdout_redactions"] >= 1
    assert len(row["command_sha256"]) == 64
