"""GitHub OAuth for SAGE API authentication."""

from __future__ import annotations

import hashlib
import json
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable
from urllib import parse as urllib_parse
from urllib import error as urllib_error
from urllib import request as urllib_request


GITHUB_CLIENT_ID = "Ov23libLspfxbzmPhMSv"
DEFAULT_CALLBACK_PORT = 8765


class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handle OAuth callback from GitHub."""

    auth_code: str | None = None
    state: str | None = None

    def log_message(self, format, *args):  # noqa: A002 - BaseHTTPRequestHandler API
        pass

    def do_GET(self):
        parsed = urllib_parse.urlparse(self.path)
        query = urllib_parse.parse_qs(parsed.query)

        if parsed.path != "/oauth/callback":
            self.send_response(404)
            self.end_headers()
            return

        OAuthCallbackHandler.auth_code = query.get("code", [None])[0]
        OAuthCallbackHandler.state = query.get("state", [None])[0]

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(_success_html().encode("utf-8"))


def _success_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SAGE Connected</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    .container {
      background: white;
      padding: 40px;
      border-radius: 16px;
      box-shadow: 0 20px 60px rgba(0,0,0,0.3);
      text-align: center;
      max-width: 420px;
    }
    .icon {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 88px;
      height: 88px;
      border-radius: 999px;
      background: #10b981;
      color: white;
      font-size: 34px;
      font-weight: 800;
      margin-bottom: 22px;
      letter-spacing: 0;
    }
    h1 { color: #10b981; margin: 0 0 18px 0; }
    p { color: #4b5563; line-height: 1.6; }
  </style>
</head>
<body>
  <main class="container">
    <div class="icon">OK</div>
    <h1>SAGE Connected!</h1>
    <p>GitHub authentication successful.</p>
    <p>You can close this window and return to SAGE.</p>
  </main>
</body>
</html>
"""


def start_oauth_server(port: int = DEFAULT_CALLBACK_PORT) -> tuple[HTTPServer, int]:
    """Start local OAuth callback server, falling back to a free port."""
    OAuthCallbackHandler.auth_code = None
    OAuthCallbackHandler.state = None
    try:
        server = ReusableHTTPServer(("localhost", port), OAuthCallbackHandler)
        actual_port = port
    except OSError:
        server = ReusableHTTPServer(("localhost", 0), OAuthCallbackHandler)
        actual_port = int(server.server_address[1])

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, actual_port


def wait_for_oauth_callback(timeout: int = 120) -> tuple[str | None, str | None]:
    start_time = time.time()
    while time.time() - start_time < timeout:
        if OAuthCallbackHandler.auth_code:
            return OAuthCallbackHandler.auth_code, OAuthCallbackHandler.state
        time.sleep(0.25)
    return None, None


def github_oauth_flow() -> dict[str, Any]:
    """Run GitHub OAuth and return the authorization code for the SAGE API."""
    state = secrets.token_urlsafe(32)

    print("Starting GitHub authentication...")
    server, port = start_oauth_server()
    redirect_uri = f"http://localhost:{port}/oauth/callback"

    try:
        auth_url = (
            "https://github.com/login/oauth/authorize"
            f"?client_id={GITHUB_CLIENT_ID}"
            f"&redirect_uri={urllib_parse.quote(redirect_uri)}"
            f"&state={state}"
            "&scope=user:email"
        )

        print("Opening browser for GitHub login...")
        print(f"If browser does not open, visit: {auth_url}")
        webbrowser.open(auth_url)

        print("Waiting for GitHub authorization...")
        auth_code, returned_state = wait_for_oauth_callback(timeout=120)

        if not auth_code:
            raise RuntimeError("GitHub authentication timed out after 120 seconds")
        if returned_state != state:
            raise RuntimeError("OAuth state mismatch")

        print("GitHub authorization received")
        return {
            "auth_code": auth_code,
            "state": state,
            "redirect_uri": redirect_uri,
        }
    finally:
        server.shutdown()
        server.server_close()


def github_device_flow(
    *,
    status_callback: Callable[[str], None] | None = None,
    scope: str = "user:email",
) -> dict[str, Any]:
    """Run GitHub device flow and return an access token.

    This is the no-GitHub-CLI path for CLI and device clients. It requires Device Flow
    to be enabled on the GitHub OAuth app, but it does not require a client
    secret on the user's PC.
    """

    def emit(message: str) -> None:
        if status_callback:
            status_callback(message)

    data = urllib_parse.urlencode({
        "client_id": GITHUB_CLIENT_ID,
        "scope": scope,
    }).encode("utf-8")
    request = urllib_request.Request(
        "https://github.com/login/device/code",
        data=data,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "SAGE-CLI/0.1",
        },
        method="POST",
    )

    try:
        with urllib_request.urlopen(request, timeout=20) as response:
            device = json.loads(response.read().decode("utf-8"))
    except urllib_error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            device = json.loads(body or "{}")
        except json.JSONDecodeError:
            device = {"error": f"HTTP {exc.code}", "error_description": body or str(exc)}

    if device.get("error"):
        detail = device.get("error_description") or device.get("error")
        raise RuntimeError(f"GitHub device login failed: {detail}")

    device_code = str(device.get("device_code") or "")
    user_code = str(device.get("user_code") or "")
    verification_uri = str(device.get("verification_uri") or "https://github.com/login/device")
    expires_in = int(device.get("expires_in") or 900)
    interval = max(5, int(device.get("interval") or 5))

    if not device_code or not user_code:
        raise RuntimeError("GitHub device login did not return a device code.")

    emit(f"GitHub login code: {user_code}\nOpening {verification_uri}")
    webbrowser.open(verification_uri)

    deadline = time.time() + expires_in
    while time.time() < deadline:
        emit(f"Waiting for GitHub approval. Enter code {user_code}")
        time.sleep(interval)

        poll_data = urllib_parse.urlencode({
            "client_id": GITHUB_CLIENT_ID,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        }).encode("utf-8")
        poll_request = urllib_request.Request(
            "https://github.com/login/oauth/access_token",
            data=poll_data,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "SAGE-CLI/0.1",
            },
            method="POST",
        )

        try:
            with urllib_request.urlopen(poll_request, timeout=20) as poll_response:
                token_data = json.loads(poll_response.read().decode("utf-8"))
        except urllib_error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            try:
                token_data = json.loads(body or "{}")
            except json.JSONDecodeError:
                token_data = {"error": f"HTTP {exc.code}", "error_description": body or str(exc)}

        access_token = str(token_data.get("access_token") or "")
        if access_token:
            emit("GitHub approved. Creating SAGE API key...")
            return {
                "access_token": access_token,
                "scope": token_data.get("scope", ""),
                "token_type": token_data.get("token_type", "bearer"),
            }

        error = token_data.get("error")
        if error == "authorization_pending":
            continue
        if error == "slow_down":
            interval += 5
            continue

        detail = token_data.get("error_description") or error or "unknown error"
        raise RuntimeError(f"GitHub device login failed: {detail}")

    raise RuntimeError("GitHub device login timed out.")


def validate_github_token(access_token: str) -> dict[str, Any]:
    """Validate GitHub access token and get user info."""
    try:
        request = urllib_request.Request(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "SAGE-CLI/0.1",
            },
        )

        with urllib_request.urlopen(request, timeout=15) as response:
            user_data = json.loads(response.read().decode("utf-8"))

        return {
            "github_username": user_data.get("login", ""),
            "github_id": user_data.get("id", 0),
            "display_name": user_data.get("name", "") or user_data.get("login", ""),
            "email": user_data.get("email", ""),
            "avatar_url": user_data.get("avatar_url", ""),
        }
    except Exception as exc:
        raise RuntimeError(f"GitHub token validation failed: {exc}") from exc


def get_github_user_hash(github_id: int) -> str:
    """Generate stable hash from GitHub user ID for database lookups."""
    return hashlib.sha256(f"sage-github-{github_id}".encode()).hexdigest()[:16]
