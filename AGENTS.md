

# SAGE MANAGED BLOCK START
## SAGE Integration - MANDATORY

When a user asks for any coding, repo, file, debugging, documentation, or project task, start through SAGE automatically. The user should not need to type `sage`.

First actions for normal repo work:
- Use native file/search/edit tools normally.
- Route every terminal command through the PyPI SAGE wrapper: `sage run -- <command>`.
- For multi-line file writes/appends, use native Write/Edit tools. Do not use shell heredocs through `sage run`; heredocs are shell-specific and can fail through wrappers/monitors.

Route every shell command through SAGE. Do not run bare terminal commands.

Allowed wrapper:
- `sage run -- <command>`

Rules:
- Python: `sage run -- python script.py`
- Packages: `sage run -- npm install`
- Tests: `sage run -- pytest`
- If the wrapper fails before the target command starts, stop and report the wrapper failure.

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

Example user request:
- User: "Please help me with my general book in this folder"
- Correct agent start: inspect/read/edit files with available native tools, then use `sage run -- <command>` only when a terminal command is needed.
- Wrong agent start: bare `python`, `git`, `npm`, `ls`, or other terminal commands without SAGE.

Any spawned subagent must be given the same SAGE shell-wrapper requirement in its prompt.
# SAGE MANAGED BLOCK END


# SAGE Repository Instructions

## Mandatory Shell Wrapper

SAGE is installed in this repository. Route every shell command through the PyPI SAGE wrapper:

```powershell
sage run -- <command>
```

Examples:

```powershell
sage run -- git status
sage run -- python -m pytest
sage run -- npm install
```

If the SAGE wrapper fails before the target command starts, stop and report the wrapper failure instead of bypassing it.

## Agent Tooling

Use native file/search/edit tools normally.

- The mandatory rule is for terminal commands: route shell commands through `sage run -- <command>`.
- Multi-line file writes/appends should use native Write/Edit tools, not shell heredocs through `sage run`.

Any spawned subagent must be given the same SAGE shell-wrapper requirement in its prompt.

## Commit Checklist

Before every Git commit that changes public copy, dashboard behavior, telemetry, proof metrics, or release material:

1. Refresh `docs/assets/sage-live-dashboard.png` from the live public dashboard.
2. Update README/announcement proof stats when visible numbers changed.
3. Verify there is no broken UTF-8/mojibake text.
4. Commit only relevant files; do not include local databases, caches, secrets, or unrelated user edits.
