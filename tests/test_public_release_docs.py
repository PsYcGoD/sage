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

    assert "pip install psycgod-sage" in readme
    assert "The PyPI distribution is `psycgod-sage`; the installed CLI command is still `sage`." in readme
    assert "local-first command wrapper for AI coding agents" in readme
    assert "## Known Limitations" in readme
    assert "The desktop GUI is not available in this public repo right now." in readme
    assert "docs/assets/sage-run.svg" in readme
    assert "demo-sage-run.gif" in readme
    assert "Team Dashboard is not published yet" in readme
    assert "team-dashboard-preview.png" in readme
    hidden_team_endpoint = "/api/v1/" + "team"
    assert hidden_team_endpoint not in readme
    removed_command = "sage " + "pric" + "ing"
    assert removed_command not in readme
