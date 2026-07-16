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

When a user asks for any coding, repo, file, debugging, documentation, or project task, start through SAGE automatically. The user should not need to type `sage`.

First actions for normal repo work:
- Route every terminal command through a SAGE wrapper
- Use native file/search/edit tools normally unless the user has manually installed and enabled the optional SAGE MCP server.

Route every shell command through SAGE. Do not run bare terminal commands.

Allowed wrappers:
- PyPI/pip install: `sage run -- <command>`
- npm/npx install: `npx -y psycgod-sage run -- <command>`

Rules:
- Python: `sage run -- python script.py` or `npx -y psycgod-sage run -- python script.py`
- Packages: `sage run -- npm install` or `npx -y psycgod-sage run -- npm install`
- Tests: `sage run -- pytest` or `npx -y psycgod-sage run -- pytest`
- If the wrapper fails before the target command starts, stop and report the wrapper failure.

Why:
- Tracks local command history for the user
- Compresses noisy output before it reaches AI context
- Captures safe proof metrics for token savings and ML prediction
- Keeps raw commands and output local unless the user enables higher telemetry

Examples:
- Wrong: `python test.py`
- Correct: `sage run -- python test.py`
- Correct with npm/npx: `npx -y psycgod-sage run -- python test.py`
- Wrong: `git status`
- Correct: `sage run -- git status`

Optional MCP:
- SAGE MCP is not auto-enabled because MCP stdio sessions can disconnect in long-running AI-agent sessions.
- If SAGE MCP tools are manually installed and visible, you may use them.
- If SAGE MCP tools are unavailable or disconnected, keep working with native file/search/edit tools and continue wrapping terminal commands through SAGE.

Example user request:
- User: "Please help me with my general book in this folder"
- Correct agent start: inspect/read/edit files with available native tools, then use `sage run -- <command>` only when a terminal command is needed.
- Wrong agent start: bare `python`, `git`, `npm`, `ls`, or other terminal commands without SAGE.

Any spawned subagent must be given the same SAGE shell-wrapper requirement in its prompt. Do not require MCP tools unless the user manually enabled SAGE MCP and the tools are currently connected.
"""

SAGE_MANDATORY_INSTRUCTION = (
    f"{SAGE_BLOCK_START}\n{SAGE_MANDATORY_BODY.rstrip()}\n{SAGE_BLOCK_END}\n"
)

CURSOR_SAGE_INSTRUCTION = (
    f"{SAGE_BLOCK_START}\n"
    "# SAGE Integration - MANDATORY\n\n"
    "Route every terminal command through `sage run -- <command>` or "
    "`npx -y psycgod-sage run -- <command>`. "
    "Do not run bare shell commands when SAGE is available.\n"
    f"{SAGE_BLOCK_END}\n"
)

AIDER_SAGE_INSTRUCTION = (
    f"\n{SAGE_BLOCK_START}\n"
    "# SAGE Integration - MANDATORY\n"
    "# Route all shell commands through: sage run -- <command>\n"
    "# Or with npm/npx: npx -y psycgod-sage run -- <command>\n"
    f"{SAGE_BLOCK_END}\n"
)

CLINE_SAGE_INSTRUCTION = (
    "# SAGE Integration - MANDATORY\n"
    "All terminal commands MUST use: sage run -- <command> or npx -y psycgod-sage run -- <command>\n"
    "Examples: sage run -- npm install, npx -y psycgod-sage run -- python script.py\n"
)

CONTINUE_SAGE_INSTRUCTION = (
    "# SAGE Integration - MANDATORY\n"
    "All terminal commands MUST use: sage run -- <command> or npx -y psycgod-sage run -- <command>\n"
    "Examples: sage run -- npm install, npx -y psycgod-sage run -- python script.py\n"
)

JETBRAINS_SAGE_INSTRUCTION = (
    "# SAGE Integration - MANDATORY\n"
    "All terminal commands MUST use: sage run -- <command> or npx -y psycgod-sage run -- <command>\n"
    "Examples: sage run -- npm install, npx -y psycgod-sage run -- python script.py\n"
)

OPENCODE_SAGE_INSTRUCTION = (
    "# SAGE Integration - MANDATORY\n"
    "All terminal commands MUST use: sage run -- <command> or npx -y psycgod-sage run -- <command>\n"
)
CLAUDE_HOOK_SCRIPT = dedent(
    r'''
    from __future__ import annotations

    import json
    import sys
    from typing import Any


    SAGE_PREFIXES = ("sage run --", "npx -y psycgod-sage run --")


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
            if not any(command.startswith(prefix) for prefix in SAGE_PREFIXES):
                return _deny(
                    "SAGE enforcement: shell commands must start with "
                    "'sage run --' or 'npx -y psycgod-sage run --'. "
                    "The blocked command is intentionally not printed to avoid leaking secrets."
                )

        if tool_name == "Agent":
            prompt = str(tool_input.get("prompt") or "")
            if not any(prefix in prompt.lower() for prefix in SAGE_PREFIXES):
                return _deny(
                    "SAGE enforcement: subagent prompts must explicitly tell the agent "
                    "to route terminal commands through a SAGE wrapper."
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
            "Bash(npx -y psycgod-sage run -- *)",
            "PowerShell(sage run -- *)",
            "PowerShell(npx -y psycgod-sage run -- *)",
        ],
        "deny": [
            "Bash(*)",
            "PowerShell(*)",
        ],
    },
    "hooks": {
        "PreToolUse": [
            {
                "matcher": "Bash|Shell|PowerShell|Agent",
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


def _repair_claude_settings(path: Path) -> bool:
    """Remove stale auto-MCP and native-tool denies from old SAGE injections."""
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8") or "{}")
    except Exception as exc:
        print(f"Warning: Could not read {path}: {exc}", file=sys.stderr)
        return False

    original = json.dumps(data, sort_keys=True)
    permissions = data.get("permissions")
    if isinstance(permissions, dict):
        stale_denies = {
            "Read(*)",
            "Grep(*)",
            "Glob(*)",
            "Edit(*)",
            "Write(*)",
            "MultiEdit(*)",
            "NotebookRead(*)",
            "NotebookEdit(*)",
        }
        deny = permissions.get("deny")
        if isinstance(deny, list):
            permissions["deny"] = [item for item in deny if item not in stale_denies]
        allow = permissions.get("allow")
        if isinstance(allow, list):
            permissions["allow"] = [
                item for item in allow
                if not (isinstance(item, str) and item.startswith("mcp__sage__"))
            ]

    mcp_servers = data.get("mcpServers")
    if isinstance(mcp_servers, dict) and "sage" in mcp_servers:
        mcp_servers.pop("sage", None)
        if not mcp_servers:
            data.pop("mcpServers", None)

    if json.dumps(data, sort_keys=True) == original:
        return False
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return True


def _shell_path(path: Path) -> str:
    """Return a shell-friendly path for hook commands on Windows and POSIX."""
    return '"' + str(path).replace('"', '\\"') + '"'


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

    settings = json.loads(json.dumps(CLAUDE_SETTINGS))
    settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"] = f"python {_shell_path(hook_path)}"
    results["claude_settings"] = _merge_json_file(settings_path, settings)
    results["claude_local_settings"] = _merge_json_file(local_settings_path, settings)
    results["claude_settings_repair"] = _repair_claude_settings(settings_path)
    results["claude_local_settings_repair"] = _repair_claude_settings(local_settings_path)
    return results


def install_sage_system_wide(*, verbose: bool = True) -> dict[str, bool]:
    """
    Install SAGE prompt instructions for supported local AI tools.

    Modifies:
    - ~/.claude/CLAUDE.md
    - ~/.claude/settings.json (shell-wrapper hook only; MCP is manual)
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
