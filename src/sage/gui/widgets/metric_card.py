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

        # Value (e.g., "7 Total") - can contain multiple lines
        self.value_widget = ctk.CTkLabel(
            self,
            text=value,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#1a1a1a", "#ffffff"),
            justify="left"
        )
        self.value_widget.grid(row=1, column=0, padx=15, pady=(0, 5), sticky="w")

        # Subtitle for supporting detail.
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


class TokenMetricCard(ctk.CTkFrame):
    """Token card with two anchored columns for all-time and session totals."""

    def __init__(self, master, label: str = "Tokens", **kwargs):
        super().__init__(
            master,
            corner_radius=10,
            fg_color=("#E8E8E8", "#2B2B2B"),
            **kwargs
        )

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.label_widget = ctk.CTkLabel(
            self,
            text=label,
            font=ctk.CTkFont(size=10),
            text_color=("#666666", "#999999"),
            anchor="w",
        )
        self.label_widget.grid(row=0, column=0, columnspan=2, padx=18, pady=(15, 6), sticky="ew")

        self.all_title = self._make_label("All Time", 13, "bold", "w")
        self.all_title.grid(row=1, column=0, padx=(18, 8), pady=(0, 0), sticky="w")

        self.session_title = self._make_label("This Session", 13, "bold", "e")
        self.session_title.grid(row=1, column=1, padx=(8, 18), pady=(0, 0), sticky="e")

        self.all_header = self._make_label("Used | Saved", 11, "bold", "w")
        self.all_header.grid(row=2, column=0, padx=(18, 8), pady=(0, 0), sticky="w")

        self.session_header = self._make_label("Used | Saved", 11, "bold", "e")
        self.session_header.grid(row=2, column=1, padx=(8, 18), pady=(0, 0), sticky="e")

        self.all_value = self._make_label("0 | 0", 15, "bold", "w")
        self.all_value.grid(row=3, column=0, padx=(18, 8), pady=(0, 8), sticky="w")

        self.session_value = self._make_label("0 | 0", 15, "bold", "e")
        self.session_value.grid(row=3, column=1, padx=(8, 18), pady=(0, 8), sticky="e")

        self.subtitle_widget = ctk.CTkLabel(
            self,
            text="No usage yet",
            font=ctk.CTkFont(size=10),
            text_color=("#888888", "#aaaaaa"),
            anchor="w",
        )
        self.subtitle_widget.grid(row=4, column=0, columnspan=2, padx=18, pady=(0, 15), sticky="ew")

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _make_label(self, text: str, size: int, weight: str, anchor: str):
        return ctk.CTkLabel(
            self,
            text=text,
            font=ctk.CTkFont(size=size, weight=weight),
            text_color=("#1a1a1a", "#ffffff"),
            anchor=anchor,
            justify="right" if anchor == "e" else "left",
        )

    def update_tokens(
        self,
        all_used: str,
        all_saved: str,
        session_used: str,
        session_saved: str,
        subtitle: str,
    ):
        self.all_value.configure(text=f"{all_used} | {all_saved}")
        self.session_value.configure(text=f"{session_used} | {session_saved}")
        self.subtitle_widget.configure(text=subtitle)

    def _on_enter(self, event):
        self.configure(fg_color=("#f0f0f0", "#333333"))

    def _on_leave(self, event):
        self.configure(fg_color=("#E8E8E8", "#2B2B2B"))


class DualMetricCard(ctk.CTkFrame):
    """Metric card with identical Total and This Session columns."""

    def __init__(self, master, label: str, **kwargs):
        kwargs.pop("value", None)
        kwargs.pop("subtitle", None)
        label_font_size = int(kwargs.pop("label_font_size", 13))
        title_font_size = int(kwargs.pop("title_font_size", 14))
        value_font_size = int(kwargs.pop("value_font_size", 20))
        muted_font_size = int(kwargs.pop("muted_font_size", 11))
        kwargs["height"] = max(int(kwargs.get("height", 150)), 150)
        super().__init__(
            master,
            corner_radius=10,
            fg_color=("#E8E8E8", "#2B2B2B"),
            **kwargs
        )
        self.grid_propagate(False)
        self.grid_columnconfigure(0, weight=1, uniform="metric")
        self.grid_columnconfigure(1, weight=1, uniform="metric")
        self._muted_font_size = muted_font_size

        self.label_widget = ctk.CTkLabel(
            self,
            text=label,
            font=ctk.CTkFont(size=label_font_size),
            text_color=("#666666", "#999999"),
            anchor="w",
        )
        self.label_widget.grid(row=0, column=0, columnspan=2, padx=16, pady=(14, 8), sticky="ew")

        self.total_title = self._make_label("Total", title_font_size, "bold", "w")
        self.total_title.grid(row=1, column=0, padx=(16, 8), sticky="w")

        self.session_title = self._make_label("This Session", title_font_size, "bold", "e")
        self.session_title.grid(row=1, column=1, padx=(8, 16), sticky="e")

        self.total_value = self._make_label("0", value_font_size, "bold", "w")
        self.total_value.grid(row=2, column=0, padx=(16, 8), pady=(4, 0), sticky="w")

        self.session_value = self._make_label("0", value_font_size, "bold", "e")
        self.session_value.grid(row=2, column=1, padx=(8, 16), pady=(4, 0), sticky="e")

        self.total_hint = self._make_muted_label("", "w")
        self.total_hint.grid(row=3, column=0, padx=(16, 8), pady=(2, 0), sticky="w")

        self.session_hint = self._make_muted_label("", "e")
        self.session_hint.grid(row=3, column=1, padx=(8, 16), pady=(2, 0), sticky="e")

        self.detail = self._make_muted_label("", "w")
        self.detail.grid(row=4, column=0, columnspan=2, padx=16, pady=(8, 14), sticky="ew")

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _make_label(self, text: str, size: int, weight: str, anchor: str):
        return ctk.CTkLabel(
            self,
            text=text,
            font=ctk.CTkFont(size=size, weight=weight),
            text_color=("#1a1a1a", "#ffffff"),
            anchor=anchor,
            justify="right" if anchor == "e" else "left",
        )

    def _make_muted_label(self, text: str, anchor: str):
        return ctk.CTkLabel(
            self,
            text=text,
            font=ctk.CTkFont(size=self._muted_font_size),
            text_color=("#777777", "#aaaaaa"),
            anchor=anchor,
            justify="right" if anchor == "e" else "left",
        )

    def update_metric(
        self,
        total_value: str,
        session_value: str,
        total_hint: str = "",
        session_hint: str = "",
        detail: str = "",
    ):
        self.total_value.configure(text=total_value)
        self.session_value.configure(text=session_value)
        self.total_hint.configure(text=total_hint)
        self.session_hint.configure(text=session_hint)
        self.detail.configure(text=detail)

    def update_value(self, value: str, subtitle: str = ""):
        """Compatibility for the old simple card API."""
        self.update_metric(value, "0", subtitle or "", "", "")

    def update_tokens(
        self,
        all_used: str,
        all_saved: str,
        session_used: str,
        session_saved: str,
        subtitle: str,
    ):
        """Compatibility for the old token card API."""
        self.update_metric(
            total_value=f"{all_used} | {all_saved}",
            session_value=f"{session_used} | {session_saved}",
            total_hint="Used | Saved",
            session_hint="Used | Saved",
            detail=subtitle,
        )

    def _on_enter(self, event):
        self.configure(fg_color=("#f0f0f0", "#333333"))

    def _on_leave(self, event):
        self.configure(fg_color=("#E8E8E8", "#2B2B2B"))
