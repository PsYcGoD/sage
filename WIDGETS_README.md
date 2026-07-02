# SAGE GUI Widgets Documentation

This document describes the input and output components created for the SAGE Desktop GUI.

## Created Components

### 1. Configuration Loader (`src/sage/gui/config.py`)

**Purpose**: Manages GUI configuration with automatic personal vs public mode detection.

**Features**:
- Loads configuration from `~/.sage/gui-config.json`
- Auto-detects personal mode (Sensei) vs public mode (GitHub users)
- Manages AI commands and system prompt paths
- Supports theme configuration and auto-compression settings

**Key Methods**:
```python
config = get_config()
config.is_personal_mode()  # True if personal mode detected
config.get_system_prompts('claude')  # Get prompt paths for AI
config.get_ai_command('claude')  # Get command to run AI
config.get_default_ai()  # Get default AI selection
```

**Auto-Detection**:
- Checks for `C:\Users\Admin\.claude\CLAUDE-FABLE-5.md`
- If exists: Personal mode with FABLE-5 + SAGE-INTEGRATION prompts
- If not: Public mode with only SAGE-INTEGRATION prompt

---

### 2. AI Selector Widget (`src/sage/gui/widgets/ai_selector.py`)

**Purpose**: Dropdown to select between different AI models.

**Features**:
- CustomTkinter ComboBox with readonly state
- Options: Claude, Codex, GPT-4, Gemini, Custom
- Callback support for selection changes
- Programmatic get/set methods

**Usage**:
```python
from sage.gui.widgets import AISelector

def on_ai_change(ai_key):
    print(f"Selected: {ai_key}")  # "claude", "gpt4", etc.

ai_selector = AISelector(
    parent,
    default_ai="Claude",
    callback=on_ai_change
)

# Get current selection
current = ai_selector.get_selected_ai()  # Returns "claude"

# Set selection programmatically
ai_selector.set_selected_ai("gpt4")  # Sets to "GPT-4"
```

---

### 3. Input Area Widget (`src/sage/gui/widgets/input_area.py`)

**Purpose**: Multi-line text input with control buttons.

**Features**:
- Multi-line CTkTextbox with word wrap
- Send, Clear, and Settings buttons
- Keyboard shortcuts:
  - `Ctrl+Enter`: Send message
  - `Shift+Enter`: New line
- Placeholder text ("Type your command or prompt...")
- Enable/disable state management
- Focus management

**Usage**:
```python
from sage.gui.widgets import InputArea

def on_send(text):
    print(f"User sent: {text}")

def on_clear():
    print("Input cleared")

def on_settings():
    print("Settings opened")

input_area = InputArea(
    parent,
    on_send=on_send,
    on_clear=on_clear,
    on_settings=on_settings
)

# Get text programmatically
text = input_area.get_text()

# Set text programmatically
input_area.set_text("Run tests")

# Clear input
input_area.clear()

# Disable during processing
input_area.set_enabled(False)
```

---

### 4. Output View Widget (`src/sage/gui/widgets/output_view.py`)

**Purpose**: Scrollable text area with streaming support and block detection.

**Features**:
- Auto-scrolling to bottom
- Block type detection with regex patterns
- Color-coded output for different block types:
  - **Thinking**: Purple (#9b87f5)
  - **Running**: Blue (#3b82f6)
  - **Coding**: Green (#10b981)
  - **Complete**: Amber (#f59e0b)
- Special styling for success (✓), errors (✗), and code blocks
- Streaming support for real-time output
- Read-only display

**Block Patterns**:
```python
THINKING_PATTERN = r"━━━ Thinking ━━━"
RUNNING_PATTERN = r"━━━ Running ━━━"
CODING_PATTERN = r"━━━ Coding ━━━"
COMPLETE_PATTERN = r"━━━ Complete ━━━"
```

**Usage**:
```python
from sage.gui.widgets import OutputView, BlockType

output_view = OutputView(parent)

# Append text with auto block detection
output_view.append_text("━━━ Thinking ━━━\nAnalyzing code...\n")

# Append streaming chunks
output_view.append_stream("Running tests... ")
output_view.append_stream("done!\n")

# Use helper methods for specific blocks
output_view.append_thinking("Analyzing the problem...")
output_view.append_running("$ pytest tests/")
output_view.append_coding("Fixed import in auth.py")
output_view.append_complete("✅ All tests passing!")

# Clear output
output_view.clear()

# Get all text
content = output_view.get_text()

# Save to file
output_view.save_to_file("conversation.txt")

# Control auto-scrolling
output_view.set_auto_scroll(False)
```

---

## File Structure

```
src/sage/gui/
├── __init__.py             # Package initialization
├── config.py               # Configuration loader
└── widgets/
    ├── __init__.py         # Widget package exports
    ├── ai_selector.py      # AI dropdown selector
    ├── input_area.py       # Multi-line input with buttons
    └── output_view.py      # Scrollable output with blocks
```

---

## Testing

Run the test script to verify all widgets:

```bash
python test_gui_widgets.py
```

The test will:
1. Load and display configuration
2. Create a window with all three widgets
3. Populate the output view with sample blocks
4. Enable interactive testing of all features

**Test Features**:
- Change AI selection
- Type messages and send with Ctrl+Enter
- Click Clear and Settings buttons
- View colored output blocks
- Verify keyboard shortcuts

---

## Integration Example

Here's how to integrate these widgets into the main SAGE GUI:

```python
import customtkinter as ctk
from sage.gui.widgets import AISelector, InputArea, OutputView
from sage.gui.config import get_config

class SAGEApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Load config
        self.config = get_config()
        
        # Create AI selector
        self.ai_selector = AISelector(
            self,
            default_ai=self.config.get_default_ai(),
            callback=self.on_ai_changed
        )
        self.ai_selector.pack(fill="x", padx=10, pady=5)
        
        # Create output view
        self.output_view = OutputView(self)
        self.output_view.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create input area
        self.input_area = InputArea(
            self,
            on_send=self.on_send,
            on_clear=self.on_clear,
            on_settings=self.on_settings
        )
        self.input_area.pack(fill="x", padx=10, pady=5)
    
    def on_ai_changed(self, ai):
        self.output_view.append_text(f"Switched to {ai}\n")
    
    def on_send(self, text):
        # Send to AI subprocess
        self.output_view.append_text(f"> {text}\n\n")
        self.process_command(text)
    
    def on_clear(self):
        pass  # Handle clear if needed
    
    def on_settings(self):
        # Open settings dialog
        pass
    
    def process_command(self, text):
        # TODO: Spawn AI subprocess and stream output
        pass
```

---

## Dependencies

Required packages (install with pip):
```bash
pip install customtkinter
```

---

## Configuration File Format

Location: `~/.sage/gui-config.json`

**Personal Mode Example**:
```json
{
  "personal_mode": true,
  "system_prompts": {
    "claude": [
      "C:\\Users\\Admin\\.claude\\CLAUDE-FABLE-5.md",
      "C:\\Users\\Admin\\.claude\\SAGE-INTEGRATION.md"
    ]
  },
  "ai_commands": {
    "claude": "claude --dangerously-skip-permissions"
  },
  "theme": "dark",
  "auto_compress": true,
  "default_ai": "claude"
}
```

**Public Mode Example**:
```json
{
  "personal_mode": false,
  "system_prompts": {
    "claude": ["~/.claude/SAGE-INTEGRATION.md"]
  },
  "ai_commands": {
    "claude": "claude"
  },
  "theme": "dark",
  "default_ai": "claude"
}
```

---

## Color Scheme

The output view uses the following color scheme (optimized for dark theme):

| Element | Color | Hex Code |
|---------|-------|----------|
| Thinking | Purple | #9b87f5 |
| Running | Blue | #3b82f6 |
| Coding | Green | #10b981 |
| Complete | Amber | #f59e0b |
| Block Headers | Light Blue | #60a5fa |
| Success (✓) | Green | #10b981 |
| Error (✗) | Red | #ef4444 |
| Code | Light Purple | #a78bfa |

---

## Next Steps

To complete the SAGE GUI, you still need to create:

1. **AI Client** (`src/sage/gui/ai_client.py`): Subprocess manager for AI execution
2. **Metric Cards** (`src/sage/gui/widgets/metric_card.py`): Real-time metrics display
3. **Main App** (`src/sage/gui/app.py`): Complete GUI application
4. **Themes** (`src/sage/gui/themes.py`): Light/dark theme definitions

These widgets provide the foundation for user interaction and output display.
