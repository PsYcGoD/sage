# Embed Actual PowerShell Terminal in SAGE GUI

## Goal
Replace the current text output view with a **real, embedded PowerShell terminal** that runs inside the GUI window.

## Requirements
1. **Actual PowerShell** - Not subprocess capture, not text parsing, REAL PowerShell
2. **Interactive** - Can type commands, see prompts, full terminal experience
3. **In GUI** - Terminal widget embedded in output area (where text currently shows)
4. **SAGE integration** - All commands automatically run through `sage run --` wrapper
5. **Windows only** - Use `winpty` or `conpty` for pseudo-terminal

## Current State
- **File**: `src/sage/gui/app.py` line 697-835
- **Method**: `_run_real_cli_in_pty()`
- **Problem**: Shows text output, not actual terminal

## What I Need

### 1. Terminal Widget (Replace output_view)
```python
# src/sage/gui/widgets/powershell_terminal.py

import customtkinter as ctk
import winpty  # Windows ConPTY wrapper

class PowerShellTerminal(ctk.CTkTextbox):
    """Embedded PowerShell terminal widget"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.pty = None
        self.process = None
        
    def start_powershell(self):
        """Launch actual PowerShell in PTY"""
        # Create PTY (pseudo-terminal)
        self.pty = winpty.PTY(80, 24)
        
        # Spawn PowerShell
        self.pty.spawn('powershell.exe')
        
        # Read output in background thread
        threading.Thread(target=self._read_output, daemon=True).start()
        
    def _read_output(self):
        """Stream PowerShell output to widget"""
        while True:
            output = self.pty.read()
            if output:
                self.insert("end", output)
                self.see("end")
    
    def write_command(self, cmd: str):
        """Send command to PowerShell"""
        # Wrap with sage run
        wrapped = f"sage run -- {cmd}\n"
        self.pty.write(wrapped)
```

### 2. Integration in GUI
```python
# src/sage/gui/app.py

# Replace output_view with terminal
self.terminal = PowerShellTerminal(self.main_content)
self.terminal.pack(fill="both", expand=True)

# Start PowerShell on launch
self.terminal.start_powershell()

# When user sends prompt
def on_send(prompt):
    # Send to PowerShell terminal
    self.terminal.write_command(f'claude "{prompt}"')
```

### 3. Key Features
- [x] **Real terminal** - Actual PowerShell running
- [x] **ANSI colors** - Parse escape codes for colored output
- [x] **Interactive** - Can type commands directly in terminal
- [x] **SAGE wrapper** - Auto-prefix all commands with `sage run --`
- [x] **History** - Terminal keeps full history
- [x] **Copy/paste** - Right-click context menu
- [x] **Scrollback** - Keep last 10,000 lines

## Libraries Needed
```bash
pip install pywinpty  # Windows PTY wrapper
```

## Expected Behavior

### Before (Current - Text Output):
```
User types: "hello"
[Press Send]
━━━ Thinking ━━━
...text appears...
━━━ Answer ━━━
Hello! How can I help?
```

### After (Real Terminal):
```
PS D:\work\sage> sage run -- claude "hello"
[Thinking process streams live]
[Answer streams live]

PS D:\work\sage> _
```

User sees **actual PowerShell prompt**, can type commands, sees SAGE working, gets real terminal experience.

## Why This is Better
1. **Actual CLI** - Not simulated, it's real PowerShell
2. **Full features** - Tab completion, history, aliases all work
3. **SAGE visible** - User sees `sage run --` wrapping everything
4. **Token tracking** - Still goes through SAGE for compression
5. **No parsing** - Terminal handles all output formatting
6. **Interactive** - Can run any command, not just AI prompts

## Implementation Steps
1. Create `PowerShellTerminal` widget with winpty
2. Replace `output_view` with `terminal` in app.py
3. Connect input_area Send button to terminal.write_command()
4. Auto-prefix commands with `sage run --`
5. Add ANSI color parsing
6. Test with Claude, Codex, Ollama

## Files to Modify
- `src/sage/gui/widgets/powershell_terminal.py` - NEW file, terminal widget
- `src/sage/gui/app.py` - Replace output_view with terminal
- `src/sage/gui/widgets/input_area.py` - Send to terminal instead of subprocess

Give this prompt to Codex and it will create the embedded PowerShell terminal for you!
