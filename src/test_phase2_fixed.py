"""Legacy phase-2 smoke snippet.

This file used to contain an indented fragment from an old manual MCP check,
which made `python -m compileall src tests` fail. The active automated tests
now live under `tests/`.
"""


def test_phase2_fixed_legacy_placeholder() -> None:
    """Keep the legacy module importable without running stale checks."""
    return None
