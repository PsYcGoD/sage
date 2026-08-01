"""Fail a release when public package versions drift apart."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _quoted_version(path: Path, name: str) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(rf"{re.escape(name)}\s*=\s*['\"]([^'\"]+)['\"]", text)
    if not match:
        raise ValueError(f"version marker {name!r} not found in {path}")
    return match.group(1)


def versions() -> dict[str, str]:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    package = json.loads((ROOT / "js" / "package.json").read_text(encoding="utf-8"))
    package_lock = json.loads((ROOT / "js" / "package-lock.json").read_text(encoding="utf-8"))
    server = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
    mcp_config = json.loads((ROOT / "sage-mcp.json").read_text(encoding="utf-8-sig"))
    return {
        "pyproject": str(pyproject["project"]["version"]),
        "python": _quoted_version(ROOT / "src" / "sage" / "__init__.py", "__version__"),
        "npm": str(package["version"]),
        "npm_lock": str(package_lock["packages"][""]["version"]),
        "npm_export": _quoted_version(ROOT / "js" / "src" / "index.ts", "VERSION"),
        "npm_python_core": _quoted_version(
            ROOT / "js" / "src" / "python" / "bridge.ts", "EXPECTED_SAGE_VERSION"
        ),
        "mcp_registry": str(server["version"]),
        "mcp_pypi": str(server["packages"][0]["version"]),
        "mcp_npm": str(server["packages"][1]["version"]),
        "mcp_config": str(mcp_config["version"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="")
    args = parser.parse_args()

    found = versions()
    expected = found["pyproject"]
    mismatches = {name: value for name, value in found.items() if value != expected}
    if args.tag:
        tag_version = args.tag.removeprefix("v")
        if tag_version != expected:
            mismatches["release_tag"] = tag_version

    if mismatches:
        print(json.dumps({"expected": expected, "mismatches": mismatches}, indent=2))
        return 1

    print(f"release versions synchronized: {expected}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
