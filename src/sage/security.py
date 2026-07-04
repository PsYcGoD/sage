from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .store import data_dir


DEFAULT_POLICY = {
    "mode": "personal",
    "redaction_strictness": "standard",
    "retain_raw_days": 30,
    "allowlist": [],
    "denylist": [
        "format",
        "diskpart",
        "cipher /w",
        "Remove-Item -Recurse -Force C:\\",
        "rm -rf /",
        "git reset --hard",
    ],
    "confirm_required": [
        "rm ",
        "del ",
        "erase ",
        "Remove-Item",
        "rmdir",
        "git clean",
        "git reset",
        "pip uninstall",
        "npm uninstall",
    ],
    "encryption_at_rest": False,
}


SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
    ("github_token", re.compile(r"\bgh[opsu]_[A-Za-z0-9_]{20,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b")),
    ("bearer_token", re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{16,}")),
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S)),
    ("password_assignment", re.compile(r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key)\s*[:=]\s*['\"]?[^'\"\s]{6,}")),
]


@dataclass(frozen=True)
class RedactionResult:
    text: str
    count: int
    labels: tuple[str, ...]


@dataclass(frozen=True)
class PolicyDecision:
    mode: str
    decision: str
    reason: str
    risky: bool = False


def policy_path() -> Path:
    return data_dir() / "security-policy.json"


def load_policy() -> dict[str, Any]:
    path = policy_path()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(DEFAULT_POLICY, indent=2), encoding="utf-8")
        return dict(DEFAULT_POLICY)
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        loaded = {}
    merged = dict(DEFAULT_POLICY)
    if isinstance(loaded, dict):
        merged.update(loaded)
    return merged


def save_policy(policy: dict[str, Any]) -> None:
    path = policy_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(policy, indent=2), encoding="utf-8")


def command_hash(command: str) -> str:
    return hashlib.sha256(command.encode("utf-8", errors="replace")).hexdigest()


def redact_text(text: str, *, strictness: str = "standard") -> RedactionResult:
    if not text:
        return RedactionResult(text="", count=0, labels=())

    redacted = text
    labels: list[str] = []
    count = 0
    patterns = SECRET_PATTERNS
    if strictness == "strict":
        patterns = patterns + [
            ("long_token", re.compile(r"\b[A-Za-z0-9_./+=-]{40,}\b")),
            ("url_secret", re.compile(r"(?i)([?&](?:key|token|secret|sig|signature)=)[^&\s]+")),
        ]

    for label, pattern in patterns:
        redacted, replacements = pattern.subn(lambda m: _replacement(label, m), redacted)
        if replacements:
            count += replacements
            labels.append(label)

    return RedactionResult(text=redacted, count=count, labels=tuple(sorted(set(labels))))


def _replacement(label: str, match: re.Match[str]) -> str:
    if label == "url_secret":
        return f"{match.group(1)}[REDACTED:{label}]"
    return f"[REDACTED:{label}]"


def evaluate_command(command: str, *, mode: str | None = None, dry_run: bool = False) -> PolicyDecision:
    policy = load_policy()
    policy_mode = mode or str(policy.get("mode") or "personal")
    text = command.lower()

    for item in policy.get("denylist", []):
        if item and _matches_policy_item(text, str(item).lower()):
            return PolicyDecision(policy_mode, "blocked", f"matched denylist: {item}", risky=True)

    risky_match = ""
    for item in policy.get("confirm_required", []):
        if item and str(item).lower() in text:
            risky_match = str(item)
            break

    if dry_run:
        reason = f"dry-run only; would execute under {policy_mode} policy"
        if risky_match:
            reason += f"; risky pattern: {risky_match}"
        return PolicyDecision(policy_mode, "dry_run", reason, risky=bool(risky_match))

    if policy_mode == "company" and risky_match and os.environ.get("SAGE_APPROVE_RISK") != "1":
        return PolicyDecision(
            policy_mode,
            "blocked",
            f"company mode requires SAGE_APPROVE_RISK=1 for: {risky_match}",
            risky=True,
        )

    if risky_match:
        return PolicyDecision(policy_mode, "allowed_with_warning", f"risky pattern: {risky_match}", risky=True)
    return PolicyDecision(policy_mode, "allowed", "no policy risk detected", risky=False)


def _matches_policy_item(command_text: str, item: str) -> bool:
    """Match policy entries without triggering on flag substrings.

    Example: denylist item `format` should block `format D:` but must not block
    Claude's `--output-format stream-json`.
    """
    if not item:
        return False
    if re.fullmatch(r"[a-z0-9_.]+", item):
        return re.search(rf"(?<![\w-]){re.escape(item)}(?![\w-])", command_text) is not None
    return item in command_text


def retention_expiry() -> str:
    policy = load_policy()
    days = int(policy.get("retain_raw_days") or 30)
    return (datetime.now(timezone.utc) + timedelta(days=max(0, days))).isoformat(timespec="seconds")
