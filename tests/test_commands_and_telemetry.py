"""Tests for classification, read, grep, artifacts, and telemetry client."""

import json

import pytest

from sage.classify import classify_command, workspace_hash
from sage.reader import read_file
from sage.searcher import render, search


# ------------------------------------------------------------ classification

def test_classify_core_kinds():
    assert classify_command("python -m pytest tests/ -q").kind == "test"
    assert classify_command("npm install express").kind == "install"
    assert classify_command("pip install requests").kind == "install"
    assert classify_command("git status --short").kind == "git"
    assert classify_command("rg pattern src").kind == "grep"
    assert classify_command("cat README.md").kind == "read"
    assert classify_command("Get-Content app.py").kind == "read"
    assert classify_command("curl https://example.com").kind == "network"
    assert classify_command("ruff check src").kind == "lint"
    assert classify_command("cargo build --release").kind == "build"
    assert classify_command("python app.py").kind == "run"


def test_classify_sees_through_sage_wrapper():
    assert classify_command("sage run -- python -m pytest").kind == "test"


def test_classify_never_raises():
    assert classify_command("").kind == "unknown"
    assert classify_command("   ").kind == "unknown"
    assert classify_command("some-unknown-tool --flag").kind == "run"


def test_workspace_hash_stable_and_salted():
    a = workspace_hash(r"D:\work\sage")
    assert a == workspace_hash("d:/work/sage/")  # normalized
    assert a != workspace_hash(r"D:\work\sage", salt="org-salt")
    assert len(a) == 64


# ------------------------------------------------------------------- reader

def test_read_small_file_exact(tmp_path):
    path = tmp_path / "small.py"
    path.write_text("import os\n\ndef main():\n    return 1\n", encoding="utf-8")
    result = read_file(str(path))
    assert result.exists and result.mode == "exact"
    assert "def main():" in result.output
    assert "    4\t" in result.output  # line numbers present


def test_read_line_range(tmp_path):
    path = tmp_path / "ranged.txt"
    path.write_text("\n".join(f"line-{i}" for i in range(1, 51)), encoding="utf-8")
    result = read_file(str(path), lines="10:12")
    assert "line-10" in result.output and "line-12" in result.output
    assert "line-13" not in result.output


def test_read_large_file_compressed(tmp_path):
    path = tmp_path / "big.py"
    body = ["import os", "import sys"]
    for i in range(3000):
        body.append(f"def func_{i}():")
        body.append(f"    return {i}  # padding padding padding padding")
    path.write_text("\n".join(body), encoding="utf-8")
    result = read_file(str(path), max_tokens=500)
    assert result.mode == "compressed"
    assert result.saved_tokens > 0
    # Soft budget: small tokenizer drift is fine, order-of-magnitude blowout is not.
    assert result.shown_tokens <= 900
    assert result.shown_tokens < result.original_tokens * 0.05
    assert "--lines" in result.output  # tells the agent how to get exact ranges
    assert any("def func_0" in s for s in result.symbols)


def test_read_symbols_only(tmp_path):
    path = tmp_path / "mod.py"
    path.write_text("import os\nclass Foo:\n    pass\ndef bar():\n    pass\n", encoding="utf-8")
    result = read_file(str(path), symbols_only=True)
    assert result.mode == "symbols"
    assert "class Foo:" in result.output and "def bar():" in result.output


def test_read_missing_file():
    result = read_file("definitely/missing/file.py")
    assert not result.exists
    assert "not found" in result.error.lower()


# ----------------------------------------------------------------- searcher

@pytest.fixture()
def search_tree(tmp_path):
    (tmp_path / "a.py").write_text("def alpha():\n    return 'needle'\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("\n".join("needle here" for _ in range(30)), encoding="utf-8")
    (tmp_path / "c.txt").write_text("no match here\n", encoding="utf-8")
    return tmp_path


def test_grep_finds_matches_with_exact_locations(search_tree):
    result = search("needle", [str(search_tree)])
    assert result.exit_code == 0
    assert result.match_count >= 31
    files = {f.replace("\\", "/").rsplit("/", 1)[-1] for f in result.matches}
    assert {"a.py", "b.py"} <= files
    a_file = next(f for f in result.matches if f.endswith("a.py"))
    assert result.matches[a_file][0][0] == 2  # exact line number


def test_grep_caps_noisy_files_and_counts_hidden(search_tree):
    result = search("needle", [str(search_tree)])
    b_file = next(f for f in result.matches if f.endswith("b.py"))
    assert len(result.matches[b_file]) <= 8
    assert result.hidden_matches > 0
    rendered = render(result)
    assert "hidden" in rendered


def test_grep_zero_matches_exit_one(search_tree):
    result = search("no_such_token_anywhere", [str(search_tree)])
    assert result.exit_code == 1
    assert "No matches" in render(result)


def test_grep_glob_filter(search_tree):
    result = search("needle", [str(search_tree)], glob="*.py")
    assert all(f.endswith(".py") for f in result.matches)


def test_grep_invalid_pattern_exit_two(search_tree):
    from sage.searcher import GrepResult, _search_python

    result = GrepResult(pattern="[invalid", paths=[str(search_tree)])
    with pytest.raises(Exception):
        _search_python(result, glob="", ignore_case=False)


# ---------------------------------------------------------------- artifacts

def test_artifact_threshold_and_roundtrip(tmp_path, monkeypatch):
    import sage.artifacts as artifacts

    monkeypatch.setattr(artifacts, "data_dir", lambda: tmp_path)
    path, sha = artifacts.store_raw_output(999_991, "tiny", "")
    assert path == "" and sha == ""

    big = "x" * 100_000
    path, sha = artifacts.store_raw_output(999_992, big, "err")
    assert path and len(sha) == 64
    data = json.loads(open(path, encoding="utf-8").read())
    assert data["stdout"] == big and data["stderr"] == "err"


def test_artifact_prune_preview_and_apply(tmp_path, monkeypatch):
    import sage.artifacts as artifacts

    monkeypatch.setattr(artifacts, "data_dir", lambda: tmp_path)
    artifacts.store_raw_output(999_993, "y" * 100_000, "")
    preview = artifacts.prune_artifacts(max_bytes=0, apply=False)
    assert preview["pruned"] == 1 and preview["applied"] == 0
    assert list(tmp_path.glob("artifacts/run-*-raw.json"))  # still there
    applied = artifacts.prune_artifacts(max_bytes=0, apply=True)
    assert applied["applied"] == 1
    assert not list(tmp_path.glob("artifacts/run-*-raw.json"))


# ---------------------------------------------------------------- telemetry

@pytest.fixture()
def isolated_telemetry(tmp_path, monkeypatch):
    import sage.telemetry as telemetry

    monkeypatch.setattr(telemetry, "data_dir", lambda: tmp_path)
    return telemetry


def test_default_level_is_local_only(isolated_telemetry):
    assert isolated_telemetry.effective_level() == 0
    assert isolated_telemetry.build_payload(1) is None  # level 0 sends nothing


def test_public_proof_snapshot_includes_agent_savings(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    from sage.context.tracker import TokenTracker
    from sage.store import save_run
    from sage import telemetry

    run_id = save_run(
        project="proof-test",
        command="sage run -- pytest",
        exit_code=0,
        duration_ms=25,
        stdout="ok",
        stderr="",
        summary="ok",
    )
    TokenTracker().record_usage(run_id, estimated_tokens=2_000_000, compressed_tokens=500_000)

    snapshot = telemetry.build_proof_snapshot()
    totals = snapshot["totals"]

    assert totals["tokens_saved"] == 1_500_000
    assert totals["estimated_savings_usd"] == 8.625
    assert totals["savings_by_model"][0]["model"] == "claude-sonnet"
    assert totals["savings_by_model"][0]["estimated_savings_usd"] == 4.5
    assert totals["savings_by_model"][1]["model"] == "codex"
    assert totals["savings_by_model"][1]["estimated_savings_usd"] == 2.25
    assert totals["savings_by_agent"][0]["agent"] == "claude-cli"
    assert totals["savings_by_agent"][0]["model"] == "Claude Sonnet"
    assert totals["savings_by_agent"][0]["estimated_savings_usd"] == 4.5
    assert totals["savings_by_agent"][1]["agent"] == "codex-cli"
    assert totals["savings_by_agent"][1]["model"] == "OpenAI Codex"
    assert totals["savings_by_agent"][1]["estimated_savings_usd"] == 2.25
    unused_agents = {
        row["agent"]: row for row in totals["savings_by_agent"] if row["agent"] in {"cursor", "windsurf", "aider"}
    }
    assert unused_agents
    assert all(row["estimated_savings_usd"] == 0 for row in unused_agents.values())
    assert "command" not in snapshot
    assert "stdout" not in snapshot


def test_strictest_policy_wins(isolated_telemetry):
    t = isolated_telemetry
    t.set_level(3)
    t.account_link("work", user_id="u1", org_id="o1", org_max_level=1, key_max_level=2)
    t.account_use("work")
    assert t.effective_level() == 1  # org policy overrides user's 3
    t.account_use("anonymous")
    assert t.effective_level() == 3


def test_set_level_validation(isolated_telemetry):
    with pytest.raises(ValueError):
        isolated_telemetry.set_level(9)


def test_account_lifecycle(isolated_telemetry):
    t = isolated_telemetry
    t.account_link("personal", user_id="me")
    assert "personal" in t.account_list()["accounts"]
    assert t.account_use("personal")
    assert not t.account_use("ghost")
    assert t.account_unlink("personal")
    assert t.account_status()["active_account"] == "anonymous"


def test_level1_payload_contains_no_raw_content(isolated_telemetry):
    """The launch-critical guarantee: Level 1 never carries code or output."""
    t = isolated_telemetry
    from sage.store import latest_run

    record = latest_run()
    if record is None:
        pytest.skip("No local run history available.")
    payload = t.build_payload(record.id, level=1)
    assert payload is not None
    for key in t.LEVEL1_FORBIDDEN_KEYS:
        assert key not in payload, f"forbidden key {key} in Level 1 payload"
    for value in payload.values():
        assert not isinstance(value, str) or len(value) <= 128
    assert payload["schema_version"] == "1.0"
    assert len(payload["workspace_hash"]) == 64


def test_dedupe_key_is_stable(isolated_telemetry):
    payload = {
        "installation_id": "abc",
        "workspace_hash": "def",
        "run_id_local_hash": "ghi",
    }
    assert isolated_telemetry.dedupe_key(payload) == isolated_telemetry.dedupe_key(dict(payload))


def test_send_without_endpoint_is_noop(isolated_telemetry):
    result = isolated_telemetry.send_queued(dry_run=False)
    assert result["sent"] == 0
    assert "not configured" in result["endpoint"]


def test_sync_all_refreshes_snapshot_when_queue_remains(isolated_telemetry, monkeypatch):
    t = isolated_telemetry
    calls = {"snapshot": 0}

    monkeypatch.setattr(t, "queue_all_runs", lambda: {"scanned": 1, "queued": 1, "skipped": 0})
    monkeypatch.setattr(t, "api_status", lambda: {"endpoint": "https://example.test/v1/telemetry"})
    monkeypatch.setattr(t, "send_queued", lambda *, dry_run, limit: {
        "sent": 0,
        "failed": 0,
        "queued": 1,
        "dry_run": False,
        "endpoint": "https://example.test/v1/telemetry",
    })
    monkeypatch.setattr(t, "queue_status", lambda: {"queued": 1})

    def fake_snapshot():
        calls["snapshot"] += 1
        return {"ok": True}

    monkeypatch.setattr(t, "send_proof_snapshot", fake_snapshot)

    result = t.sync_all_runs(dry_run=False)

    assert calls["snapshot"] == 1
    assert result["snapshot"] == {"ok": True}


def test_background_sender_publishes_snapshot_before_batch(monkeypatch):
    from pathlib import Path
    import tempfile

    from sage import telemetry
    from sage import telemetry_sender

    calls = []

    monkeypatch.setattr(telemetry, "load_config", lambda: {
        "api_endpoint": "https://example.test/v1/telemetry",
        "api_key": "key",
    })
    monkeypatch.setattr(telemetry, "send_proof_snapshot", lambda: calls.append("snapshot") or {"ok": True})
    monkeypatch.setattr(telemetry, "send_queued", lambda *, dry_run, limit: calls.append(("send", dry_run, limit)) or {"sent": 1, "queued": 0})
    monkeypatch.setattr(telemetry, "data_dir", lambda: Path(tempfile.gettempdir()))

    telemetry_sender.send_batch_background(limit=123)

    assert calls[:2] == ["snapshot", ("send", False, 123)]
    assert calls[-1] == "snapshot"


def test_api_key_storage_uses_keyring(monkeypatch):
    import types
    import sys

    from sage import telemetry

    stored = {}

    fake_keyring = types.SimpleNamespace(
        set_password=lambda service, account, password: stored.__setitem__((service, account), password),
        get_password=lambda service, account: stored.get((service, account)),
        delete_password=lambda service, account: stored.pop((service, account), None),
    )
    monkeypatch.setitem(sys.modules, "keyring", fake_keyring)

    config = {"installation_id": "install-test"}
    storage = telemetry._store_api_key(config, "sage_live_secret", "key_test")

    assert storage == "keyring"
    assert config["api_key_storage"] == "keyring"
    assert "api_key" not in config
    assert telemetry.resolve_api_key(config) == "sage_live_secret"

    telemetry._delete_api_key(config)

    assert telemetry.resolve_api_key(config) == ""


def test_run_command_spawns_sender_when_output_is_captured(monkeypatch, tmp_path):
    from sage import runner
    from sage import telemetry

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("SAGE_SUPPRESS_FOOTER", "1")
    monkeypatch.setenv("SAGE_DISABLE_AGENTS", "1")
    monkeypatch.setenv("SAGE_AUTO_SEND_TELEMETRY", "1")

    calls = {"spawn": 0}

    def fake_spawn():
        calls["spawn"] += 1
        return True

    monkeypatch.setattr(telemetry, "queue_event", lambda run_id: {"queued": run_id})
    monkeypatch.setattr("sage.telemetry_sender.spawn_background_sender", fake_spawn)

    exit_code = runner.run_command(["python", "-c", "print('sync probe')"])

    assert exit_code == 0
    assert calls["spawn"] == 1
