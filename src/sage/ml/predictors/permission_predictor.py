"""Permission Denied Predictor - detects commands needing elevated privileges."""

from __future__ import annotations

import os
import re
import sys
from typing import Optional

from .base import BasePredictor, Prediction

NEEDS_ADMIN_PATTERNS = (
    r"^npm install -g\b",
    r"^npm i -g\b",
    r"^yarn global\b",
    r"^pip install(?!.*--user)",
    r"^pip3 install(?!.*--user)",
    r"^gem install\b",
    r"^apt ",
    r"^apt-get ",
    r"^yum ",
    r"^dnf ",
    r"^pacman ",
    r"^systemctl ",
    r"^service ",
    r"^mount ",
    r"^umount ",
    r"^chmod .*/usr/",
    r"^chown ",
    r"^iptables ",
)

PROTECTED_PATHS = ("/usr/local", "/usr/bin", "/etc/", "/var/", "/opt/", "C:\\Program Files")


class PermissionPredictor(BasePredictor):
    """Detects commands that need sudo/admin privileges."""

    CATEGORY = "permission_denied"

    def predict(self, command: str, **context) -> Optional[Prediction]:
        cmd_lower = command.lower().strip()
        if not cmd_lower:
            return None

        # Already has sudo/admin - no issue
        if cmd_lower.startswith(("sudo ", "runas ", "gsudo ")):
            return None

        reasons = []
        probability = 0.0
        suggestion = None

        # Check regex patterns
        for pattern in NEEDS_ADMIN_PATTERNS:
            if re.search(pattern, cmd_lower):
                reasons.append(f"Command typically requires elevated privileges")
                probability = max(probability, 0.70)
                if sys.platform == "win32":
                    suggestion = "Run as Administrator or use: gsudo"
                else:
                    suggestion = f"Try: sudo {command}"
                break

        # Writing to protected paths
        parts = command.split()
        for part in parts:
            for protected in PROTECTED_PATHS:
                if part.startswith(protected) or part.startswith(protected.lower()):
                    reasons.append(f"Writes to protected path: {protected}")
                    probability = max(probability, 0.80)
                    if sys.platform == "win32":
                        suggestion = "Run as Administrator"
                    else:
                        suggestion = f"Try: sudo {command}"
                    break

        # Port < 1024 binding
        port_match = re.search(r"(?:--port|--listen|-p)\s*(\d+)", command)
        if port_match:
            port = int(port_match.group(1))
            if port < 1024 and os.name != "nt":
                reasons.append(f"Binding port {port} requires root")
                probability = max(probability, 0.85)
                suggestion = f"Use port >= 1024 or: sudo {command}"

        # npm global without prefix on non-Windows
        if "npm install -g" in cmd_lower or "npm i -g" in cmd_lower:
            if sys.platform != "win32":
                npm_prefix = os.environ.get("NPM_CONFIG_PREFIX", "")
                if not npm_prefix or npm_prefix.startswith("/usr"):
                    reasons.append("npm global install to system prefix")
                    probability = max(probability, 0.80)
                    suggestion = "Try: npm install -g --prefix ~/.npm-global or use sudo"

        if not reasons:
            return None

        return Prediction(
            category=self.CATEGORY,
            probability=probability,
            will_trigger=probability >= 0.65,
            reason="; ".join(reasons),
            suggestion=suggestion,
        )
