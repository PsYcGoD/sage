"""Permission Settings Dialog for SAGE Desktop GUI."""

import customtkinter as ctk
from typing import Optional


class PermissionSettingsDialog(ctk.CTkToplevel):
    """Dialog for configuring AI permission modes."""

    PERMISSION_MODES = {
        "ask": {
            "label": "Ask for approval",
            "description": "Always ask to edit external files and use internet",
            "icon": "🛡️"
        },
        "approve": {
            "label": "Approve for me",
            "description": "Only ask for actions detected as potentially unsafe",
            "icon": "⚡"
        },
        "full": {
            "label": "Full access",
            "description": "Unrestricted access to internet and any file",
            "icon": "🔓"
        }
    }

    def __init__(self, parent, config):
        """
        Initialize permission settings dialog.

        Args:
            parent: Parent window
            config: GUIConfig instance
        """
        super().__init__(parent)

        self.config = config
        self.selected_mode = ctk.StringVar(value=config.get_permission_mode())

        # Window configuration
        self.title("Permission Settings")
        self.geometry("500x400")
        self.resizable(False, False)

        # Center on parent
        self.transient(parent)
        self.grab_set()

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header = ctk.CTkLabel(
            self,
            text="⚙️  Permission Settings",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        header.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        description = ctk.CTkLabel(
            self,
            text="Choose how SAGE handles file operations and internet access",
            font=ctk.CTkFont(size=12),
            text_color="gray60"
        )
        description.grid(row=0, column=0, padx=20, pady=(45, 10), sticky="w")

        # Permission modes frame
        modes_frame = ctk.CTkFrame(self, fg_color="transparent")
        modes_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        modes_frame.grid_columnconfigure(0, weight=1)

        # Create radio buttons for each mode
        self.mode_widgets = {}
        for i, (mode_key, mode_info) in enumerate(self.PERMISSION_MODES.items()):
            mode_widget = self._create_mode_option(modes_frame, mode_key, mode_info)
            mode_widget.grid(row=i, column=0, padx=5, pady=8, sticky="ew")
            self.mode_widgets[mode_key] = mode_widget

        # Buttons frame
        buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        buttons_frame.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="ew")

        # Cancel button
        cancel_btn = ctk.CTkButton(
            buttons_frame,
            text="Cancel",
            command=self.destroy,
            width=100,
            fg_color="gray40",
            hover_color="gray30"
        )
        cancel_btn.pack(side="right", padx=5)

        # Save button
        save_btn = ctk.CTkButton(
            buttons_frame,
            text="Save",
            command=self._save_settings,
            width=100,
            font=ctk.CTkFont(weight="bold")
        )
        save_btn.pack(side="right", padx=5)

    def _create_mode_option(self, parent, mode_key: str, mode_info: dict):
        """Create a permission mode option widget."""
        # Container frame
        frame = ctk.CTkFrame(parent, fg_color="gray20", corner_radius=8)

        # Make frame clickable
        frame.bind("<Button-1>", lambda e: self.selected_mode.set(mode_key))

        # Main content frame
        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=15, pady=12)

        # Radio button and label in header
        header_frame = ctk.CTkFrame(content, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 5))

        radio = ctk.CTkRadioButton(
            header_frame,
            text="",
            variable=self.selected_mode,
            value=mode_key,
            width=20
        )
        radio.pack(side="left")

        label = ctk.CTkLabel(
            header_frame,
            text=f"{mode_info['icon']}  {mode_info['label']}",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        label.pack(side="left", padx=(5, 0))

        # Description
        desc = ctk.CTkLabel(
            content,
            text=mode_info['description'],
            font=ctk.CTkFont(size=11),
            text_color="gray60",
            anchor="w",
            wraplength=380
        )
        desc.pack(fill="x", padx=(25, 0))

        # Bind click events to all widgets
        label.bind("<Button-1>", lambda e: self.selected_mode.set(mode_key))
        desc.bind("<Button-1>", lambda e: self.selected_mode.set(mode_key))

        return frame

    def _save_settings(self):
        """Save permission settings and close dialog."""
        mode = self.selected_mode.get()
        self.config.set_permission_mode(mode)
        self.config.save()
        self.destroy()
