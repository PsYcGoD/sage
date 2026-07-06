from __future__ import annotations

import json
import re
import sys


def _block(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def _text(value: object) -> str:
    return str(value or "")


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        return 0

    try:
        event = json.loads(raw)
    except json.JSONDecodeError as exc:
        _block(f"SAGE enforcement hook could not parse Claude hook JSON: {exc}")

    tool_name = _text(
        event.get("tool_name")
        or event.get("toolName")
        or event.get("tool")
    )
    tool_input = (
        event.get("tool_input")
        or event.get("toolInput")
        or event.get("input")
        or {}
    )
    if not isinstance(tool_input, dict):
        tool_input = {}

    direct_file_tools = {"Read", "Grep", "Glob", "Edit", "Write", "NotebookEdit"}
    if tool_name in direct_file_tools:
        _block(
            "SAGE REQUIRED: Claude tried to use direct tool "
            f"'{tool_name}'. Use SAGE MCP tools instead: "
            "mcp__sage__sage_read_file, mcp__sage__sage_grep, "
            "mcp__sage__sage_glob, mcp__sage__sage_tree, "
            "mcp__sage__sage_write_file, or mcp__sage__sage_edit_file."
        )

    if tool_name in {"Bash", "PowerShell"}:
        command = _text(
            tool_input.get("command")
            or tool_input.get("cmd")
            or tool_input.get("script")
        ).strip()
        if not re.match(r"(?i)^sage\s+run\s+--(?:\s|$)", command):
            _block(
                "SAGE REQUIRED: shell commands must start with "
                f"'sage run --'. Blocked command: {command}"
            )

    if tool_name in {"Agent", "Task"}:
        prompt = _text(
            tool_input.get("prompt")
            or tool_input.get("description")
            or tool_input.get("task")
            or tool_input.get("instructions")
        )
        mentions_sage_shell = re.search(r"(?i)sage\s+run\s+--", prompt)
        mentions_sage_mcp = re.search(r"mcp__sage__", prompt)
        if not (mentions_sage_shell and mentions_sage_mcp):
            _block(
                "SAGE REQUIRED: subagent prompts must explicitly tell the "
                "agent to use 'sage run --' for shell and SAGE MCP tools "
                "for file/search/edit operations."
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
