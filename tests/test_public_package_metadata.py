from __future__ import annotations

import pathlib
import tomllib


def test_public_distribution_metadata():
    data = tomllib.loads(pathlib.Path("pyproject.toml").read_text(encoding="utf-8"))

    assert data["project"]["name"] == "psycgod-sage"
    assert data["project"]["scripts"]["sage"] == "sage.cli:main"
    assert "Development Status :: 4 - Beta" in data["project"]["classifiers"]
    assert any(dep.startswith("keyring") for dep in data["project"]["dependencies"])
