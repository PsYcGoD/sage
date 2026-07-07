from __future__ import annotations

import json
import sys
from typing import Any


SAGE_PREFIX = "sage run --"
FILE_TOOLS = {
    "Read",
    "Grep",
    "Glob",
    "Write",
    "Edit",
    "MultiEdit",
    "NotebookRead",
    "NotebookEdit",
}


def _payload() -> dict[str, Any]:
    try:
        return json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return {}


def _deny(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


def _allows_subagent(prompt: str) -> bool:
    lowered = prompt.lower()
    return SAGE_PREFIX in lowered and "mcp__sage__" in lowered


def main() -> int:
    payload = _payload()
    tool_name = str(payload.get("tool_name") or "")
    tool_input = payload.get("tool_input") or {}

    if tool_name in {"Bash", "Shell"}:
        command = str(tool_input.get("command") or "").strip()
        if not command.startswith(SAGE_PREFIX):
            return _deny("SAGE enforcement: shell commands must start with 'sage run --'.")

    if tool_name in FILE_TOOLS:
        return _deny("SAGE enforcement: Use SAGE MCP tools instead of direct file/search/edit tools.")

    if tool_name == "Agent":
        prompt = str(tool_input.get("prompt") or "")
        if not _allows_subagent(prompt):
            return _deny(
                "SAGE enforcement: subagent prompts must explicitly tell the agent "
                "to use 'sage run --' and SAGE MCP tools."
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
