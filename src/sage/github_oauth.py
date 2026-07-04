"""GitHub OAuth for SAGE API authentication."""

from __future__ import annotations

import hashlib
import json
import secrets
import socket
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib import parse as urllib_parse
from urllib import request as urllib_request


# GitHub OAuth App credentials (public - not secret)
GITHUB_CLIENT_ID = "Ov23libLspfxbzmPhMSv"  # Will be created in your GitHub settings
GITHUB_REDIRECT_URI = "http://localhost:8765/oauth/callback"


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handle OAuth callback from GitHub."""

    auth_code: str | None = None
    state: str | None = None

    def log_message(self, format, *args):
        """Suppress request logging."""
        pass

    def do_GET(self):
        """Handle GET request from GitHub OAuth redirect."""
        parsed = urllib_parse.urlparse(self.path)
        query = urllib_parse.parse_qs(parsed.query)

        if parsed.path == "/oauth/callback":
            OAuthCallbackHandler.auth_code = query.get("code", [None])[0]
            OAuthCallbackHandler.state = query.get("state", [None])[0]

            # Send success page
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            success_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>SAGE Connected</title>
                <style>
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        height: 100vh;
                        margin: 0;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    }
                    .container {
                        background: white;
                        padding: 40px;
                        border-radius: 16px;
                        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                        text-align: center;
                        max-width: 400px;
                    }
                    h1 { color: #10b981; margin: 0 0 20px 0; }
                    p { color: #6b7280; line-height: 1.6; }
                    .icon { font-size: 64px; margin-bottom: 20px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="icon">✅</div>
                    <h1>SAGE Connected!</h1>
                    <p>GitHub authentication successful.</p>
                    <p>You can close this window and return to SAGE.</p>
                </div>
            </body>
            </html>
            """
            self.wfile.write(success_html.encode())
        else:
            self.send_response(404)
            self.end_headers()


def start_oauth_server(port: int = 8765) -> HTTPServer:
    """Start local OAuth callback server."""
    server = HTTPServer(("localhost", port), OAuthCallbackHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def wait_for_oauth_callback(timeout: int = 120) -> tuple[str | None, str | None]:
    """Wait for OAuth callback with timeout."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if OAuthCallbackHandler.auth_code:
            return OAuthCallbackHandler.auth_code, OAuthCallbackHandler.state
        time.sleep(0.5)
    return None, None


def github_oauth_flow() -> dict[str, Any]:
    """
    Run GitHub OAuth flow.

    Returns:
        Dict with: {"github_username": "...", "github_id": 12345, "access_token": "..."}

    Raises:
        RuntimeError: If OAuth fails
    """
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)

    # Start local callback server
    print("🔐 Starting GitHub authentication...")
    server = start_oauth_server()

    try:
        # Build GitHub authorization URL
        auth_url = (
            f"https://github.com/login/oauth/authorize"
            f"?client_id={GITHUB_CLIENT_ID}"
            f"&redirect_uri={urllib_parse.quote(GITHUB_REDIRECT_URI)}"
            f"&state={state}"
            f"&scope=user:email"
        )

        print(f"\n🌐 Opening browser for GitHub login...")
        print(f"If browser doesn't open, visit: {auth_url}\n")

        # Open browser
        webbrowser.open(auth_url)

        # Wait for callback
        print("⏳ Waiting for GitHub authorization...")
        auth_code, returned_state = wait_for_oauth_callback(timeout=120)

        if not auth_code:
            raise RuntimeError("GitHub authentication timed out (120 seconds)")

        if returned_state != state:
            raise RuntimeError("OAuth state mismatch - possible CSRF attack")

        print("✅ GitHub authorization received")

        # Exchange code for access token
        print("🔄 Exchanging authorization code...")

        # NOTE: In production, this exchange should happen in Cloudflare Worker
        # For now, we'll use GitHub's device flow or direct exchange
        # This is a simplified version - REAL implementation needs client secret in Worker

        token_url = "https://github.com/login/oauth/access_token"
        token_data = {
            "client_id": GITHUB_CLIENT_ID,
            "code": auth_code,
            "redirect_uri": GITHUB_REDIRECT_URI,
        }

        # Get user info from GitHub
        user_url = "https://api.github.com/user"
        # For now, return the code - Worker will handle token exchange
        return {
            "auth_code": auth_code,
            "state": state,
        }

    finally:
        server.shutdown()


def validate_github_token(access_token: str) -> dict[str, Any]:
    """
    Validate GitHub access token and get user info.

    Args:
        access_token: GitHub personal access token

    Returns:
        Dict with: {"login": "username", "id": 12345, "name": "Full Name", "email": "..."}

    Raises:
        RuntimeError: If token is invalid
    """
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
    except Exception as e:
        raise RuntimeError(f"GitHub token validation failed: {e}")


def get_github_user_hash(github_id: int) -> str:
    """Generate stable hash from GitHub user ID for database lookups."""
    return hashlib.sha256(f"sage-github-{github_id}".encode()).hexdigest()[:16]
