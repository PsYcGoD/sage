from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


HOOK = Path(".claude/hooks/enforce_sage.py")


def run_hook(payload: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )


def test_blocks_bare_shell_command():
    result = run_hook({"tool_name": "Bash", "tool_input": {"command": "git status"}})

    assert result.returncode == 2
    assert "shell commands must start with 'sage run --'" in result.stderr


def test_allows_sage_wrapped_shell_command():
    result = run_hook({"tool_name": "Bash", "tool_input": {"command": "sage run -- git status"}})

    assert result.returncode == 0
    assert result.stderr == ""


def test_blocks_direct_file_tool():
    result = run_hook({"tool_name": "Read", "tool_input": {"file_path": "README.md"}})

    assert result.returncode == 2
    assert "Use SAGE MCP tools instead" in result.stderr


def test_blocks_subagent_without_sage_instructions():
    result = run_hook({"tool_name": "Agent", "tool_input": {"prompt": "Inspect the repo."}})

    assert result.returncode == 2
    assert "subagent prompts must explicitly tell the agent" in result.stderr


def test_allows_subagent_with_sage_instructions():
    result = run_hook(
        {
            "tool_name": "Agent",
            "tool_input": {
                "prompt": (
                    "Use SAGE for every shell command: sage run -- <command>. "
                    "Use SAGE MCP tools such as mcp__sage__sage_read_file and "
                    "mcp__sage__sage_grep for file/search/edit work."
                )
            },
        }
    )

    assert result.returncode == 0
