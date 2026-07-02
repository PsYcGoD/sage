# 🔌 SAGE MCP Integration Guide

## What is MCP?

**MCP (Model Context Protocol)** allows Claude Code and other AI tools to directly call SAGE commands as native tools.

## Quick Setup

### Step 1: Install MCP Config
```bash
cd D:\work\sage
sage mcp install
```

This creates: `C:\Users\Admin\.claude\mcp-servers.json`

### Step 2: Configure Claude Code

#### For Claude Code CLI:
1. The config is already at `~/.claude/mcp-servers.json`
2. Restart Claude Code: `claude code` or restart the CLI
3. Claude can now use SAGE tools automatically!

#### For Claude.ai Web/Desktop:
1. Open Settings → Developer → MCP Servers
2. Add server manually:
   ```json
   {
     "sage": {
       "command": "python",
       "args": ["-m", "sage.mcp.server"],
       "description": "Smart Agent Guidance Engine"
     }
   }
   ```
3. Click "Save" and restart Claude

#### For VS Code Extension:
1. Open VS Code Settings
2. Search for "MCP"
3. Add to `claude.mcpServers`:
   ```json
   {
     "sage": {
       "command": "python",
       "args": ["-m", "sage.mcp.server"]
     }
   }
   ```

### Step 3: Verify Installation
```bash
# Test MCP server manually
sage mcp start

# Send test request (in another terminal):
echo '{"method":"tools/list"}' | python -m sage.mcp.server
```

## Available SAGE Tools

Once MCP is configured, Claude can call:

### 1. `sage_run_command`
Run a command through SAGE
```json
{
  "command": "python test.py"
}
```

### 2. `sage_explain_error`
Get explanation of last error
```json
{
  "run_id": 5
}
```

### 3. `sage_suggest_fix`
Get auto-fix suggestions
```json
{
  "run_id": 5,
  "apply": false
}
```

### 4. `sage_spawn_agent`
Create a new AI agent
```json
{
  "agent_type": "CodeAgent",
  "name": "test-fixer",
  "task": "Fix unit tests"
}
```

### 5. `sage_run_workflow`
Execute a workflow
```json
{
  "workflow_name": "ci-test"
}
```

### 6. `sage_get_history`
Get command history
```json
{
  "limit": 10
}
```

## Usage with Claude Code

### Example 1: Run Tests with SAGE
```
User: Run the Python tests through SAGE
Claude: [calls sage_run_command with "python -m pytest"]
```

### Example 2: Auto-Fix Errors
```
User: The last command failed, can you fix it?
Claude: [calls sage_explain_error, then sage_suggest_fix with apply=true]
```

### Example 3: Spawn Agent for Task
```
User: Create an agent to review the code
Claude: [calls sage_spawn_agent with type="ReviewAgent"]
```

## Troubleshooting

### MCP Server Not Starting
```bash
# Check if Python can find sage
python -m sage --version

# Reinstall sage
pip install -e .

# Test MCP manually
sage mcp start
```

### Claude Not Seeing Tools
1. Restart Claude Code completely
2. Check MCP config location:
   ```bash
   cat ~/.claude/mcp-servers.json  # Linux/Mac
   type %USERPROFILE%\.claude\mcp-servers.json  # Windows
   ```
3. Verify python path in config is correct
4. Check Claude Code logs for MCP errors

### Tools Not Working
```bash
# Test each tool manually
echo '{"method":"tools/list"}' | sage mcp start
echo '{"method":"tools/call","params":{"name":"sage_run_command","arguments":{"command":"python --version"}}}' | sage mcp start
```

## Architecture

```
┌─────────────────┐
│  Claude Code    │
│   (MCP Client)  │
└────────┬────────┘
         │ stdio
         ▼
┌─────────────────┐
│  SAGE MCP       │
│  Server         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SAGE Core      │
│  • Runner       │
│  • Auto-Fix     │
│  • Agents       │
│  • Workflows    │
└─────────────────┘
```

## Advanced: Custom Tool Integration

### Add Your Own SAGE Tool

1. Edit `src/sage/mcp/tools.py`:
```python
def sage_my_custom_tool(param1: str, param2: int):
    """Your custom tool description."""
    # Your logic here
    return {"result": "success"}

# Add to SAGE_TOOLS list
SAGE_TOOLS.append({
    "name": "sage_my_custom_tool",
    "description": "Does something custom",
    "inputSchema": {
        "type": "object",
        "properties": {
            "param1": {"type": "string"},
            "param2": {"type": "integer"}
        },
        "required": ["param1"]
    }
})
```

2. Register in `src/sage/mcp/server.py`:
```python
self.tools["sage_my_custom_tool"] = sage_my_custom_tool
```

3. Reinstall: `pip install -e .`
4. Restart MCP: `sage mcp start`

## Next Steps

- ✅ MCP installed and configured
- ✅ 6 SAGE tools available to Claude
- ✅ Auto-fix engine accessible via MCP
- ✅ Multi-agent system controllable from Claude

**Try it**: Tell Claude "Run my tests through SAGE and auto-fix any errors"

---

**Support**: https://github.com/PsYcGoD/sage/issues
