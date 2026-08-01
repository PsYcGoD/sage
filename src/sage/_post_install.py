"""Post-install script: GitHub OAuth during pip install.

Safely skipped in CI, Docker, headless, or non-interactive terminals.
"""

import os
import sys
import time


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

    try:
        from .telemetry import auto_register_silent, load_config, save_config

        cfg = load_config()

        if cfg.get("api_endpoint") and cfg.get("api_key_id"):
            return

        from .github_oauth import github_oauth_flow

        print()
        print("SAGE needs GitHub authentication to connect this machine.")
        print("A browser window will open for you to authorize.")
        print()

        result = github_oauth_flow()

        api_key = str(result.get("api_key") or "")
        key_id = str(result.get("key_id") or "")
        github_username = str(result.get("github_username") or "")

        if not api_key or not key_id:
            return

        from . import telemetry

        base = telemetry.DEFAULT_API_BASE_URL
        cfg["api_base_url"] = base
        cfg["api_endpoint"] = f"{base}/v1/telemetry"
        cfg["api_key_id"] = key_id
        telemetry._store_api_key(cfg, api_key, key_id)
        cfg["api_profile"] = {
            "display_name": result.get("display_name", github_username),
            "username": github_username,
            "github_id": int(result.get("github_id", 0)),
            "public_profile": True,
            "scope": "personal",
        }
        cfg["telemetry_level"] = 1
        save_config(cfg)

        telemetry.account_link(
            github_username,
            user_id=str(result.get("github_id", "")),
            api_key_ref=key_id,
            key_max_level=1,
        )
        telemetry.account_use(github_username)

    except Exception:
        pass

    print(_BANNER)
