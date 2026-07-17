from __future__ import annotations

import json
import sys
from typing import Any


SAGE_PREFIX = "sage run --"


def _payload() -> dict[str, Any]:
    try:
        return json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return {}


def _deny(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


def main() -> int:
    payload = _payload()
    tool_name = str(payload.get("tool_name") or "")
    tool_input = payload.get("tool_input") or {}

    if tool_name in {"Bash", "Shell", "PowerShell"}:
        command = str(tool_input.get("command") or "").strip()
        if not command.startswith(SAGE_PREFIX):
            return _deny(
                "SAGE enforcement: shell commands must start with "
                "'sage run --'. "
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
