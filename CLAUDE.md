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

Use SAGE MCP tools instead of Claude's direct file tools:

- Read files with `mcp__sage__sage_read_file`
- Search with `mcp__sage__sage_grep`
- Find files with `mcp__sage__sage_glob`
- Inspect trees with `mcp__sage__sage_tree`
- Write files with `mcp__sage__sage_write_file`
- Edit files with `mcp__sage__sage_edit_file`
- Inspect raw/summary output with `mcp__sage__sage_show_raw`

Do not use direct `Read`, `Grep`, `Glob`, `Edit`, `Write`, or `NotebookEdit`.

## Subagents

Any spawned subagent must receive the same SAGE instruction in its prompt:

```text
Use SAGE for every shell command: sage run -- <command> or npx -y psycgod-sage run -- <command>.
Use SAGE MCP tools for read/search/write/edit work.
Do not use direct Read/Grep/Glob/Edit/Write or bare Bash/PowerShell.
```

Project hooks block non-SAGE shell commands and direct file tools.

## ML Prediction Daemon

SAGE includes a background ML daemon that predicts command failures automatically.
It auto-starts on first `sage run` command. If predictions stop appearing, restart it:

```powershell
sage serve start
```

The daemon loads the model once (~10s) then serves predictions in ~5ms per query.
Commands: `sage serve start`, `sage serve stop`, `sage serve status`.
