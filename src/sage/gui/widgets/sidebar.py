"""Sidebar Widget for SAGE Desktop GUI."""

import customtkinter as ctk
from typing import Callable, Optional, List
from datetime import datetime


class Sidebar(ctk.CTkFrame):
    """Left sidebar with recent chats, projects, and settings."""

    def __init__(
        self,
        parent,
        on_chat_select: Optional[Callable[[int], None]] = None,
        on_project_select: Optional[Callable[[str], None]] = None,
        on_settings_click: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        """
        Initialize sidebar widget.

        Args:
            parent: Parent widget
            on_chat_select: Callback when chat is selected (chat_id)
            on_project_select: Callback when project is selected (project_path)
            on_settings_click: Callback when settings button is clicked
        """
        super().__init__(parent, width=250, **kwargs)

        self.on_chat_select = on_chat_select
        self.on_project_select = on_project_select
        self.on_settings_click = on_settings_click

        # Configure grid
        self.grid_rowconfigure(2, weight=1)  # Chats/Projects area expands
        self.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkLabel(
            self,
            text="🧠 SAGE",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        header.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="w")

        # New Chat button
        new_chat_btn = ctk.CTkButton(
            self,
            text="+ New Chat",
            command=self._on_new_chat,
            height=32,
            font=ctk.CTkFont(size=13)
        )
        new_chat_btn.grid(row=1, column=0, padx=15, pady=(0, 10), sticky="ew")

        # Scrollable frame for chats and projects
        self.scroll_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent"
        )
        self.scroll_frame.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        # Recent Chats section
        self.chats_header = ctk.CTkLabel(
            self.scroll_frame,
            text="Recent Chats (0)",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        )
        self.chats_header.grid(row=0, column=0, padx=10, pady=(5, 5), sticky="w")

        self.chats_container = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        self.chats_container.grid(row=1, column=0, padx=5, pady=0, sticky="ew")
        self.chats_container.grid_columnconfigure(0, weight=1)

        # Projects section
        self.projects_header = ctk.CTkLabel(
            self.scroll_frame,
            text="Projects (0)",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        )
        self.projects_header.grid(row=2, column=0, padx=10, pady=(15, 5), sticky="w")

        self.projects_container = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        self.projects_container.grid(row=3, column=0, padx=5, pady=0, sticky="ew")
        self.projects_container.grid_columnconfigure(0, weight=1)

        # Settings button at bottom
        settings_btn = ctk.CTkButton(
            self,
            text="⚙️  Settings",
            command=self._on_settings,
            height=40,
            fg_color="gray30",
            hover_color="gray25",
            font=ctk.CTkFont(size=13)
        )
        settings_btn.grid(row=3, column=0, padx=15, pady=15, sticky="ew")

        # Load initial data
        self.load_recent_chats([])
        self.load_projects([])

    def _on_new_chat(self):
        """Handle new chat button click."""
        # Clear current chat in main area
        pass

    def _on_settings(self):
        """Handle settings button click."""
        if self.on_settings_click:
            self.on_settings_click()

    def load_recent_chats(self, chats: List[dict]):
        """
        Load recent chats into sidebar.

        Args:
            chats: List of dicts with keys: id, title, timestamp, ai_model
        """
        # Update header with count
        count = len(chats) if chats else 0
        self.chats_header.configure(text=f"Recent Chats ({count})")

        # Clear existing
        for widget in self.chats_container.winfo_children():
            widget.destroy()

        if not chats:
            # Show placeholder
            placeholder = ctk.CTkLabel(
                self.chats_container,
                text="No recent chats",
                font=ctk.CTkFont(size=11),
                text_color="gray50"
            )
            placeholder.grid(row=0, column=0, padx=10, pady=5)
            return

        # Add chat items
        for i, chat in enumerate(chats[:10]):  # Show last 10
            chat_item = self._create_chat_item(chat)
            chat_item.grid(row=i, column=0, padx=5, pady=2, sticky="ew")

    def _create_chat_item(self, chat: dict):
        """Create a chat list item."""
        frame = ctk.CTkFrame(
            self.chats_container,
            fg_color="transparent",
            cursor="hand2"
        )

        # Title
        title = chat.get("title", f"Chat #{chat.get('id', '?')}")
        title_label = ctk.CTkLabel(
            frame,
            text=title[:30] + "..." if len(title) > 30 else title,
            font=ctk.CTkFont(size=11),
            anchor="w"
        )
        title_label.pack(fill="x", padx=8, pady=(4, 0))

        # Metadata
        ai_model = chat.get("ai_model", "Claude")
        timestamp = chat.get("timestamp", "")
        meta_label = ctk.CTkLabel(
            frame,
            text=f"{ai_model} • {timestamp}",
            font=ctk.CTkFont(size=9),
            text_color="gray60",
            anchor="w"
        )
        meta_label.pack(fill="x", padx=8, pady=(0, 4))

        # Click handler
        frame.bind("<Button-1>", lambda e: self._on_chat_click(chat["id"]))
        title_label.bind("<Button-1>", lambda e: self._on_chat_click(chat["id"]))
        meta_label.bind("<Button-1>", lambda e: self._on_chat_click(chat["id"]))

        # Hover effect
        def on_enter(e):
            frame.configure(fg_color="gray25")

        def on_leave(e):
            frame.configure(fg_color="transparent")

        frame.bind("<Enter>", on_enter)
        frame.bind("<Leave>", on_leave)

        return frame

    def _on_chat_click(self, chat_id: int):
        """Handle chat item click."""
        if self.on_chat_select:
            self.on_chat_select(chat_id)

    def load_projects(self, projects: List[dict]):
        """
        Load projects into sidebar.

        Args:
            projects: List of dicts with keys: path, name, last_used
        """
        # Update header with count
        count = len(projects) if projects else 0
        self.projects_header.configure(text=f"Projects ({count})")

        # Clear existing
        for widget in self.projects_container.winfo_children():
            widget.destroy()

        if not projects:
            # Show current directory
            import os
            current_dir = os.getcwd()
            dir_name = os.path.basename(current_dir)

            project_item = self._create_project_item({
                "path": current_dir,
                "name": dir_name or "Current Directory",
                "last_used": "Now"
            })
            project_item.grid(row=0, column=0, padx=5, pady=2, sticky="ew")
            return

        # Add project items
        for i, project in enumerate(projects[:5]):  # Show last 5
            project_item = self._create_project_item(project)
            project_item.grid(row=i, column=0, padx=5, pady=2, sticky="ew")

    def _create_project_item(self, project: dict):
        """Create a project list item."""
        frame = ctk.CTkFrame(
            self.projects_container,
            fg_color="transparent",
            cursor="hand2"
        )

        # Name
        name = project.get("name", "Unknown")
        name_label = ctk.CTkLabel(
            frame,
            text=f"📁 {name}",
            font=ctk.CTkFont(size=11),
            anchor="w"
        )
        name_label.pack(fill="x", padx=8, pady=(4, 0))

        # Path
        path = project.get("path", "")
        if len(path) > 35:
            path = "..." + path[-32:]
        path_label = ctk.CTkLabel(
            frame,
            text=path,
            font=ctk.CTkFont(size=9),
            text_color="gray60",
            anchor="w"
        )
        path_label.pack(fill="x", padx=8, pady=(0, 4))

        # Click handler
        full_path = project.get("path", "")
        frame.bind("<Button-1>", lambda e: self._on_project_click(full_path))
        name_label.bind("<Button-1>", lambda e: self._on_project_click(full_path))
        path_label.bind("<Button-1>", lambda e: self._on_project_click(full_path))

        # Hover effect
        def on_enter(e):
            frame.configure(fg_color="gray25")

        def on_leave(e):
            frame.configure(fg_color="transparent")

        frame.bind("<Enter>", on_enter)
        frame.bind("<Leave>", on_leave)

        return frame

    def _on_project_click(self, project_path: str):
        """Handle project item click."""
        if self.on_project_select:
            self.on_project_select(project_path)
