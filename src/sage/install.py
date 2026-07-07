"""System-wide SAGE prompt integration after API authentication."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path


SAGE_BLOCK_START = "# SAGE MANAGED BLOCK START"
SAGE_BLOCK_END = "# SAGE MANAGED BLOCK END"

SAGE_MANDATORY_BODY = """## SAGE Integration - MANDATORY

This system has SAGE installed. You MUST route every shell command through SAGE.

Rules:
- Every shell command MUST use: `sage run -- <command>`
- Every Python command: `sage run -- python script.py`
- Every package command: `sage run -- npm install`
- Every test command: `sage run -- pytest`
- Never run bare terminal commands when SAGE is available.

Why:
- Tracks local command history for the user
- Compresses noisy output before it reaches AI context
- Captures safe proof metrics for token savings and ML prediction
- Keeps raw commands and output local unless the user enables higher telemetry

Examples:
- Wrong: `python test.py`
- Correct: `sage run -- python test.py`
- Wrong: `git status`
- Correct: `sage run -- git status`

If `sage run --` fails before the target command starts, stop and report the SAGE wrapper failure.
"""

SAGE_MANDATORY_INSTRUCTION = (
    f"{SAGE_BLOCK_START}\n{SAGE_MANDATORY_BODY.rstrip()}\n{SAGE_BLOCK_END}\n"
)

CURSOR_SAGE_INSTRUCTION = (
    f"{SAGE_BLOCK_START}\n"
    "# SAGE Integration - MANDATORY\n\n"
    "Route every terminal command through `sage run -- <command>`. "
    "Do not run bare shell commands when SAGE is available.\n"
    f"{SAGE_BLOCK_END}\n"
)

AIDER_SAGE_INSTRUCTION = (
    f"\n{SAGE_BLOCK_START}\n"
    "# SAGE Integration - MANDATORY\n"
    "# Route all shell commands through: sage run -- <command>\n"
    f"{SAGE_BLOCK_END}\n"
)


@dataclass(frozen=True)
class AgentConfigTarget:
    name: str
    path: Path
    instruction: str
    create_if_missing: bool = True


def _targets() -> list[AgentConfigTarget]:
    home = Path.home()
    return [
        AgentConfigTarget("claude", home / ".claude" / "CLAUDE.md", SAGE_MANDATORY_INSTRUCTION),
        AgentConfigTarget("codex", home / ".codex" / "AGENTS.md", SAGE_MANDATORY_INSTRUCTION),
        AgentConfigTarget("cursor", home / ".cursorrules", CURSOR_SAGE_INSTRUCTION),
        AgentConfigTarget("aider", home / ".aider.conf.yml", AIDER_SAGE_INSTRUCTION, create_if_missing=False),
    ]


def _has_sage_instruction(content: str) -> bool:
    return SAGE_BLOCK_START in content or "SAGE Integration - MANDATORY" in content


def is_sage_installed_system_wide() -> bool:
    """Return True only when the main agent configs already contain SAGE."""
    required = [target for target in _targets() if target.name in {"claude", "codex", "cursor"}]
    for target in required:
        if not target.path.exists():
            return False
        content = target.path.read_text(encoding="utf-8", errors="ignore")
        if not _has_sage_instruction(content):
            return False
    return True


def inject_sage_requirement(config_path: Path, instruction_text: str, *, create_if_missing: bool = True) -> bool:
    """Insert or refresh the managed SAGE instruction block."""
    try:
        if config_path.exists():
            content = config_path.read_text(encoding="utf-8", errors="ignore")
        elif create_if_missing:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            content = ""
        else:
            return False

        if SAGE_BLOCK_START in content and SAGE_BLOCK_END in content:
            before, rest = content.split(SAGE_BLOCK_START, 1)
            _, after = rest.split(SAGE_BLOCK_END, 1)
            new_content = before.rstrip() + "\n\n" + instruction_text.rstrip() + "\n" + after
        elif _has_sage_instruction(content):
            return False
        else:
            new_content = instruction_text.rstrip() + "\n\n" + content

        if new_content != content:
            config_path.write_text(new_content, encoding="utf-8")
            return True
        return False
    except Exception as exc:
        print(f"Warning: Could not modify {config_path}: {exc}", file=sys.stderr)
        return False


def _register_mcp_server() -> bool:
    """Register SAGE as MCP server in Claude Code settings."""
    claude_settings = Path.home() / ".claude" / "settings.json"
    
    if not claude_settings.exists():
        return False
    
    try:
        settings = json.loads(claude_settings.read_text(encoding="utf-8"))
        
        if "mcpServers" not in settings:
            settings["mcpServers"] = {}
        
        if "sage" in settings["mcpServers"]:
            return False
        
        settings["mcpServers"]["sage"] = {
            "command": "python",
            "args": ["-m", "sage.mcp.server"],
            "description": "Smart Agent Guidance Engine - Mandatory wrapper"
        }
        
        claude_settings.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        return True
    except Exception as exc:
        print(f"Warning: Could not register MCP server: {exc}", file=sys.stderr)
        return False


def install_sage_system_wide() -> dict[str, bool]:
    """
    Install SAGE prompt instructions for supported local AI tools.

    Modifies:
    - ~/.claude/CLAUDE.md
    - ~/.claude/settings.json (MCP server registration)
    - ~/.codex/AGENTS.md
    - ~/.cursorrules
    - ~/.aider.conf.yml, only when it already exists
    """
    results: dict[str, bool] = {}
    print("Installing SAGE agent configs system-wide...")

    for target in _targets():
        changed = inject_sage_requirement(
            target.path,
            target.instruction,
            create_if_missing=target.create_if_missing,
        )
        results[target.name] = changed
        if changed:
            print(f"Installed SAGE instruction for {target.name}: {target.path}")
        elif target.path.exists():
            print(f"{target.name} already has a SAGE instruction or was unchanged")
        else:
            print(f"Skipped {target.name}; config file does not exist")

    # Register MCP server for Claude Code
    mcp_registered = _register_mcp_server()
    results["mcp_server"] = mcp_registered
    if mcp_registered:
        print("Registered SAGE MCP server in Claude Code")
    else:
        print("MCP server already registered or Claude Code not found")

    print("\nSAGE prompt integration complete")
    return results


def uninstall_sage_system_wide() -> dict[str, bool]:
    """Remove managed SAGE instruction blocks from supported configs."""
    results: dict[str, bool] = {}

    for target in _targets():
        if not target.path.exists():
            results[target.name] = False
            continue

        try:
            content = target.path.read_text(encoding="utf-8", errors="ignore")
            if SAGE_BLOCK_START not in content or SAGE_BLOCK_END not in content:
                results[target.name] = False
                continue
            before, rest = content.split(SAGE_BLOCK_START, 1)
            _, after = rest.split(SAGE_BLOCK_END, 1)
            target.path.write_text((before.rstrip() + "\n" + after.lstrip()).strip() + "\n", encoding="utf-8")
            results[target.name] = True
        except Exception as exc:
            print(f"Warning: Could not modify {target.path}: {exc}", file=sys.stderr)
            results[target.name] = False

    return results
