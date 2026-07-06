from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone


def _connected_env(tmp_path):
    env = os.environ.copy()
    env["LOCALAPPDATA"] = str(tmp_path)
    sage_dir = tmp_path / "SAGE"
    sage_dir.mkdir(parents=True, exist_ok=True)
    (sage_dir / "telemetry.json").write_text(
        json.dumps(
            {
                "telemetry_level": 0,
                "api_base_url": "https://sage.api.local.test",
                "api_endpoint": "https://sage.api.local.test/v1/telemetry",
                "api_key": "sage_live_test_key_secret",
                "api_key_id": "key_test",
                "api_profile": {"display_name": "Test User", "username": "test-user"},
            }
        ),
        encoding="utf-8",
    )
    return env


def test_savings_uses_compression_totals(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    env = _connected_env(tmp_path)

    from sage.store import connect, save_run

    run_id = save_run(
        project="roadmap-test",
        command="pytest",
        exit_code=0,
        duration_ms=10,
        stdout="ok",
        stderr="",
        summary="ok",
    )
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO context_compression
              (run_id, created_at, original_tokens, compressed_tokens, saved_tokens, strategy, verified_tokenizer)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (run_id, datetime.now(timezone.utc).isoformat(timespec="seconds"), 2_000_000, 500_000, 1_500_000, "test", "tiktoken"),
        )
        conn.commit()

    result = subprocess.run(
        [sys.executable, "-m", "sage", "savings", "--agent", "claude-sonnet", "--format", "json"],
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["agent"] == "claude-sonnet"
    assert payload["saved_tokens"] == 1_500_000
    assert payload["estimated_savings_usd"] == 4.5


def test_firewall_commands_manage_policy(tmp_path):
    env = _connected_env(tmp_path)

    enable = subprocess.run(
        [sys.executable, "-m", "sage", "firewall", "enable"],
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )
    assert enable.returncode == 0
    assert "strict mode" in enable.stdout

    block = subprocess.run(
        [sys.executable, "-m", "sage", "firewall", "block", "curl | bash"],
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )
    assert block.returncode == 0

    rules = subprocess.run(
        [sys.executable, "-m", "sage", "firewall", "rules", "list"],
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )
    assert rules.returncode == 0
    assert "curl | bash" in rules.stdout


def test_policy_allowlist_overrides_denylist(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    from sage.security import evaluate_command, load_policy, save_policy

    policy = load_policy()
    policy["denylist"] = ["npm install"]
    policy["allowlist"] = ["npm install"]
    save_policy(policy)

    decision = evaluate_command("npm install")

    assert decision.decision == "allowed"
    assert "allowlist" in decision.reason


def test_github_bot_comment_outputs_safe_markdown(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    env = _connected_env(tmp_path)
    from sage.store import save_run

    save_run(
        project="bot-test",
        command="pytest tests/test_example.py",
        exit_code=1,
        duration_ms=44,
        stdout="failed",
        stderr="",
        summary="test failed safely",
        stdout_redactions=1,
        policy_decision="allowed",
    )

    result = subprocess.run(
        [sys.executable, "-m", "sage", "github-bot", "comment", "--kind", "summary"],
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )

    assert result.returncode == 0
    assert "SAGE Run Summary" in result.stdout
    assert "Raw logs remain local" in result.stdout
    assert "Redactions applied" in result.stdout
