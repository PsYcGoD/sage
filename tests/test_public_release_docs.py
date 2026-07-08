from __future__ import annotations

from pathlib import Path


def test_public_release_docs_and_assets_exist():
    required = [
        "CHANGELOG.md",
        "SECURITY.md",
        "CONTRIBUTING.md",
        "docs/releases/v2.0.0-cli-public.md",
        "docs/PYPI_RELEASE.md",
        "docs/demo/DEMO_GIFS.md",
        ".github/workflows/pypi-publish.yml",
        "docs/assets/sage-run.svg",
        "docs/assets/sage-context-report.svg",
        "docs/assets/sage-mcp-install.svg",
        "docs/assets/demo-sage-run.gif",
        "docs/assets/demo-sage-savings.gif",
        "docs/assets/demo-github-bot.gif",
        "docs/assets/team-dashboard-preview.png",
        "docs/assets/sage-live-dashboard.png",
    ]

    for path in required:
        assert Path(path).exists(), path


def test_readme_public_positioning():
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "# SAGE" in readme
    assert "pip install psycgod-sage" in readme
    assert "Raw logs" in readme or "raw logs" in readme.lower()
    assert "## Known Limitations" in readme
    assert "raw.githubusercontent.com/PsYcGoD/sage/main/docs/assets/sage-run.svg" in readme
    hidden_team_endpoint = "/api/v1/" + "team"
    assert hidden_team_endpoint not in readme
    removed_command = "sage " + "pric" + "ing"
    assert removed_command not in readme


def test_public_worker_dashboard_exposes_aggregate_savings():
    worker = Path("cloudflare/sage-api/src/worker.js").read_text(encoding="utf-8")

    assert "Estimated Savings" in worker
    assert "Estimated savings by model" in worker
    assert "Estimated savings by AI agent" in worker
    assert "Money Saved by each AI Agent" in worker
    assert "AI Agent / Provider" in worker
    assert "Codex" in worker
    assert "SAGE" in worker
    assert "Claude Code" in worker
    assert "OpenCode" in worker
    assert "Ollama" in worker
    assert "Cursor" in worker
    assert "estimated_savings_usd" in worker
    assert "savings_by_model" in worker
    assert "savings_by_agent" in worker
    assert "total_agents" in worker
    assert "agent_runs_completed" in worker
    assert "ml_training_examples" in worker
    assert "agent_quality_metrics" in worker
    assert "sanitizeSavingsByAgent" in worker
    assert "/v1/dashboard-click" in worker
    assert "dashboard_clicks" in worker
    assert "new_installs_today" in worker
    assert "live_installs_15m" in worker
    assert "live_api_users_15m" in worker
    assert "clicks_today" in worker


def test_admin_users_endpoint_defaults_to_sanitized_rows():
    worker = Path("cloudflare/sage-api/src/worker.js").read_text(encoding="utf-8")

    assert 'searchParams.get("raw") === "1"' in worker
    assert "looksLikeHash" in worker
    assert "firstUsefulText" in worker
    assert "machine_ids" in worker
    assert "NULLIF(k.display_name, '')" in worker
    assert "NULLIF(k.username, '')" in worker
    assert worker.index("NULLIF(k.display_name, '')") < worker.index("NULLIF(k.username, '')")
    assert "if (!raw) return base;" in worker


def test_public_proof_snapshot_uses_live_run_totals():
    worker = Path("cloudflare/sage-api/src/worker.js").read_text(encoding="utf-8")

    assert "async function getAggregateRunTotals" in worker
    assert "...aggregateRuns" in worker
    assert "if (!seen.has(row.model)) sanitized.push(row);" in worker
    assert "if (!seen.has(row.agent)) sanitized.push(row);" in worker
