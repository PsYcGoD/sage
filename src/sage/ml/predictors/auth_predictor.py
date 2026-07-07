"""Auth Failure Predictor - detects commands likely to fail due to auth issues."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Optional

from .base import BasePredictor, Prediction

AUTH_COMMANDS = {
    "git push", "git pull", "git fetch", "git clone",
    "aws ", "gcloud ", "az ",
    "docker push", "docker pull",
    "kubectl", "helm",
    "ssh ", "scp ",
    "gh pr", "gh issue", "gh repo",
}

AUTH_ERROR_PATTERNS = (
    "permission denied",
    "unauthorized",
    "authentication failed",
    "could not read from remote",
    "403",
    "401",
    "invalid credentials",
    "access denied",
    "fatal: could not read",
)


class AuthPredictor(BasePredictor):
    """Detects commands likely to fail due to authentication/authorization issues."""

    CATEGORY = "auth_failure"

    def predict(self, command: str, **context) -> Optional[Prediction]:
        cmd_lower = command.lower().strip()
        if not cmd_lower:
            return None

        reasons = []
        probability = 0.0
        suggestion = None

        # Check if this is an auth-sensitive command
        is_auth_cmd = any(cmd_lower.startswith(ac) for ac in AUTH_COMMANDS)
        if not is_auth_cmd:
            return None

        # Git push/pull without SSH key or credential helper
        if cmd_lower.startswith(("git push", "git pull", "git fetch")):
            # Check for SSH agent
            if not os.environ.get("SSH_AUTH_SOCK") and not os.environ.get("SSH_AGENT_PID"):
                # Check if .git/config uses SSH
                git_config = Path(".git/config")
                if git_config.exists():
                    config_text = git_config.read_text(errors="ignore")
                    if "git@" in config_text or "ssh://" in config_text:
                        reasons.append("SSH remote but no SSH_AUTH_SOCK set")
                        suggestion = "Check: ssh-add -l or eval $(ssh-agent)"
                        probability = max(probability, 0.60)

        # AWS commands without credentials
        if cmd_lower.startswith("aws "):
            if not any(os.environ.get(k) for k in ("AWS_ACCESS_KEY_ID", "AWS_PROFILE", "AWS_SESSION_TOKEN")):
                aws_creds = Path.home() / ".aws" / "credentials"
                if not aws_creds.exists():
                    reasons.append("No AWS credentials found")
                    suggestion = "Run: aws configure"
                    probability = max(probability, 0.85)

        # Docker push without login
        if cmd_lower.startswith("docker push"):
            docker_config = Path.home() / ".docker" / "config.json"
            if not docker_config.exists():
                reasons.append("No Docker login found")
                suggestion = "Run: docker login"
                probability = max(probability, 0.75)

        # Check command history for past auth failures
        db_path = context.get("db_path")
        if db_path:
            hist_prob = self._check_auth_history(command, db_path)
            if hist_prob > probability:
                probability = hist_prob
                reasons.append("Past auth failures with this command")

        if not reasons:
            return None

        return Prediction(
            category=self.CATEGORY,
            probability=probability,
            will_trigger=probability >= 0.60,
            reason="; ".join(reasons),
            suggestion=suggestion,
        )

    def _check_auth_history(self, command: str, db_path: Path) -> float:
        """Check if this command has failed with auth errors before."""
        try:
            base_cmd = command.split()[:2]
            pattern = " ".join(base_cmd) + "%"

            with sqlite3.connect(db_path) as conn:
                rows = conn.execute(
                    """
                    SELECT stderr FROM runs
                    WHERE command LIKE ? AND exit_code != 0
                    ORDER BY created_at DESC LIMIT 5
                    """,
                    (pattern,),
                ).fetchall()

            for row in rows:
                stderr = (row[0] or "").lower()
                if any(p in stderr for p in AUTH_ERROR_PATTERNS):
                    return 0.75
            return 0.0
        except Exception:
            return 0.0
