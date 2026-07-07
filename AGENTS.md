# SAGE Repository Instructions

## Mandatory Shell Wrapper

SAGE is installed in this repository. Route every shell command through:

```powershell
sage run -- <command>
```

Examples:

```powershell
sage run -- git status
sage run -- python -m pytest
sage run -- npm install
```

If `sage run --` fails before the target command starts, stop and report the SAGE wrapper failure instead of bypassing it.

## Mandatory Agent Tooling

For Claude Code and other agents with native file/search/edit tools, shell wrapping is not enough. Use SAGE MCP tools for repository work:

- `mcp__sage__sage_read_file` instead of direct `Read`
- `mcp__sage__sage_grep` instead of direct `Grep`
- `mcp__sage__sage_glob` instead of direct `Glob`
- `mcp__sage__sage_tree` instead of direct tree/listing tools
- `mcp__sage__sage_write_file` and `mcp__sage__sage_edit_file` instead of direct `Write` or `Edit`

Any spawned subagent must be given the same SAGE requirements in its prompt. Do not spawn an agent without explicitly telling it to use `sage run --` and SAGE MCP tools.

## Commit Checklist

Before every Git commit that changes public copy, dashboard behavior, telemetry, proof metrics, or release material:

1. Refresh `docs/assets/sage-live-dashboard.png` from the live public dashboard.
2. Update README/announcement proof stats when visible numbers changed.
3. Verify there is no broken UTF-8/mojibake text.
4. Commit only relevant files; do not include local databases, caches, secrets, or unrelated user edits.
