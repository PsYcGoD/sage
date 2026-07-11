"""System-wide and per-project SAGE agent enforcement."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent


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

For agents with native file/search/edit tools, shell wrapping is not enough. Use SAGE MCP tools for repository work:
- `mcp__sage__sage_read_file` instead of direct `Read`
- `mcp__sage__sage_grep` instead of direct `Grep`
- `mcp__sage__sage_glob` instead of direct `Glob`
- `mcp__sage__sage_tree` instead of direct tree/listing tools
- `mcp__sage__sage_write_file` and `mcp__sage__sage_edit_file` instead of direct `Write` or `Edit`

Any spawned subagent must be given the same SAGE requirements in its prompt. Do not spawn an agent without explicitly telling it to use `sage run --` and SAGE MCP tools.
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

CLINE_SAGE_INSTRUCTION = (
    "# SAGE Integration - MANDATORY\n"
    "All terminal commands MUST use: sage run -- <command>\n"
    "Examples: sage run -- npm install, sage run -- python script.py\n"
)

CONTINUE_SAGE_INSTRUCTION = (
    "# SAGE Integration - MANDATORY\n"
    "All terminal commands MUST use: sage run -- <command>\n"
    "Examples: sage run -- npm install, sage run -- python script.py\n"
)

JETBRAINS_SAGE_INSTRUCTION = (
    "# SAGE Integration - MANDATORY\n"
    "All terminal commands MUST use: sage run -- <command>\n"
    "Examples: sage run -- npm install, sage run -- python script.py\n"
)

OPENCODE_SAGE_INSTRUCTION = (
    "# SAGE Integration - MANDATORY\n"
    "All terminal commands MUST use: sage run -- <command>\n"
)
CLAUDE_HOOK_SCRIPT = dedent(
    r'''
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

        if tool_name in {"Bash", "Shell", "PowerShell"}:
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
    '''
).lstrip()

CLAUDE_SETTINGS = {
    "permissions": {
        "allow": [
            "Bash(sage run -- *)",
            "PowerShell(sage run -- *)",
            "mcp__sage__sage_call",
            "mcp__sage__sage_edit_file",
            "mcp__sage__sage_explain_error",
            "mcp__sage__sage_get_history",
            "mcp__sage__sage_glob",
            "mcp__sage__sage_grep",
            "mcp__sage__sage_read_file",
            "mcp__sage__sage_run_workflow",
            "mcp__sage__sage_show_raw",
            "mcp__sage__sage_spawn_agent",
            "mcp__sage__sage_suggest_fix",
            "mcp__sage__sage_tree",
            "mcp__sage__sage_write_file",
        ],
        "deny": [
            "Bash(*)",
            "PowerShell(*)",
            "Read(*)",
            "Grep(*)",
            "Glob(*)",
            "Edit(*)",
            "Write(*)",
            "NotebookEdit(*)",
        ],
    },
    "hooks": {
        "PreToolUse": [
            {
                "matcher": "Bash|Shell|PowerShell|Read|Grep|Glob|Write|Edit|MultiEdit|NotebookRead|NotebookEdit|Agent",
                "hooks": [
                    {
                        "type": "command",
                        "command": "python .claude/hooks/enforce_sage.py",
                    }
                ],
            }
        ]
    },
}


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
        AgentConfigTarget("windsurf", home / ".windsurfrules", SAGE_MANDATORY_INSTRUCTION),
        AgentConfigTarget("cline", home / ".cline" / "AGENTS.md", SAGE_MANDATORY_INSTRUCTION),
        AgentConfigTarget("opencode", home / ".config" / "opencode" / "AGENTS.md", SAGE_MANDATORY_INSTRUCTION),
        AgentConfigTarget("aider", home / ".aider.conf.yml", AIDER_SAGE_INSTRUCTION, create_if_missing=False),
        AgentConfigTarget("cline", home / ".clinerules", CLINE_SAGE_INSTRUCTION),
        AgentConfigTarget("continue", home / ".continue" / "config.json", CONTINUE_SAGE_INSTRUCTION, create_if_missing=False),
        AgentConfigTarget("jetbrains", home / ".junie" / "guidelines.md", JETBRAINS_SAGE_INSTRUCTION),
        AgentConfigTarget("opencode", home / ".opencode" / "AGENTS.md", OPENCODE_SAGE_INSTRUCTION),
    ]


def _has_sage_instruction(content: str) -> bool:
    return SAGE_BLOCK_START in content or "SAGE Integration - MANDATORY" in content


def is_sage_installed_system_wide() -> bool:
    """Return True only when the main agent configs already contain SAGE."""
    required = [target for target in _targets() if target.name in {"claude", "codex", "cursor", "cline", "jetbrains", "opencode"}]
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


def _merge_json_file(path: Path, patch: dict) -> bool:
    """Deep-merge a JSON config file, creating it when needed."""
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8") or "{}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            data = {}

        original = json.dumps(data, sort_keys=True)

        def merge(dst: dict, src: dict) -> None:
            for key, value in src.items():
                if isinstance(value, dict) and isinstance(dst.get(key), dict):
                    merge(dst[key], value)
                elif isinstance(value, list) and isinstance(dst.get(key), list):
                    existing = dst[key]
                    for item in value:
                        if item not in existing:
                            existing.append(item)
                else:
                    dst[key] = value

        merge(data, patch)
        if json.dumps(data, sort_keys=True) == original:
            return False
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return True
    except Exception as exc:
        print(f"Warning: Could not modify {path}: {exc}", file=sys.stderr)
        return False


def _install_claude_enforcement(root: Path) -> dict[str, bool]:
    """Install Claude Code permissions and PreToolUse hook under root."""
    claude_dir = root / ".claude"
    hook_path = claude_dir / "hooks" / "enforce_sage.py"
    settings_path = claude_dir / "settings.json"
    local_settings_path = claude_dir / "settings.local.json"
    results: dict[str, bool] = {}

    hook_path.parent.mkdir(parents=True, exist_ok=True)
    existing_hook = hook_path.read_text(encoding="utf-8", errors="ignore") if hook_path.exists() else ""
    if existing_hook != CLAUDE_HOOK_SCRIPT:
        hook_path.write_text(CLAUDE_HOOK_SCRIPT, encoding="utf-8")
        results["claude_hook"] = True
    else:
        results["claude_hook"] = False

    results["claude_settings"] = _merge_json_file(settings_path, CLAUDE_SETTINGS)
    results["claude_local_settings"] = _merge_json_file(local_settings_path, CLAUDE_SETTINGS)
    return results


def _register_mcp_server() -> bool:
    """Register SAGE as MCP server in Claude Code settings."""
    claude_settings = Path.home() / ".claude" / "settings.json"
    
    try:
        settings = json.loads(claude_settings.read_text(encoding="utf-8")) if claude_settings.exists() else {}
        
        if "mcpServers" not in settings:
            settings["mcpServers"] = {}
        
        if "sage" in settings["mcpServers"]:
            return False
        
        settings["mcpServers"]["sage"] = {
            "command": "python",
            "args": ["-m", "sage.mcp.server"],
            "description": "Smart Agent Guidance Engine - Mandatory wrapper"
        }
        
        claude_settings.parent.mkdir(parents=True, exist_ok=True)
        claude_settings.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
        return True
    except Exception as exc:
        print(f"Warning: Could not register MCP server: {exc}", file=sys.stderr)
        return False


def install_sage_system_wide(*, verbose: bool = True) -> dict[str, bool]:
    """
    Install SAGE prompt instructions for supported local AI tools.

    Modifies:
    - ~/.claude/CLAUDE.md
    - ~/.claude/settings.json (MCP server registration)
    - ~/.codex/AGENTS.md
    - ~/.cursorrules
    - ~/.windsurfrules
    - ~/.cline/AGENTS.md
    - ~/.config/opencode/AGENTS.md
    - ~/.aider.conf.yml, only when it already exists
    """
    results: dict[str, bool] = {}
    if verbose:
        print("Installing SAGE agent configs system-wide...")

    for target in _targets():
        changed = inject_sage_requirement(
            target.path,
            target.instruction,
            create_if_missing=target.create_if_missing,
        )
        results[target.name] = changed
        if verbose:
            if changed:
                print(f"Installed SAGE instruction for {target.name}: {target.path}")
            elif target.path.exists():
                print(f"{target.name} already has a SAGE instruction or was unchanged")
            else:
                print(f"Skipped {target.name}; config file does not exist")

    claude_results = _install_claude_enforcement(Path.home())
    results.update(claude_results)
    if verbose:
        for name, changed in claude_results.items():
            print(f"{'Installed' if changed else 'Verified'} {name.replace('_', ' ')}")

    # Register MCP server for Claude Code
    mcp_registered = _register_mcp_server()
    results["mcp_server"] = mcp_registered
    if verbose:
        if mcp_registered:
            print("Registered SAGE MCP server in Claude Code")
        else:
            print("MCP server already registered or Claude Code not found")

    if verbose:
        print("\nSAGE prompt integration complete")
    return results


def install_sage_project(root: Path | None = None) -> dict[str, bool]:
    """Install mandatory SAGE instructions and Claude hook into a project."""
    project_root = root or Path.cwd()
    project_root.mkdir(parents=True, exist_ok=True)
    results: dict[str, bool] = {}
    project_targets = [
        AgentConfigTarget("agents_md", project_root / "AGENTS.md", SAGE_MANDATORY_INSTRUCTION),
        AgentConfigTarget("claude_md", project_root / "CLAUDE.md", SAGE_MANDATORY_INSTRUCTION),
        AgentConfigTarget("sage_md", project_root / "SAGE.md", SAGE_MANDATORY_INSTRUCTION),
    ]

    for target in project_targets:
        results[target.name] = inject_sage_requirement(target.path, target.instruction)

    results.update(_install_claude_enforcement(project_root))
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
