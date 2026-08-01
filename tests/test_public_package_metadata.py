from __future__ import annotations

import pathlib
import runpy
import tomllib

import yaml


def test_public_distribution_metadata():
    data = tomllib.loads(pathlib.Path("pyproject.toml").read_text(encoding="utf-8"))

    assert data["project"]["name"] == "psycgod-sage"
    assert data["project"]["scripts"]["sage"] == "sage.cli:main"
    assert "Development Status :: 4 - Beta" in data["project"]["classifiers"]
    assert any(dep.startswith("keyring") for dep in data["project"]["dependencies"])
    excluded = set(data["tool"]["setuptools"]["packages"]["find"]["exclude"])
    assert {"sage.gui", "sage.dashboard", "sage.tui"} <= excluded


def test_release_versions_are_synchronized():
    module = runpy.run_path("scripts/check_release_versions.py", run_name="release_check")
    found = module["versions"]()
    assert len(set(found.values())) == 1, found


def test_legacy_setup_has_no_install_side_effects():
    setup_text = pathlib.Path("setup.py").read_text(encoding="utf-8")
    assert "cmdclass" not in setup_text
    assert "PostInstallCommand" not in setup_text


def test_release_workflows_parse_and_publish_pypi_before_npm():
    for path in (".github/workflows/ci.yml", ".github/workflows/pypi-publish.yml"):
        assert yaml.safe_load(pathlib.Path(path).read_text(encoding="utf-8"))

    workflow = pathlib.Path(".github/workflows/pypi-publish.yml").read_text(
        encoding="utf-8"
    )
    assert "publish-npm:" in workflow
    assert "needs: publish" in workflow
    assert "scripts/wait_for_pypi.py" in workflow
