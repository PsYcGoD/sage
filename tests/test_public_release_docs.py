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
    ]

    for path in required:
        assert Path(path).exists(), path


def test_readme_public_positioning():
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "# SAGE" in readme
    assert "pip install psycgod-sage" in readme
    assert "## Start Here:" in readme
    assert "Then Use Any AI Agent" in readme
    assert "sage install" in readme
    assert "sage doctor --activation" in readme
    assert "npx -y psycgod-sage doctor --activation" in readme
    assert "After install, restart any open AI-agent sessions" in readme
    assert "Please help me with my general book in this folder" in readme
    assert "Raw logs" in readme or "raw logs" in readme.lower()
    assert "## Known Limitations" in readme
    assert "raw.githubusercontent.com/PsYcGoD/sage/main/docs/assets/sage-run.svg" in readme
    hidden_team_endpoint = "/api/v1/" + "team"
    assert hidden_team_endpoint not in readme
    removed_command = "sage " + "pric" + "ing"
    assert removed_command not in readme
