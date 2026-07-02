"""Metric Card Widget for SAGE Desktop GUI"""

import customtkinter as ctk


class MetricCard(ctk.CTkFrame):
    """Reusable metric card widget with label, value, and subtitle"""

    def __init__(self, master, label: str, value: str = "0", subtitle: str = "", **kwargs):
        # Card styling with hover effect
        super().__init__(
            master,
            corner_radius=10,
            fg_color=("#E8E8E8", "#2B2B2B"),
            **kwargs
        )

        self.label = label
        self._value = value
        self._subtitle = subtitle

        # Configure grid
        self.grid_columnconfigure(0, weight=1)

        # Label (e.g., "Total Commands")
        self.label_widget = ctk.CTkLabel(
            self,
            text=label,
            font=ctk.CTkFont(size=12, weight="normal"),
            text_color=("#666666", "#999999")
        )
        self.label_widget.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")

        # Value (e.g., "7 Total")
        self.value_widget = ctk.CTkLabel(
            self,
            text=value,
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=("#1a1a1a", "#ffffff")
        )
        self.value_widget.grid(row=1, column=0, padx=15, pady=(0, 5), sticky="w")

        # Subtitle (e.g., "99.3% Rate")
        if subtitle:
            self.subtitle_widget = ctk.CTkLabel(
                self,
                text=subtitle,
                font=ctk.CTkFont(size=11, weight="normal"),
                text_color=("#888888", "#aaaaaa")
            )
            self.subtitle_widget.grid(row=2, column=0, padx=15, pady=(0, 15), sticky="w")
        else:
            self.subtitle_widget = None

        # Hover effect bindings
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def update_value(self, value: str, subtitle: str = None):
        """Update the card's value and optional subtitle"""
        self._value = value
        self.value_widget.configure(text=value)

        if subtitle is not None:
            self._subtitle = subtitle
            if self.subtitle_widget:
                self.subtitle_widget.configure(text=subtitle)
            elif subtitle:
                # Create subtitle widget if it doesn't exist
                self.subtitle_widget = ctk.CTkLabel(
                    self,
                    text=subtitle,
                    font=ctk.CTkFont(size=11, weight="normal"),
                    text_color=("#888888", "#aaaaaa")
                )
                self.subtitle_widget.grid(row=2, column=0, padx=15, pady=(0, 15), sticky="w")

    def _on_enter(self, event):
        """Hover effect - slightly lighter background"""
        self.configure(fg_color=("#f0f0f0", "#333333"))

    def _on_leave(self, event):
        """Remove hover effect"""
        self.configure(fg_color=("#E8E8E8", "#2B2B2B"))
