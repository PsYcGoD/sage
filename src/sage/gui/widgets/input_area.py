import logging
"""
Input Area Widget for SAGE Desktop GUI.

Provides a multi-line text input with Send, Clear, permission, and theme controls.
Supports keyboard shortcuts: Ctrl+Enter to send, Shift+Enter for newline.
"""

import os
from datetime import datetime
from pathlib import Path
from tkinter import filedialog
from typing import Callable, Optional, Any

import customtkinter as ctk

log = logging.getLogger(__name__)

try:
    from PIL import ImageGrab
    HAS_PIL = True
except ImportError:
    ImageGrab = None
    HAS_PIL = False

class InputArea(ctk.CTkFrame):
    """Multi-line text input area with control buttons."""

    PLACEHOLDER = "Type your command or prompt..."
    SLASH_COMMANDS = [
        ("/login", "Log in to Claude"),
        ("/model", "Set model for current AI"),
        ("/clear", "Clear output"),
        ("/help", "Show local actions"),
        ("/skills", "Show installed skills"),
        ("/plugins", "Show installed plugins"),
        ("/project", "Show current folder"),
        ("/history", "Show recent chats"),
        ("/agents", "Show agent records"),
        ("/models", "Show AI options"),
        ("/theme", "Toggle output theme"),
        ("/refresh", "Reload sidebar and metrics"),
        ("/new", "Start fresh context"),
    ]

    def __init__(
        self,
        parent,
        on_send: Optional[Callable[[str], Any]] = None,
        on_clear: Optional[Callable[[], None]] = None,
        on_permission_change: Optional[Callable[[str], None]] = None,
        on_cancel: Optional[Callable[[], None]] = None,
        on_output_theme_toggle: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        """
        Initialize input area widget.

        Args:
            parent: Parent widget
            on_send: Callback when Send button is clicked or Ctrl+Enter pressed
            on_clear: Callback when Clear button is clicked
            on_permission_change: Callback when permission mode changes
            **kwargs: Additional arguments for CTkFrame
        """
        super().__init__(parent, **kwargs)

        # Store callbacks
        self.on_send = on_send
        self.on_clear = on_clear
        self.on_permission_change = on_permission_change
        self.on_cancel = on_cancel
        self.on_output_theme_toggle = on_output_theme_toggle
        self._placeholder_active = False
        self._visible_suggestions: list[tuple[str, str]] = []

        # Create text input area
        self.text_input = ctk.CTkTextbox(
            self,
            height=100,
            wrap="word",
            font=ctk.CTkFont(size=13),
            undo=True,
            autoseparators=True,
            maxundo=-1
        )
        self.text_input.grid(row=0, column=0, columnspan=4, padx=5, pady=5, sticky="ew")

        self.suggestions_frame = ctk.CTkFrame(self, fg_color=("#eeeeee", "#202020"))
        self.suggestions_frame.grid_columnconfigure(0, weight=1)
        self.suggestions_frame.grid_remove()

        # Attached files shown as removable chips above the buttons
        self.attachments: list[str] = []
        self.attachments_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.attachments_frame.grid_remove()

        # Bind keyboard shortcuts
        # Enter = Send, Shift+Enter = New line (NORMAL behavior!)
        self.text_input.bind("<Return>", self._on_enter_key)
        self.text_input.bind("<KP_Enter>", self._on_enter_key)
        self.text_input.bind("<Shift-Return>", self._on_shift_enter)
        self.text_input.bind("<Shift-KP_Enter>", self._on_shift_enter)
        self.text_input.bind("<Up>", self._on_up_arrow)
        self.text_input.bind("<Down>", self._on_down_arrow)

        # Command history
        self.command_history = []
        self.history_index = -1
        self.text_input.bind("<Escape>", self._on_escape_key)
        self.text_input.bind("<Control-c>", self._on_ctrl_c_key)
        self.text_input.bind("<Control-z>", self._on_undo_key)
        self.text_input.bind("<Control-Z>", self._on_undo_key)
        self.text_input.bind("<Control-y>", self._on_redo_key)
        self.text_input.bind("<Control-Y>", self._on_redo_key)
        self.text_input.bind("<Control-Shift-z>", self._on_redo_key)
        self.text_input.bind("<Control-Shift-Z>", self._on_redo_key)
        self.text_input.bind("<KeyRelease>", self._on_key_release)
        self.text_input.bind("<Tab>", self._on_tab_key)
        self.text_input.bind("<Control-v>", self._on_paste)
        self.text_input.bind("<Control-V>", self._on_paste)

        # Create button frame for alignment
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=3, column=0, columnspan=4, padx=5, pady=(0, 5), sticky="ew")

        # Attach button (bottom-left): pick files, or paste images/files with Ctrl+V
        self.attach_button = ctk.CTkButton(
            button_frame,
            text="+",
            command=self._on_attach_clicked,
            width=34,
            height=28,
            fg_color="gray35",
            hover_color="gray28",
            font=ctk.CTkFont(size=17, weight="bold")
        )
        self.attach_button.pack(side="left", padx=5)

        # Create Send button
        self.send_button = ctk.CTkButton(
            button_frame,
            text="Send",
            command=self._on_send_clicked,
            width=80,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.send_button.pack(side="right", padx=5)

        # Create Clear button
        self.clear_button = ctk.CTkButton(
            button_frame,
            text="Clear",
            command=self._on_clear_clicked,
            width=80,
            fg_color="gray40",
            hover_color="gray30"
        )
        self.clear_button.pack(side="right", padx=5)

        # Create Permission dropdown (replaces settings button)
        self.permission_menu = ctk.CTkOptionMenu(
            button_frame,
            values=["🛡️ Ask for approval", "⚡ Approve for me", "🔓 Full access"],
            command=self._on_permission_changed,
            width=180,
            font=ctk.CTkFont(size=12)
        )
        self.permission_menu.pack(side="right", padx=5)

        self.output_theme_button = ctk.CTkButton(
            button_frame,
            text="☀",
            command=self._on_output_theme_clicked,
            width=34,
            height=28,
            fg_color="gray35",
            hover_color="gray28",
            font=ctk.CTkFont(size=15)
        )
        self.output_theme_button.pack(side="right", padx=5)

        # Configure grid weights
        self.grid_columnconfigure(0, weight=1)

        # Add placeholder text
        self._add_placeholder()

    # ----- Attachments -----

    def _on_attach_clicked(self):
        """Open a file picker and attach the chosen files."""
        paths = filedialog.askopenfilenames(title="Attach files to your prompt")
        for path in paths:
            self._add_attachment(path)

    def _on_paste(self, event):
        """Handle Ctrl+V: attach clipboard images/files, else default text paste."""
        if not HAS_PIL:
            return None
        try:
            clip = ImageGrab.grabclipboard()
        except Exception:
            return None

        if clip is None:
            return None  # plain text - let Tk paste normally

        if isinstance(clip, list):
            added = False
            for item in clip:
                path = str(item)
                if os.path.exists(path):
                    self._add_attachment(path)
                    added = True
            return "break" if added else None

        # Clipboard holds an image (e.g. a screenshot)
        try:
            attach_dir = Path.home() / ".sage" / "attachments"
            attach_dir.mkdir(parents=True, exist_ok=True)
            file_path = attach_dir / f"pasted-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.png"
            clip.save(file_path, "PNG")
            self._add_attachment(str(file_path))
            return "break"
        except Exception:
            return None

    def _add_attachment(self, path: str):
        path = str(path)
        if path and path not in self.attachments:
            self.attachments.append(path)
        self._render_attachment_chips()

    def _remove_attachment(self, path: str):
        self.attachments = [item for item in self.attachments if item != path]
        self._render_attachment_chips()

    def _render_attachment_chips(self):
        for widget in self.attachments_frame.winfo_children():
            widget.destroy()
        if not self.attachments:
            self.attachments_frame.grid_remove()
            return

        for index, path in enumerate(self.attachments[:10]):
            name = os.path.basename(path) or path
            if len(name) > 26:
                name = name[:23] + "..."
            chip = ctk.CTkButton(
                self.attachments_frame,
                text=f"{name}  ✕",
                height=24,
                fg_color="gray30",
                hover_color="#7f1d1d",
                font=ctk.CTkFont(size=11),
                command=lambda p=path: self._remove_attachment(p),
            )
            chip.grid(row=index // 4, column=index % 4, padx=3, pady=2, sticky="w")

        self.attachments_frame.grid(row=1, column=0, columnspan=4, padx=5, pady=(0, 2), sticky="w")

    def _compose_outgoing_text(self, text: str) -> str:
        """Append attached file paths so the AI can read them from disk."""
        if not self.attachments:
            return text
        listing = "\n".join(f"- {path}" for path in self.attachments)
        return f"{text}\n\n[Attached files - read these from disk]\n{listing}"

    def _clear_attachments(self):
        self.attachments = []
        self._render_attachment_chips()

    def _add_placeholder(self):
        """Add placeholder text to the input area."""
        if not self.get_text():
            raw_text = self.text_input.get("1.0", "end-1c")
            if raw_text:
                self.text_input.delete("1.0", "end")
            self._placeholder_active = True
            self.text_input.insert("1.0", self.PLACEHOLDER)
            self.text_input.configure(text_color="gray50")
            # Clear on FIRST keypress - fixes typing glitch!
            self.text_input.bind("<Key>", self._on_first_keypress, add="+")
            self.text_input.bind("<FocusOut>", self._on_focus_out)
            self._reset_undo_stack()

    def _on_first_keypress(self, event):
        """Clear placeholder on first keypress - prevents typing continuation bug."""
        # Ignore modifier keys only
        if event.keysym in ("Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R", "Caps_Lock", "Super_L", "Super_R"):
            return None

        if self._placeholder_active:
            # Clear placeholder immediately BEFORE this key is processed
            self.text_input.delete("1.0", "end")
            self._placeholder_active = False
            self.text_input.configure(text_color=("gray10", "gray90"))
            self.text_input.unbind("<Key>")
            self._reset_undo_stack()
            # Let key event continue normally
            return None

    def _on_focus_in(self, event):
        """No longer used - cleared on keypress instead."""
        return None

    def _on_focus_out(self, event):
        """Restore placeholder if empty."""
        if not self.get_text():
            self._add_placeholder()

    def _on_enter_key(self, event):
        """Handle Enter key - SEND command."""
        self._on_send_clicked()
        return "break"  # Prevent default

    def _on_shift_enter(self, event):
        """Handle Shift+Enter - NEW LINE."""
        # Allow default newline
        return None

    def _on_up_arrow(self, event):
        """Up arrow - previous command from history."""
        if not self.command_history:
            return "break"

        if self.history_index < 0 or self.history_index > len(self.command_history):
            self.history_index = len(self.command_history)
        if self.history_index > 0:
            self.history_index -= 1
        elif self.history_index == 0:
            self.history_index = len(self.command_history) - 1
        self.set_text(self.command_history[self.history_index])
        self.text_input.focus_set()

        return "break"

    def _on_down_arrow(self, event):
        """Down arrow - next command from history."""
        if not self.command_history:
            return "break"

        if self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            self.set_text(self.command_history[self.history_index])
            self.text_input.focus_set()
        elif self.history_index == len(self.command_history) - 1:
            self.history_index = len(self.command_history)
            self.text_input.delete("1.0", "end")
            self._add_placeholder()

        return "break"

    def _on_key_release(self, event):
        """Show slash command suggestions while typing a local action."""
        if event.keysym in {"Up", "Down", "Left", "Right", "Return", "Escape"}:
            return None
        self._update_slash_suggestions()
        return None

    def _on_tab_key(self, event):
        """Complete the first visible slash command."""
        if self._visible_suggestions:
            self._apply_slash_command(self._visible_suggestions[0][0])
            return "break"
        return None

    def _on_escape_key(self, event):
        """Handle Escape key - cancel running process."""
        if self.on_cancel:
            self.on_cancel()
        return "break"

    def _on_undo_key(self, event):
        """Handle Ctrl+Z in the prompt box."""
        if self._placeholder_active:
            return "break"
        try:
            self.text_input.edit_undo()
        except Exception:
            log.debug("suppressed", exc_info=True)
        return "break"

    def _on_redo_key(self, event):
        """Handle Ctrl+Y or Ctrl+Shift+Z in the prompt box."""
        if self._placeholder_active:
            return "break"
        try:
            self.text_input.edit_redo()
        except Exception:
            log.debug("suppressed", exc_info=True)
        return "break"

    def _on_ctrl_c_key(self, event):
        """Handle Ctrl+C - cancel running process if no text selected."""
        # Check if there's a text selection
        try:
            selected = self.text_input.selection_get()
            if selected:
                # There's a selection, let default copy behavior happen
                return None
        except:
            # No selection, treat as cancel
            pass

        # No selection, cancel running process
        if self.on_cancel:
            self.on_cancel()
            return "break"

        return None

    def _on_send_clicked(self):
        """Handle Send button click."""
        text = self.get_text()
        if text or self.attachments:
            if text:
                self.command_history.append(text)
                self.command_history = self.command_history[-100:]
                self.history_index = len(self.command_history)
            self._hide_slash_suggestions()
            outgoing = self._compose_outgoing_text(text or "Look at the attached files.")
            sent = True
            if self.on_send:
                sent = self.on_send(outgoing) is not False
            if sent:
                self._clear_attachments()
                self.clear()
            else:
                self.set_text(text)

    def _on_clear_clicked(self):
        """Handle Clear button click."""
        self._hide_slash_suggestions()
        self.clear()
        if self.on_clear:
            self.on_clear()

    def _on_permission_changed(self, value: str):
        """Handle permission dropdown change."""
        # Map display text to mode key
        mode_map = {
            "🛡️ Ask for approval": "ask",
            "⚡ Approve for me": "approve",
            "🔓 Full access": "full"
        }
        mode = mode_map.get(value, "ask")
        if self.on_permission_change:
            self.on_permission_change(mode)

    def _on_output_theme_clicked(self):
        """Handle output light/dark button click."""
        if self.on_output_theme_toggle:
            self.on_output_theme_toggle()

    def set_output_light_mode(self, enabled: bool):
        """Update the light/dark output toggle icon."""
        self.output_theme_button.configure(text="☾" if enabled else "☀")

    def set_permission(self, mode: str):
        """Set the permission dropdown value."""
        display_map = {
            "ask": "🛡️ Ask for approval",
            "approve": "⚡ Approve for me",
            "full": "🔓 Full access"
        }
        self.permission_menu.set(display_map.get(mode, "🛡️ Ask for approval"))

    def get_text(self) -> str:
        """
        Get the current text from the input area.

        Returns:
            Text content (stripped of trailing whitespace)
        """
        text = self.text_input.get("1.0", "end-1c")
        if self._placeholder_active or text == self.PLACEHOLDER:
            return ""
        return text.strip()

    def set_text(self, text: str):
        """
        Set the text in the input area.

        Args:
            text: Text to set
        """
        self._placeholder_active = False
        self.text_input.delete("1.0", "end")
        self.text_input.insert("1.0", text)
        self.text_input.configure(text_color=("gray10", "gray90"))
        self._reset_undo_stack()
        self._update_slash_suggestions()
        self.text_input.mark_set("insert", "end-1c")

    def clear(self):
        """Clear the input area."""
        self._hide_slash_suggestions()
        self._placeholder_active = False
        self.text_input.delete("1.0", "end")
        self._reset_undo_stack()
        self._add_placeholder()

    def _update_slash_suggestions(self):
        """Render available local commands when input starts with slash."""
        text = self.text_input.get("1.0", "end-1c").strip()
        if self._placeholder_active or not text.startswith("/") or "\n" in text:
            self._hide_slash_suggestions()
            return

        query = text.lower()
        matches = [
            item for item in self.SLASH_COMMANDS
            if item[0].startswith(query) or query in item[1].lower()
        ]
        if not matches:
            self._hide_slash_suggestions()
            return

        self._visible_suggestions = matches
        for widget in self.suggestions_frame.winfo_children():
            widget.destroy()

        for row, (command, description) in enumerate(matches[:8]):
            item = ctk.CTkButton(
                self.suggestions_frame,
                text=f"{command}   {description}",
                anchor="w",
                height=26,
                fg_color="transparent",
                hover_color=("#d9e8ff", "#2d3748"),
                text_color=("#111827", "#e5e7eb"),
                command=lambda value=command: self._apply_slash_command(value),
            )
            item.grid(row=row, column=0, padx=4, pady=1, sticky="ew")

        self.suggestions_frame.grid(row=2, column=0, columnspan=4, padx=5, pady=(0, 5), sticky="ew")

    def _hide_slash_suggestions(self):
        """Hide slash suggestions."""
        self._visible_suggestions = []
        self.suggestions_frame.grid_remove()

    def _apply_slash_command(self, command: str):
        """Fill a slash command from suggestions."""
        self._placeholder_active = False
        self.text_input.delete("1.0", "end")
        self.text_input.insert("1.0", command)
        self.text_input.configure(text_color=("gray10", "gray90"))
        self._reset_undo_stack()
        self.text_input.focus()
        self.text_input.mark_set("insert", "end-1c")
        self._hide_slash_suggestions()

    def _reset_undo_stack(self):
        """Keep placeholder/programmatic edits out of Ctrl+Z history."""
        try:
            self.text_input.edit_reset()
            self.text_input.edit_separator()
        except Exception:
            log.debug("suppressed", exc_info=True)

    def set_enabled(self, enabled: bool):
        """
        Enable or disable the input area and buttons.

        Args:
            enabled: True to enable, False to disable
        """
        state = "normal" if enabled else "disabled"
        self.text_input.configure(state=state)
        self.send_button.configure(state=state)
        self.clear_button.configure(state=state)

    def focus(self):
        """Set focus to the text input area."""
        self.text_input.focus()
