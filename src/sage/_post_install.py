"""Post-install message for the local-only SAGE package."""

import os
import sys


_BANNER = """
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║                      SAGE INSTALLED                                  ║
║                                                                      ║
║            Enter the command below to activate:                      ║
║                                                                      ║
║                    sage install                                      ║
║                                                                      ║
║     Your AI agents will then use SAGE automatically.                 ║
║     Every command runs compressed, tracked, and protected.           ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""


def _is_interactive() -> bool:
    if "CI" in os.environ or "PYTEST_CURRENT_TEST" in os.environ:
        return False
    if not sys.stdout or not sys.stdout.isatty():
        return False
    if not sys.stdin or not sys.stdin.isatty():
        return False
    return True


def run_post_install() -> None:
    if not _is_interactive():
        return
    print(_BANNER)
