from __future__ import annotations

from pathlib import Path


def test_public_release_docs_and_assets_exist():
    required = [
        "CHANGELOG.md",
        "SECURITY.md",
        "CONTRIBUTING.md",
        "docs/releases/v2.0.0-cli-public.md",
        "docs/assets/sage-run.svg",
        "docs/assets/sage-context-report.svg",
        "docs/assets/sage-mcp-install.svg",
        "docs/assets/sage-live-dashboard.png",
    ]

    for path in required:
        assert Path(path).exists(), path


def test_readme_public_positioning():
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "pip install sage-cli" in readme
    assert "The PyPI distribution is `sage-cli`; the installed CLI command is still `sage`." in readme
    assert "local-first command wrapper for AI coding agents" in readme
    assert "## Known Limitations" in readme
    assert "The desktop GUI is not available in this public repo right now." in readme
    assert "docs/assets/sage-run.svg" in readme
