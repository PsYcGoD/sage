# SAGE GUI Session Filtering Implementation

## Overview
The SAGE GUI now only displays AI-assisted sessions in the left sidebar, filtering out regular CLI commands. All commands executed by the AI agent during one request are grouped under a single session entry.

## Changes Made

### 1. Database Schema (`src/sage/store.py`)
- Added `session_id TEXT DEFAULT ''` column to `runs` table
- Added `is_ai_session INTEGER DEFAULT 0` column to `runs` table
- Updated `save_run()` function to accept these new parameters

### 2. Command Execution (`src/sage/runner.py`)
- Added `uuid` import for session ID generation
- Updated `run_command()` to accept `session_id` and `is_ai_session` parameters
- Auto-detection of AI sessions:
  - Commands containing `--claude` or `--codex`
  - Commands from `caller="mcp"` or `caller="agent"`
- Generates new session ID when not provided
- Sets `SAGE_SESSION_ID` environment variable for child processes

### 3. GUI Integration (`src/sage/gui/app.py`)
- Generates unique `session_id` for each AI interaction
- Passes session ID via `SAGE_SESSION_ID` environment variable
- Updated sidebar query to filter `WHERE is_ai_session = 1`
- Groups multiple runs with same `session_id` into single sidebar entry
- Shows run count for sessions with multiple commands (e.g., "Fix tests (3 cmds)")

### 4. MCP Tools (`src/sage/mcp/tools.py`)
- Updated `sage_call()` to inherit `SAGE_SESSION_ID` from environment
- Marks MCP commands as AI sessions

### 5. File Operations (`src/sage/fileops.py`)
- Updated `save_fileop_run()` to inherit session context
- Marks MCP file operations as AI sessions

### 6. Read/Grep Operations (`src/sage/reader.py`, `src/sage/searcher.py`)
- Updated `save_read_run()` and `save_grep_run()` to inherit session context
- Marks MCP read/grep operations as AI sessions

## Behavior

### What Shows in GUI Sidebar:
✅ `sage run --claude` (from GUI or CLI)
✅ `sage run --codex` (from GUI or CLI)  
✅ All commands executed by MCP/AI agent (grouped by session)
✅ All file operations done by AI during a session

### What Doesn't Show:
❌ Regular `sage run` commands from CLI (non-AI)
❌ Manual file operations from CLI
❌ Regular grep/read commands from CLI

### Session Grouping:
- When AI runs multiple commands to complete one request, they all share the same `session_id`
- The GUI shows them as one entry with a count: "Fix failing tests (5 cmds)"
- Clicking the session shows the first command's output (future: show all commands in session)

## Testing

To test:
1. Start SAGE GUI
2. Send a prompt to Claude/Codex
3. The AI will run multiple commands (e.g., reading files, running tests)
4. All commands should be grouped under ONE session in the left sidebar
5. Regular CLI commands (`sage run -- python test.py`) should NOT appear

## Environment Variables

- `SAGE_SESSION_ID`: Set by GUI or parent AI process, inherited by child commands
- Persists throughout the AI interaction session
- Cleared when session ends

## Future Improvements

1. **Session Detail View**: Click a session to see all commands in that session
2. **Session Metadata**: Store session start/end time, total duration
3. **Session Naming**: Allow users to name sessions or auto-generate meaningful names
4. **Session Filtering**: Filter by date, AI model, project, success/failure
5. **Session Export**: Export entire session as markdown or JSON
