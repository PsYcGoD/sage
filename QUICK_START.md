# 🚀 SAGE Quick Start Guide

## TL;DR - 3 Ways to Use SAGE

### 1️⃣ **Standalone SAGE Commands** (No Claude needed)
```bash
sage run -- python test.py     # Run with compression
sage explain                    # Explain last error
sage suggest                    # Get fix suggestions
sage fix --apply                # Auto-fix errors
sage context stats              # Show token savings
```

### 2️⃣ **Claude Code with MCP Tools** (Auto-connected)
```bash
# Just start Claude normally - MCP auto-loads!
claude

# Or in any folder
cd D:\my-project
claude

# SAGE tools automatically available via MCP
```

Claude can now call:
- ✅ `sage_run_command` - Run commands with compression
- ✅ `sage_suggest_fix` - Auto-fix errors
- ✅ `sage_spawn_agent` - Create AI agents
- ✅ And 3 more tools...

**No manual setup needed after `sage mcp install`!**

### 3️⃣ **Claude Code + System Prompt** (Knows about SAGE)
```bash
# Option A: Use the alias (after restart)
sage-claude

# Option B: Use the script
.\start-claude-with-sage.ps1

# Option C: Manual
claude --append-system-prompt-file "C:\Users\Admin\.claude\SAGE-INTEGRATION.md"
```

Claude now:
- ✅ Has MCP tools
- ✅ Knows what SAGE is
- ✅ Uses tools proactively
- ✅ Understands context compression

---

## Installation Checklist

### ✅ One-Time Setup (Already Done!)
```bash
# 1. Install SAGE
pip install -e .

# 2. Configure MCP (makes tools auto-available)
sage mcp install

# 3. Start dashboard (optional)
sage dashboard start --port 8765
```

### ✅ PowerShell Alias (Already Added!)
```bash
# Restart PowerShell, then:
sage-claude
```

---

## Understanding the Components

### Component 1: MCP Server (Auto-starts)
**Location**: `C:\Users\Admin\.claude\mcp-servers.json`
```json
{
  "sage": {
    "command": "python",
    "args": ["-m", "sage.mcp.server"]
  }
}
```

**What it does**: Claude Code auto-starts this on launch
**Result**: 6 SAGE tools available in every conversation
**Manual start**: `sage mcp start` (usually not needed)

### Component 2: System Prompt (Manual)
**Location**: `C:\Users\Admin\.claude\SAGE-INTEGRATION.md`

**What it does**: Tells Claude about SAGE features
**Result**: Claude uses tools naturally
**How to use**: Add `--append-system-prompt-file` flag

### Component 3: Dashboard (Optional)
**Start**: `sage dashboard start --port 8765`
**URL**: http://localhost:8765
**Shows**: Live metrics, command history, agent status

---

## Common Workflows

### Workflow 1: Quick Testing
```bash
# Terminal 1: Run tests through SAGE
sage run -- pytest

# Terminal 2: Get suggestions
sage suggest
```

### Workflow 2: With Claude (MCP only)
```bash
# Start Claude normally
claude

# You: "Run the tests through SAGE"
# Claude: [calls sage_run_command("pytest")]
```

### Workflow 3: With Claude (Full integration)
```bash
# Start with alias
sage-claude

# You: "Run tests and auto-fix any errors"
# Claude: [calls sage_run_command, then sage_suggest_fix with apply=true]
```

---

## FAQ

### Q: Do I need to start `sage mcp start` manually?
**A: No!** Claude Code auto-starts it when you run `claude`.

### Q: Will Claude use SAGE without the system prompt?
**A: Partially.** Tools are available, but Claude won't know when/how to use them proactively.

### Q: Does SAGE work with other AI tools (Codex, Cursor, etc)?
**A: Yes!** 
- **Standalone**: Use `sage run -- <command>` in any tool
- **MCP**: Any MCP-compatible client can connect
- **System prompt**: Adapt `SAGE-INTEGRATION.md` for other tools

### Q: Do I need the dashboard running?
**A: No!** Dashboard is optional monitoring only. SAGE works without it.

### Q: Can I use SAGE in multiple projects?
**A: Yes!** Each project gets its own SQLite database at `~/.sage/sage.db`.

---

## Test Your Setup

### Test 1: Standalone SAGE
```bash
sage run -- python --version
sage context stats
```
**Expected**: Command runs, shows token savings

### Test 2: MCP Tools
```bash
claude
# In chat: "Call sage_get_history with limit 5"
```
**Expected**: Returns recent command history

### Test 3: Full Integration
```bash
sage-claude
# In chat: "Run python --version through SAGE"
```
**Expected**: Claude calls tool and explains results

---

## Quick Reference

### SAGE CLI Commands
```bash
sage run -- <cmd>        # Run with compression
sage explain             # Explain last command
sage suggest             # Get suggestions
sage fix [--apply]       # Auto-fix errors
sage history             # Command history
sage context stats       # Token usage
sage agents list         # Active agents
sage dashboard start     # Start dashboard
sage mcp install         # Configure MCP
```

### Start Claude with SAGE
```bash
sage-claude              # Alias (restart PS first)
.\start-claude-with-sage.ps1   # Script
```

### MCP Tools (via Claude)
- `sage_run_command` - Execute commands
- `sage_explain_error` - Analyze errors
- `sage_suggest_fix` - Get/apply fixes
- `sage_spawn_agent` - Create agents
- `sage_run_workflow` - Run workflows
- `sage_get_history` - Get history

---

## Support

- **GitHub**: https://github.com/PsYcGoD/sage
- **MCP Setup**: See `MCP_SETUP.md`
- **Full Docs**: See `SAGE_V2_COMPLETE.md`

---

**You're all set, Sensei! 🚀**
