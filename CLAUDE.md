

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


# Claude Instructions For SAGE

SAGE enforcement is mandatory in this repository.

## Shell Commands

Every shell command must be routed through one SAGE wrapper:

```powershell
sage run -- <command>
# or, for npm/npx installs:
npx -y psycgod-sage run -- <command>
```

Do not use bare `Bash`, bare `PowerShell`, or direct terminal commands.
If the SAGE wrapper fails before the target command starts, stop and report that wrapper failure.

## Files, Search, And Edits

Use Claude's native file/search/edit tools normally.

SAGE MCP is optional and manual only. If SAGE MCP tools are visible and connected, they may be used. If they are unavailable or disconnected, continue with native Read/Grep/Glob/Edit/Write tools. Do not block work just because MCP is down.

## Subagents

Any spawned subagent must receive the same SAGE instruction in its prompt:

```text
Use SAGE for every shell command: sage run -- <command> or npx -y psycgod-sage run -- <command>.
Use native file/search/edit tools unless optional SAGE MCP tools are manually enabled and currently connected.
Do not use bare Bash/PowerShell.
```

Project hooks block non-SAGE shell commands only.

## ML Prediction Daemon

SAGE includes a background ML daemon that predicts command failures automatically.
It auto-starts on first `sage run` command. If predictions stop appearing, restart it:

```powershell
sage serve start
```

The daemon loads the model once (~10s) then serves predictions in ~5ms per query.
Commands: `sage serve start`, `sage serve stop`, `sage serve status`.
