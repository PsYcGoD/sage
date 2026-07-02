# 🖥️ SAGE Desktop GUI - Complete Specification

## Overview

**SAGE GUI** is a native desktop application that provides a modern interface for interacting with AI coding assistants (Claude, Codex, GPT-4) through SAGE's intelligent orchestration layer.

## Launch Commands

```bash
# Start GUI with default AI
sage gui

# Start with specific AI pre-selected
sage gui --ai claude
sage gui --ai codex
sage gui --ai gpt4

# Use personal configuration
sage gui --config personal
```

## Screen Layout

```
┌────────────────────────────────────────────────────────────────┐
│  🧠 SAGE Desktop - Smart AI Guidance Engine            [⚙️] [×] │
├────────────────┬────────────────┬────────────────┬──────────────┤
│  📊 Commands   │  ⚡ Tokens     │  🤖 Agents     │  ✅ Success  │
│     7 Total    │   148 Saved    │   0 Active     │   85.7%      │
│                │   99.3% Rate   │                │              │
├────────────────┴────────────────┴────────────────┴──────────────┤
│  AI: [Claude ▼] [Codex] [GPT-4] [Gemini] [Custom...]            │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Type your command or prompt...                           │  │
│  │                                                           │  │
│  │                                                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                            [Send] [Clear] [⚙️]  │
├──────────────────────────────────────────────────────────────────┤
│  ━━━ Thinking ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  Analyzing the test suite structure...                          │
│  • Found 15 test files                                          │
│  • 3 tests are failing                                          │
│  • Running through SAGE for context compression...              │
│                                                                  │
│  ━━━ Running ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  $ sage run -- pytest tests/                                    │
│  ✓ 12 passed                                                    │
│  ✗ 3 failed (test_auth.py, test_db.py, test_api.py)           │
│                                                                  │
│  ━━━ Coding ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  Fixing import error in test_auth.py:12                         │
│  ```python                                                      │
│  - from auth import verify_token                                │
│  + from src.auth import verify_token                            │
│  ```                                                            │
│  Applied fix. Re-running tests...                               │
│                                                                  │
│  ━━━ Complete ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  ✅ All tests passing! Fixed 3 import errors.                   │
│  Token savings: 1,247 tokens (96.8% compression)                │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Core Features

### 1. **4 Metric Cards** (Top Section)
- **Total Commands**: Lifetime commands run through SAGE
- **Token Savings**: Total tokens saved via compression (with percentage)
- **Active Agents**: Currently running AI agents
- **Success Rate**: Percentage of successful command executions

**Update Frequency**: Real-time (every 2 seconds)

### 2. **AI Selector** (Dropdown)
Available AIs:
- **Claude** (default)
- **Codex** 
- **GPT-4**
- **Gemini**
- **Custom** (user-defined command)

**Auto-Configuration**:
- **Personal setup** (Sensei): Auto-loads FABLE-5.md + SAGE-INTEGRATION.md for Claude
- **Public setup** (GitHub users): Auto-loads only SAGE-INTEGRATION.md

### 3. **Command Input Area**
- Multi-line text input
- Supports:
  - Natural language prompts ("Fix the failing tests")
  - Direct commands ("run pytest")
  - File paths ("analyze src/auth.py")
- Send button with keyboard shortcut (Ctrl+Enter)

### 4. **Live Streaming Output**
Shows real-time AI responses with distinct visual blocks:

#### Thinking Block
```
━━━ Thinking ━━━━━━━━━━━━━━━━━━━━━━━━━
Understanding the error...
• Analyzing stack trace
• Checking dependencies
```

#### Running Block
```
━━━ Running ━━━━━━━━━━━━━━━━━━━━━━━━━
$ sage run -- python test.py
Output: [streaming in real-time]
```

#### Coding Block
```
━━━ Coding ━━━━━━━━━━━━━━━━━━━━━━━━━
Modifying file: src/auth.py:45
```python
- old_code()
+ new_code()
```
```

#### Complete Block
```
━━━ Complete ━━━━━━━━━━━━━━━━━━━━━━━
✅ Task completed successfully!
Token savings: 1,247 tokens
```

### 5. **Settings Panel** (Hidden by Default)
Click ⚙️ to reveal:
- System prompt file paths
- AI executable paths
- Auto-start preferences
- Theme (Light/Dark)
- Additional metrics cards toggle
- Token compression settings

## Configuration System

### Personal Configuration
**Location**: `~/.sage/gui-config.json`

```json
{
  "personal_mode": true,
  "system_prompts": {
    "claude": [
      "C:\\Users\\Admin\\.claude\\CLAUDE-FABLE-5.md",
      "C:\\Users\\Admin\\.claude\\SAGE-INTEGRATION.md"
    ],
    "codex": [
      "C:\\Users\\Admin\\.claude\\SAGE-INTEGRATION.md"
    ]
  },
  "ai_commands": {
    "claude": "claude --dangerously-skip-permissions",
    "codex": "codex",
    "gpt4": "aichat -m gpt-4"
  },
  "theme": "dark",
  "auto_compress": true
}
```

### Public Configuration (Default)
```json
{
  "personal_mode": false,
  "system_prompts": {
    "claude": [
      "~/.claude/SAGE-INTEGRATION.md"
    ]
  },
  "ai_commands": {
    "claude": "claude",
    "codex": "codex"
  }
}
```

## Technical Architecture

### Technology Stack
- **GUI Framework**: CustomTkinter (modern, native look)
- **AI Integration**: subprocess with stdio streaming
- **Database**: SQLite (existing SAGE database)
- **Process Management**: psutil
- **Syntax Highlighting**: pygments

### File Structure
```
src/sage/gui/
├── __init__.py
├── app.py              # Main GUI application
├── widgets/
│   ├── metric_card.py  # Metric card widget
│   ├── ai_selector.py  # AI dropdown
│   ├── input_area.py   # Command input
│   └── output_view.py  # Streaming output display
├── ai_client.py        # AI subprocess manager
├── config.py           # Configuration loader
└── themes.py           # Theme definitions
```

### Process Flow

```
User Input → GUI → AI Subprocess (with system prompts) → Stream Output
                ↓                                              ↓
           SAGE Runner                                   Update Metrics
                ↓
          SQLite Database
```

1. **User types command** → Input area
2. **Click Send** → Spawn AI subprocess with:
   - Selected AI executable
   - System prompt files (based on config)
   - User's prompt as stdin
3. **AI responds** → Stream stdout/stderr to output view
4. **AI calls MCP tools** → SAGE executes via MCP server
5. **Results stream back** → Display in output view
6. **Update metrics** → Query SQLite database every 2s

## Auto-Start Behavior

### For Sensei (Personal Mode)
```bash
sage gui --ai claude

# Internally runs:
claude --dangerously-skip-permissions \
  --append-system-prompt-file "C:\Users\Admin\.claude\CLAUDE-FABLE-5.md" \
  --append-system-prompt-file "C:\Users\Admin\.claude\SAGE-INTEGRATION.md"
```

### For GitHub Users (Public Mode)
```bash
sage gui --ai claude

# Internally runs:
claude --append-system-prompt-file "~/.claude/SAGE-INTEGRATION.md"
```

## Advanced Features

### 1. Command History
- Up/Down arrows cycle through previous commands
- Persistent across sessions
- Stored in `~/.sage/gui-history.txt`

### 2. Interrupt Handling
- **Stop button** appears during execution
- Sends SIGINT to AI subprocess
- Gracefully handles cleanup

### 3. Multi-line Input
- Shift+Enter for new line
- Ctrl+Enter to send
- Auto-resize input area

### 4. Syntax Highlighting
- Code blocks highlighted based on language
- Supports Python, JavaScript, Bash, etc.

### 5. Export Conversation
- **File → Export** saves entire conversation to markdown
- Includes all blocks (thinking, running, coding)

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Enter` | Send command |
| `Ctrl+L` | Clear output |
| `Ctrl+,` | Open settings |
| `Ctrl+Q` | Quit |
| `Up/Down` | Command history |
| `Shift+Enter` | New line in input |
| `Ctrl+K` | Focus input area |

## Installation

```bash
# Install GUI dependencies
pip install customtkinter pillow psutil pygments

# Launch GUI
sage gui
```

## Development Roadmap

### Phase 1 (Current) ✅
- Basic window with 4 metric cards
- AI selector dropdown
- Command input area
- Simple subprocess integration

### Phase 2
- Live streaming output with block detection
- Syntax highlighting
- Settings panel
- Configuration system

### Phase 3
- Command history
- Interrupt handling
- Export conversations
- Theme customization

### Phase 4
- Multi-tab support (multiple AI sessions)
- File attachment drag-drop
- Voice input
- Plugin system

## Usage Examples

### Example 1: Fix Tests
```
User Input: "Run the tests and fix any errors"

Output:
━━━ Thinking ━━━
Analyzing test suite...

━━━ Running ━━━
$ sage run -- pytest
3 failed, 12 passed

━━━ Coding ━━━
Fixed import errors in 3 files

━━━ Complete ━━━
✅ All tests passing!
```

### Example 2: Code Review
```
User Input: "Review src/auth.py for security issues"

Output:
━━━ Thinking ━━━
Analyzing authentication logic...

━━━ Running ━━━
$ sage run -- bandit src/auth.py

━━━ Complete ━━━
Found 2 medium severity issues:
1. Weak password hashing
2. Missing rate limiting
```

## FAQ

### Q: Can I use multiple AIs simultaneously?
**A**: Not in Phase 1. Phase 4 will add multi-tab support.

### Q: Does the GUI work offline?
**A**: The GUI itself works offline, but AI features require the selected AI executable to be installed and accessible.

### Q: Can I add custom AIs?
**A**: Yes! In settings, add custom AI commands with their executable paths.

### Q: Does it work on Mac/Linux?
**A**: Yes! CustomTkinter is cross-platform. Adjust paths in config for your OS.

---

**Built with ❤️ for developers who want a unified AI coding interface**
