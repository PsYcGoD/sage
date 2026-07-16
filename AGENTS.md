

# SAGE MANAGED BLOCK START
## SAGE Integration - MANDATORY

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
# SAGE MANAGED BLOCK END


# SAGE Repository Instructions

## Mandatory Shell Wrapper

SAGE is installed in this repository. Route every shell command through one SAGE wrapper:

```powershell
sage run -- <command>
# or, for npm/npx installs:
npx -y psycgod-sage run -- <command>
```

Examples:

```powershell
sage run -- git status
sage run -- python -m pytest
sage run -- npm install
npx -y psycgod-sage run -- git status
```

If the SAGE wrapper fails before the target command starts, stop and report the wrapper failure instead of bypassing it.

## Agent Tooling

Use native file/search/edit tools normally. SAGE MCP is optional and manual only; do not require it for repository work because MCP sessions can disconnect in long-running AI-agent sessions.

- If SAGE MCP tools are visible and connected, they may be used.
- If SAGE MCP tools are unavailable or disconnected, continue with native Read/Grep/Glob/Edit/Write tools.
- The mandatory rule is for terminal commands: route shell commands through `sage run -- <command>` or `npx -y psycgod-sage run -- <command>`.
- Multi-line file writes/appends should use native Write/Edit tools, not shell heredocs through `sage run`.

Any spawned subagent must be given the same SAGE shell-wrapper requirement in its prompt. Do not require MCP tools unless the user manually enabled SAGE MCP and the tools are currently connected.

## Commit Checklist

Before every Git commit that changes public copy, dashboard behavior, telemetry, proof metrics, or release material:

1. Refresh `docs/assets/sage-live-dashboard.png` from the live public dashboard.
2. Update README/announcement proof stats when visible numbers changed.
3. Verify there is no broken UTF-8/mojibake text.
4. Commit only relevant files; do not include local databases, caches, secrets, or unrelated user edits.
