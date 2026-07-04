"""Project grouped sidebar for SAGE Desktop GUI."""

from __future__ import annotations

import os
import tkinter as tk
from typing import Callable, Optional

import customtkinter as ctk


class FloatingSidebar(ctk.CTkFrame):
    """Left sidebar with project groups, chats, and a chat context menu."""

    def __init__(
        self,
        parent,
        on_chat_select: Optional[Callable[[int], None]] = None,
        on_project_select: Optional[Callable[[str], None]] = None,
        on_settings_click: Optional[Callable[[], None]] = None,
        on_new_chat: Optional[Callable[[], None]] = None,
        on_chat_delete: Optional[Callable[[int], None]] = None,
        on_chat_action: Optional[Callable[[str, dict], None]] = None,
        **kwargs,
    ):
        sidebar_width = kwargs.pop("width", 300)
        super().__init__(parent, width=sidebar_width, **kwargs)

        self.on_chat_select = on_chat_select
        self.on_project_select = on_project_select
        self.on_settings_click = on_settings_click
        self.on_new_chat = on_new_chat
        self.on_chat_delete = on_chat_delete
        self.on_chat_action = on_chat_action
        self.expanded_projects: set[str] = set()
        self._all_groups: list[dict] = []

        self.grid_rowconfigure(4, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=15, pady=(15, 8), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        header = ctk.CTkLabel(
            header_frame,
            text="SAGE",
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        )
        header.grid(row=0, column=0, sticky="w")

        new_chat_btn = ctk.CTkButton(
            self,
            text="✏️ New Chat",
            command=self._on_new_chat_clicked,
            height=34,
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        new_chat_btn.grid(row=1, column=0, padx=15, pady=(0, 6), sticky="ew")

        self.search_entry = ctk.CTkEntry(
            self,
            placeholder_text="🔍 Search",
            height=30,
            font=ctk.CTkFont(size=12),
        )
        self.search_entry.grid(row=2, column=0, padx=15, pady=(0, 8), sticky="ew")
        self.search_entry.bind("<KeyRelease>", lambda _event: self._render_groups())
        self.search_entry.bind("<Escape>", self._clear_search)

        # Menu items container (Scheduled, Plugins)
        menu_frame = ctk.CTkFrame(self, fg_color="transparent")
        menu_frame.grid(row=3, column=0, padx=15, pady=(0, 8), sticky="ew")
        menu_frame.grid_columnconfigure(0, weight=1)

        scheduled_btn = ctk.CTkButton(
            menu_frame,
            text="🕐 Scheduled",
            command=self._on_scheduled_clicked,
            height=32,
            fg_color="transparent",
            hover_color="gray25",
            anchor="w",
            font=ctk.CTkFont(size=13),
        )
        scheduled_btn.grid(row=0, column=0, sticky="ew", pady=(0, 4))

        plugins_btn = ctk.CTkButton(
            menu_frame,
            text="🔌 Plugins",
            command=self._on_plugins_clicked,
            height=32,
            fg_color="transparent",
            hover_color="gray25",
            anchor="w",
            font=ctk.CTkFont(size=13),
        )
        plugins_btn.grid(row=1, column=0, sticky="ew")

        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.grid(row=4, column=0, padx=5, pady=5, sticky="nsew")
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        self.groups_container = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        self.groups_container.grid(row=0, column=0, padx=0, pady=0, sticky="ew")
        self.groups_container.grid_columnconfigure(0, weight=1)

        # Bottom buttons container
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.grid(row=5, column=0, padx=15, pady=15, sticky="ew")
        bottom_frame.grid_columnconfigure(0, weight=1)

        # Settings button
        settings_btn = ctk.CTkButton(
            bottom_frame,
            text="Settings",
            command=self._on_settings,
            height=40,
            fg_color="gray30",
            hover_color="gray25",
            font=ctk.CTkFont(size=13),
        )
        settings_btn.grid(row=0, column=0, sticky="ew")

        self.load_project_groups([])

    def _on_new_chat_clicked(self):
        if self.on_new_chat:
            self.on_new_chat()

    def _on_settings(self):
        if self.on_settings_click:
            self.on_settings_click()

    def _on_scheduled_clicked(self):
        """Show scheduled tasks/workflows."""
        if self.on_chat_action:
            self.on_chat_action("show_scheduled", {"id": ""})

    def _on_plugins_clicked(self):
        """Show plugins/extensions management."""
        if self.on_chat_action:
            self.on_chat_action("show_plugins", {"id": ""})

    def load_project_groups(self, groups: list[dict]):
        """Store fresh data and render it through the active search filter."""
        self._all_groups = groups or []
        self._render_groups()

    def _clear_search(self, _event=None):
        self.search_entry.delete(0, "end")
        self._render_groups()
        return "break"

    def _filtered_groups(self) -> tuple[list[dict], str]:
        """Apply the search box filter to chats and project names."""
        try:
            query = self.search_entry.get().strip().lower()
        except Exception:
            query = ""
        if not query:
            return self._all_groups, ""

        filtered = []
        for group in self._all_groups:
            name_match = query in str(group.get("name", "")).lower()
            chats = [
                chat for chat in group.get("chats", [])
                if query in str(chat.get("title", "")).lower()
            ]
            if name_match and not chats:
                chats = group.get("chats", [])
            if chats or name_match:
                shown = dict(group)
                shown["chats"] = chats
                filtered.append(shown)
        return filtered, query

    def _render_groups(self):
        """Render projects with small chat rows under each project."""
        groups, query = self._filtered_groups()

        for widget in self.groups_container.winfo_children():
            widget.destroy()

        if not groups:
            placeholder = ctk.CTkLabel(
                self.groups_container,
                text="No matching chats" if query else "No chats yet",
                font=ctk.CTkFont(size=12),
                text_color="gray55",
                anchor="w",
            )
            placeholder.grid(row=0, column=0, padx=12, pady=8, sticky="ew")
            return

        # Add "Projects" section header with count
        project_count = len(groups)
        projects_section = ctk.CTkLabel(
            self.groups_container,
            text=f"PROJECTS ({project_count})",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="gray50",
            anchor="w",
        )
        projects_section.grid(row=0, column=0, padx=12, pady=(8, 4), sticky="ew")

        row = 1
        for group in groups:
            project_header = self._create_project_header(group)
            project_header.grid(row=row, column=0, padx=6, pady=(8, 2), sticky="ew")
            row += 1

            project_path = group.get("path", "")
            # Support both 'chats' and 'sessions' keys
            chats = group.get("sessions") or group.get("chats", [])
            expanded = query or project_path in self.expanded_projects
            visible_chats = chats if expanded else chats[:5]

            for chat in visible_chats:
                chat_item = self._create_chat_item(chat)
                chat_item.grid(row=row, column=0, padx=(28, 6), pady=1, sticky="ew")
                row += 1

            if len(chats) > 5 and not query:
                more = ctk.CTkLabel(
                    self.groups_container,
                    text="Show less" if expanded else "Show more",
                    font=ctk.CTkFont(size=11),
                    text_color="gray55",
                    anchor="w",
                    cursor="hand2",
                )
                more.grid(row=row, column=0, padx=(42, 6), pady=(2, 6), sticky="ew")
                more.bind("<Button-1>", lambda _event, path=project_path: self._toggle_project(path))
                row += 1

    def _create_project_header(self, group: dict):
        frame = ctk.CTkFrame(self.groups_container, fg_color="transparent", cursor="hand2")
        frame.grid_columnconfigure(0, weight=1)

        name = str(group.get("name") or "Project")
        count = int(group.get("run_count", 0))

        # Icon and name together
        title = ctk.CTkLabel(
            frame,
            text=f"📁 {name}",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        )
        title.grid(row=0, column=0, padx=8, pady=(5, 0), sticky="ew")

        # Session count badge (support both 'session_count' and 'run_count')
        session_count = group.get("session_count", count)
        meta = ctk.CTkLabel(
            frame,
            text=f"{session_count}",
            font=ctk.CTkFont(size=10),
            text_color="white",
            fg_color="gray40",
            width=28,
            height=18,
            corner_radius=9,
        )
        meta.grid(row=0, column=1, padx=8, pady=(5, 0), sticky="e")

        path = str(group.get("path") or "")
        path_label = ctk.CTkLabel(
            frame,
            text=self._shorten_path(path),
            font=ctk.CTkFont(size=9),
            text_color="gray45",
            anchor="w",
        )
        path_label.grid(row=1, column=0, columnspan=2, padx=8, pady=(0, 5), sticky="ew")

        for widget in (frame, title, meta, path_label):
            widget.bind("<Button-1>", lambda _event, p=path: self._on_project_click(p))

        def on_enter(_event):
            frame.configure(fg_color="gray25")

        def on_leave(_event):
            frame.configure(fg_color="transparent")

        frame.bind("<Enter>", on_enter)
        frame.bind("<Leave>", on_leave)
        return frame

    def _create_chat_item(self, chat: dict):
        frame = ctk.CTkFrame(self.groups_container, fg_color="transparent", cursor="hand2")
        frame.grid_columnconfigure(0, weight=1)

        # Support both old format (int id) and new format (string session_id)
        chat_id = chat.get("id")  # Can be int or str
        raw_title = str(chat.get("display_title") or chat.get("title") or "New Chat")
        title = raw_title[:50] + "..." if len(raw_title) > 50 else raw_title

        # Add visual indicators
        prefix = ""
        if chat.get("pinned") or chat.get("is_pinned"):
            prefix = "📌 "
        elif chat.get("unread") or chat.get("is_unread"):
            prefix = "🔵 "
        else:
            prefix = "💬 "

        title_label = ctk.CTkLabel(
            frame,
            text=f"{prefix}{title}",
            font=ctk.CTkFont(size=11),
            anchor="w",
        )
        title_label.grid(row=0, column=0, padx=5, pady=4, sticky="ew")

        time_label = ctk.CTkLabel(
            frame,
            text=str(chat.get("relative_time") or ""),
            font=ctk.CTkFont(size=11),
            text_color="gray55",
            anchor="e",
        )
        time_label.grid(row=0, column=1, padx=5, pady=4, sticky="e")

        for widget in (frame, title_label, time_label):
            widget.bind("<Button-1>", lambda _event, cid=chat_id: self._on_chat_click(cid))
            widget.bind("<Button-3>", lambda event, c=chat: self._show_context_menu(event, c))

        def on_enter(_event):
            frame.configure(fg_color="gray25")

        def on_leave(_event):
            frame.configure(fg_color="transparent")

        frame.bind("<Enter>", on_enter)
        frame.bind("<Leave>", on_leave)
        return frame

    def _show_context_menu(self, event, chat: dict):
        menu = tk.Menu(self, tearoff=0)
        items = [
            ("Pin chat", "pin"),
            ("Rename chat", "rename"),
            ("Archive chat", "archive"),
            ("Mark as unread", "unread"),
            (None, None),
            ("Open in Explorer", "open_explorer"),
            ("Copy working directory", "copy_workdir"),
            ("Copy session ID", "copy_session_id"),
            ("Copy deeplink", "copy_deeplink"),
            (None, None),
            ("Fork into local", "fork_local"),
            ("Fork into new worktree", "fork_worktree"),
            (None, None),
            ("Open in new window", "open_new_window"),
            ("Delete chat", "delete"),
        ]
        for label, action in items:
            if label is None:
                menu.add_separator()
            else:
                menu.add_command(
                    label=label,
                    command=lambda a=action, c=chat: self._on_chat_action(a, c),
                )
        menu.tk_popup(event.x_root, event.y_root)

    def _on_chat_click(self, chat_id: int):
        if self.on_chat_select:
            self.on_chat_select(chat_id)

    def _on_chat_action(self, action: str, chat: dict):
        if action == "delete" and self.on_chat_delete:
            self.on_chat_delete(int(chat["id"]))
            return
        if self.on_chat_action:
            self.on_chat_action(action, chat)

    def _on_project_click(self, project_path: str):
        if self.on_project_select:
            self.on_project_select(project_path)

    def _toggle_project(self, project_path: str):
        if project_path in self.expanded_projects:
            self.expanded_projects.remove(project_path)
        else:
            self.expanded_projects.add(project_path)
        if self.on_chat_action:
            self.on_chat_action("refresh_sidebar", {"id": -1})

    def _shorten_path(self, path: str) -> str:
        if len(path) <= 42:
            return path
        return "..." + path[-39:]

    # Backwards-compatible methods used by older app code/tests.
    def load_recent_chats(self, chats: list[dict]):
        self.load_project_groups([
            {
                "name": "Current Project",
                "path": os.getcwd(),
                "run_count": len(chats),
                "chats": chats,
            }
        ])

    def load_projects(self, projects: list[dict]):
        if projects and not self.groups_container.winfo_children():
            self.load_project_groups([
                {
                    "name": project.get("name", "Project"),
                    "path": project.get("path", ""),
                    "run_count": project.get("run_count", 0),
                    "chats": [],
                }
                for project in projects
            ])
