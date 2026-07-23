from __future__ import annotations

import json
import sys
from typing import Any


SAGE_PREFIX = "sage run --"

# Every wrapper form documented in CLAUDE.md and allowed in settings.json.
# The hook must accept the whole fallback chain, otherwise the agent has no
# permitted path when the primary `sage` script is unavailable.
SAGE_WRAPPER_PREFIXES = (
    "sage run --",
    "python -m sage run --",
    "python3 -m sage run --",
    "py -m sage run --",
    "py -3 -m sage run --",
    "npx -y psycgod-sage run --",
    "npx psycgod-sage run --",
)


def _payload() -> dict[str, Any]:
    try:
        return json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return {}


def _deny(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


def _is_sage_wrapped(command: str) -> bool:
    lowered = command.strip().lower()
    return any(lowered.startswith(prefix) for prefix in SAGE_WRAPPER_PREFIXES)


def main() -> int:
    payload = _payload()
    tool_name = str(payload.get("tool_name") or "")
    tool_input = payload.get("tool_input") or {}

    if tool_name in {"Bash", "Shell", "PowerShell"}:
        command = str(tool_input.get("command") or "").strip()
        if not _is_sage_wrapped(command):
            return _deny(
                "SAGE enforcement: prefix the exact same command with "
                "'sage run -- ' and retry once (fallbacks: 'python -m sage run -- ' "
                "or 'npx -y psycgod-sage run -- '). "
                "The blocked command is intentionally not printed to avoid leaking secrets."
            )

    if tool_name == "Agent":
        prompt = str(tool_input.get("prompt") or "")
        if SAGE_PREFIX not in prompt.lower():
            return _deny(
                "SAGE enforcement: subagent prompts must explicitly tell the agent "
                "to route terminal commands through 'sage run --'."
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
