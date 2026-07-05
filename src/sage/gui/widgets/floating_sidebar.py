"""Project grouped sidebar for SAGE Desktop GUI."""

from __future__ import annotations

import hashlib
import json
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
        self._last_groups_hash: str = ""  # Track when data actually changes

        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=15, pady=(15, 8), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        header = ctk.CTkLabel(
            header_frame,
            text="SAGE",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#8b5cf6",
            anchor="w",
        )
        header.grid(row=0, column=0, sticky="w")

        new_chat_btn = ctk.CTkButton(
            self,
            text="+ New Chat",
            command=self._on_new_chat_clicked,
            height=34,
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        new_chat_btn.grid(row=1, column=0, padx=15, pady=(0, 8), sticky="ew")

        self.search_entry = ctk.CTkEntry(
            self,
            placeholder_text="Search chats...",
            height=30,
            font=ctk.CTkFont(size=12),
        )
        self.search_entry.grid(row=2, column=0, padx=15, pady=(0, 8), sticky="ew")
        self.search_entry.bind("<KeyRelease>", lambda _event: self._render_groups())
        self.search_entry.bind("<Escape>", self._clear_search)

        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.grid(row=3, column=0, padx=5, pady=5, sticky="nsew")
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        self.groups_container = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        self.groups_container.grid(row=0, column=0, padx=0, pady=0, sticky="ew")
        self.groups_container.grid_columnconfigure(0, weight=1)

        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.grid(row=4, column=0, padx=15, pady=15, sticky="ew")
        bottom_frame.grid_columnconfigure(0, weight=1)

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
        if self.on_chat_action:
            self.on_chat_action("show_scheduled", {"id": ""})

    def _on_plugins_clicked(self):
        if self.on_chat_action:
            self.on_chat_action("show_plugins", {"id": ""})

    def load_project_groups(self, groups: list[dict]):
        self._all_groups = groups or []
        self._render_groups()

    def _clear_search(self, _event=None):
        self.search_entry.delete(0, "end")
        self._render_groups()
        return "break"

    def _filtered_groups(self) -> tuple[list[dict], str]:
        try:
            query = self.search_entry.get().strip().lower()
        except Exception:
            query = ""
        if not query:
            return self._all_groups, ""

        filtered = []
        for group in self._all_groups:
            chats = group.get("sessions") or group.get("chats", [])
            name_match = query in str(group.get("name", "")).lower()
            shown_chats = [
                chat for chat in chats
                if query in str(chat.get("title") or chat.get("display_title") or "").lower()
            ]
            if name_match and not shown_chats:
                shown_chats = chats
            if shown_chats or name_match:
                shown = dict(group)
                shown["chats"] = shown_chats
                shown["sessions"] = shown_chats
                filtered.append(shown)
        return filtered, query

    def _render_groups(self):
        groups, query = self._filtered_groups()

        # Only rebuild if data actually changed (prevents sidebar blink every 2s)
        current_hash = hashlib.md5(json.dumps(groups, sort_keys=True).encode()).hexdigest()
        if current_hash == self._last_groups_hash and not query:
            return
        self._last_groups_hash = current_hash

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

        projects_section = ctk.CTkLabel(
            self.groups_container,
            text="Projects",
            font=ctk.CTkFont(size=13),
            text_color="gray50",
            anchor="w",
        )
        projects_section.grid(row=0, column=0, padx=12, pady=(8, 8), sticky="ew")

        row = 1
        for group in groups:
            project_path = str(group.get("path") or "")
            chats = group.get("sessions") or group.get("chats", [])

            project_header = self._create_project_header(group, len(chats))
            project_header.grid(row=row, column=0, padx=6, pady=(6, 2), sticky="ew")
            row += 1

            expanded = bool(query) or project_path in self.expanded_projects
            visible_chats = chats if expanded else chats[:5]

            for chat in visible_chats:
                chat_item = self._create_chat_item(chat)
                chat_item.grid(row=row, column=0, padx=(32, 6), pady=1, sticky="ew")
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
                more.grid(row=row, column=0, padx=(42, 6), pady=(3, 8), sticky="ew")
                more.bind("<Button-1>", lambda _event, path=project_path: self._toggle_project(path))
                row += 1

    def _create_project_header(self, group: dict, chat_count: int):
        frame = ctk.CTkFrame(self.groups_container, fg_color="transparent", cursor="hand2")
        frame.grid_columnconfigure(0, weight=1)

        name = str(group.get("name") or "Project")
        title = ctk.CTkLabel(
            frame,
            text=f"[project] {name}",
            font=ctk.CTkFont(size=13),
            anchor="w",
        )
        title.grid(row=0, column=0, padx=8, pady=(5, 0), sticky="ew")

        meta = ctk.CTkLabel(
            frame,
            text=str(chat_count),
            font=ctk.CTkFont(size=10),
            text_color="gray55",
            width=28,
            height=18,
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

        frame.bind("<Enter>", lambda _event: frame.configure(fg_color="gray25"))
        frame.bind("<Leave>", lambda _event: frame.configure(fg_color="transparent"))
        return frame

    def _create_chat_item(self, chat: dict):
        frame = ctk.CTkFrame(self.groups_container, fg_color="transparent", cursor="hand2")
        frame.grid_columnconfigure(0, weight=1)

        chat_id = chat.get("id")
        raw_title = str(chat.get("display_title") or chat.get("title") or "New Chat")
        title = raw_title[:36] + "..." if len(raw_title) > 36 else raw_title
        if chat.get("pinned") or chat.get("is_pinned"):
            title = f"* {title}"

        title_label = ctk.CTkLabel(
            frame,
            text=title,
            font=ctk.CTkFont(size=12),
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

        frame.bind("<Enter>", lambda _event: frame.configure(fg_color="gray25"))
        frame.bind("<Leave>", lambda _event: frame.configure(fg_color="transparent"))
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
                menu.add_command(label=label, command=lambda a=action, c=chat: self._on_chat_action(a, c))
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
        self._render_groups()

    def _shorten_path(self, path: str) -> str:
        if len(path) <= 42:
            return path
        return "..." + path[-39:]

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
