"""GitHub OAuth for SAGE API authentication — server-side callback flow.

The client:
1. POSTs to /v1/github-auth/start → gets a session_id + authorize_url
2. Opens the browser to GitHub's authorize page
3. User authenticates on GitHub
4. GitHub redirects to api.marketingstudios.in/auth/github/callback
5. API exchanges code for token, creates SAGE API key, stores in session
6. CLI polls /v1/github-auth/status?session=<id> until completed
"""

from __future__ import annotations

import json
import time
import urllib.request
import urllib.parse
import urllib.error
import webbrowser
from typing import Any

DEFAULT_API_BASE = "https://sage.api.marketingstudios.in"


def github_oauth_flow(
    *,
    api_base: str = DEFAULT_API_BASE,
    install_id: str = "",
    client_version: str = "",
    platform: str = "",
    poll_interval: float = 2.0,
    timeout: int = 300,
) -> dict[str, Any]:
    """Run GitHub OAuth with server-side callback and return the SAGE API key info."""
    print("Starting GitHub authentication...")
    print(f"API:  {api_base}")

    # 1. Start OAuth session
    session = _start_session(api_base, install_id, client_version, platform)
    session_id = session["session_id"]
    authorize_url = session["authorize_url"]

    print(f"Session: {session_id}")
    print()
    print("Opening browser for GitHub login...")
    print(f"If browser does not open, visit:")
    print(f"  {authorize_url}")
    print()
    webbrowser.open(authorize_url)

    # 2. Poll for completion
    print("Waiting for GitHub authorization...")
    print("(Complete the authorization in your browser)")
    deadline = time.time() + timeout
    last_status = ""
    while time.time() < deadline:
        result = _poll_status(api_base, session_id)
        status = result.get("status", "pending")

        if status != last_status and status == "pending":
            pass
        last_status = status

        if status == "completed":
            print()
            print("GitHub authorization successful!")
            return result

        if status == "error":
            error_msg = result.get("error", "Unknown error")
            raise RuntimeError(f"GitHub OAuth failed: {error_msg}")

        time.sleep(poll_interval)

    raise RuntimeError("GitHub authentication timed out.")


def _start_session(
    api_base: str,
    install_id: str = "",
    client_version: str = "",
    platform: str = "",
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if install_id:
        payload["installation_id"] = install_id
    if client_version:
        payload["client_version"] = client_version
    if platform:
        payload["platform"] = platform

    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{api_base}/v1/github-auth/start",
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "SAGE-CLI/0.1",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Failed to start OAuth session: HTTP {exc.code} {detail}")
    except OSError as exc:
        raise RuntimeError(f"Cannot reach SAGE API: {exc}")

    if not body.get("ok"):
        raise RuntimeError(body.get("error", "Failed to start OAuth session"))
    return body


def _poll_status(api_base: str, session_id: str) -> dict[str, Any]:
    url = f"{api_base}/v1/github-auth/status?session={urllib.parse.quote(session_id)}"
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {"status": "error", "error": "Session expired"}
        detail = exc.read().decode("utf-8", errors="replace")
        return {"status": "error", "error": f"HTTP {exc.code}: {detail}"}
    except OSError as exc:
        return {"status": "error", "error": str(exc)}
