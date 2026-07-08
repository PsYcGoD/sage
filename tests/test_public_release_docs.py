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

    assert "# SAGE CLI" in readme
    assert "pip install psycgod-sage" in readme
    assert "By default, SAGE CLI runs locally." in readme
    assert "GitHub login is optional" in readme
    assert "pip install psycgod-sage" in readme
    assert "PyPI publishing is prepared but still blocked" not in readme
    assert "Local-first terminal wrapper for AI coding agents" in readme
    assert "Estimated savings by model/provider" in readme
    assert "## Known Limitations" in readme
    assert "The desktop GUI is not available in this public repo right now." in readme
    assert "raw.githubusercontent.com/PsYcGoD/sage/main/docs/assets/sage-run.svg" in readme
    assert "demo-sage-run.gif" in readme
    assert "Team Dashboard is not published yet" in readme
    assert "team-dashboard-preview.png" in readme
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
