import logging
"""SAGE Desktop GUI - Main Application (Redesigned Layout)"""

import customtkinter as ctk
from sage.gui.widgets.metric_card import DualMetricCard as MetricCard, DualMetricCard as TokenMetricCard
from sage.gui.widgets.ai_selector import AISelector
from sage.gui.widgets.input_area import InputArea
from sage.gui.widgets.powershell_terminal import PowerShellTerminal, HAS_WINPTY
from sage.gui.widgets.floating_sidebar import FloatingSidebar
from sage.gui.widgets.led_border import ThinkingOverlay
from sage.gui.config import GUIConfig
from sage.gui.cli_client import CLIClient, check_cli_available, _clean_for_display
from sage.gui.persistent_ai_client import PersistentAIClient
from sage.gui.session_manager import SessionManager
from sage.gui import api_travel
from sage.store import connect, data_dir, save_run
from sage.context import ContextManager
from sage.agents import DEFAULT_AGENT_SPECS, ensure_default_agents, get_agent_tasks_for_run, select_agents_for_command
from sage.ml import FailurePredictor, SklearnFailureModel
from sage.classify import workspace_hash
from sage.security import command_hash, evaluate_command, load_policy, redact_text, retention_expiry
import json
import queue
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
from PIL import Image
from typing import Optional
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime, timezone
import sys
import os

log = logging.getLogger(__name__)

LOG = logging.getLogger(__name__)

def _set_windows_app_id() -> None:
    """Make Windows taskbar grouping use the SAGE icon instead of Tk's default."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("sage.desktop")
    except Exception:
        log.debug("suppressed", exc_info=True)

class SAGEApp(ctk.CTk):
    """Main SAGE Desktop GUI Application"""

    def __init__(self):
        super().__init__()

        # Window configuration
        self.title("SAGE Desktop - By PsYcGoD AI&ML")
        self.geometry("1300x800")
        self._set_window_icon()

        # Set appearance mode and color theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Load configuration
        self.config = GUIConfig()
        self._restore_current_project()
        ensure_default_agents()

        # Configure grid layout: sidebar (0) | center content (1) | right metrics (2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar (fixed left side)
        self.sidebar = FloatingSidebar(
            self,
            on_chat_select=self.load_chat,
            on_project_select=self.switch_project,
            on_settings_click=self.open_permission_settings,
            on_new_chat=self.new_chat_with_folder_picker,
            on_chat_delete=self.delete_chat,
            on_chat_action=self.handle_chat_action,
            width=320
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        # Main content frame (right side)
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.grid(row=0, column=1, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(2, weight=1)  # Output view expands

        # LED border animation overlay
        self.thinking_overlay = ThinkingOverlay(main_frame)
        self.thinking_overlay.place_forget()

        # Row 0: Header with title and AI selector
        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        # Title on left — small header with product branding
        self.header = ctk.CTkLabel(
            header_frame,
            text="Sage Desktop - By PsYcGoD AI&ML",
            font=ctk.CTkFont(size=15, weight="bold")
        )
        self.header.grid(row=0, column=0, sticky="w")

        self.project_label = ctk.CTkLabel(
            header_frame,
            text=f"Working dir: {os.getcwd()}",
            font=ctk.CTkFont(size=11),
            text_color="gray60",
            anchor="w",
        )
        self.project_label.grid(row=1, column=0, sticky="w")

        self.runtime_label = ctk.CTkLabel(
            header_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray60",
            anchor="w",
        )
        self.runtime_label.grid(row=2, column=0, sticky="w")

        self.run_status_label = ctk.CTkLabel(
            header_frame,
            text="Idle",
            font=ctk.CTkFont(size=11),
            text_color="gray60",
            anchor="e",
        )
        self.run_status_label.grid(row=1, column=1, sticky="e")

        # Response timer, kept a little gap to the side of the status.
        self.timer_label = ctk.CTkLabel(
            header_frame,
            text="⏱ 0.0s",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="gray60",
            anchor="e",
        )
        self.timer_label.grid(row=2, column=1, sticky="e", padx=(12, 0))
        self._timer_running = False
        self._timer_start = 0.0
        self._last_answer_seconds = 0.0

        # AI selector and Connect button on right (compact)
        ai_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        ai_frame.grid(row=0, column=1, sticky="e")

        # Connection status indicator
        self.status_indicator = ctk.CTkLabel(
            ai_frame,
            text="●",
            font=ctk.CTkFont(size=16),
            text_color="red"
        )
        self.status_indicator.pack(side="left", padx=(0, 5))

        ai_label = ctk.CTkLabel(
            ai_frame,
            text="AI:",
            font=ctk.CTkFont(size=12)
        )
        ai_label.pack(side="left", padx=(0, 5))

        self.ai_selector = ctk.CTkComboBox(
            ai_frame,
            values=["Claude", "Codex", "Ollama", "Gemini", "Llama", "Mistral"],
            command=self.on_ai_changed,
            state="readonly",
            width=100
        )
        self.ai_selector.set(self.config.get_default_ai().capitalize())
        self.ai_selector.pack(side="left", padx=(0, 5))

        # Connect button
        self.connect_btn = ctk.CTkButton(
            ai_frame,
            text="Connect",
            command=self.on_connect_ai,
            width=80,
            height=28,
            font=ctk.CTkFont(size=12)
        )
        self.connect_btn.pack(side="left")

        self.debug_btn = ctk.CTkButton(
            ai_frame,
            text="Debug",
            command=self.copy_debug_bundle,
            width=64,
            height=28,
            font=ctk.CTkFont(size=12)
        )
        self.debug_btn.pack(side="left", padx=(5, 0))

        # Row 1: Live 24-agent status strip (green=active, orange=idle/stopped)
        from sage.gui.widgets.agent_strip import AgentStrip

        self.agent_strip = AgentStrip(main_frame)
        self.agent_strip.grid(row=1, column=0, padx=20, pady=(2, 6), sticky="ew")
        self._manual_active_agent_types: set[str] = set()

        # Right metrics panel: the 4 cards stacked vertically, autofit.
        metrics_panel = ctk.CTkFrame(self, fg_color=("#DEDEDE", "#1c1c1c"), width=232)
        metrics_panel.grid(row=0, column=2, sticky="nsew", padx=(0, 0), pady=0)
        metrics_panel.grid_propagate(False)
        metrics_panel.grid_columnconfigure(0, weight=1)
        for r in range(1, 5):
            metrics_panel.grid_rowconfigure(r, weight=1)

        metrics_title = ctk.CTkLabel(
            metrics_panel,
            text="Live Metrics",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="gray60",
            anchor="w",
        )
        metrics_title.grid(row=0, column=0, padx=12, pady=(12, 4), sticky="ew")

        self.create_metric_cards(metrics_panel)

        # Per-output-tab runtime state. Conversation memory is keyed by project
        # so tabs (and different AIs) on the SAME project share one memory and
        # reuse context to save tokens, while different projects stay isolated.
        self.output_tabs: dict[int, dict] = {}
        self._live_memory_by_project: dict[str, list] = {}
        self._saved_memory_by_project: dict[str, list] = {}
        self.active_output_tab_id: int | None = None
        self.next_output_tab_id = 1
        self.persistent_client = None
        self.current_client = None
        self.ai_thread = None
        self.ai_connected = False
        self.ai_process = None
        self.ai_running = False
        self._bind_project_memory(os.getcwd())
        self.max_context_chars = 14000
        self.pending_context_compression = None

        # Session management
        self.session_manager = SessionManager()
        self.current_session_id = None

        # Row 2: Output view container (with LED border)
        output_container = ctk.CTkFrame(main_frame, fg_color="transparent")
        output_container.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        output_container.grid_columnconfigure(0, weight=1)
        output_container.grid_rowconfigure(1, weight=1)

        self.output_container = output_container
        self.output_tab_bar = ctk.CTkFrame(output_container, fg_color="transparent")
        self.output_tab_bar.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self.output_tab_bar.grid_columnconfigure(99, weight=1)

        self.output_stack = ctk.CTkFrame(output_container, fg_color="transparent")
        self.output_stack.grid(row=1, column=0, sticky="nsew")
        self.output_stack.grid_columnconfigure(0, weight=1)
        self.output_stack.grid_rowconfigure(0, weight=1)

        self.add_tab_btn = ctk.CTkButton(
            self.output_tab_bar,
            text="+",
            command=self.add_output_tab,
            width=32,
            height=28,
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        self.add_tab_btn.grid(row=0, column=98, padx=(6, 0), pady=0, sticky="e")
        self.output_view = None

        # Thin thinking activity strip between output and prompt input.
        self.thinking_strip_frame = ctk.CTkFrame(main_frame, fg_color="transparent", height=6)
        self.thinking_strip_frame.grid(row=3, column=0, padx=20, pady=(0, 4), sticky="ew")
        self.thinking_strip_frame.grid_propagate(False)
        self.thinking_overlay = ThinkingOverlay(self.thinking_strip_frame)
        self.thinking_overlay.place_forget()

        # Row 4: Input area at bottom
        self.input_area = InputArea(
            main_frame,
            on_send=self.on_send_command,
            on_clear=self.on_clear_output,
            on_permission_change=self.on_permission_changed,
            on_cancel=self.on_cancel_process,
            on_output_theme_toggle=self.toggle_output_light_mode
        )
        self.input_area.grid(row=4, column=0, padx=20, pady=(0, 15), sticky="ew")
        self.bind("<Escape>", self._on_escape_key)

        # Set initial permission from config
        self.input_area.set_permission(self.config.get_permission_mode())
        self.output_light_mode = bool(self.config.get("output_light_mode", False))
        self.input_area.set_output_light_mode(self.output_light_mode)
        self._create_output_tab(
            ai_name=self.ai_selector.get().lower(),
            project=os.getcwd(),
            activate=True,
        )

        # Restore this project's chat memory after the welcome screen renders.
        self.after(700, lambda: self._load_saved_conversation(announce=True))

        # Auto-create or load session for current project
        self.current_session_id = self.session_manager.get_or_create_session(os.getcwd())

        # Session metric baseline
        self.session_start_commands = 0
        self.session_start_successes = 0
        self.session_start_agents = 0
        self.session_start_agent_tasks = 0
        self.session_start_used = 0
        self.session_start_saved = 0
        self._init_session_baseline()

        # Load sidebar data
        self.load_sidebar_data()
        self._refresh_runtime_labels()
        self.update_running = True
        self.update_metrics()

    def _on_escape_key(self, event):
        """Esc cancels the active run; it must not close the SAGE window."""
        self.on_cancel_process()
        return "break"

    def _set_window_icon(self) -> None:
        """Use bundled SAGE icons for the title bar and Windows taskbar."""
        assets_dir = Path(__file__).parent / "assets"
        ico_path = assets_dir / "sage-icon.ico"
        png_path = assets_dir / "sage-icon-256.png"

        try:
            if ico_path.exists():
                self.iconbitmap(str(ico_path))
        except Exception:
            log.debug("suppressed", exc_info=True)

        try:
            if png_path.exists():
                self._sage_window_icon = tk.PhotoImage(file=str(png_path))
                self.iconphoto(True, self._sage_window_icon)
        except Exception:
            log.debug("suppressed", exc_info=True)

    def _refresh_runtime_labels(self) -> None:
        """Refresh compact permission/model/policy status in the header."""
        try:
            ai_name = self._active_ai_name()
            model = self._get_selected_model(ai_name) or "CLI default"
            permission = self.config.get_permission_mode()
            policy = load_policy()
            policy_mode = policy.get("mode", "personal")
            self.runtime_label.configure(
                text=f"Permission: {permission} | Model: {model} | Policy: {policy_mode}"
            )
        except Exception:
            log.debug("suppressed", exc_info=True)

    def _set_run_status(self, text: str, color: str = "gray60") -> None:
        try:
            self.run_status_label.configure(text=text, text_color=color)
        except Exception:
            log.debug("suppressed", exc_info=True)
        # Drive the per-answer response timer from the run status transitions.
        try:
            if str(text).lower().startswith("running"):
                self._start_response_timer()
            elif str(text).lower().startswith("idle"):
                self._stop_response_timer()
        except Exception:
            log.debug("suppressed", exc_info=True)

    def _start_response_timer(self) -> None:
        """Begin timing the current answer and tick the header timer live."""
        if getattr(self, "_timer_running", False):
            return
        self._timer_running = True
        self._timer_start = time.monotonic()
        self._tick_response_timer()

    def _tick_response_timer(self) -> None:
        if not getattr(self, "_timer_running", False):
            return
        elapsed = time.monotonic() - self._timer_start
        try:
            self.timer_label.configure(text=f"⏱ {elapsed:.1f}s", text_color="#facc15")
        except Exception:
            return
        self.after(100, self._tick_response_timer)

    def _stop_response_timer(self) -> None:
        """Freeze the timer at the final answer duration."""
        if not getattr(self, "_timer_running", False):
            return
        self._timer_running = False
        self._last_answer_seconds = time.monotonic() - self._timer_start
        try:
            self.timer_label.configure(
                text=f"⏱ {self._last_answer_seconds:.1f}s", text_color="#22c55e"
            )
        except Exception:
            log.debug("suppressed", exc_info=True)

    def _confirm_company_mode_send(self, ai_name: str, prompt: str) -> bool:
        """Preview AI prompt execution when policy is in company mode."""
        try:
            policy = load_policy()
            if policy.get("mode") != "company":
                return True
            decision = evaluate_command(prompt, mode="company", dry_run=False)
            preview = prompt.strip().replace("\n", " ")
            if len(preview) > 220:
                preview = preview[:217] + "..."
            return messagebox.askyesno(
                "SAGE company mode preview",
                "Send this prompt through SAGE?\n\n"
                f"AI: {ai_name.capitalize()}\n"
                f"Policy: {decision.decision} - {decision.reason}\n\n"
                f"{preview}",
            )
        except Exception:
            return True

    def copy_debug_bundle(self) -> None:
        """Copy a compact local debug bundle to the clipboard."""
        try:
            with connect() as conn:
                runs = conn.execute(
                    "SELECT COUNT(*), SUM(CASE WHEN exit_code = 0 THEN 1 ELSE 0 END), "
                    "SUM(CASE WHEN exit_code != 0 THEN 1 ELSE 0 END) FROM runs"
                ).fetchone()
                compression = conn.execute(
                    "SELECT COALESCE(SUM(original_tokens),0), COALESCE(SUM(compressed_tokens),0), "
                    "COALESCE(SUM(saved_tokens),0) FROM context_compression"
                ).fetchone()
                redactions = conn.execute(
                    "SELECT COALESCE(SUM(stdout_redactions + stderr_redactions + summary_redactions),0) FROM runs"
                ).fetchone()[0]
                tasks = conn.execute("SELECT COUNT(*) FROM agent_tasks").fetchone()[0]
            policy = load_policy()
            bundle = (
                "SAGE debug bundle\n"
                f"Project: {os.getcwd()}\n"
                f"AI: {self.ai_selector.get()}\n"
                f"Permission: {self.config.get_permission_mode()}\n"
                f"Policy: {policy.get('mode')} / {policy.get('redaction_strictness')}\n"
                f"Runs: {runs[0]} ({runs[1] or 0} ok, {runs[2] or 0} failed)\n"
                f"Tokens: original={compression[0] or 0}, compressed={compression[1] or 0}, saved={compression[2] or 0}\n"
                f"Agent tasks: {tasks}\n"
                f"Redactions: {redactions or 0}\n"
            )
            self.clipboard_clear()
            self.clipboard_append(bundle)
            self.output_view.append_text("\n[Debug bundle copied to clipboard]\n", "info")
        except Exception as exc:
            self.output_view.append_text(f"\n[Debug bundle failed: {exc}]\n", "error")

    def add_output_tab(self) -> int:
        """Create a new output terminal tab using the current connector/project."""
        ai_name = self.ai_selector.get().lower()
        project = os.getcwd()
        return self._create_output_tab(ai_name=ai_name, project=project, activate=True)

    def _create_output_tab(self, *, ai_name: str, project: str, activate: bool = False) -> int:
        """Create one independently scrollable terminal session."""
        tab_id = self.next_output_tab_id
        self.next_output_tab_id += 1
        terminal = PowerShellTerminal(
            self.output_stack,
            on_reply_to_selection=self.reply_to_output_selection,
            on_ai_response_complete=self._remember_terminal_ai_response,
            on_ai_stream_finished=lambda error, tid=tab_id: self._finish_terminal_ai_run(tid, error),
        )
        terminal.grid(row=0, column=0, sticky="nsew")
        terminal.grid_remove()
        terminal.set_light_mode(bool(getattr(self, "output_light_mode", False)))

        mode = "Personal Mode" if self.config.is_personal_mode() else "Full Access"
        terminal.start_powershell(project=project, ai_name=ai_name.capitalize(), mode=mode)
        self.output_tabs[tab_id] = {
            "id": tab_id,
            "title": f"{ai_name.capitalize()} {tab_id}",
            "ai_name": ai_name,
            "project": project,
            "terminal": terminal,
            "persistent_client": None,
            "current_client": None,
            "ai_connected": False,
            "ai_running": False,
            "ai_thread": None,
            "ai_process": None,
            "pending_prompts": [],
        }
        self._render_output_tabs()
        if activate:
            self._activate_output_tab(tab_id)
        return tab_id

    def _render_output_tabs(self) -> None:
        """Render Excel-style output tabs above the active terminal."""
        for widget in self.output_tab_bar.winfo_children():
            if widget is not self.add_tab_btn:
                widget.destroy()
        column = 0
        for tab_id, tab in sorted(self.output_tabs.items()):
            active = tab_id == self.active_output_tab_id
            project_name = Path(tab.get("project") or "").name or "Project"
            label = f"{tab.get('ai_name', 'ai').capitalize()} - {project_name}"
            if len(label) > 30:
                label = label[:27] + "..."
            btn = ctk.CTkButton(
                self.output_tab_bar,
                text=label,
                command=lambda tid=tab_id: self._activate_output_tab(tid),
                width=138,
                height=28,
                fg_color="#2563eb" if active else "gray25",
                hover_color="#1d4ed8" if active else "gray35",
                font=ctk.CTkFont(size=12, weight="bold" if active else "normal"),
            )
            btn.grid(row=0, column=column, padx=(0, 4), pady=0, sticky="w")
            column += 1
            close_btn = ctk.CTkButton(
                self.output_tab_bar,
                text="x",
                command=lambda tid=tab_id: self.close_output_tab(tid),
                width=28,
                height=28,
                fg_color="#1f2937" if active else "gray20",
                hover_color="#7f1d1d",
                font=ctk.CTkFont(size=12, weight="bold"),
            )
            close_btn.grid(row=0, column=column, padx=(0, 8), pady=0, sticky="w")
            column += 1
        self.add_tab_btn.grid(row=0, column=98, padx=(6, 0), pady=0, sticky="e")

    def close_output_tab(self, tab_id: int) -> None:
        """Close one output tab without killing the whole GUI."""
        if tab_id not in self.output_tabs:
            return
        if len(self.output_tabs) <= 1:
            self.output_view.append_text("\n[Keep at least one output tab open]\n", "info")
            return
        tab = self.output_tabs[tab_id]
        if tab.get("ai_running"):
            terminal = tab.get("terminal") or self.output_view
            try:
                terminal.append_text("\n[Stop the running command before closing this tab]\n", "info")
            except Exception:
                log.debug("suppressed", exc_info=True)
            return

        was_active = tab_id == self.active_output_tab_id
        terminal = tab.get("terminal")
        try:
            if terminal and hasattr(terminal, "stop"):
                terminal.stop()
            if terminal:
                terminal.grid_remove()
                terminal.destroy()
        except Exception:
            log.debug("suppressed", exc_info=True)
        self.output_tabs.pop(tab_id, None)

        if was_active:
            next_id = sorted(self.output_tabs)[0]
            self.active_output_tab_id = None
            self._activate_output_tab(next_id)
        else:
            self._render_output_tabs()

    def _save_active_output_tab_state(self) -> None:
        if self.active_output_tab_id is None:
            return
        tab = self.output_tabs.get(self.active_output_tab_id)
        if not tab:
            return
        current_ai = str(tab.get("ai_name") or self.ai_selector.get()).lower()
        if not tab.get("ai_connected"):
            current_ai = self.ai_selector.get().lower()
        tab["ai_name"] = current_ai
        tab["project"] = os.getcwd()
        tab["persistent_client"] = self.persistent_client
        tab["current_client"] = self.current_client
        tab["ai_connected"] = self.ai_connected
        tab["ai_running"] = self.ai_running
        tab["ai_thread"] = self.ai_thread
        tab["ai_process"] = self.ai_process

    def _active_tab_state(self) -> dict | None:
        if self.active_output_tab_id is None:
            return None
        return self.output_tabs.get(self.active_output_tab_id)

    def _active_ai_name(self) -> str:
        tab = self._active_tab_state()
        if tab and tab.get("ai_name"):
            return str(tab["ai_name"]).lower()
        return self.ai_selector.get().lower()

    def _queue_prompt_for_active_tab(self, command: str) -> bool:
        """Park a prompt behind the current running AI call for this tab."""
        tab = self._active_tab_state()
        if not tab:
            return False
        pending = tab.setdefault("pending_prompts", [])
        pending.append(command)
        self._append_parked_prompt(command, label="Queued")
        try:
            self.output_view.append_text(
                f"\n[Queued] Prompt parked. It will run after the current response finishes. Queue: {len(pending)}\n",
                "info",
            )
        except Exception:
            log.debug("suppressed", exc_info=True)
        self._set_run_status(f"Running, {len(pending)} queued", "#facc15")
        return True

    def _append_parked_prompt(self, prompt: str, *, label: str) -> None:
        """Show a queued or steered prompt immediately in the active output."""
        try:
            if hasattr(self.output_view, "append_user_prompt"):
                self.output_view.append_user_prompt(f"[{label}] {prompt}")
            elif hasattr(self.output_view, "append_user_message"):
                self.output_view.append_user_message(f"[{label}] {prompt}")
            else:
                self.output_view.append_text(f"\n> [{label}] {prompt}\n", "user")
        except Exception:
            log.debug("suppressed", exc_info=True)

    def _steer_active_prompt(self, command: str) -> bool:
        """Cancel the active response and run this prompt next."""
        command = command.strip()
        if not command:
            self._show_local_response("Usage: /steer <message to send next>\n")
            return False

        tab = self._active_tab_state()
        if not tab or not tab.get("ai_running"):
            return self.on_send_command(command)

        pending = tab.setdefault("pending_prompts", [])
        pending.insert(0, command)
        self._append_parked_prompt(command, label="Steer")
        try:
            self.output_view.append_text(
                "\n[Steer] Stopping the current response and sending this next.\n",
                "info",
            )
        except Exception:
            log.debug("suppressed", exc_info=True)
        self.on_cancel_process()
        self.after(250, lambda tid=self.active_output_tab_id: self._drain_queued_prompt(tid))
        return True

    def _drain_queued_prompt(self, tab_id: int | None) -> None:
        """Run the next parked prompt for a tab once that tab is idle."""
        if tab_id is None:
            return
        tab = self.output_tabs.get(tab_id)
        if not tab or tab.get("ai_running"):
            return
        pending = tab.get("pending_prompts") or []
        if not pending:
            return
        if tab_id != self.active_output_tab_id:
            tab["queued_ready"] = True
            return

        next_prompt = pending.pop(0)
        tab["queued_ready"] = False
        try:
            self.output_view.append_text(
                f"\n[Queued] Running parked prompt. Remaining: {len(pending)}\n",
                "info",
            )
        except Exception:
            log.debug("suppressed", exc_info=True)
        self.on_send_command(next_prompt)

    def _append_run_status(self, output_view, text: str) -> None:
        """Show live progress without storing it as assistant memory."""
        try:
            if hasattr(output_view, "append_status_text"):
                output_view.append_status_text(text)
            else:
                output_view.append_text(text, "info")
        except Exception:
            log.debug("suppressed", exc_info=True)

    def _mark_tab_stream_event(self, tab_id: int | None) -> None:
        tab = self.output_tabs.get(tab_id)
        if tab is not None:
            tab["stream_events"] = int(tab.get("stream_events") or 0) + 1
            tab["last_stream_at"] = time.perf_counter()

    def _start_live_heartbeat(self, tab_id: int | None, output_view, ai_name: str) -> None:
        """Keep the output screen alive while a backend call is waiting."""
        tab = self.output_tabs.get(tab_id)
        if tab is not None:
            tab["stream_events"] = 0
            tab["run_started_at"] = time.perf_counter()
            tab["heartbeat_notice_shown"] = False

        display_name = ai_name.capitalize()
        self._append_run_status(output_view, f"\n[Working] Sent prompt to {display_name}. Waiting for CLI output...\n")

        def heartbeat() -> None:
            current = self.output_tabs.get(tab_id)
            if not current or not current.get("ai_running"):
                return
            elapsed = int(time.perf_counter() - float(current.get("run_started_at") or time.perf_counter()))
            events = int(current.get("stream_events") or 0)
            if events == 0 and elapsed >= 10 and not current.get("heartbeat_notice_shown"):
                current["heartbeat_notice_shown"] = True
                self._append_run_status(
                    output_view,
                    f"[Working] {display_name} is still running. Some CLIs return final text instead of live chunks.\n",
                )
            self.after(3000, heartbeat)

        self.after(3000, heartbeat)

    def _activate_output_tab(self, tab_id: int) -> None:
        """Switch the active output terminal and connector state."""
        if tab_id == self.active_output_tab_id:
            return
        self._save_active_output_tab_state()
        if self.active_output_tab_id in self.output_tabs:
            self.output_tabs[self.active_output_tab_id]["terminal"].grid_remove()

        tab = self.output_tabs[tab_id]
        self.active_output_tab_id = tab_id
        self.output_view = tab["terminal"]
        self.output_view.grid(row=0, column=0, sticky="nsew")

        project = tab.get("project") or os.getcwd()
        try:
            os.chdir(project)
        except OSError:
            project = os.getcwd()
            tab["project"] = project
        # Rebind shared memory to this tab's project (same project = same memory).
        self._bind_project_memory(project)

        ai_name = tab.get("ai_name") or self.config.get_default_ai()
        self.ai_selector.set(str(ai_name).capitalize())
        self.persistent_client = tab.get("persistent_client")
        self.current_client = tab.get("current_client")
        self.ai_connected = bool(tab.get("ai_connected"))
        self.ai_running = bool(tab.get("ai_running"))
        self.ai_thread = tab.get("ai_thread")
        self.ai_process = tab.get("ai_process")

        self.project_label.configure(text=f"Project: {project}")
        self.status_indicator.configure(text_color="green" if self.ai_connected else "red")
        self.connect_btn.configure(text="Disconnect" if self.ai_connected else "Connect")
        self.ai_selector.configure(state="disabled" if self.ai_connected else "readonly")
        if self.ai_running:
            self.thinking_overlay.show()
            self._set_run_status(f"Running {str(ai_name).capitalize()}...", "#facc15")
        else:
            self.thinking_overlay.hide()
            self._set_run_status("Idle", "gray60")
            if tab.get("pending_prompts"):
                self.after(100, lambda tid=tab_id: self._drain_queued_prompt(tid))
        self._refresh_runtime_labels()
        self.load_sidebar_data()
        self._render_output_tabs()

    def create_metric_cards(self, parent):
        """Create the 4 metric cards stacked vertically in the right panel."""

        # Total Commands card
        self.commands_card = MetricCard(
            parent,
            label="Commands",
            height=150,
            value_font_size=18,
        )
        self.commands_card.grid(row=1, column=0, padx=10, pady=4, sticky="new")

        # Tokens card (shows both used and saved with labels)
        self.tokens_card = TokenMetricCard(
            parent,
            label="Context Tokens",
            height=150,
            label_font_size=11,
            title_font_size=12,
            value_font_size=16,
            muted_font_size=9,
        )
        self.tokens_card.grid(row=2, column=0, padx=10, pady=4, sticky="new")

        # Active Agents card
        self.agents_card = MetricCard(
            parent,
            label="Agents",
            height=150,
        )
        self.agents_card.grid(row=3, column=0, padx=10, pady=4, sticky="new")

        # Success Rate card
        self.success_card = MetricCard(
            parent,
            label="Success",
            height=150,
        )
        self.success_card.grid(row=4, column=0, padx=10, pady=(4, 12), sticky="new")

    def update_metrics(self):
        """Update metric cards from database"""
        if not self.update_running:
            return

        # Run database query in thread to avoid blocking UI
        threading.Thread(target=self._fetch_metrics, daemon=True).start()

        # Schedule next update
        self.after(2000, self.update_metrics)

    def _fetch_metrics(self):
        """Fetch metrics from database (runs in background thread)"""
        try:
            with connect() as conn:
                # Total commands
                raw_total_commands = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
                raw_successful_commands = conn.execute(
                    "SELECT COUNT(*) FROM runs WHERE exit_code = 0"
                ).fetchone()[0]

                self._ensure_context_compression_table(conn)
                token_row = self._fetch_ai_token_totals(conn)
                raw_original_tokens = token_row[0] or 0
                raw_compressed_tokens = token_row[1] or 0
                raw_token_savings = token_row[2] or 0

                # Agent roster and live work. Registered agents comes from the
                # catalog; active work comes from agent_runs.
                raw_total_agents = len(DEFAULT_AGENT_SPECS)
                agent_row = conn.execute(
                    """
                    SELECT
                        SUM(CASE WHEN status = 'queued' THEN 1 ELSE 0 END) as queued,
                        SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running,
                        SUM(CASE WHEN status = 'waiting_for_tool' THEN 1 ELSE 0 END) as waiting
                    FROM agent_runs
                    WHERE status IN ('queued', 'running', 'waiting_for_tool')
                      AND run_id = (SELECT MAX(run_id) FROM agent_runs)
                    """
                ).fetchone()
                raw_queued_agents = agent_row["queued"] or 0
                raw_running_agents = agent_row["running"] or 0
                raw_waiting_agents = agent_row["waiting"] or 0
                raw_active_agents = raw_queued_agents + raw_running_agents + raw_waiting_agents
                raw_agent_tasks = conn.execute(
                    "SELECT COUNT(*) FROM agent_tasks WHERE status = 'completed'"
                ).fetchone()[0] or 0
                latest_agent_row = conn.execute(
                    """
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                        SUM(CASE WHEN status IN ('queued', 'running', 'waiting_for_tool') THEN 1 ELSE 0 END) as active
                    FROM agent_runs
                    WHERE run_id = (SELECT MAX(run_id) FROM agent_runs)
                    """
                ).fetchone()
                latest_agent_total = latest_agent_row["total"] or 0
                latest_agent_completed = latest_agent_row["completed"] or 0
                latest_agent_active = latest_agent_row["active"] or 0

                # Which agent *types* are currently active, for the live strip.
                active_type_rows = conn.execute(
                    """
                    SELECT DISTINCT a.type
                    FROM agent_runs ar
                    JOIN agents a ON a.id = ar.agent_id
                    WHERE ar.status IN ('queued', 'running', 'waiting_for_tool')
                      AND ar.run_id = (SELECT MAX(run_id) FROM agent_runs)
                    """
                ).fetchall()
                active_agent_types = {row["type"] for row in active_type_rows}

                # If no agents are active on the latest run, clear manual predictions.
                # This handles the case where completion handlers haven't fired yet.
                if not active_agent_types and latest_agent_active == 0:
                    self._manual_active_agent_types = set()

                # Dashboard "Total" must match the full local database, the same
                # source used by `sage context stats`. Resets affect only the
                # session column, not all-time proof numbers.
                total_commands = raw_total_commands
                successful_commands = raw_successful_commands
                original_tokens = raw_original_tokens
                compressed_tokens = raw_compressed_tokens
                token_savings = raw_token_savings
                total_agents = raw_total_agents
                active_agents = raw_active_agents
                agent_tasks = raw_agent_tasks
                queued_agents = raw_queued_agents
                running_agents = raw_running_agents
                waiting_agents = raw_waiting_agents

                if original_tokens > 0:
                    token_rate = token_savings / original_tokens * 100
                else:
                    token_rate = 0

                # Success rate
                if total_commands > 0:
                    success_rate = successful_commands / total_commands
                else:
                    success_rate = 0

            # Calculate session metrics from the GUI startup baseline.
            session_commands = max(0, total_commands - self.session_start_commands)
            session_successes = max(0, successful_commands - self.session_start_successes)

            # Session tokens: compressed (used) + saved since session start
            session_used = max(0, compressed_tokens - self.session_start_used)
            session_saved = max(0, token_savings - self.session_start_saved)

            session_agent_tasks = max(0, agent_tasks - getattr(self, "session_start_agent_tasks", 0))
            session_success_rate = (session_successes / session_commands) if session_commands else 0
            session_token_total = session_used + session_saved
            session_token_rate = (session_saved / session_token_total * 100) if session_token_total else 0

            # Update UI on main thread
            self.after(0, lambda: self._update_ui_metrics(
                total_commands, session_commands,
                compressed_tokens, token_savings, token_rate, session_used, session_saved,
                total_agents, active_agents, agent_tasks, session_agent_tasks,
                success_rate, session_success_rate, successful_commands, session_successes,
                session_token_rate, queued_agents, running_agents, waiting_agents,
                latest_agent_total, latest_agent_completed, latest_agent_active
            ))
            self.after(0, lambda types=active_agent_types: self._update_agent_strip(types))

        except Exception as e:
            print(f"DB Error: {e}")

    def _update_ui_metrics(
        self,
        total_commands,
        session_commands,
        compressed_tokens,
        token_savings,
        token_rate,
        session_used,
        session_saved,
        total_agents,
        active_agents,
        agent_tasks,
        session_agent_tasks,
        success_rate,
        session_success_rate,
        successful_commands,
        session_successes,
        session_token_rate,
        queued_agents=0,
        running_agents=0,
        waiting_agents=0,
        latest_agent_total=0,
        latest_agent_completed=0,
        latest_agent_active=0,
    ):
        """Update metric card UI elements"""
        self.commands_card.update_metric(
            total_value=f"{total_commands}",
            session_value=f"{session_commands}",
            total_hint="Runs",
            session_hint="Runs",
            detail=f"{successful_commands} successful total",
        )

        all_used_k = self._format_count(compressed_tokens)
        all_saved_k = self._format_count(token_savings)
        sess_used_k = self._format_count(session_used)
        sess_saved_k = self._format_count(session_saved)

        self.tokens_card.update_metric(
            total_value=f"{all_used_k} | {all_saved_k}",
            session_value=f"{sess_used_k} | {sess_saved_k}",
            total_hint=f"Used | Saved\n{token_rate:.1f}% est.",
            session_hint=f"Used | Saved\n{session_token_rate:.1f}% est.",
            detail="Real prompt context compression",
        )

        self.agents_card.update_metric(
            total_value=f"{total_agents}",
            session_value=f"{session_agent_tasks}",
            total_hint=f"{running_agents} running\n{queued_agents} queued",
            session_hint=f"{agent_tasks} all-time\n{waiting_agents} waiting",
            detail=f"Latest run: {latest_agent_completed}/{latest_agent_total} done, {latest_agent_active} active",
        )

        self.success_card.update_metric(
            total_value=f"{success_rate * 100:.1f}%",
            session_value=f"{session_success_rate * 100:.1f}%",
            total_hint=f"{successful_commands}/{total_commands}",
            session_hint=f"{session_successes}/{session_commands}",
            detail="Successful runs",
        )

    def _update_agent_strip(self, active_types: set) -> None:
        """Turn agent cards green when their type is active on the latest run."""
        strip = getattr(self, "agent_strip", None)
        if strip is not None:
            try:
                manual = getattr(self, "_manual_active_agent_types", set())
                strip.update_active(set(active_types) | set(manual))
            except Exception:
                log.debug("suppressed", exc_info=True)

    def _set_manual_active_agents(self, active_types: set[str]) -> None:
        self._manual_active_agent_types = set(active_types)
        self._update_agent_strip(set())

    def _format_count(self, value: int) -> str:
        """Format metric counts compactly."""
        value = int(value or 0)
        if value >= 1_000_000:
            return f"{value / 1_000_000:.1f}M"
        if value >= 1000:
            return f"{value // 1000}K"
        return str(value)

    def _init_session_baseline(self):
        """Initialize session baseline from reset-adjusted database values."""
        try:
            with connect() as conn:
                raw_commands = conn.execute(
                    "SELECT COUNT(*) FROM runs"
                ).fetchone()[0]
                raw_successes = conn.execute(
                    "SELECT COUNT(*) FROM runs WHERE exit_code = 0"
                ).fetchone()[0]
                raw_agents = conn.execute(
                    "SELECT COUNT(*) FROM agents"
                ).fetchone()[0]
                raw_agent_tasks = conn.execute(
                    "SELECT COUNT(*) FROM agent_tasks"
                ).fetchone()[0]

                self._ensure_context_compression_table(conn)
                token_row = self._fetch_ai_token_totals(conn)
                raw_compressed_tokens = token_row[1] or 0
                raw_token_savings = token_row[2] or 0
                self.session_start_commands = raw_commands
                self.session_start_successes = raw_successes
                self.session_start_agents = raw_agents
                self.session_start_agent_tasks = raw_agent_tasks
                self.session_start_used = raw_compressed_tokens
                self.session_start_saved = raw_token_savings

                print(
                    "# Session baseline:"
                    f"{self.session_start_commands} runs, "
                    f"{self.session_start_used} context tokens kept, {self.session_start_saved} saved"
                )
        except Exception as e:
            # DEBUG:Error initializing session baseline: {e}")
            pass

    def _ensure_context_compression_table(self, conn):
        """Create the real prompt context compression table if needed."""
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS context_compression (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                created_at TEXT NOT NULL,
                original_tokens INTEGER NOT NULL,
                compressed_tokens INTEGER NOT NULL,
                saved_tokens INTEGER NOT NULL
            )
            """
        )

    def _fetch_ai_token_totals(self, conn):
        """Return token totals for actual AI sessions, falling back to all rows."""
        ai_row = conn.execute(
            """
            SELECT
                SUM(cc.original_tokens),
                SUM(CASE WHEN cc.saved_tokens < 0 THEN cc.original_tokens ELSE cc.compressed_tokens END),
                SUM(CASE WHEN cc.saved_tokens < 0 THEN 0 ELSE cc.saved_tokens END)
            FROM context_compression cc
            JOIN runs r ON r.id = cc.run_id
            WHERE r.is_ai_session = 1
               OR r.caller = 'gui'
               OR lower(r.command_family) IN ('claude', 'codex', 'ollama')
               OR lower(r.command) GLOB 'claude *'
               OR lower(r.command) GLOB 'codex *'
            """
        ).fetchone()
        if ai_row and (ai_row[0] or ai_row[1] or ai_row[2]):
            return ai_row
        return conn.execute(
            """
            SELECT
                SUM(original_tokens),
                SUM(CASE WHEN saved_tokens < 0 THEN original_tokens ELSE compressed_tokens END),
                SUM(CASE WHEN saved_tokens < 0 THEN 0 ELSE saved_tokens END)
            FROM context_compression
            """
        ).fetchone()

    def on_ai_changed(self, ai_name: str):
        """Callback when AI selection changes"""
        self.output_view.append_text(f"Switched to {ai_name}\n", "info")
        if self.active_output_tab_id in self.output_tabs:
            tab = self.output_tabs[self.active_output_tab_id]
            tab["ai_name"] = ai_name.lower()
            tab["ai_connected"] = False
            tab["persistent_client"] = None
            tab["current_client"] = None
            self.ai_connected = False
            self.persistent_client = None
            self.current_client = None
            self.status_indicator.configure(text_color="red")
            self.connect_btn.configure(text="Connect")
            self._render_output_tabs()
        self._refresh_runtime_labels()

    def on_connect_ai(self):
        """Handle Connect button click - connects to local CLI."""
        ai_name = self._active_ai_name()

        if self.ai_connected:
            # Disconnect and clean up persistent session
            try:
                self.ai_connected = False
                history = "CLI session"

                # Stop persistent client session
                if self.persistent_client:
                    history = self.persistent_client.get_history_summary()
                    self.persistent_client.stop_session()
                    self.persistent_client = None

                self.current_client = None
                self.connect_btn.configure(text="Connect")
                self.status_indicator.configure(text_color="red")
                self.ai_selector.configure(state="readonly")  # Re-enable selector
                self._save_active_output_tab_state()
                self._render_output_tabs()

                self.output_view.append_text(
                    f"\n[Disconnected from {ai_name.capitalize()}]\n"
                    f"Session saved: {history}\n",
                    "info"
                )
            except Exception as e:
                # DEBUG:Disconnect error: {e}")
                pass
            return

        # Special handling for Ollama - show model picker
        if ai_name == "ollama":
            self._show_ollama_model_picker()
            return

        self._connect_selected_ai(show_status=True)

    def _connect_selected_ai(self, show_status: bool = True) -> bool:
        """Connect to AI with PERSISTENT SESSION - NO MORE SUBPROCESS BULLSHIT!"""
        ai_name = self._active_ai_name()
        if self.ai_connected and (self.current_client or (self.persistent_client and self.persistent_client.session_active)):
            return True

        try:
            if self.active_output_tab_id in self.output_tabs:
                self.output_tabs[self.active_output_tab_id]["ai_name"] = ai_name
                self._render_output_tabs()

            # Get system prompts
            system_prompts = self.config.get_system_prompts(ai_name)

            if ai_name == "claude":
                custom_command = self.config.get_ai_command(ai_name)
                if show_status:
                    self.output_view.append_text(f"\n[Connecting to {ai_name.capitalize()} CLI...]\n", "info")

                if not check_cli_available(ai_name, custom_command):
                    self.ai_connected = False
                    self.status_indicator.configure(text_color="red")
                    self._save_active_output_tab_state()
                    self._render_output_tabs()
                    self.output_view.append_text(
                        "ERROR: Claude CLI not available or not logged in.\n\n"
                        "Run: claude auth login\n",
                        "error",
                    )
                    return False

                self.persistent_client = None
                self.current_client = CLIClient(ai_name, system_prompts, custom_command)
                self.ai_connected = True
                self.connect_btn.configure(text="Disconnect")
                self.ai_selector.configure(state="disabled")
                self.status_indicator.configure(text_color="green")
                self._save_active_output_tab_state()
                self._render_output_tabs()
                if show_status:
                    self.output_view.append_text(
                        "[OK] Connected to Claude CLI\n",
                        "info",
                    )
                return True

            if show_status:
                session_kind = "CLI-backed" if ai_name == "codex" else "persistent"
                self.output_view.append_text(f"\n[Starting {session_kind} {ai_name.capitalize()} session...]\n", "info")

            # Create PERSISTENT client - maintains conversation history!
            self.persistent_client = PersistentAIClient(
                ai_name,
                system_prompts,
                permission_mode=self.config.get_permission_mode(),
                project_cwd=os.getcwd(),
            )

            # Start the persistent session
            if not self.persistent_client.start_session():
                self.ai_connected = False
                self.status_indicator.configure(text_color="red")
                self._save_active_output_tab_state()
                self._render_output_tabs()
                diagnostic = getattr(self.persistent_client, "last_error", "") or "No diagnostic was reported."
                self.output_view.append_text(
                    f"ERROR: Could not start {ai_name.capitalize()} persistent session!\n\n"
                    f"Diagnostic:\n{diagnostic}\n\n"
                    f"Requirements:\n"
                    f"- Claude: ANTHROPIC_API_KEY env var or logged in via 'claude auth login'\n"
                    f"- Codex: logged in via 'codex login'\n"
                    f"- Ollama: Running at http://localhost:11434\n\n"
                    f"Install SDKs:\n"
                    f"- pip install anthropic requests\n",
                    "error"
                )
                return False

            # Hydrate the fresh session from this project's SHARED memory so a
            # second AI on the same project reuses the first AI's context instead
            # of starting cold — that reuse is what saves tokens.
            try:
                self._bind_project_memory(os.getcwd())
                shared_turns = (self.project_memory_turns + self.conversation_turns)[-8:]
                if shared_turns:
                    self.persistent_client.load_history(shared_turns)
                    if show_status:
                        self.output_view.append_text(
                            f"[Memory] Reusing {len(shared_turns)} shared turn"
                            f"{'s' if len(shared_turns) != 1 else ''} from this project's other sessions.\n",
                            "info",
                        )
            except Exception:
                log.debug("suppressed", exc_info=True)

            # Keep legacy CLI client for fallback
            custom_command = self.config.get_ai_command(ai_name)
            self.current_client = CLIClient(ai_name, system_prompts, custom_command)

            self.ai_connected = True
            self.connect_btn.configure(text="Disconnect")
            self.ai_selector.configure(state="disabled")
            self.status_indicator.configure(text_color="green")
            self._save_active_output_tab_state()
            self._render_output_tabs()

            if show_status:
                history = self.persistent_client.get_history_summary()
                memory_line = (
                    "Codex CLI session resume enabled across turns"
                    if ai_name == "codex"
                    else "Context automatically managed by SDK"
                )
                heading = "Codex CLI session" if ai_name == "codex" else f"PERSISTENT {ai_name.capitalize()} session"
                self.output_view.append_text(
                    f"[OK] {heading} started!\n"
                    f"Conversation history maintained across questions\n"
                    f"{memory_line}\n"
                    f"{history}\n",
                    "info"
                )
            return True

        except Exception as err:
            self.ai_connected = False
            self.status_indicator.configure(text_color="red")
            self.ai_selector.configure(state="readonly")
            self._save_active_output_tab_state()
            self._render_output_tabs()
            self.output_view.append_text(f"ERROR: Connection failed: {str(err)}\n", "error")
            return False

    def _claude_auth_warning(self) -> str:
        """Return a warning when the claude CLI is installed but not logged in."""
        if os.environ.get("ANTHROPIC_API_KEY"):
            return ""
        try:
            result = subprocess.run(
                [shutil.which("claude") or "claude", "auth", "status"],
                env=os.environ.copy(),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
            if '"loggedin": true' in result.stdout.lower():
                return ""
            return (
                "\n[WARNING] Claude CLI is installed but NOT logged in - prompts will fail.\n"
                "Type /login to open a Claude login window, or set ANTHROPIC_API_KEY "
                "and optional ANTHROPIC_BASE_URL before starting SAGE.\n"
            )
        except Exception:
            # Cannot determine auth state; do not block the user.
            return ""

    def _open_claude_login(self) -> bool:
        """Open a real terminal running the Claude login flow."""
        try:
            subprocess.Popen(
                [
                    "powershell",
                    "-NoLogo",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-NoExit",
                    "-Command",
                    "claude /login",
                ],
                creationflags=subprocess.CREATE_NEW_CONSOLE if hasattr(subprocess, "CREATE_NEW_CONSOLE") else 0,
            )
            self._show_local_response(
                "Opened a Claude login terminal.\n"
                "Finish the login in that window (it will open your browser), "
                "then come back here and send your prompt again.\n"
            )
        except Exception as exc:
            self._show_local_response(f"Could not open the login terminal: {exc}\n")
        return True

    def _show_ollama_model_picker(self):
        """Show Ollama model selection dialog."""
        import subprocess
        try:
            # Get list of Ollama models
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                # Parse model list
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                models = []
                for line in lines:
                    if line.strip():
                        model_name = line.split()[0]
                        models.append(model_name)

                if not models:
                    self.output_view.append_text("ERROR: No Ollama models found!\n\nRun: ollama pull qwen2.5-coder:7b\n", "error")
                    return

                # Show selection dialog
                dialog = ctk.CTkToplevel(self)
                dialog.title("Select Ollama Model")
                dialog.geometry("400x300")
                dialog.transient(self)
                dialog.grab_set()

                ctk.CTkLabel(
                    dialog,
                    text="Choose Ollama Model:",
                    font=ctk.CTkFont(size=14, weight="bold")
                ).pack(pady=10)

                selected_model = ctk.StringVar(value=models[0])

                for model in models:
                    ctk.CTkRadioButton(
                        dialog,
                        text=model,
                        variable=selected_model,
                        value=model
                    ).pack(pady=5, padx=20, anchor="w")

                def on_select():
                    model = selected_model.get()
                    dialog.destroy()
                    self._connect_ollama(model)

                ctk.CTkButton(
                    dialog,
                    text="Connect",
                    command=on_select
                ).pack(pady=20)

            else:
                self.output_view.append_text("ERROR: ollama command failed!\n\nInstall from: https://ollama.ai\n", "error")

        except FileNotFoundError:
            self.output_view.append_text("ERROR: ollama not found!\n\nInstall from: https://ollama.ai\n", "error")
        except Exception as e:
            self.output_view.append_text(f"ERROR: {str(e)}\n", "error")

    def _connect_ollama(self, model: str):
        """Connect to Ollama with selected model."""
        try:
            # Override command with selected model (always through sage for tracking)
            custom_command = f"sage run -- ollama run {model}"
            system_prompts = self.config.get_system_prompts("ollama")

            # DEBUG:Connecting to Ollama model: {model}")
            # DEBUG:Command: {custom_command}")

            self.current_client = CLIClient("ollama", system_prompts, custom_command)
            self.ai_connected = True
            self.connect_btn.configure(text="Disconnect")
            self.status_indicator.configure(text_color="green")
            self.ai_selector.configure(state="disabled")  # Lock selector while connected
            self._save_active_output_tab_state()
            self._render_output_tabs()
            self.output_view.append_text(f"[OK] Connected to Ollama ({model})\n", "info")

        except Exception as err:
            self.ai_connected = False
            self.status_indicator.configure(text_color="red")
            self.ai_selector.configure(state="readonly")
            self._save_active_output_tab_state()
            self._render_output_tabs()
            self.output_view.append_text(f"ERROR: Connection failed: {str(err)}\n", "error")

    def on_send_command(self, command: str):
        """Handle send button click - USES PERSISTENT SESSION NOW!"""
        if not command.strip():
            return False

        command = command.strip()
        if self._handle_slash_command(command):
            return True

        tab = self._active_tab_state()
        if tab and tab.get("ai_running"):
            return self._queue_prompt_for_active_tab(command)

        # Auto-connect on first prompt.
        if not self.ai_connected or (not self.persistent_client and not self.current_client):
            if not self._connect_selected_ai(show_status=False):
                return False

        # Get selected AI
        ai_name = self._active_ai_name()
        self._remember_project(os.getcwd())
        self._refresh_runtime_labels()
        if not self._confirm_company_mode_send(ai_name, command):
            self.output_view.append_text("\n[Cancelled by company mode preview]\n", "info")
            return False
        use_persistent_memory = (
            ai_name != "claude"
            and self.persistent_client is not None
            and self.persistent_client.session_active
        )
        contextual_command = command if use_persistent_memory else self._build_contextual_prompt(command)
        if use_persistent_memory:
            self.pending_context_compression = None

        # Spawn agents for complex requests. The strip only turns green from
        # live agent_runs rows, not from broad planning guesses.
        self._set_manual_active_agents(set())
        self._spawn_agents_if_needed(command)

        # ── API-Travel: auto-select cheapest capable agent ────────────────────
        if getattr(self, "_api_travel_enabled", True):
            try:
                avail  = api_travel.detect_available()
                routed, complexity, label = api_travel.route(command, self.conversation_turns, avail)
                travel_c = self._get_travel_client(routed)
                if travel_c is not None:
                    # Tag the client so begin_ai_stream can show the badge
                    travel_c._api_travel_label = f"{label}  ·  {complexity}"
                    # Inject shared session history into this agent
                    try:
                        msgs = self.session_manager.get_messages(
                            os.getcwd(), str(self.current_session_id or "")
                        )
                        if msgs:
                            travel_c.load_history(msgs[-8:])
                    except Exception:
                        pass
                    return self._run_persistent_client(
                        command, routed, visible_prompt=command, _travel_client=travel_c
                    )
            except Exception:
                pass  # Fall through to normal dispatch on any router error
        # ── end API-Travel ─────────────────────────────────────────────────────

        if ai_name == "claude":
            return self._run_claude_cli_stream(contextual_command, visible_prompt=command)

        # Persistent clients already carry conversation history; send raw text to avoid token waste.
        return self._run_persistent_client(contextual_command, ai_name, visible_prompt=command)

    def _run_claude_cli_stream(self, prompt: str, visible_prompt: str | None = None) -> bool:
        """Run Claude through SAGE while rendering structured thinking/tool events."""
        visible_prompt = visible_prompt or prompt
        tab = self._active_tab_state()
        if tab and tab.get("ai_running"):
            return False
        if not self.current_client:
            self.output_view.append_text("\n[ERROR] Claude CLI client is not connected.\n", "error")
            return False

        self.ai_running = True
        if tab:
            tab["ai_running"] = True
        self.thinking_overlay.show()
        self._set_run_status("Running Claude...", "#facc15")
        command = self._external_terminal_command("claude", human_readable=False)
        self.current_client.command = command
        output_view = self.output_view
        client = self.current_client
        tab_id = self.active_output_tab_id

        if hasattr(output_view, "_ai_stream_format"):
            output_view._ai_stream_format = None
        if hasattr(output_view, "_json_line_buffer"):
            output_view._json_line_buffer = ""
        if hasattr(output_view, "_capture_active"):
            output_view._capture_active = False

        if hasattr(output_view, "set_terminal_mode"):
            output_view.set_terminal_mode(False)
        if hasattr(output_view, "append_user_prompt"):
            output_view.append_user_prompt(visible_prompt)
        elif hasattr(output_view, "append_user_message"):
            output_view.append_user_message(visible_prompt)
        self._start_live_heartbeat(tab_id, output_view, "claude")

        self.ai_thread = threading.Thread(
            target=self._run_cli_stream,
            args=(prompt, "claude", visible_prompt, tab_id, client, output_view),
            daemon=True,
        )
        self._save_active_output_tab_state()
        if tab:
            tab["ai_thread"] = self.ai_thread
        self.ai_thread.start()
        return True

    def _get_travel_client(self, agent_name: str) -> PersistentAIClient | None:
        """Get or lazily create a pooled persistent client for API-Travel."""
        if not hasattr(self, "_api_travel_clients"):
            self._api_travel_clients: dict[str, PersistentAIClient] = {}
        client = self._api_travel_clients.get(agent_name)
        if client is None or not getattr(client, "session_active", False):
            system_prompts = self.config.get_system_prompts(agent_name)
            client = PersistentAIClient(
                agent_name,
                system_prompts=system_prompts,
                permission_mode=self.config.get_permission_mode(),
                project_cwd=os.getcwd(),
            )
            if not client.start_session():
                return None
            self._api_travel_clients[agent_name] = client
        return client

    def _run_persistent_client(self, prompt: str, ai_name: str, visible_prompt: str | None = None, _travel_client: PersistentAIClient | None = None) -> bool:
        """Run command through PERSISTENT AI client - NO SUBPROCESS, REAL MEMORY!"""
        visible_prompt = visible_prompt or prompt
        tab = self._active_tab_state()
        if tab and tab.get("ai_running"):
            return False

        self.ai_running = True
        if tab:
            tab["ai_running"] = True
        self.thinking_overlay.show()
        self._set_run_status(f"Running {ai_name.capitalize()}...", "#facc15")
        output_view = self.output_view
        client = _travel_client if _travel_client is not None else self.persistent_client
        tab_id = self.active_output_tab_id
        if client is None:
            if tab:
                tab["ai_running"] = False
            self.ai_running = False
            self.thinking_overlay.hide()
            self._set_run_status("Idle", "gray60")
            return self._run_real_cli_in_pty(prompt, ai_name, visible_prompt)

        # Show user message
        if hasattr(output_view, "append_user_prompt"):
            output_view.append_user_prompt(visible_prompt)
        if hasattr(output_view, "begin_ai_stream"):
            route_lbl = getattr(client, "_api_travel_label", None)
            output_view.begin_ai_stream(ai_name, route_label=route_lbl)
        self._start_live_heartbeat(tab_id, output_view, ai_name)

        # One ordered, coalesced UI queue for ALL event kinds (text, thinking,
        # coding, tool, error). Immediate per-event self.after(0) calls flood the
        # Tk loop and cause visible lag when two tabs stream at once; a single
        # pending flush that preserves order keeps it smooth.
        ui_ops: list = []
        ui_buffer_lock = threading.Lock()
        ui_flush_state = {"scheduled": False}

        def flush_ui_buffer() -> None:
            with ui_buffer_lock:
                ops = list(ui_ops)
                ui_ops.clear()
                ui_flush_state["scheduled"] = False
            # Merge consecutive plain-text appends into one insert.
            pending_text: list[str] = []

            def flush_text() -> None:
                if pending_text:
                    output_view.append_text("".join(pending_text))
                    pending_text.clear()

            for op in ops:
                if op[0] == "text":
                    pending_text.append(op[1])
                else:
                    flush_text()
                    op[1]()
            flush_text()

        def _schedule_flush() -> None:
            if ui_flush_state["scheduled"]:
                return
            ui_flush_state["scheduled"] = True
            self.after(33, flush_ui_buffer)

        def queue_ui_text(text: str, tag: str | None = None) -> None:
            if not text:
                return
            with ui_buffer_lock:
                if tag:
                    ui_ops.append(("op", lambda t=text, g=tag: output_view.append_text(t, g)))
                else:
                    ui_ops.append(("text", text))
                _schedule_flush()

        def queue_ui_op(fn) -> None:
            with ui_buffer_lock:
                ui_ops.append(("op", fn))
                _schedule_flush()

        def stream_worker():
            fallback_used = False
            try:
                # Try streaming from persistent client
                had_output = False
                assistant_chunks: list[str] = []
                # Tool Activity: one growing section per response (mutable holder for closure)
                tool_sid: list[str | None] = [None]

                def _queue_tool_event(c: str) -> None:
                    def _run(c=c, view=output_view, holder=tool_sid):
                        if holder[0] is None:
                            holder[0] = view.append_expandable_section(
                                "Tool Activity", c, "running", collapsed=False
                            )
                        else:
                            view.append_to_expandable_section(holder[0], c)
                    queue_ui_op(_run)

                for event_type, content in client.send_message(prompt):
                    current_tab = self.output_tabs.get(tab_id)
                    if current_tab and not current_tab.get("ai_running"):
                        break

                    had_output = True
                    self._mark_tab_stream_event(tab_id)

                    if event_type == "thinking":
                        assistant_chunks.append(content)
                        queue_ui_op(lambda c=content, view=output_view: view.append_expandable_section("Thinking", c, "thinking_text", collapsed=False))
                    elif event_type == "coding":
                        assistant_chunks.append(content)
                        queue_ui_op(lambda c=content, view=output_view: view.append_expandable_section("Coding", c, "code", collapsed=False))
                    elif event_type == "tool":
                        assistant_chunks.append(content)
                        _queue_tool_event(content)
                    elif event_type == "text":
                        assistant_chunks.append(content)
                        queue_ui_text(content)
                    elif event_type == "error":
                        # Check if it's the "restricted to Claude Code client" error
                        if "restricted to the official Claude Code client" in content or "403" in content:
                            queue_ui_op(lambda view=output_view: view.append_text(
                                "\n[WARN] SDK mode requires Anthropic API key. Falling back to CLI mode...\n",
                                "info"
                            ))
                            fallback_used = True
                            break
                        queue_ui_text(f"\n{content}\n", "error")
                    elif event_type == "complete":
                        assistant_text = "".join(assistant_chunks).strip()
                        run_id = self._save_gui_ai_run(ai_name, prompt, visible_prompt, assistant_text)
                        if run_id:
                            self._record_context_compression(run_id, output_view)

                        # EXECUTE AGENTS NOW - create database run and execute agents
                        threading.Thread(
                            target=self._execute_agents_for_response,
                            args=(prompt, visible_prompt),
                            daemon=True,
                        ).start()

                # If SDK failed with 403, fall back to subprocess
                if fallback_used:
                    self.after(0, lambda: self._run_real_cli_in_pty(prompt, ai_name, visible_prompt))
                    return

            except Exception as e:
                error_msg = f"\n[ERROR] Persistent client failed: {e}\n[INFO] Falling back to CLI mode...\n"
                self.after(0, lambda view=output_view: view.append_text(error_msg, "error"))
                # Fall back to subprocess mode
                self.after(0, lambda: self._run_real_cli_in_pty(prompt, ai_name, visible_prompt))
            finally:
                self.after(0, flush_ui_buffer)
                if not fallback_used:
                    current_tab = self.output_tabs.get(tab_id)
                    if current_tab:
                        current_tab["ai_running"] = False
                    if tab_id == self.active_output_tab_id:
                        self.ai_running = False
                        self.after(0, self.thinking_overlay.hide)
                        self.after(0, lambda: self._set_run_status("Idle", "gray60"))
                        self.after(0, lambda: self._set_manual_active_agents(set()))
                    self.after(1500, self.update_metrics)
                    # REMOVED: load_sidebar_data() - causes sidebar flicker on every command
                    self.after(100, lambda tid=tab_id: self._drain_queued_prompt(tid))

        self.ai_thread = threading.Thread(target=stream_worker, daemon=True)
        self._save_active_output_tab_state()
        if tab:
            tab["ai_thread"] = self.ai_thread
        self.ai_thread.start()
        return True

    def _track_persistent_run(self, history_summary: str | None = None):
        """Deprecated no-op kept for older callbacks.

        The GUI used to log `sage run -- echo Persistent session...` here. That
        polluted compression metrics with tiny fake rows instead of recording the
        actual AI output. Persistent streams now call `_save_gui_ai_run`.
        """
        return None

    def _save_gui_ai_run(self, ai_name: str, prompt: str, visible_prompt: str, assistant_text: str) -> int | None:
        """Persist a real GUI SDK AI interaction and its output compression."""
        try:
            summary = f"{ai_name.capitalize()} GUI response to: {visible_prompt[:160]}"
            strictness = str(load_policy().get("redaction_strictness") or "standard")
            stdout_redacted = redact_text(assistant_text or "", strictness=strictness)
            summary_redacted = redact_text(summary, strictness=strictness)
            command = f"{ai_name} gui-session"
            run_id = save_run(
                project=os.getcwd(),
                command=command,
                exit_code=0,
                duration_ms=0,
                stdout=stdout_redacted.text,
                stderr="",
                summary=summary_redacted.text,
                stdout_redactions=stdout_redacted.count,
                stderr_redactions=0,
                summary_redactions=summary_redacted.count,
                command_sha256=command_hash(command),
                policy_mode=str(load_policy().get("mode", "personal")),
                policy_decision="allowed",
                policy_reason="gui persistent AI session",
                retention_expires_at=retention_expiry(),
                raw_retained=1,
                command_kind="ai",
                command_family=ai_name,
                caller="gui",
                workspace_hash=workspace_hash(os.getcwd()),
                session_id=str(self.current_session_id or ""),
                is_ai_session=1,
            )
            result = ContextManager().process_command_output(
                stdout=stdout_redacted.text,
                stderr="",
                exit_code=0,
                run_id=run_id,
            )
            self._insert_context_compression(run_id, result)
            self._save_prompt_for_run(run_id, visible_prompt)
            return run_id
        except Exception:
            return None

    def _insert_context_compression(self, run_id: int, result: dict) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        saved_tokens = int(result.get("token_savings", 0))
        original_tokens = int(result.get("original_tokens", saved_tokens))
        compressed_tokens = int(result.get("compressed_tokens", max(0, original_tokens - saved_tokens)))
        with connect() as conn:
            self._ensure_context_compression_table(conn)
            conn.execute(
                """
                INSERT INTO context_compression
                (run_id, created_at, original_tokens, compressed_tokens, saved_tokens)
                VALUES (?, ?, ?, ?, ?)
                """,
                (run_id, now, original_tokens, compressed_tokens, saved_tokens),
            )

    def _run_real_cli_in_pty(self, prompt: str, ai_name: str, visible_prompt: str) -> bool:
        """Run CLI through sage wrapper in PTY - TRACKS TOKENS + SHOWS THINKING!"""
        if not hasattr(self.output_view, "send_command"):
            self.output_view.append_text("\n[ERROR] Embedded PowerShell terminal is unavailable.\n", "error")
            return False

        try:
            run_dir = data_dir() / "terminal-runs"
            run_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            prompt_path = run_dir / f"sage-prompt-{stamp}.txt"
            if ai_name not in ("claude", "codex"):
                # These CLIs have no system-prompt-file flag; prepend the content.
                system_content = []
                for prompt_file in self.config.get_system_prompts(ai_name):
                    p = Path(prompt_file)
                    if p.exists():
                        try:
                            system_content.append(p.read_text(encoding="utf-8"))
                        except OSError:
                            pass
                if system_content:
                    prompt = "\n\n".join(system_content) + "\n\n---\n\nUser: " + prompt
            prompt_path.write_text(prompt, encoding="utf-8")

            command = self._external_terminal_command(ai_name, human_readable=False)
            quoted_prompt = self._ps_quote(str(prompt_path))
            terminal_command = f"$prompt = Get-Content -Raw -LiteralPath {quoted_prompt}; {command} $prompt"

            if hasattr(self.output_view, "append_user_prompt"):
                self.output_view.append_user_prompt(visible_prompt)
            if hasattr(self.output_view, "begin_ai_stream"):
                self.output_view.begin_ai_stream(ai_name)
            self._append_run_status(
                self.output_view,
                f"\n[Working] Sent prompt to {ai_name.capitalize()} terminal. Streaming will appear here as soon as the CLI writes output.\n",
            )
            self.output_view.send_command(terminal_command, wrap_with_sage=False)
            self._remember_conversation_turn("user", visible_prompt)
            self.after(1500, self.update_metrics)
            # REMOVED: load_sidebar_data() - causes sidebar flicker on every command
            return True
        except Exception as exc:
            self.output_view.append_text(f"\n[ERROR] Could not send command to terminal: {exc}\n", "error")
            return False

        if self.ai_running:
            return False

        from sage.gui.widgets.pty_terminal import PTYTerminal, HAS_WINPTY

        if not HAS_WINPTY:
            self.output_view.append_text("\n[ERROR] pywinpty not installed. Run: pip install pywinpty\n", "error")
            return False

        # Use output view directly - DON'T hide it!
        self.output_view.clear()

        # Build command through sage run wrapper (REQUIRED for token tracking!)
        if ai_name == "claude":
            cmd = [
                "sage", "run", "--",
                "claude",
                "--print",
                "--output-format", "stream-json",
                "--include-partial-messages"
            ]
        elif ai_name == "codex":
            cmd = [
                "sage", "run", "--",
                "codex", "exec", "--json"
            ]
        elif ai_name == "ollama":
            cmd = [
                "sage", "run", "--",
                "ollama", "run", "qwen2.5-coder:7b"
            ]
        else:
            cmd = ["sage", "run", "--", ai_name]

        # Run command through subprocess with streaming output
        self.ai_running = True
        self.thinking_overlay.show()

        def run_command():
            import subprocess
            import json
            import uuid

            seen_thinking = False
            seen_reasoning = False
            seen_coding = False
            seen_answer = False

            try:
                # Generate session ID for this AI interaction
                session_id = str(uuid.uuid4())

                # Set environment for subprocess
                env = os.environ.copy()
                env["SAGE_SESSION_ID"] = session_id

                # Run sage command with streaming
                process = subprocess.Popen(
                    cmd + [prompt],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    env=env,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )

                for line in process.stdout:
                    if not line.strip() or line.startswith('[DEBUG]'):
                        continue

                    # Try parse JSON
                    if line.strip().startswith('{'):
                        try:
                            event = json.loads(line)
                            event_type = event.get('type')

                            # Claude format
                            if event_type == 'stream_event':
                                stream_event = event.get('event', {})
                                stream_type = stream_event.get('type')

                                if stream_type == 'content_block_start':
                                    block = stream_event.get('content_block', {})
                                    block_type = block.get('type')

                                    if block_type == 'thinking' and not seen_thinking:
                                        seen_thinking = True
                                        self.output_view.append_text('\n━━━ Thinking ━━━\n', 'thinking_header')
                                    elif block_type == 'text' and not seen_answer:
                                        seen_answer = True
                                        self.output_view.append_text('\n━━━ Answer ━━━\n', 'answer_header')
                                    elif block_type == 'tool_use':
                                        # Tool call - show it!
                                        tool_name = block.get('name', 'UnknownTool')
                                        tool_input = block.get('input', {})
                                        self._format_tool_call(tool_name, tool_input)

                                elif stream_type == 'content_block_delta':
                                    delta = stream_event.get('delta', {})
                                    delta_type = delta.get('type')

                                    if delta_type == 'thinking_delta':
                                        text = delta.get('thinking', '')
                                        if text:
                                            self.output_view.append_text(text, 'thinking_text')
                                    elif delta_type == 'text_delta':
                                        text = delta.get('text', '')
                                        if text:
                                            self.output_view.append_text(text)
                                    elif delta_type == 'input_json_delta':
                                        # Tool input being streamed (we already showed the call, ignore deltas)
                                        pass

                                elif stream_type == 'content_block_stop':
                                    block_data = stream_event.get('content_block', {})
                                    if block_data.get('type') == 'tool_use':
                                        # Tool finished, show result marker
                                        self.output_view.append_text('  L  ', 'thinking_text')

                                elif stream_type == 'message_delta':
                                    # Message-level events (tool results come here)
                                    message = stream_event.get('message', {})
                                    for content_item in message.get('content', []):
                                        if isinstance(content_item, dict):
                                            if content_item.get('type') == 'tool_result':
                                                # Show tool result
                                                result_content = content_item.get('content', '')
                                                self._format_tool_result(result_content)

                            # Codex format
                            elif event_type == 'reasoning':
                                if not seen_reasoning:
                                    seen_reasoning = True
                                    self.output_view.append_text('\n━━━ Reasoning ━━━\n', 'reasoning_header')
                                text = event.get('text', '')
                                if text:
                                    self.output_view.append_text(text, 'thinking_text')

                            elif event_type == 'coding':
                                if not seen_coding:
                                    seen_coding = True
                                    self.output_view.append_text('\n━━━ Coding ━━━\n', 'coding_header')
                                text = event.get('text', '')
                                if text:
                                    self.output_view.append_text(text, 'thinking_text')

                            elif event_type in ('output', 'message'):
                                if not seen_answer:
                                    seen_answer = True
                                    self.output_view.append_text('\n━━━ Answer ━━━\n', 'answer_header')
                                text = event.get('text', '') or event.get('content', '')
                                if text:
                                    self.output_view.append_text(text)

                        except json.JSONDecodeError:
                            self.output_view.append_text(line)
                    else:
                        # Non-JSON lines - includes SAGE footer metrics
                        self.output_view.append_text(line)

                process.wait()

                # Show SAGE metrics footer after AI completes
                self.output_view.append_text('\n━━━ SAGE Metrics ━━━\n', 'thinking_header')
                self.output_view.append_text('Loading metrics...\n')

                # Get latest run metrics from database
                try:
                    from sage.store import connect
                    with connect() as conn:
                        latest = conn.execute(
                            """
                            SELECT r.id, r.exit_code,
                                   cc.saved_tokens, cc.compressed_tokens, cc.original_tokens,
                                   GROUP_CONCAT(DISTINCT ar.agent_type) as agents
                            FROM runs r
                            LEFT JOIN context_compression cc ON cc.run_id = r.id
                            LEFT JOIN agent_runs ar ON ar.run_id = r.id
                            WHERE r.id = (SELECT MAX(id) FROM runs)
                            GROUP BY r.id
                            """
                        ).fetchone()

                        if latest:
                            run_id = latest['id']
                            saved = latest['saved_tokens'] or 0
                            compressed = latest['compressed_tokens'] or 0
                            original = latest['original_tokens'] or 0
                            ratio = f"{(saved / original * 100):.1f}%" if original else "0%"
                            agents = latest['agents'] or 'none'

                            metrics_text = (
                                f"Run #{run_id} | Exit: {latest['exit_code']}\n"
                                f"Tokens: {original:,} → {compressed:,} (saved {saved:,} = {ratio})\n"
                                f"Agents: {agents}\n"
                            )
                            self.output_view.append_text(metrics_text)
                except Exception as e:
                    self.output_view.append_text(f"Failed to load metrics: {e}\n", 'error')

            except Exception as e:
                self.output_view.append_text(f"\n[ERROR] {e}\n", 'error')
            finally:
                self.ai_running = False
                # CRITICAL: Hide thinking overlay on MAIN thread, not background thread!
                self.after(0, lambda: self.thinking_overlay.hide())
                # Clear agent status back to idle
                self.after(0, lambda: self._set_manual_active_agents(set()))
                # Update metrics card WITHOUT reloading entire sidebar
                self.after(0, self.update_metrics)

        import threading
        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()
        return True

    def _run_native_cli(self, prompt: str, ai_name: str, visible_prompt: str) -> bool:
        """Run ACTUAL CLI in embedded PTY terminal - REAL terminal in GUI!"""
        if self.ai_running:
            return False

        self.ai_running = True
        self.thinking_overlay.show()

        # Use PTY terminal widget to run REAL CLI
        from sage.gui.widgets.pty_terminal import HAS_WINPTY

        if not HAS_WINPTY:
            # Fallback to text output
            self.output_view.set_terminal_mode(True)
            self.ai_thread = threading.Thread(
                target=self._run_native_cli_worker,
                args=(prompt, ai_name, visible_prompt),
                daemon=True
            )
            self.ai_thread.start()
            return True

        # Replace output_view with PTY terminal
        self._switch_to_pty_mode(ai_name, prompt, visible_prompt)
        return True

    def _run_native_cli_worker(self, prompt: str, ai_name: str, visible_prompt: str):
        """Native CLI worker thread"""
        try:
            from sage.gui.native_cli_client import NativeCLIClient

            # Get system prompts
            system_prompts = self.config.get_system_prompts(ai_name)

            # Create native CLI client
            client = NativeCLIClient(ai_name, system_prompts)

            # Stream response
            for event_type, content in client.stream_response(prompt):
                if not self.ai_running:
                    client.stop()
                    break

                if event_type in ("status", "text", "error", "complete"):
                    self.after(0, lambda c=content: self.output_view.append_terminal_text(c))

            # Save conversation
            if self.ai_running:
                self._remember_conversation_turn("user", visible_prompt)
                self._remember_conversation_turn(ai_name, "[Response via native CLI]")

        except Exception as e:
            error_msg = f"\n[ERROR] Native CLI failed: {e}\n"
            self.after(0, lambda: self.output_view.append_terminal_text(error_msg))
        finally:
            self.ai_running = False
            self.after(0, lambda: self.thinking_overlay.hide())
            self.after(0, lambda: self._set_manual_active_agents(set()))

    def _switch_to_pty_mode(self, ai_name: str, prompt: str, visible_prompt: str):
        """Switch output view to PTY terminal and run REAL CLI"""
        from sage.gui.widgets.pty_terminal import PTYTerminal

        # Create PTY terminal
        if not hasattr(self, 'pty_terminal'):
            self.pty_terminal = PTYTerminal(self.output_view)
            self.pty_terminal.pack(fill="both", expand=True)

        # Hide text widget, show PTY
        self.output_view.text_widget.pack_forget()
        self.pty_terminal.pack(fill="both", expand=True)

        # Build command (always through sage run for token tracking).
        # Claude loads CLAUDE-FABLE-5.md + SAGE-INTEGRATION.md globally via
        # ~/.claude/CLAUDE.md, so we don't append them here.
        if ai_name == "claude":
            cmd = ["sage", "run", "--", "claude", "--print"]
        elif ai_name == "codex":
            cmd = ["sage", "run", "--", "codex", "exec", "--skip-git-repo-check"]
        else:
            cmd = ["sage", "run", "--", ai_name]

        # Start PTY session with REAL CLI
        success = self.pty_terminal.start_pty_session(cmd)

        if success:
            # Write prompt to PTY (like typing in terminal)
            self.pty_terminal.write_to_pty(prompt + "\n")

            # Monitor for completion
            def check_completion():
                if not self.pty_terminal.is_pty_active():
                    self.ai_running = False
                    self.thinking_overlay.hide()
                    self._set_manual_active_agents(set())
                elif self.ai_running:
                    self.after(500, check_completion)

            self.after(500, check_completion)
        else:
            # PTY failed, fall back
            self.output_view.text_widget.pack(fill="both", expand=True)
            self.pty_terminal.pack_forget()
            self.ai_running = False
            self.thinking_overlay.hide()

    def _run_direct_integration(self, prompt: str, ai_name: str, visible_prompt: str) -> bool:
        """Run AI directly IN the GUI process - NO SUBPROCESS!"""
        if self.ai_running:
            return False

        self.output_view.set_terminal_mode(True)
        self.ai_running = True
        self.thinking_overlay.show()

        # Run directly in thread (no subprocess!)
        self.ai_thread = threading.Thread(
            target=self._run_direct_worker,
            args=(prompt, ai_name, visible_prompt),
            daemon=True
        )
        self.ai_thread.start()
        return True

    def _run_direct_worker(self, prompt: str, ai_name: str, visible_prompt: str):
        """Direct integration worker - runs AI in same process"""
        try:
            from sage.gui.direct_ai_client import create_direct_client

            # Get system prompts
            system_prompts = self.config.get_system_prompts(ai_name)

            # Create direct client (no subprocess!)
            client = create_direct_client(ai_name, system_prompts)

            # Stream response directly
            for event_type, content in client.stream_response(prompt):
                if not self.ai_running:
                    break

                if event_type == "status":
                    self.after(0, lambda c=content: self.output_view.append_terminal_text(c + "\n"))
                elif event_type == "thinking":
                    self.after(0, lambda c=content: self.output_view.append_terminal_text(c))
                elif event_type == "text":
                    self.after(0, lambda c=content: self.output_view.append_terminal_text(c))
                elif event_type == "error":
                    self.after(0, lambda c=content: self.output_view.append_terminal_text(c))
                elif event_type == "complete":
                    self.after(0, lambda: self.output_view.append_terminal_text("\n\n[Complete]\n"))

            # Save to conversation
            if self.ai_running:
                self._remember_conversation_turn("user", visible_prompt)
                # TODO: Get actual response text
                self._remember_conversation_turn(ai_name, "[Response completed]")

        except Exception as e:
            error_msg = f"\n[ERROR] Direct integration failed: {e}\n"
            self.after(0, lambda: self.output_view.append_terminal_text(error_msg))
        finally:
            self.ai_running = False
            self.after(0, lambda: self.thinking_overlay.hide())
            self.after(0, lambda: self._set_manual_active_agents(set()))

    def _run_cli_embedded_terminal(self, prompt: str, ai_name: str, visible_prompt: str) -> bool:
        """Run the real SAGE CLI and stream its terminal output inside the desktop."""
        if self.ai_running:
            return False

        self.output_view.set_terminal_mode(True)
        self.ai_running = True
        self.ai_process = None
        self.thinking_overlay.show()

        self.ai_thread = threading.Thread(
            target=self._run_cli_embedded_terminal_worker,
            args=(prompt, ai_name, visible_prompt),
            daemon=True,
        )
        self.ai_thread.start()
        return True

    def _run_cli_embedded_terminal_worker(self, prompt: str, ai_name: str, visible_prompt: str) -> None:
        """Background worker for the embedded terminal mode."""
        run_id = None
        output_parts: list[str] = []
        try:
            run_dir = data_dir() / "terminal-runs"
            run_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            prompt_path = run_dir / f"sage-prompt-{stamp}.txt"
            script_path = run_dir / f"sage-embedded-{stamp}.ps1"
            prompt_path.write_text(prompt, encoding="utf-8")

            command = self._external_terminal_command(ai_name)
            project = os.getcwd()
            script = self._external_terminal_script(
                ai_name=ai_name,
                command=command,
                prompt_path=prompt_path,
                project=project,
                clear_host=False,
            )
            script_path.write_text(script, encoding="utf-8")

            process = subprocess.Popen(
                [
                    "powershell",
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(script_path),
                ],
                cwd=project,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            self.ai_process = process

            # Show working state
            self.after(0, lambda: self.output_view.append_terminal_text("\n[Working...] Initializing Claude...\n"))

            terminal_queue: queue.Queue[str | None] = queue.Queue()

            def read_output() -> None:
                try:
                    if process.stdout:
                        while True:
                            chunk = process.stdout.read(1)
                            if chunk == "":
                                break
                            terminal_queue.put(chunk)
                finally:
                    terminal_queue.put(None)

            threading.Thread(target=read_output, daemon=True).start()

            buffer: list[str] = []
            last_flush = datetime.now()
            done = False
            first_output = True

            while not done:
                item = terminal_queue.get()
                if item is None:
                    done = True
                else:
                    # Clear working state on first real output
                    if first_output and item.strip() and not item.startswith("[Working"):
                        first_output = False

                    output_parts.append(item)
                    buffer.append(item)

                now = datetime.now()
                if buffer and (done or (now - last_flush).total_seconds() >= 0.05 or len(buffer) >= 512):
                    text = "".join(buffer)
                    buffer.clear()
                    last_flush = now
                    self.after(0, lambda value=text: self.output_view.append_terminal_text(value))

                if not self.ai_running and process.poll() is None:
                    process.terminate()

            exit_code = process.wait()
            output_text = "".join(output_parts)
            match = re.search(r"\[sage\] saved run #(\d+)", output_text)
            if match:
                run_id = int(match.group(1))

            if run_id:
                self._save_prompt_for_run(run_id, visible_prompt)
                self._record_context_compression(run_id)

            if self.ai_running:
                self._remember_conversation_turn("user", visible_prompt)
                self._remember_conversation_turn(ai_name, self._clean_terminal_answer(output_text))

            # Only show footer once if not already in output
            if "SAGE CLI finished" not in output_text:
                footer = f"\n----------------------------------------\nSAGE CLI finished. Exit code: {exit_code}\n"
                self.after(0, lambda value=footer: self.output_view.append_terminal_text(value))
        except Exception as err:
            message = f"\nERROR: Embedded SAGE CLI failed: {err}\n"
            self.after(0, lambda value=message: self.output_view.append_text(value, "error"))
        finally:
            self.ai_running = False
            self.ai_process = None
            self.after(0, self.thinking_overlay.hide)
            self.after(0, lambda: self._set_manual_active_agents(set()))
            self.after(0, self.update_metrics)
            # REMOVED: load_sidebar_data() - causes sidebar flicker on every command

    def _clean_terminal_answer(self, output_text: str) -> str:
        """Keep memory focused on the assistant answer, not the terminal footer."""
        text = output_text
        text = re.sub(r"(?s)^SAGE CLI starting\.\.\..*?-{8,}\s*", "", text)
        text = re.sub(r"\n\[sage\] saved run #.*", "", text).strip()
        return text

    def _run_cli_external_terminal(self, prompt: str, ai_name: str, visible_prompt: str) -> bool:
        """Open a real terminal for long AI work so the GUI stays responsive."""
        try:
            run_dir = data_dir() / "terminal-runs"
            run_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            prompt_path = run_dir / f"sage-prompt-{stamp}.txt"
            script_path = run_dir / f"sage-terminal-{stamp}.ps1"
            prompt_path.write_text(prompt, encoding="utf-8")

            command = self._external_terminal_command(ai_name)
            project = os.getcwd()
            script = self._external_terminal_script(
                ai_name=ai_name,
                command=command,
                prompt_path=prompt_path,
                project=project,
            )
            script_path.write_text(script, encoding="utf-8")

            subprocess.Popen(
                [
                    "powershell",
                    "-NoExit",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(script_path),
                ],
                cwd=project,
            )

            self.output_view.append_assistant_text(
                "Opened real SAGE CLI terminal for this run.\n"
                "The full live CLI output is in that terminal window; the desktop GUI will stay responsive.\n"
            )
            self._remember_conversation_turn("user", visible_prompt)
            self._remember_conversation_turn(ai_name, "[Opened in external SAGE CLI terminal]")
            return True
        except Exception as exc:
            self.output_view.append_text(f"\nERROR: Could not open external CLI terminal: {exc}\n", "error")
            return False

    def _external_terminal_command(self, ai_name: str, human_readable: bool = True) -> str:
        """Build the real command shown/run in the external terminal."""
        command = self.config.get_ai_command(ai_name)
        if self.current_client and getattr(self.current_client, "command", ""):
            command = self.current_client.command

        if not command.strip().lower().startswith("sage run --"):
            command = f"sage run -- {command}"

        if ai_name == "claude":
            if human_readable:
                command = self._strip_claude_json_stream_flags(command)
            else:
                command = self._ensure_claude_stream_json_flags(command)
            # Note: CLAUDE-FABLE-5.md and SAGE-INTEGRATION.md are loaded globally
            # via ~/.claude/CLAUDE.md imports, which the claude CLI reads on every
            # run. We no longer append them here to avoid loading them twice.

        command = self._apply_model_to_command(command, ai_name)
        command = self._apply_permission_to_command(command, ai_name)
        return command

    # ----- Per-AI model selection (/model command) -----

    def _model_catalog(self, ai_name: str) -> list[str]:
        """Suggested models for each AI. Users can also type any custom name."""
        if ai_name == "claude":
            return ["sonnet", "opus", "haiku"]
        if ai_name == "codex":
            return ["gpt-5-codex", "gpt-5", "o3", "o4-mini"]
        if ai_name == "ollama":
            return self._list_ollama_models() or ["qwen2.5-coder:7b"]
        if ai_name == "gemini":
            return ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"]
        if ai_name == "llama":
            return ["llama3.1", "llama3.2", "llama3.3"]
        if ai_name == "mistral":
            return ["mistral-large", "mistral-small", "codestral"]
        return []

    def _list_ollama_models(self) -> list[str]:
        """Return installed Ollama model names, or [] if unavailable."""
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
            models = []
            for line in result.stdout.strip().splitlines()[1:]:  # skip header
                if line.strip():
                    models.append(line.split()[0])
            return models
        except Exception:
            return []

    def _get_selected_model(self, ai_name: str) -> str:
        """Return the user-chosen model for an AI, or '' for the CLI default."""
        models = self.config.get("ai_models", {})
        return models.get(ai_name, "") if isinstance(models, dict) else ""

    def _set_selected_model(self, ai_name: str, model: str) -> None:
        """Persist the chosen model for an AI."""
        models = self.config.get("ai_models", {})
        if not isinstance(models, dict):
            models = {}
        models[ai_name] = model
        self.config.set("ai_models", models)
        self._refresh_runtime_labels()

    def _apply_model_to_command(self, command: str, ai_name: str) -> str:
        """Inject the selected model into a command using that CLI's own syntax."""
        model = self._get_selected_model(ai_name)
        if not model:
            return command

        if ai_name in ("claude", "codex"):
            if re.search(r"--model\s+\S+", command):
                return re.sub(r"--model\s+\S+", f"--model {model}", command)
            anchor = "codex exec" if ai_name == "codex" else "claude"
            return command.replace(anchor, f"{anchor} --model {model}", 1)

        if ai_name == "ollama":
            # Model is the positional argument after "ollama run".
            return re.sub(r"(ollama\s+run\s+)\S+", rf"\g<1>{model}", command)

        if ai_name in ("gemini", "llama", "mistral"):
            if re.search(r"\s-m\s+\S+", command):
                return re.sub(r"(\s-m\s+)\S+", rf"\g<1>{model}", command)
            return command.replace("aichat", f"aichat -m {model}", 1)

        return command

    def _apply_permission_to_command(self, command: str, ai_name: str) -> str:
        """Apply the bottom permission selector to the actual AI CLI command."""
        mode = self.config.get_permission_mode()

        if ai_name == "claude":
            command = re.sub(r"\s--dangerously-skip-permissions\b", "", command)
            command = re.sub(r"\s--allow-dangerously-skip-permissions\b", "", command)
            command = re.sub(r"\s--permission-mode\s+\S+", "", command)
            permission = {
                "ask": "default",
                "approve": "acceptEdits",
                "full": "bypassPermissions",
            }.get(mode, "default")
            return command.replace("claude", f"claude --permission-mode {permission}", 1)

        if ai_name == "codex":
            command = re.sub(r"\s--dangerously-bypass-approvals-and-sandbox\b", "", command)
            command = re.sub(r"\s(?:-s|--sandbox)\s+\S+", "", command)
            command = re.sub(r"\s-c\s+approval_policy=(?:\"[^\"]+\"|\S+)", "", command)
            command = re.sub(r"\s-c\s+sandbox_mode=(?:\"[^\"]+\"|\S+)", "", command)
            if mode == "full":
                return command + " --dangerously-bypass-approvals-and-sandbox"
            if mode == "approve":
                return command + ' -c approval_policy="never" -c sandbox_mode="workspace-write"'
            return command + ' -c approval_policy="on-request" -c sandbox_mode="workspace-write"'

        return command

    def _ensure_claude_stream_json_flags(self, command: str) -> str:
        """Use Claude's structured stream so the GUI can render thinking/answer sections."""
        if "claude" not in command:
            return command
        if "--print" not in command:
            command += " --print"
        if "--verbose" not in command:
            command += " --verbose"
        if "--output-format" not in command:
            command += " --output-format stream-json"
        if "--include-partial-messages" not in command:
            command += " --include-partial-messages"
        return command

    def _strip_claude_json_stream_flags(self, command: str) -> str:
        """Use human-readable Claude CLI output in the real terminal."""
        parts = command.split()
        cleaned = []
        skip_next = False
        for index, part in enumerate(parts):
            if skip_next:
                skip_next = False
                continue
            if part == "--verbose":
                continue
            if part == "--include-partial-messages":
                continue
            if part == "--output-format":
                skip_next = True
                continue
            cleaned.append(part)
        if "claude" in cleaned and "--print" not in cleaned:
            insert_at = cleaned.index("claude") + 1
            cleaned.insert(insert_at, "--print")
        return " ".join(cleaned)

    def _external_terminal_script(
        self,
        ai_name: str,
        command: str,
        prompt_path: Path,
        project: str,
        clear_host: bool = True,
    ) -> str:
        """PowerShell script that runs the selected AI through SAGE CLI."""
        quoted_prompt = self._ps_quote(str(prompt_path))
        quoted_project = self._ps_quote(project)
        quoted_pythonpath = self._ps_quote(str(Path(__file__).resolve().parents[2]))
        clear_line = "Clear-Host\n" if clear_host else ""

        run_line = f"$prompt = Get-Content -Raw -LiteralPath {quoted_prompt}\n{command} $prompt"

        return (
            "$ErrorActionPreference = 'Continue'\n"
            "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()\n"
            "$env:PYTHONIOENCODING = 'utf-8'\n"
            "$env:PYTHONUTF8 = '1'\n"
            "$env:SAGE_SUPPRESS_SUMMARY = '1'\n"
            "$env:SAGE_CLEAN_MODE = '1'\n"
            f"$env:PYTHONPATH = {quoted_pythonpath}\n"
            f"Set-Location -LiteralPath {quoted_project}\n"
            f"{clear_line}"
            "Write-Host 'SAGE CLI starting...' -ForegroundColor Cyan\n"
            f"Write-Host 'Project: {project}' -ForegroundColor DarkGray\n"
            f"Write-Host 'AI: {ai_name.capitalize()}' -ForegroundColor DarkGray\n"
            "Write-Host '----------------------------------------' -ForegroundColor DarkGray\n"
            f"{run_line}\n"
            "$exitCode = $LASTEXITCODE\n"
            "Write-Host ''\n"
            "Write-Host '----------------------------------------' -ForegroundColor DarkGray\n"
            "Write-Host \"SAGE CLI finished. Exit code: $exitCode\" -ForegroundColor Cyan\n"
        )

    def _ps_quote(self, value: str) -> str:
        """Quote a string for PowerShell single-quoted literals."""
        return "'" + str(value).replace("'", "''") + "'"

    def _build_contextual_prompt(self, command: str) -> str:
        """Attach compact SAGE memory so fresh CLI processes keep context."""
        self.pending_context_compression = None

        include_older = self._asks_for_older_history(command)
        live_turns = list(self.conversation_turns[-6:])
        older_turns = list(getattr(self, "project_memory_turns", [])[-6:]) if include_older else []
        context_turns = (older_turns + live_turns)[-10:]

        if not context_turns:
            return command

        raw_context = self._format_turns(context_turns)
        live_context = self._compress_context(live_turns) if live_turns else ""
        older_context = self._compress_context(older_turns) if older_turns else ""
        compressed_parts = []
        if live_context:
            compressed_parts.extend([
                "Previous live messages in this current SAGE GUI session for this project/tab group:",
                live_context,
            ])
        if older_context:
            if compressed_parts:
                compressed_parts.append("")
            compressed_parts.extend([
                "Older saved project memory, included only because the user asked for older history:",
                older_context,
            ])
        compressed_context = "\n".join(compressed_parts)

        tracker = ContextManager().tracker
        original_tokens = tracker.estimate_tokens(raw_context)
        compressed_tokens = tracker.estimate_tokens(compressed_context)
        saved_tokens = max(0, original_tokens - compressed_tokens)
        savings_percent = (saved_tokens / original_tokens * 100) if original_tokens else 0

        self.pending_context_compression = {
            "original_tokens": original_tokens,
            "compressed_tokens": compressed_tokens,
            "saved_tokens": saved_tokens,
            "savings_percent": savings_percent,
        }

        lines = [
            "SAGE memory for this prompt:",
            compressed_context,
            "",
            "Rule: if the user asks what they just asked, what their previous question was, or what happened before this, answer from the latest live-session user message only.",
            "Use older saved project memory only when the user explicitly asks for older history, previous sessions, project history, or all history.",
            "Current user request:",
            command,
        ]
        return "\n".join(lines)

    def _asks_for_older_history(self, command: str) -> bool:
        """Return true only for prompts that explicitly ask beyond the live session."""
        text = " ".join(str(command or "").lower().split())
        older_markers = (
            "older history",
            "old history",
            "previous session",
            "previous sessions",
            "last session",
            "project history",
            "saved history",
            "saved memory",
            "all history",
            "full history",
            "before this session",
            "from earlier sessions",
            "from old sessions",
            "from saved chats",
            "everything i said",
        )
        return any(marker in text for marker in older_markers)

    def _format_turns(self, turns: list[dict]) -> str:
        """Format turns without compression."""
        blocks = []
        for turn in turns:
            role = str(turn.get("role", "user")).strip().title()
            text = str(turn.get("text", "")).strip()
            if text:
                blocks.append(f"{role}: {text}")
        return "\n\n".join(blocks)

    def _compress_context(self, turns: list[dict]) -> str:
        """Actually reduce old conversation turns before sending prompt context."""
        if len(turns) <= 4:
            return self._format_turns(turns)

        old_turns = turns[:-4]
        recent_turns = turns[-4:]
        old_summary = self._summarize_old_turns(old_turns)
        recent_text = self._format_turns(recent_turns)

        compressed = [
            "Older conversation summary:",
            old_summary,
            "",
            "Recent conversation kept verbatim:",
            recent_text,
        ]
        return "\n".join(part for part in compressed if part.strip())

    def _summarize_old_turns(self, turns: list[dict]) -> str:
        """Local extractive summary for old turns so fewer tokens are sent."""
        bullets = []
        for turn in turns:
            role = str(turn.get("role", "user")).strip().title()
            text = " ".join(str(turn.get("text", "")).strip().split())
            if not text:
                continue
            text = self._strip_low_value_output(text)
            bullets.append(f"- {role}: {text[:180]}")

        summary = "\n".join(bullets)
        if len(summary) > 1400:
            summary = summary[:650] + "\n- ... older discussion compressed ...\n" + summary[-650:]
        return summary

    def _strip_low_value_output(self, text: str) -> str:
        """Remove obvious noise before old-turn summarization."""
        noise_markers = [
            "[sage] saved run",
            "[sage] summary:",
            "Claude started",
            "Claude status:",
            "thinking tokens:",
        ]
        lines = []
        for line in text.splitlines():
            clean = line.strip()
            if not clean:
                continue
            if any(marker.lower() in clean.lower() for marker in noise_markers):
                continue
            lines.append(clean)
        return " ".join(lines)

    def _format_context_compression_status(self) -> str:
        """Show real context compression stats for this prompt."""
        stats = self.pending_context_compression
        if not stats or stats["saved_tokens"] <= 0:
            return ""
        return (
            "Context compressed: "
            f"{stats['original_tokens']} -> {stats['compressed_tokens']} estimated tokens "
            f"({stats['savings_percent']:.1f}% saved).\n\n"
        )

    def _project_key(self, project: str | None = None) -> str:
        """Normalized identity for per-project shared memory."""
        target = project or os.getcwd()
        return os.path.normcase(os.path.abspath(target))

    def _bind_project_memory(self, project: str | None = None) -> None:
        """Point conversation_turns/project_memory_turns at this project's shared lists.

        Same-project tabs get the SAME list objects, so a second AI reuses the
        first AI's context and both save tokens. Switching tabs rebinds instead
        of wiping, so each project keeps its own live memory.
        """
        # Use __dict__ access so a partially-constructed app (e.g. tests using
        # __new__) never triggers CTk's __getattr__ recursion on a missing attr.
        if not isinstance(self.__dict__.get("_live_memory_by_project"), dict):
            self.__dict__["_live_memory_by_project"] = {}
        if not isinstance(self.__dict__.get("_saved_memory_by_project"), dict):
            self.__dict__["_saved_memory_by_project"] = {}
        key = self._project_key(project)
        self.conversation_turns = self._live_memory_by_project.setdefault(key, [])
        self.project_memory_turns = self._saved_memory_by_project.setdefault(key, [])

    def _remember_conversation_turn(self, role: str, text: str):
        """Keep recent chat context AND save to session."""
        text = (text or "").strip()
        if not text:
            return
        text = self._strip_low_value_output(text)
        if len(text) > 3500:
            text = text[:1700] + "\n[Middle of long response trimmed for GUI memory]\n" + text[-1700:]

        # Shared per-project live memory. Mutate in place so all tabs on this
        # project (and both AIs) see the same conversation without re-sending it.
        self._bind_project_memory(os.getcwd())
        self.conversation_turns.append({"role": role, "text": text})
        self.conversation_turns[:] = self.conversation_turns[-16:]
        self._persist_conversation()

        # NEW: Save to SessionManager
        if self.current_session_id:
            try:
                self.session_manager.add_message(
                    os.getcwd(),
                    self.current_session_id,
                    role,
                    text
                )
            except Exception:
                pass  # Don't break if session save fails

    def _conversation_store_path(self) -> Path:
        return Path.home() / ".sage" / "conversations.json"

    def _persist_conversation(self):
        """Save this project's conversation so the GUI remembers it after restart."""
        try:
            path = self._conversation_store_path()
            data = {}
            if path.exists():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    data = {}
            if not isinstance(data, dict):
                data = {}
            saved_turns = (getattr(self, "project_memory_turns", []) + self.conversation_turns)[-16:]
            data[self._project_key()] = saved_turns
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception:
            log.debug("suppressed", exc_info=True)

    def _load_saved_conversation(self, announce: bool = False):
        """Restore saved project memory without mixing it into the live session."""
        try:
            self._bind_project_memory(os.getcwd())
            path = self._conversation_store_path()
            if not path.exists():
                return
            data = json.loads(path.read_text(encoding="utf-8"))
            turns = data.get(self._project_key(), []) if isinstance(data, dict) else []
            # Restore saved memory in place; preserve this project's live turns.
            self.project_memory_turns[:] = [
                turn for turn in turns
                if isinstance(turn, dict) and str(turn.get("text", "")).strip()
            ][-16:]
            if announce and self.project_memory_turns:
                count = len(self.project_memory_turns)
                self.output_view.append_text(
                    f"[Memory] Loaded {count} older saved turn{'s' if count != 1 else ''} for this project. "
                    "Live-session memory starts fresh; ask for older history to use saved memory.\n",
                    "info",
                )
        except Exception:
            self._bind_project_memory(os.getcwd())
            self.project_memory_turns.clear()
            self.conversation_turns.clear()

    def _remember_terminal_ai_response(self, text: str):
        """Store the actual streamed terminal response for same-chat context."""
        self._remember_conversation_turn(self.ai_selector.get().lower(), text)
        self._set_manual_active_agents(set())

    def _finish_terminal_ai_run(self, tab_id: int, error: str | None = None) -> None:
        """Reset GUI run state when an embedded terminal AI command completes."""
        tab = self.output_tabs.get(tab_id)
        if tab:
            tab["ai_running"] = False
        if tab_id == self.active_output_tab_id:
            self.ai_running = False
            self.thinking_overlay.hide()
            self._set_run_status("Idle", "gray60")
        self._set_manual_active_agents(set())
        self.after(1500, self.update_metrics)
        self.after(100, lambda tid=tab_id: self._drain_queued_prompt(tid))

    def _format_run_preamble(self, ai_name: str, command: str, terminal: bool = False) -> str:
        """Show AI, PTY, ML, and agent plan for the run."""
        lines = [
            "",
            "SAGE run plan",
            f"AI: {ai_name.capitalize()}",
            f"PTY: {'Windows ConPTY available' if HAS_WINPTY else 'subprocess fallback'}",
            self._format_ml_prediction(command).strip(),
            self._format_run_agents(command).strip(),
        ]
        text = "\n".join(line for line in lines if line) + "\n"
        return text + ("----------------------------------------\n" if terminal else "\n")

    def _format_ml_prediction(self, command: str) -> str:
        """Show current ML failure prediction for this command."""
        try:
            will_fail, confidence, reason = FailurePredictor().predict(command)
            outcome = "likely to fail" if will_fail else "likely to succeed"
            status = SklearnFailureModel().status()
            model_state = "trained" if status.get("trained") else "heuristic fallback"
            return f"ML: {outcome} ({confidence:.0%}, {model_state}) - {reason}\n"
        except Exception as exc:
            return f"ML: unavailable - {exc}\n"

    def _format_run_agents(self, command: str) -> str:
        """Show planned agents and active agent records for this run."""
        planned = select_agents_for_command(command, limit=6)
        lines = ["Planned agents:"]
        for spec in planned:
            lines.append(f"- {spec.name} ({spec.type})")

        try:
            with connect() as conn:
                rows = conn.execute(
                    """
                    SELECT name, type, status
                    FROM agents
                    WHERE status = 'busy'
                    ORDER BY id DESC
                    LIMIT 8
                    """
                ).fetchall()
        except Exception:
            rows = []

        if rows:
            lines.append("Currently busy:")
            for row in rows:
                lines.append(f"- {row['name']} ({row['type']}, {row['status']})")
        return "\n".join(lines) + "\n\n"

    def _spawn_agents_if_needed(self, command: str) -> None:
        """Spawn agents for complex requests to parallelize work."""
        import asyncio
        from sage.agents.orchestrator import Orchestrator
        from sage.agents.specialized.code_agent import CodeAgent
        from sage.agents.specialized.test_agent import TestAgent
        from sage.agents.specialized.debug_agent import DebugAgent

        # Criteria for spawning agents
        word_count = len(command.split())
        keywords = ["test", "debug", "refactor", "optimize", "analyze", "review", "fix", "create", "build"]
        has_keyword = any(kw in command.lower() for kw in keywords)

        # Spawn if complex (>50 words) OR contains action keywords
        if word_count > 50 or has_keyword:
            try:
                orchestrator = Orchestrator()

                # Spawn appropriate agents based on command content
                agents_to_spawn = []

                if any(kw in command.lower() for kw in ["test", "testing", "pytest", "unittest"]):
                    agents_to_spawn.append((TestAgent, "test-agent-1"))

                if any(kw in command.lower() for kw in ["debug", "error", "fix", "bug"]):
                    agents_to_spawn.append((DebugAgent, "debug-agent-1"))

                if any(kw in command.lower() for kw in ["code", "refactor", "optimize", "create", "build"]):
                    agents_to_spawn.append((CodeAgent, "code-agent-1"))

                # Default: spawn at least one code agent for complex requests
                if not agents_to_spawn:
                    agents_to_spawn.append((CodeAgent, "code-agent-main"))

                # Spawn agents asynchronously and assign tasks
                async def spawn_all():
                    try:
                        for agent_class, name in agents_to_spawn:
                            try:
                                agent = await orchestrator.spawn_agent(agent_class, name)
                                print(f"[SAGE] Spawned {name} for this request")

                                # Assign task immediately so agent goes to "busy" status
                                task_desc = f"Handle: {command[:100]}"
                                await orchestrator.assign_task(name, task_desc, {"command": command})
                                print(f"[SAGE] Assigned task to {name}")
                            except Exception as e:
                                print(f"[SAGE] Failed to spawn {name}: {e}")

                        for agent in orchestrator.agents.values():
                            await agent.ensure_task_queue().join()
                    finally:
                        await orchestrator.shutdown()

                # Run in background thread to not block UI
                def run_async():
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(spawn_all())
                        loop.close()
                    except Exception as e:
                        print(f"[SAGE] Agent spawning error: {e}")

                threading.Thread(target=run_async, daemon=True).start()

            except Exception as e:
                print(f"[SAGE] Could not spawn agents: {e}")

    def _execute_agents_for_response(self, command: str, visible_command: str):
        """Execute agents through the REAL executor.py system after AI response."""
        try:
            from sage.agents.executor import execute_agents_for_run
            from sage.store import connect

            # Create a database run entry for this AI response
            now = datetime.now().isoformat()
            with connect() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO command_runs
                    (command, working_dir, status, started_at, completed_at, exit_code, summary)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        visible_command,
                        os.getcwd(),
                        "completed",
                        now,
                        now,
                        0,  # AI responses are always "successful"
                        f"AI response to: {visible_command[:100]}"
                    )
                )
                run_id = cursor.lastrowid
                conn.commit()

            # Execute agents for this run - they'll analyze the command
            print(f"[SAGE] Executing agents for run #{run_id}")
            results = execute_agents_for_run(
                run_id=run_id,
                command=visible_command,
                stdout="",  # AI response is the "output"
                stderr="",
                exit_code=0,
                summary=f"AI processing: {visible_command[:200]}",
                limit=4,  # Spawn up to 4 agents
            )

            # Display agent results in output view
            if results:
                self.after(0, lambda: self._display_agent_results(results))
                LOG.info("%s agents completed analysis", len(results))

        except Exception as e:
            LOG.warning("Agent execution failed: %s", e, exc_info=LOG.isEnabledFor(logging.DEBUG))

    def _display_agent_results(self, results: list[dict]):
        """Display agent analysis results in the output view."""
        if not self.output_view or not results:
            return

        try:
            self.output_view.append_text("\n━━━ Agent Analysis ━━━\n", "section_header")

            for result in results:
                agent_name = result.get("agent", "Unknown Agent")
                agent_type = result.get("agent_type", "generic")
                finding = result.get("finding", "Analysis complete")
                evidence = result.get("evidence", [])
                severity = result.get("severity", "info")
                confidence = result.get("confidence", 0.5)
                next_action = result.get("next_action", "")

                # Color based on severity
                severity_colors = {
                    "high": "error",
                    "medium": "warning",
                    "low": "info",
                    "info": "section_header"
                }
                severity_tag = severity_colors.get(severity, "section_header")

                self.output_view.append_text(f"\n[{agent_type.upper()}] ", "section_header")
                self.output_view.append_text(f"{finding}\n", severity_tag)
                self.output_view.append_text(f"  Confidence: {confidence:.0%} | Severity: {severity}\n", "info")

                if evidence:
                    self.output_view.append_text("  Evidence:\n", "section_header")
                    for ev in evidence[:3]:  # Show first 3 evidence items
                        self.output_view.append_text(f"    - {ev}\n", "info")

                if next_action:
                    self.output_view.append_text(f"  → {next_action}\n", "section_header")

            self.output_view.append_text("\n", "info")

        except Exception as e:
            print(f"[SAGE] Failed to display agent results: {e}")

    def _handle_slash_command(self, command: str) -> bool:
        """Handle local SAGE slash commands before any AI call."""
        if not command.startswith("/"):
            return False

        parts = command.split(maxsplit=1)
        name = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if name == "/login":
            return self._open_claude_login()

        if name == "/model":
            return self._handle_model_command(arg)

        if name == "/steer":
            return self._steer_active_prompt(arg)

        if name in {"/clear", "/cls"}:
            self.output_view.clear()
            return True

        if name in {"/new", "/newchat"}:
            # Clear this project's SHARED memory in place so every tab/AI on it
            # forgets together (rebinding to a fresh list would not clear the dict).
            self._bind_project_memory(os.getcwd())
            self.project_memory_turns.clear()
            self.conversation_turns.clear()
            self._persist_conversation()

            # Clear persistent client history - THIS IS THE REAL FIX!
            if self.persistent_client:
                self.persistent_client.clear_history()
                self._show_local_response(
                    "Started fresh conversation!\n"
                    "✅ Persistent session history cleared\n"
                    "✅ Bot memory reset - no context from previous questions\n"
                )

            self.output_view.clear()
            return True

        if name in {"/help", "/commands"}:
            self._show_local_response(
                "Local SAGE actions:\n"
                "/login - Open a terminal window to log in to Claude\n"
                "/model - Show or set the model for the current AI (per-AI)\n"
                "/steer <message> - Stop the active response and send this next\n"
                "/clear - Clear the output screen\n"
                "/skills - Show installed skills found on this computer\n"
                "/plugins - Show installed plugin bundles found on this computer\n"
                "/project - Show current project folder\n"
                "/history - Show recent saved chats\n"
                "/agents - Show agent records from the database\n"
                "/tasks - Show agent task results for the latest run\n"
                "/ml - Show trained ML model status\n"
                "/trainml - Train the sklearn failure predictor\n"
                "/models - Show configured AI options\n"
                "/theme - Toggle output light/dark mode\n"
                "/refresh - Reload sidebar and metrics\n"
                "/new - Clear output and start a fresh context\n"
            )
            return True

        if name == "/skills":
            self._show_local_response(self._format_skills(arg))
            return True

        if name in {"/plugins", "/plugin"}:
            self._show_local_response(self._format_plugins(arg))
            return True

        if name in {"/project", "/pwd"}:
            self._show_local_response(f"Current project:\n{os.getcwd()}\n")
            return True

        if name == "/history":
            self._show_local_response(self._format_history())
            return True

        if name == "/agents":
            self._show_local_response(self._format_agents())
            return True

        if name == "/tasks":
            self._show_local_response(self._format_latest_agent_tasks())
            return True

        if name == "/ml":
            self._show_local_response(self._format_ml_status())
            return True

        if name == "/trainml":
            self._show_local_response(self._train_ml_model())
            return True

        if name in {"/models", "/ais"}:
            self._show_local_response(self._format_ai_options())
            return True

        if name == "/theme":
            self.toggle_output_light_mode()
            mode = "light" if self.output_light_mode else "dark"
            self._show_local_response(f"Output theme changed to {mode} mode.\n")
            return True

        if name == "/refresh":
            self.load_sidebar_data()
            self.update_metrics()
            self._show_local_response("Sidebar and metrics refreshed.\n")
            return True

        self._show_local_response(f"Unknown local action: {name}\nType /help to see available actions.\n")
        return True

    def _handle_model_command(self, arg: str) -> bool:
        """Show or set the model for the currently selected AI."""
        ai_name = self.ai_selector.get().lower()
        arg = arg.strip()

        if not arg:
            # Show interactive picker dialog instead of text!
            self._show_model_picker(ai_name)
            return True

        if arg.lower() in ("default", "clear", "reset"):
            self._set_selected_model(ai_name, "")
            self._show_local_response(
                f"{ai_name.capitalize()} model reset to the CLI default.\n"
                "Applies to your next prompt.\n"
            )
            return True

        self._set_selected_model(ai_name, arg)
        self._show_local_response(
            f"{ai_name.capitalize()} model set to: {arg}\n"
            "Applies to your next prompt in this AI.\n"
        )
        return True

    def _show_model_picker(self, ai_name: str):
        """Show interactive model selection dialog."""
        catalog = self._model_catalog(ai_name)
        current = self._get_selected_model(ai_name)

        if not catalog:
            self._show_local_response(
                f"No model catalog available for {ai_name.capitalize()}.\n"
                "Type /model <name> to set a custom model.\n"
            )
            return

        # Create dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Select {ai_name.capitalize()} Model")
        dialog.geometry("450x400")
        dialog.transient(self)
        dialog.grab_set()

        # Header
        ctk.CTkLabel(
            dialog,
            text=f"Choose {ai_name.capitalize()} Model:",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=15)

        # Current model display
        current_display = current or "CLI default"
        ctk.CTkLabel(
            dialog,
            text=f"Current: {current_display}",
            font=ctk.CTkFont(size=12),
            text_color="gray60"
        ).pack(pady=5)

        # Scrollable frame for models
        scroll_frame = ctk.CTkScrollableFrame(dialog, height=200)
        scroll_frame.pack(pady=10, padx=20, fill="both", expand=True)

        selected_model = ctk.StringVar(value=current or "")

        # Add "CLI Default" option
        ctk.CTkRadioButton(
            scroll_frame,
            text="CLI Default (recommended)",
            variable=selected_model,
            value="",
            font=ctk.CTkFont(size=13)
        ).pack(pady=5, padx=10, anchor="w")

        # Add catalog models
        for model in catalog:
            ctk.CTkRadioButton(
                scroll_frame,
                text=model,
                variable=selected_model,
                value=model,
                font=ctk.CTkFont(size=13)
            ).pack(pady=5, padx=10, anchor="w")

        # Custom model entry
        ctk.CTkLabel(
            dialog,
            text="Or enter custom model name:",
            font=ctk.CTkFont(size=11)
        ).pack(pady=(10, 5))

        custom_entry = ctk.CTkEntry(dialog, width=300, placeholder_text="custom-model-name")
        custom_entry.pack(pady=5)

        # Buttons
        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=15)

        def on_select():
            custom = custom_entry.get().strip()
            model = custom if custom else selected_model.get()
            dialog.destroy()
            self._set_selected_model(ai_name, model)
            display = model if model else "CLI default"
            self._show_local_response(
                f"{ai_name.capitalize()} model set to: {display}\n"
                "Applies to your next prompt.\n"
            )

        def on_cancel():
            dialog.destroy()

        ctk.CTkButton(
            button_frame,
            text="Apply",
            command=on_select,
            width=120
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=on_cancel,
            width=120,
            fg_color="gray40",
            hover_color="gray30"
        ).pack(side="left", padx=5)

    def _show_local_response(self, text: str):
        """Show a local SAGE response without sending anything to AI."""
        self.output_view.append_assistant_start("SAGE")
        self.output_view.append_assistant_text(text if text.endswith("\n") else text + "\n")

    def _format_skills(self, search: str = "") -> str:
        """Return installed skills found from real local files."""
        skills = self._scan_skill_files()
        if search:
            needle = search.lower()
            skills = [
                item for item in skills
                if needle in item["name"].lower() or needle in item["description"].lower()
            ]

        if not skills:
            return "No installed skill files found.\n"

        lines = [f"Skills found: {len(skills)}"]
        for item in skills[:80]:
            desc = f" - {item['description']}" if item["description"] else ""
            lines.append(f"- {item['name']} ({item['source']}){desc}")
        if len(skills) > 80:
            lines.append(f"...and {len(skills) - 80} more")
        return "\n".join(lines) + "\n"

    def _scan_skill_files(self) -> list[dict]:
        """Scan local skill folders for SKILL.md files."""
        home = Path.home()
        roots = [
            (home / ".codex" / "skills", "Codex"),
            (home / ".agents" / "skills", "Personal"),
            (home / ".codex" / "plugins" / "cache", "Plugin"),
        ]

        found = {}
        for root, source in roots:
            if not root.exists():
                continue
            try:
                skill_files = list(root.rglob("SKILL.md"))
            except OSError:
                continue

            for path in skill_files:
                name, description = self._read_skill_summary(path)
                key = name.lower()
                found.setdefault(key, {
                    "name": name,
                    "description": description,
                    "source": source,
                })

        return sorted(found.values(), key=lambda item: item["name"].lower())

    def _read_skill_summary(self, path: Path) -> tuple[str, str]:
        """Read a short skill name and description from a SKILL.md file."""
        name = path.parent.name.replace("-", " ").replace("_", " ").title()
        description = ""

        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return name, description

        for line in lines[:40]:
            clean = line.strip()
            if not clean:
                continue
            if clean.startswith("#"):
                possible_name = clean.lstrip("#").strip()
                if possible_name:
                    name = possible_name
                continue
            if clean.lower().startswith("description:"):
                description = clean.split(":", 1)[1].strip()
                break
            if not description and len(clean) > 20:
                description = clean[:140]
                break

        return name, description

    def _format_plugins(self, search: str = "") -> str:
        """Return installed plugin bundles found from real local files."""
        plugins = self._scan_plugins()
        if search:
            needle = search.lower()
            plugins = [
                item for item in plugins
                if needle in item["name"].lower() or needle in item["path"].lower()
            ]

        if not plugins:
            return "No plugin bundles found in the local Codex plugin cache.\n"

        lines = [f"Plugins found: {len(plugins)}"]
        for item in plugins[:80]:
            version = f" v{item['version']}" if item["version"] else ""
            lines.append(f"- {item['name']}{version} ({item['source']})")
        if len(plugins) > 80:
            lines.append(f"...and {len(plugins) - 80} more")
        return "\n".join(lines) + "\n"

    def _scan_plugins(self) -> list[dict]:
        """Scan local plugin cache for plugin manifests."""
        root = Path.home() / ".codex" / "plugins" / "cache"
        if not root.exists():
            return []

        plugins = []
        seen = set()
        try:
            manifests = list(root.rglob("plugin.json"))
        except OSError:
            manifests = []

        for manifest in manifests:
            try:
                data = json.loads(manifest.read_text(encoding="utf-8", errors="replace"))
            except (OSError, json.JSONDecodeError):
                data = {}

            plugin_root = manifest.parent.parent if manifest.parent.name == ".codex-plugin" else manifest.parent
            name = data.get("name") or data.get("id") or plugin_root.name
            version = data.get("version") or ""
            source = plugin_root.parent.name if plugin_root.parent != root else "cache"
            key = str(plugin_root).lower()
            if key in seen:
                continue
            seen.add(key)
            plugins.append({
                "name": str(name),
                "version": str(version),
                "source": str(source),
                "path": str(plugin_root),
            })

        if not plugins:
            for child in root.iterdir():
                if child.is_dir():
                    plugins.append({
                        "name": child.name,
                        "version": "",
                        "source": "cache",
                        "path": str(child),
                    })

        return sorted(plugins, key=lambda item: item["name"].lower())

    def _format_history(self) -> str:
        """Return recent saved chats without raw CLI launch commands."""
        try:
            with connect() as conn:
                rows = conn.execute(
                    """
                    SELECT id, command, summary, created_at, project
                    FROM runs
                    ORDER BY id DESC
                    LIMIT 12
                    """
                ).fetchall()
        except Exception as exc:
            return f"Could not read history: {exc}\n"

        if not rows:
            return "No saved chats yet.\n"

        lines = ["Recent chats:"]
        for row in rows:
            title = self._chat_title_from_run(row["id"], row["command"], row["summary"])
            project = os.path.basename(row["project"]) or row["project"]
            lines.append(f"- #{row['id']} {title} ({project})")
        return "\n".join(lines) + "\n"

    def _format_agents(self) -> str:
        """Return real agent records from the database."""
        try:
            ensure_default_agents()
            with connect() as conn:
                rows = conn.execute(
                    """
                    SELECT id, name, type, status, last_active
                    FROM agents
                    ORDER BY id DESC
                    LIMIT 30
                    """
                ).fetchall()
        except Exception as exc:
            return f"Could not read agents: {exc}\n"

        if not rows:
            return "No agent records found.\n"

        lines = ["Agents:"]
        for row in rows:
            last_active = row["last_active"] or "never"
            lines.append(f"- #{row['id']} {row['name']} [{row['type']}] {row['status']} - {last_active}")
        return "\n".join(lines) + "\n"

    def _format_latest_agent_tasks(self) -> str:
        """Return agent task results for the latest run."""
        try:
            with connect() as conn:
                row = conn.execute("SELECT id FROM runs ORDER BY id DESC LIMIT 1").fetchone()
            if not row:
                return "No command history yet.\n"
            run_id = int(row["id"])
            tasks = get_agent_tasks_for_run(run_id)
        except Exception as exc:
            return f"Could not read agent tasks: {exc}\n"

        if not tasks:
            return f"No agent tasks found for run #{run_id}.\n"

        lines = [f"Agent tasks for run #{run_id}:"]
        for task in tasks:
            result = task["result"]
            lines.append(f"- #{task['id']} {task['agent_name']} [{task['agent_type']}] {task['status']}")
            lines.append(f"  Severity: {result.get('severity', 'n/a')} | Confidence: {result.get('confidence', 0):.0%}")
            lines.append(f"  Finding: {result.get('finding', 'completed')}")
            if result.get("next_step"):
                lines.append(f"  Next: {result['next_step']}")
            for action in (result.get("actions") or [])[:3]:
                lines.append(f"  Action: {action}")
        return "\n".join(lines) + "\n"

    def _format_ml_status(self) -> str:
        """Return trained ML model status."""
        status = SklearnFailureModel().status()
        lines = ["ML failure predictor:"]
        lines.append(f"- Trained: {status['trained']}")
        lines.append(f"- Model: {status['model_path']}")
        if status.get("trained"):
            metrics = status.get("metrics", {})
            lines.append(f"- Trained at: {status.get('trained_at')}")
            lines.append(f"- History samples: {status.get('history_samples', 0)}")
            lines.append(f"- Accuracy: {metrics.get('accuracy', 0):.3f}")
            lines.append(f"- Precision: {metrics.get('precision', 0):.3f}")
            lines.append(f"- Recall: {metrics.get('recall', 0):.3f}")
            roc_auc = metrics.get("roc_auc")
            lines.append(f"- ROC AUC: {roc_auc:.3f}" if roc_auc is not None else "- ROC AUC: n/a")
            lines.append(f"- Features: {len(status.get('features', []))}")
        return "\n".join(lines) + "\n"

    def _train_ml_model(self) -> str:
        """Train the sklearn model from local SAGE history."""
        try:
            result = SklearnFailureModel().train_from_history()
        except Exception as exc:
            return f"ML training failed: {exc}\n"

        lines = ["ML training complete:"]
        lines.append(f"- Trained: {result.trained}")
        lines.append(f"- Model: {result.model_path}")
        lines.append(f"- Samples: {result.samples} ({result.positives} failed, {result.negatives} succeeded)")
        lines.append(f"- Accuracy: {result.accuracy:.3f}")
        lines.append(f"- Precision: {result.precision:.3f}")
        lines.append(f"- Recall: {result.recall:.3f}")
        lines.append(f"- ROC AUC: {result.roc_auc:.3f}" if result.roc_auc is not None else "- ROC AUC: n/a")
        lines.append(f"- Message: {result.message}")
        return "\n".join(lines) + "\n"

    def _format_ai_options(self) -> str:
        """Return configured AI choices and availability."""
        names = ["claude", "codex", "ollama", "gemini", "llama", "mistral"]
        lines = ["AI options:"]
        for name in names:
            command = self.config.get_ai_command(name)
            status = "available" if check_cli_available(name, command) else "not found"
            selected = " selected" if self.ai_selector.get().lower() == name else ""
            connected = " connected" if self.ai_connected and selected else ""
            lines.append(f"- {name.capitalize()}: {status}{selected}{connected}")
        return "\n".join(lines) + "\n"

    def _load_system_prompts(self, ai_name: str) -> str:
        """Load and combine system prompts."""
        prompts = []
        for prompt_file in self.config.get_system_prompts(ai_name):
            path = Path(prompt_file)
            if path.exists():
                try:
                    prompts.append(path.read_text(encoding='utf-8'))
                except Exception as e:
                    print(f"Error loading {prompt_file}: {e}")

        return "\n\n".join(prompts) if prompts else None

    def _run_cli_stream(
        self,
        prompt: str,
        ai_name: str,
        visible_prompt: str,
        tab_id: int | None = None,
        client: CLIClient | None = None,
        output_view=None,
    ):
        """Stream CLI response."""
        client = client or self.current_client
        output_view = output_view or self.output_view
        try:
            if tab_id in self.output_tabs:
                self.output_tabs[tab_id]["ai_running"] = True
            if tab_id == self.active_output_tab_id:
                self.ai_running = True
            assistant_chunks = []
            stream_buffer = []
            stream_buffer_lock = threading.Lock()
            stream_state = {"line_count": 0, "flush_scheduled": False}

            # Start LED border animation on main thread
            if tab_id == self.active_output_tab_id:
                self.after(0, self.thinking_overlay.show)

            def show_wait_status():
                tab_running = self.output_tabs.get(tab_id, {}).get("ai_running", self.ai_running)
                if tab_running and stream_state["line_count"] == 0:
                    self._append_run_status(output_view, f"[Working] {ai_name.capitalize()} is running. Waiting for live CLI output...\n")

            self.after(2500, show_wait_status)

            def flush_stream_buffer():
                with stream_buffer_lock:
                    text = "".join(stream_buffer)
                    stream_buffer.clear()
                    stream_state["flush_scheduled"] = False
                if text:
                    output_view.append_assistant_text(text)

            def queue_stream_text(text: str):
                with stream_buffer_lock:
                    stream_buffer.append(text)
                    if stream_state["flush_scheduled"]:
                        return
                    stream_state["flush_scheduled"] = True
                self.after(60, flush_stream_buffer)

            # Stream response line by line
            for line in client.stream_response(prompt):
                # Check if cancelled
                tab_running = self.output_tabs.get(tab_id, {}).get("ai_running", self.ai_running)
                if not tab_running:
                    self.after(0, lambda view=output_view: view.append_text("\n[CANCELLED by user]\n", "error"))
                    break

                # Update UI on main thread
                stream_state["line_count"] += 1
                self._mark_tab_stream_event(tab_id)
                assistant_chunks.append(line)
                queue_stream_text(line)

            # Stop LED animation on main thread
            self.after(0, flush_stream_buffer)
            if tab_id == self.active_output_tab_id:
                self.after(0, self.thinking_overlay.hide)
                self.after(0, lambda: self._set_run_status("Idle", "gray60"))

            run_id = getattr(client, "last_run_id", None) if client else None
            if run_id:
                self.after(0, lambda rid=run_id, text=visible_prompt: self._save_prompt_for_run(rid, text))
                self._record_context_compression(run_id, output_view)

            if self.output_tabs.get(tab_id, {}).get("ai_running", self.ai_running):
                assistant_text = "".join(assistant_chunks).strip()
                self._remember_conversation_turn("user", visible_prompt)
                self._remember_conversation_turn(ai_name, assistant_text)

            if tab_id in self.output_tabs:
                self.output_tabs[tab_id]["ai_running"] = False
            if tab_id == self.active_output_tab_id:
                self.ai_running = False
            self.after(100, lambda tid=tab_id: self._drain_queued_prompt(tid))

        except Exception as err:
            if tab_id in self.output_tabs:
                self.output_tabs[tab_id]["ai_running"] = False
            if tab_id == self.active_output_tab_id:
                self.ai_running = False
            self.after(100, lambda tid=tab_id: self._drain_queued_prompt(tid))
            error_msg = str(err)
            LOG.warning("AI stream worker failed: %s", err, exc_info=LOG.isEnabledFor(logging.DEBUG))
            if tab_id == self.active_output_tab_id:
                self.after(0, self.thinking_overlay.hide)
                self.after(0, lambda: self._set_run_status("Idle", "gray60"))
            self.after(0, lambda msg=error_msg, view=output_view: view.append_text(f"\nERROR: {msg}\n", "error"))

    def _format_tool_result(self, result_content):
        """Format and display a tool result."""
        # Extract text from result
        if isinstance(result_content, str):
            text = result_content
        elif isinstance(result_content, list):
            parts = []
            for block in result_content:
                if isinstance(block, dict) and isinstance(block.get("text"), str):
                    parts.append(block["text"])
            text = "\n".join(parts)
        else:
            text = "(no output)"

        # Show first line + count if multiline
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            self.output_view.append_text("(no output)\n", 'thinking_text')
            return

        first_line = lines[0]
        if len(first_line) > 100:
            first_line = first_line[:97] + "..."

        if len(lines) > 1:
            self.output_view.append_text(f"{first_line} ... +{len(lines) - 1} lines\n", 'thinking_text')
        else:
            self.output_view.append_text(f"{first_line}\n", 'thinking_text')

    def _format_tool_call(self, tool_name: str, tool_input: dict):
        """Format and display a tool call with its inputs."""
        from sage.gui.diff_formatter import format_edit_diff, format_write_diff

        if tool_name == 'Edit':
            file_path = tool_input.get('file_path', '???')
            old_string = tool_input.get('old_string', '')
            new_string = tool_input.get('new_string', '')
            diff = format_edit_diff(file_path, old_string, new_string)
            self.output_view.append_text(diff)

        elif tool_name == 'Write':
            file_path = tool_input.get('file_path', '???')
            content = tool_input.get('content', '')
            diff = format_write_diff(file_path, content)
            self.output_view.append_text(diff)

        elif tool_name == 'Read':
            file_path = tool_input.get('file_path', '???')
            limit = tool_input.get('limit')
            offset = tool_input.get('offset')
            if limit and offset:
                self.output_view.append_text(f"\n● Read({file_path}) — lines {offset}:{offset + limit}\n")
            elif limit:
                self.output_view.append_text(f"\n● Read({file_path}) — first {limit} lines\n")
            else:
                self.output_view.append_text(f"\n● Read({file_path})\n")

        else:
            # Generic tool format
            params_str = ", ".join(f"{k}={v!r}" for k, v in tool_input.items())
            self.output_view.append_text(f"\n● {tool_name}({params_str})\n")

    def _record_context_compression(self, run_id: int, output_view=None):
        """Persist real prompt context compression stats for the token card."""
        stats = self.pending_context_compression
        if not stats:
            return
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        try:
            with connect() as conn:
                self._ensure_context_compression_table(conn)
                conn.execute(
                    """
                    INSERT INTO context_compression
                    (run_id, created_at, original_tokens, compressed_tokens, saved_tokens)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        now,
                        int(stats["original_tokens"]),
                        int(stats["compressed_tokens"]),
                        int(stats["saved_tokens"]),
                    ),
                )

            # Display per-request token savings
            if output_view:
                saved_k = self._format_count(int(stats["saved_tokens"]))
                savings_pct = stats["savings_percent"]
                msg = f"\n💾 Saved {saved_k} tokens on this request ({savings_pct:.1f}% compression)\n"
                self.after(0, lambda: output_view.append_text(msg, "success"))
        except Exception as e:
            # DEBUG:Error recording context compression: {e}")
            pass

    def on_clear_output(self):
        """Handle clear button click"""
        self.output_view.clear()
        self.output_view.append_text("Output cleared.\n", "info")

    def reply_to_output_selection(self, selected_text: str):
        """Quote selected output text into the prompt box for reply."""
        selected_text = selected_text.strip()
        if not selected_text:
            return

        quote_lines = [f"> {line}" if line.strip() else ">" for line in selected_text.splitlines()]
        draft = "Reply to this:\n\n" + "\n".join(quote_lines) + "\n\n"
        self.input_area.set_text(draft)
        self.input_area.focus()

    def load_sidebar_data(self):
        """Load chat history and projects into sidebar"""
        threading.Thread(target=self._fetch_sidebar_data, daemon=True).start()

    def _fetch_sidebar_data(self):
        """Fetch sidebar data from SessionManager"""
        try:
            # Get all projects with their sessions from SessionManager
            projects = self.session_manager.get_all_projects()

            # Convert to sidebar format
            groups = []
            for project in projects:
                sessions = project.get("sessions", [])
                # Convert sessions to chat format for sidebar
                chats = []
                for session in sessions:
                    chats.append({
                        "id": session.get("id"),
                        "title": session.get("title", "New Chat"),
                        "display_title": session.get("title", "New Chat"),
                        "relative_time": self._format_relative_time(session.get("updated_at", "")),
                        "pinned": session.get("pinned", False),
                        "unread": session.get("unread", False),
                    })

                groups.append({
                    "path": project.get("path"),
                    "name": project.get("name"),
                    "session_count": project.get("session_count", 0),
                    "run_count": project.get("session_count", 0),  # Compat
                    "sessions": chats,
                    "chats": chats,  # Compat with old sidebar code
                })

            # Add current project if not in list
            current_dir = os.getcwd()
            if not any(g["path"] == current_dir for g in groups):
                groups.insert(0, {
                    "path": current_dir,
                    "name": os.path.basename(current_dir) or "Current Directory",
                    "session_count": 0,
                    "run_count": 0,
                    "sessions": [],
                    "chats": [],
                })

            # Merge older run-backed chats into the same project groups. These
            # are loaded by integer run id through the legacy load_chat path.
            try:
                from sage.store import connect

                by_path = {str(group.get("path")): group for group in groups}
                with connect() as conn:
                    rows = conn.execute(
                        """
                        SELECT id, project, command, summary, created_at
                        FROM runs
                        ORDER BY id DESC
                        LIMIT 250
                        """
                    ).fetchall()

                for row in rows:
                    command = str(row["command"] or "")
                    if self._is_sidebar_noise(command):
                        continue
                    project_path = str(row["project"] or current_dir)
                    group = by_path.get(project_path)
                    if group is None:
                        group = {
                            "path": project_path,
                            "name": os.path.basename(project_path) or project_path,
                            "session_count": 0,
                            "run_count": 0,
                            "sessions": [],
                            "chats": [],
                        }
                        groups.append(group)
                        by_path[project_path] = group

                    chats = group.setdefault("chats", group.get("sessions", []))
                    if any(str(chat.get("id")) == str(row["id"]) for chat in chats):
                        continue
                    chats.append({
                        "id": int(row["id"]),
                        "title": self._chat_title_from_run(int(row["id"]), command, str(row["summary"] or "")),
                        "display_title": self._chat_title_from_run(int(row["id"]), command, str(row["summary"] or "")),
                        "relative_time": self._format_relative_time(str(row["created_at"] or "")),
                        "project": project_path,
                    })
                    group["sessions"] = chats
                    group["session_count"] = len(chats)
                    group["run_count"] = len(chats)
            except Exception as exc:
                print(f"Sidebar legacy history error: {exc}")

            # Sort: current project first, then by most recent activity
            groups.sort(key=lambda g: (g["path"] != current_dir, g.get("session_count", 0) == 0))

            self.after(0, lambda g=groups: self.sidebar.load_project_groups(g))

        except Exception as e:
            print(f"Sidebar Error: {e}")

    def _format_sidebar_time(self, timestamp: str) -> str:
        """Return a compact timestamp for the sidebar."""
        if not timestamp:
            return ""
        return timestamp.replace("T", " ").split("+")[0].split(".")[0]

    def _format_relative_time(self, timestamp: str) -> str:
        """Return compact relative time like 4h, 2d, or 1w."""
        if not timestamp:
            return ""
        try:
            value = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - value.astimezone(timezone.utc)
            seconds = max(0, int(delta.total_seconds()))
            if seconds < 60:
                return "now"
            if seconds < 3600:
                return f"{seconds // 60}m"
            if seconds < 86400:
                return f"{seconds // 3600}h"
            if seconds < 604800:
                return f"{seconds // 86400}d"
            return f"{seconds // 604800}w"
        except Exception:
            return self._format_sidebar_time(timestamp)

    def _is_sidebar_noise(self, command: str) -> bool:
        """Hide internal GUI/bootstrap commands from the chat list."""
        normalized = " ".join((command or "").strip().lower().split())
        noise_commands = {
            "python -m sage gui",
            "sage gui",
            "python -m sage --version",
        }
        return normalized in noise_commands

    def _prompt_title(self, prompt: str) -> str:
        """Create a sidebar title from the user's prompt."""
        title = " ".join((prompt or "").strip().split())
        return title[:70] if title else ""

    def _chat_title_from_run(self, chat_id: int, command: str, summary: str = "") -> str:
        """Create a useful chat title when the original prompt was not saved."""
        summary_title = self._clean_sidebar_text(summary)
        if summary_title:
            return summary_title

        command_title = self._clean_command_title(command)
        if command_title:
            return f"{command_title} #{chat_id}"

        return f"Run #{chat_id}"

    def _clean_sidebar_text(self, text: str) -> str:
        """Clean answer summaries into readable sidebar labels."""
        text = " ".join((text or "").strip().split())
        if not text:
            return ""

        removals = ["**", "__", "`", "#"]
        for item in removals:
            text = text.replace(item, "")
        for prefix in ("Sensei, ", "Done. ", "DONE. "):
            if text.startswith(prefix):
                text = text[len(prefix):]
        return text[:70]

    def _clean_command_title(self, command: str) -> str:
        """Fallback title for old technical command-only runs."""
        command = " ".join((command or "").strip().split())
        lower = command.lower()

        if "claude" in lower:
            return "Claude run"
        if "codex" in lower:
            return "Codex run"
        if "ollama" in lower:
            return "Ollama run"

        prefixes = [
            "sage run -- ",
            "python -m sage run -- ",
        ]
        for prefix in prefixes:
            if lower.startswith(prefix):
                command = command[len(prefix):].strip()
                break
        return command[:70]

    def _get_sidebar_state(self) -> dict:
        """Load local sidebar state from GUI config."""
        state = self.config.get("sidebar_state", {})
        if not isinstance(state, dict):
            state = {}
        state.setdefault("pinned", [])
        state.setdefault("archived", [])
        state.setdefault("unread", [])
        state.setdefault("titles", {})
        state.setdefault("prompts", {})
        return state

    def _save_sidebar_state(self, state: dict):
        """Persist local sidebar state."""
        self.config.set("sidebar_state", state)
        self.config.save()

    def _save_prompt_for_run(self, run_id: int, prompt: str):
        """Persist the user's prompt title for the saved run."""
        prompt_title = self._prompt_title(prompt)
        if not prompt_title:
            return

        state = self._get_sidebar_state()
        prompts = state.get("prompts", {})
        prompts[str(run_id)] = prompt_title
        state["prompts"] = prompts
        self._save_sidebar_state(state)
        self.load_sidebar_data()

    def _copy_to_clipboard(self, text: str):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.output_view.append_text("\nCopied to clipboard.\n", "info")

    def _restore_current_project(self):
        """Restore the last selected project when the GUI opens."""
        project = self.config.get("current_project", "")
        if project and os.path.isdir(project):
            try:
                os.chdir(project)
            except OSError:
                pass
        self._remember_project(os.getcwd(), save=False)

    def _remember_project(self, project_path: str, save: bool = True):
        """Persist current and recent project folders."""
        if not project_path:
            return

        project_path = os.path.abspath(project_path)
        self.config.config["current_project"] = project_path

        recent = self.config.get("recent_projects", [])
        if not isinstance(recent, list):
            recent = []

        cleaned = []
        seen = set()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")

        cleaned.append({
            "path": project_path,
            "name": os.path.basename(project_path) or project_path,
            "last_used": now,
        })
        seen.add(project_path.lower())

        for item in recent:
            if not isinstance(item, dict):
                continue
            path = os.path.abspath(str(item.get("path", "")))
            if not path or path.lower() in seen:
                continue
            seen.add(path.lower())
            cleaned.append({
                "path": path,
                "name": item.get("name") or os.path.basename(path) or path,
                "last_used": item.get("last_used", ""),
            })

        self.config.config["recent_projects"] = cleaned[:20]
        if hasattr(self, "project_label"):
            self.project_label.configure(text=f"Project: {project_path}")
        if save:
            self.config.save()

    def load_chat(self, session_id_or_chat_id):
        """Load a session (new) or legacy chat (old)."""
        try:
            # Try loading as session ID (string)
            if isinstance(session_id_or_chat_id, str):
                messages = self.session_manager.get_messages(os.getcwd(), session_id_or_chat_id)
                if messages:
                    self.current_session_id = session_id_or_chat_id
                    self._bind_project_memory(os.getcwd())
                    # FIXED: Show ALL messages, not just last 16
                    self.conversation_turns[:] = [
                        {"role": msg.get("role", ""), "text": msg.get("text", "")}
                        for msg in messages
                        if msg.get("text")
                    ]
                    if self.persistent_client:
                        self.persistent_client.load_history(messages)
                    self.output_view.clear()

                    # FIXED: Disable pruning while loading history - users expect to see ALL messages
                    self.output_view.prune_enabled = False

                    # Show full message count at top
                    total_messages = len(messages)
                    if total_messages > 0:
                        self.output_view.append_text(
                            f"\n━━━ Loaded {total_messages} message{'s' if total_messages != 1 else ''} from this chat ━━━\n\n",
                            "info"
                        )

                    # Display ALL messages with full content
                    for msg in messages:
                        role = msg.get("role", "")
                        text = msg.get("text", "")
                        if role == "user":
                            self.output_view.append_user_message(text)
                        else:
                            self.output_view.append_assistant_start(role.capitalize())
                            self.output_view.append_assistant_text(f"{text}\n")

                    # Re-enable pruning for future streaming (new messages)
                    self.output_view.prune_enabled = True

                    self.session_manager.mark_unread(os.getcwd(), session_id_or_chat_id, False)
                    self.load_sidebar_data()
                    return

            # Fallback: old database chat_id (int)
            with connect() as conn:
                row = conn.execute(
                    """
                    SELECT id, created_at, project, command, exit_code,
                           duration_ms, stdout, stderr, summary
                    FROM runs
                    WHERE id = ?
                    """,
                    (int(session_id_or_chat_id),),
                ).fetchone()

            if not row:
                self.output_view.append_text(f"\nSession not found: {session_id_or_chat_id}\n", "error")
                return

            state = self._get_sidebar_state()
            saved_prompt = state.get("prompts", {}).get(str(row["id"]))
            self.output_view.clear()
            if saved_prompt:
                self.output_view.append_user_message(saved_prompt)
            self.output_view.append_assistant_start("SAGE")

            assistant_text = ""
            if row["stderr"]:
                assistant_text = self._format_saved_output(row["stderr"])
                self.output_view.append_assistant_text(f"{assistant_text}\n")
            elif row["stdout"]:
                output = row["stdout"]
                # FIXED: Show FULL output, not just first 4K chars
                assistant_text = self._format_saved_output(output)
                self.output_view.append_assistant_text(f"{assistant_text}\n")
            elif row["summary"]:
                assistant_text = self._format_saved_output(row["summary"])
                self.output_view.append_assistant_text(f"{assistant_text}\n")

            self._bind_project_memory(os.getcwd())
            self.project_memory_turns.clear()
            self.conversation_turns.clear()
            if saved_prompt:
                self._remember_conversation_turn("user", saved_prompt)
            if assistant_text:
                self._remember_conversation_turn("assistant", assistant_text)
        except Exception as e:
            self.output_view.append_text(f"\nERROR: Could not load: {e}\n", "error")

    def _format_saved_output(self, text: str) -> str:
        """Convert saved raw output into readable chat text."""
        text = text or ""
        if text.lstrip().startswith('{"type"') and '"stream_event"' in text:
            parser = CLIClient(
                "claude",
                [],
                "sage run -- claude --print --verbose --output-format stream-json",
            )
            parsed = []
            for line in text.splitlines():
                parsed.extend(parser._parse_claude_json_line(line))
            return "".join(parsed).strip()
        return _clean_for_display(text)

    def delete_chat(self, chat_id: int):
        """Delete a saved chat/run from SAGE history."""
        try:
            with connect() as conn:
                token_table = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='token_usage'"
                ).fetchone()
                if token_table:
                    conn.execute("DELETE FROM token_usage WHERE run_id = ?", (chat_id,))
                compression_table = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='context_compression'"
                ).fetchone()
                if compression_table:
                    conn.execute("DELETE FROM context_compression WHERE run_id = ?", (chat_id,))
                deleted = conn.execute("DELETE FROM runs WHERE id = ?", (chat_id,)).rowcount

            if deleted:
                self.output_view.append_text(f"\nDeleted chat #{chat_id}.\n", "info")
            else:
                self.output_view.append_text(f"\nChat #{chat_id} was already gone.\n", "info")
            self.load_sidebar_data()
            self.update_metrics()
        except Exception as e:
            self.output_view.append_text(f"\nERROR: Could not delete chat #{chat_id}: {e}\n", "error")

    def reset_dashboard_data(self) -> bool:
        """Reset only this-session counters; keep all-time proof totals visible."""
        ok = messagebox.askyesno(
            "Reset SAGE dashboard?",
            "This will reset only the This Session columns to 0.\n\n"
            "All-time Total cards, saved chats, projects, profile, and database history will stay.",
            parent=self,
        )
        if not ok:
            return False

        try:
            with connect() as conn:
                totals = self._read_current_metric_totals(conn)
            self._set_session_baseline_from_totals(totals)
            self.config.set("dashboard_reset_baseline", {})

            compressed_tokens = totals.get("compressed_tokens", 0)
            token_savings = totals.get("token_savings", 0)
            original_tokens = totals.get("original_tokens", 0)
            token_rate = (token_savings / original_tokens * 100) if original_tokens else 0
            total_commands = totals.get("total_commands", 0)
            successful_commands = totals.get("successful_commands", 0)
            success_rate = (successful_commands / total_commands) if total_commands else 0
            self._update_ui_metrics(
                total_commands,
                0,
                compressed_tokens,
                token_savings,
                token_rate,
                0,
                0,
                totals.get("total_agents", 0),
                totals.get("active_agents", 0),
                0,
                success_rate,
                0,
                successful_commands,
                0,
                0,
            )
            self.output_view.append_text("\nDashboard session columns reset to 0. All-time totals were kept.\n", "info")
            return True
        except Exception as e:
            messagebox.showerror("Reset failed", f"SAGE could not reset dashboard data:\n\n{e}", parent=self)
            return False

    def delete_all_profile_data(self) -> bool:
        """Delete SAGE's local profile/config folder and database folder."""
        ok = messagebox.askyesno(
            "Delete all SAGE data?",
            "WARNING: This deletes your local SAGE profile, GUI settings, license/user files, "
            "saved chats, database, metrics, and sidebar history.\n\n"
            "This does not delete your project folders or GitHub repositories.\n\n"
            "Click Yes only if you want a clean SAGE profile.",
            parent=self,
        )
        if not ok:
            return False

        confirm = ctk.CTkInputDialog(
            text="Type DELETE to permanently delete SAGE profile and database:",
            title="Final confirmation",
        )
        if (confirm.get_input() or "").strip() != "DELETE":
            messagebox.showinfo("Delete cancelled", "Nothing was deleted.", parent=self)
            return False

        try:
            self.update_running = False
            self.ai_connected = False
            self.current_client = None
            self.ai_running = False
            self.thinking_overlay.hide()

            paths = []
            profile_dir = Path.home() / ".sage"
            for path in (data_dir(), profile_dir):
                resolved = path.resolve()
                if resolved not in paths:
                    paths.append(resolved)

            for path in paths:
                if path.exists():
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()

            self.config = GUIConfig()
            self._restore_current_project()
            self.config.save()
            self.input_area.set_permission(self.config.get_permission_mode())
            self.output_light_mode = bool(self.config.get("output_light_mode", False))
            self.output_view.set_light_mode(self.output_light_mode)
            self.input_area.set_output_light_mode(self.output_light_mode)
            self.connect_btn.configure(text="Connect")
            self.status_indicator.configure(text_color="red")
            self.ai_selector.configure(state="readonly")
            self._bind_project_memory(os.getcwd())
            self._reset_session_baseline_to_zero()
            self.output_view.clear()
            self.output_view.append_text(
                "SAGE profile and database deleted. A fresh empty profile has been created.\n",
                "info",
            )
            self.load_sidebar_data()
            self.update_running = True
            self.update_metrics()
            return True
        except Exception as e:
            self.update_running = True
            messagebox.showerror("Delete failed", f"SAGE could not delete all local data:\n\n{e}", parent=self)
            return False

    def _read_current_metric_totals(self, conn) -> dict:
        """Return current raw metric totals for non-destructive reset offsets."""
        self._ensure_context_compression_table(conn)
        run_row = conn.execute(
            """
            SELECT
                COUNT(*) as total_commands,
                SUM(CASE WHEN exit_code = 0 THEN 1 ELSE 0 END) as successful_commands
            FROM runs
            """
        ).fetchone()
        token_row = self._fetch_ai_token_totals(conn)
        agent_row = conn.execute(
            """
            SELECT
                COUNT(*) as total_agents,
                SUM(CASE WHEN status = 'busy' THEN 1 ELSE 0 END) as active_agents
            FROM agents
            """
        ).fetchone()
        return {
            "total_commands": int(run_row["total_commands"] or 0),
            "successful_commands": int(run_row["successful_commands"] or 0),
            "original_tokens": int(token_row[0] or 0),
            "compressed_tokens": int(token_row[1] or 0),
            "token_savings": int(token_row[2] or 0),
            "total_agents": int(agent_row["total_agents"] or 0),
            "active_agents": int(agent_row["active_agents"] or 0),
            "total_agent_tasks": int(conn.execute("SELECT COUNT(*) FROM agent_tasks").fetchone()[0] or 0),
        }

    def _get_dashboard_reset_baseline(self) -> dict:
        """Read reset offsets stored in config."""
        baseline = self.config.get("dashboard_reset_baseline", {})
        if not isinstance(baseline, dict):
            return {}
        keys = [
            "total_commands",
            "successful_commands",
            "original_tokens",
            "compressed_tokens",
            "token_savings",
            "total_agents",
            "active_agents",
            "total_agent_tasks",
        ]
        return {key: int(baseline.get(key, 0) or 0) for key in keys}

    def _reset_session_baseline_to_zero(self):
        """Make new post-reset activity count from zero in the session column."""
        self.session_start_commands = 0
        self.session_start_successes = 0
        self.session_start_agents = 0
        self.session_start_agent_tasks = 0
        self.session_start_used = 0
        self.session_start_saved = 0

    def _set_session_baseline_from_totals(self, totals: dict):
        """Make future session deltas count from the provided all-time totals."""
        self.session_start_commands = int(totals.get("total_commands", 0) or 0)
        self.session_start_successes = int(totals.get("successful_commands", 0) or 0)
        self.session_start_agents = int(totals.get("total_agents", 0) or 0)
        self.session_start_agent_tasks = int(totals.get("total_agent_tasks", 0) or 0)
        self.session_start_used = int(totals.get("compressed_tokens", 0) or 0)
        self.session_start_saved = int(totals.get("token_savings", 0) or 0)

    def handle_chat_action(self, action: str, chat: dict):
        """Handle sidebar right-click actions."""
        if action == "refresh_sidebar":
            self.load_sidebar_data()
            return

        if action == "show_scheduled":
            self._show_local_response(self._format_scheduled_view())
            return

        if action == "show_plugins":
            self._show_local_response(self._format_plugins_view())
            return

        chat_id = str(chat.get("id"))
        project = str(chat.get("project") or os.getcwd())
        state = self._get_sidebar_state()

        if action == "pin":
            pinned = set(map(str, state.get("pinned", [])))
            pinned.remove(chat_id) if chat_id in pinned else pinned.add(chat_id)
            state["pinned"] = sorted(pinned, key=int)
            self._save_sidebar_state(state)
            self.load_sidebar_data()
            return

        if action == "rename":
            dialog = ctk.CTkInputDialog(text="New chat name:", title="Rename chat")
            new_title = dialog.get_input()
            if new_title:
                titles = state.get("titles", {})
                titles[chat_id] = new_title.strip()
                state["titles"] = titles
                self._save_sidebar_state(state)
                self.load_sidebar_data()
            return

        if action == "archive":
            archived = set(map(str, state.get("archived", [])))
            archived.add(chat_id)
            state["archived"] = sorted(archived, key=int)
            self._save_sidebar_state(state)
            self.load_sidebar_data()
            return

        if action == "unread":
            unread = set(map(str, state.get("unread", [])))
            unread.remove(chat_id) if chat_id in unread else unread.add(chat_id)
            state["unread"] = sorted(unread, key=int)
            self._save_sidebar_state(state)
            self.load_sidebar_data()
            return

        if action == "open_explorer":
            if os.path.isdir(project):
                os.startfile(project)
            else:
                self.output_view.append_text(f"\nProject folder not found: {project}\n", "error")
            return

        if action == "copy_workdir":
            self._copy_to_clipboard(project)
            return

        if action == "copy_session_id":
            self._copy_to_clipboard(chat_id)
            return

        if action == "copy_deeplink":
            self._copy_to_clipboard(f"sage://chat/{chat_id}")
            return

        if action == "fork_local":
            if os.path.isdir(project):
                os.chdir(project)
                self._remember_project(project)
                if self.active_output_tab_id in self.output_tabs:
                    self.output_tabs[self.active_output_tab_id]["project"] = project
                self.output_view.clear()
                self.output_view.append_text(f"Forked chat #{chat_id} locally in:\n{project}\n", "info")
                self.project_label.configure(text=f"Project: {project}")
                self.load_sidebar_data()
                self._render_output_tabs()
            return

        if action == "fork_worktree":
            branch_dialog = ctk.CTkInputDialog(text="Branch name:", title="Fork into worktree")
            branch = (branch_dialog.get_input() or "").strip()
            if not branch:
                return
            if not os.path.isdir(project):
                self.output_view.append_text(f"\nProject folder not found: {project}\n", "error")
                return
            target = str(Path(project).parent / f"{Path(project).name}-{branch.replace('/', '-')}")
            try:
                import subprocess

                result = subprocess.run(
                    ["git", "worktree", "add", "-b", branch, target],
                    cwd=project,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=120,
                )
                if result.returncode == 0:
                    self.output_view.append_text(f"\nCreated worktree for chat #{chat_id}:\n{target}\n", "info")
                    self._remember_project(target)
                    self.load_sidebar_data()
                else:
                    self.output_view.append_text(f"\nERROR: git worktree failed:\n{result.stderr or result.stdout}\n", "error")
            except Exception as e:
                self.output_view.append_text(f"\nERROR: Could not create worktree: {e}\n", "error")
            return

        if action == "open_new_window":
            try:
                import subprocess

                env = os.environ.copy()
                env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])
                subprocess.Popen(
                    [sys.executable, "-m", "sage", "gui"],
                    cwd=project if os.path.isdir(project) else os.getcwd(),
                    env=env,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
                )
            except Exception as e:
                self.output_view.append_text(f"\nERROR: Could not open new SAGE window: {e}\n", "error")
            return

    def _format_scheduled_view(self) -> str:
        """Return a real scheduled/workflow status view for the sidebar button."""
        lines = ["Scheduled workflows and background work:"]
        with connect() as conn:
            workflows = conn.execute(
                """
                SELECT workflow_name, status, steps_completed, steps_total, started_at, completed_at
                FROM workflow_runs
                ORDER BY id DESC
                LIMIT 12
                """
            ).fetchall()
            agent_runs = conn.execute(
                """
                SELECT status, COUNT(*) as n
                FROM agent_runs
                WHERE status IN ('queued', 'running', 'waiting_for_tool')
                GROUP BY status
                """
            ).fetchall()
        if agent_runs:
            lines.append("\nAgent queue:")
            for row in agent_runs:
                lines.append(f"- {row['status']}: {row['n']}")
        if workflows:
            lines.append("\nRecent workflows:")
            for row in workflows:
                lines.append(
                    f"- {row['workflow_name']} [{row['status']}] "
                    f"{row['steps_completed'] or 0}/{row['steps_total'] or 0} "
                    f"started {row['started_at']}"
                )
        if not agent_runs and not workflows:
            lines.append("- No scheduled or running work is currently recorded.")
        return "\n".join(lines) + "\n"

    def _format_plugins_view(self) -> str:
        """Return useful plugin/cache information for the plugin command."""
        plugins = self._scan_plugins()
        roots = [
            Path.home() / ".codex" / "plugins" / "cache",
            Path.home() / ".codex" / "plugins",
        ]
        lines = ["Codex plugins"]
        if plugins:
            lines.append(f"Installed: {len(plugins)}")
            for item in plugins[:40]:
                version = f" v{item['version']}" if item.get("version") else ""
                lines.append(f"- {item['name']}{version}")
                lines.append(f"  Path: {item['path']}")
            if len(plugins) > 40:
                lines.append(f"...and {len(plugins) - 40} more")
        else:
            lines.append("No plugin bundles found in the standard Codex plugin paths.")

        lines.extend([
            "",
            "How to use:",
            "- Install/connect plugins in Codex Desktop or place plugin bundles under the paths below.",
            "- Restart or reconnect Codex in SAGE after installing a plugin.",
            "- Ask Codex to use a plugin by name; available plugin skills are loaded by the Codex runtime.",
            "",
            "Plugin paths:",
        ])
        for root in roots:
            lines.append(f"- {root}")
        return "\n".join(lines) + "\n"

    def new_chat_with_folder_picker(self):
        """Create NEW session in current project (NOT clearing existing chats!)"""
        # NO folder picker - just create new session in current project
        current_project = os.getcwd()

        # Create new session
        session_id = self.session_manager.create_session(current_project, title="New Chat")
        self.current_session_id = session_id

        # Clear this project's shared in-memory conversation in place
        # (not persisted sessions!)
        self._bind_project_memory(current_project)
        self.conversation_turns.clear()
        self.project_memory_turns.clear()

        # Clear persistent AI client history
        if hasattr(self, 'persistent_client') and self.persistent_client:
            self.persistent_client.clear_history()

        # Clear output
        self.output_view.clear()
        self.output_view.append_text(
            f"✨ New chat session created: {session_id}\n\n",
            "info"
        )

        # Reload sidebar to show new session
        self.load_sidebar_data()
        self._render_output_tabs()

    def switch_project(self, project_path: str):
        """Switch to a different project directory"""
        try:
            os.chdir(project_path)
            self._remember_project(project_path)
            if self.active_output_tab_id in self.output_tabs:
                self.output_tabs[self.active_output_tab_id]["project"] = project_path
            if hasattr(self.output_view, "send_command"):
                self.output_view.send_command(
                    f"Set-Location -LiteralPath {self._ps_quote(project_path)}",
                    wrap_with_sage=False,
                )
            self.output_view.append_text(f"\n[Switched to: {project_path}]\n", "info")
            self._load_saved_conversation(announce=True)
            self.project_label.configure(text=f"Project: {project_path}")
            self.load_sidebar_data()
            self._render_output_tabs()
        except Exception as e:
            self.output_view.append_text(f"\nError switching project: {e}\n", "error")

    def on_permission_changed(self, mode: str):
        """Handle permission mode change from dropdown."""
        self.config.set_permission_mode(mode)
        self.config.save()
        if self.persistent_client:
            self.persistent_client.permission_mode = mode
        self.output_view.append_text(f"\n[Permission mode: {mode}]\n", "info")
        self._refresh_runtime_labels()

    def toggle_output_light_mode(self):
        """Toggle light mode for the output screen only."""
        self.output_light_mode = not bool(getattr(self, "output_light_mode", False))
        for tab in self.output_tabs.values():
            terminal = tab.get("terminal")
            if terminal and hasattr(terminal, "set_light_mode"):
                terminal.set_light_mode(self.output_light_mode)
        self.input_area.set_output_light_mode(self.output_light_mode)
        self.config.set("output_light_mode", self.output_light_mode)

    def on_cancel_process(self):
        """Handle Esc/Ctrl+C - cancel running AI process."""
        tab = self._active_tab_state()
        tab_running = bool(tab.get("ai_running")) if tab else False
        if not self.ai_running and not tab_running:
            return

        active_client = tab.get("current_client") if tab else self.current_client
        if active_client and hasattr(active_client, "stop"):
            try:
                active_client.stop()
            except Exception:
                log.debug("suppressed", exc_info=True)
        self.ai_running = False
        if tab:
            tab["ai_running"] = False
        self._set_manual_active_agents(set())

        if self.ai_process:
            try:
                self.ai_process.terminate()
                self.ai_process = None
                if tab:
                    tab["ai_process"] = None
                self.thinking_overlay.hide()
                self.output_view.append_text("\n[CANCELLED by user - Esc pressed]\n", "error")
            except Exception as e:
                # DEBUG:Cancel error: {e}")
                pass
        elif tab_running:
            # Process not stored yet, just set flag
            self.thinking_overlay.hide()
            self.output_view.append_text("\n[CANCELLED by user]\n", "error")

        terminal = tab.get("terminal") if tab else self.output_view
        if terminal and hasattr(terminal, "interrupt"):
            terminal.interrupt()

    def open_permission_settings(self):
        """Open full settings panel (from sidebar button)."""
        from sage.gui.dialogs.settings_panel import SettingsPanel
        dialog = SettingsPanel(self, self.config)
        dialog.wait_window()

    def on_closing(self):
        """Clean shutdown"""
        try:
            self.update_running = False
            self.ai_connected = False
            self.current_client = None
            for tab in getattr(self, "output_tabs", {}).values():
                terminal = tab.get("terminal")
                if terminal and hasattr(terminal, "stop"):
                    terminal.stop()
            if self.ai_thread and self.ai_thread.is_alive():
                # Thread will terminate on its own
                pass
        except Exception as e:
            # DEBUG:Shutdown error: {e}")
            pass
        finally:
            self.destroy()

def main():
    """Launch the SAGE Desktop GUI"""
    _set_windows_app_id()
    app = SAGEApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()

if __name__ == "__main__":
    main()
