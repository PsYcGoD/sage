import logging
"""Full Settings Panel for SAGE Desktop GUI."""

import customtkinter as ctk
from typing import Optional
from pathlib import Path
import os
import re
import subprocess
import threading
from tkinter import messagebox

log = logging.getLogger(__name__)

class SettingsPanel(ctk.CTkToplevel):
    """Full settings panel with Features Active and configuration options."""

    FEATURES = [
        {"icon": "\u26a1", "name": "Context Manager", "description": "Real context compression", "color": "#FFB84D"},
        {"icon": "\U0001f527", "name": "Auto-Fix Engine", "description": "ML-powered fixes", "color": "#8B8B8B"},
        {"icon": "\U0001f916", "name": "Multi-Agent", "description": "Parallel execution", "color": "#FF6B9D"},
        {"icon": "\U0001f4cb", "name": "Workflows", "description": "YAML automation", "color": "#C8C8DC"},
        {"icon": "\U0001f50c", "name": "MCP Integration", "description": "Claude Code ready", "color": "#9B6FFF"},
        {"icon": "\U0001f3b2", "name": "ML Prediction", "description": "Failure detection", "color": "#E8E8E8"},
    ]

    def __init__(self, parent, config):
        """
        Initialize full settings panel.

        Args:
            parent: Parent window
            config: GUIConfig instance
        """
        super().__init__(parent)

        self.parent_app = parent
        self.config = config

        # Window configuration
        self.title("SAGE Settings")
        self.geometry("900x700")

        # Center on parent
        self.transient(parent)
        self.grab_set()

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header = ctk.CTkLabel(
            self,
            text="\u2699\ufe0f  SAGE Settings",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        header.grid(row=0, column=0, padx=30, pady=(25, 15), sticky="w")

        # Scrollable content frame
        scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        scroll_frame.grid_columnconfigure(0, weight=1)

        # Features Active section
        self._create_features_section(scroll_frame)

        # Profile Settings section
        self._create_profile_section(scroll_frame)

        # SAGE Cloud API section
        self._create_sage_api_section(scroll_frame)

        # Git Integration section
        self._create_git_section(scroll_frame)

        # Custom Endpoint section (3rd-party / self-hosted API key + base URL)
        self._create_custom_endpoint_section(scroll_frame)

        # API-Travel section
        self._create_api_travel_section(scroll_frame)

        # MCP Servers section
        self._create_mcp_section(scroll_frame)

        # System Prompts section
        self._create_prompts_section(scroll_frame)

        # Runtime behavior section
        self._create_runtime_section(scroll_frame)

        # Reset and delete controls
        self._create_danger_zone_section(scroll_frame)

        # Buttons
        self._create_buttons()

    def _create_features_section(self, parent):
        """Create Features Active cards section."""
        section = ctk.CTkFrame(parent, fg_color="transparent")
        section.grid(row=0, column=0, padx=10, pady=(0, 20), sticky="ew")
        section.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

        # Section header
        header = ctk.CTkLabel(
            section,
            text="Features Active",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        header.grid(row=0, column=0, columnspan=6, padx=5, pady=(0, 10), sticky="w")

        # Feature cards
        for i, feature in enumerate(self.FEATURES):
            card = self._create_feature_card(section, feature)
            card.grid(row=1, column=i, padx=5, pady=0, sticky="ew")

    def _create_feature_card(self, parent, feature: dict):
        """Create a single feature card."""
        card = ctk.CTkFrame(parent, fg_color="gray20", corner_radius=8, height=100)

        # Icon
        icon_label = ctk.CTkLabel(
            card,
            text=feature["icon"],
            font=ctk.CTkFont(size=32)
        )
        icon_label.pack(pady=(12, 5))

        # Name
        name_label = ctk.CTkLabel(
            card,
            text=feature["name"],
            font=ctk.CTkFont(size=11, weight="bold")
        )
        name_label.pack(pady=2)

        # Description
        desc_label = ctk.CTkLabel(
            card,
            text=feature["description"],
            font=ctk.CTkFont(size=9),
            text_color="gray60"
        )
        desc_label.pack(pady=(0, 10))

        return card

    def _create_profile_section(self, parent):
        """Create profile settings section."""
        section = self._create_section(parent, "Profile Settings", row=1)
        profile_name = self.config.get("profile_name", "User")
        try:
            from sage import telemetry

            status = telemetry.api_whoami()
            if status.get("connected") and status.get("display_name"):
                profile_name = status.get("display_name")
        except Exception:
            log.debug("suppressed", exc_info=True)

        # Display Name (only field user sets manually; git username/email auto-fill from OAuth)
        self._create_input(section, "Display Name:", "profile_name",
                          profile_name, row=0)

    def _create_sage_api_section(self, parent):
        """Create SAGE cloud API connection controls."""
        section = self._create_section(parent, "SAGE Cloud API", row=2)

        try:
            from sage import telemetry

            status = telemetry.api_whoami()
        except Exception:
            status = {"connected": False, "display_name": "", "username": "", "public_profile": False}

        # Show GitHub connection status (read-only)
        github_status = status.get("username", "Not connected")
        if status.get("connected"):
            github_status = f"@{status.get('username')} (GitHub)"

        github_label = ctk.CTkLabel(
            section,
            text="GitHub Account:",
            font=ctk.CTkFont(size=12),
            anchor="w",
            width=150,
        )
        github_label.grid(row=1, column=0, padx=15, pady=8, sticky="w")

        self.sage_api_github_label = ctk.CTkLabel(
            section,
            text=github_status,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
            text_color="#10b981" if status.get("connected") else "#6b7280",
        )
        self.sage_api_github_label.grid(row=1, column=1, padx=(10, 15), pady=8, sticky="w")

        self.sage_api_public_switch = ctk.CTkSwitch(
            section,
            text="Show my name on public proof",
            font=ctk.CTkFont(size=12),
        )
        if status.get("public_profile"):
            self.sage_api_public_switch.select()
        self.sage_api_public_switch.grid(row=3, column=0, columnspan=2, padx=15, pady=8, sticky="w")

        # 🔒 SECURITY: Key expiration settings
        expiry_label = ctk.CTkLabel(
            section,
            text="Key Expiration:",
            font=ctk.CTkFont(size=12),
            anchor="w",
            width=150,
        )
        expiry_label.grid(row=4, column=0, padx=15, pady=8, sticky="w")

        self.sage_api_expiry_menu = ctk.CTkOptionMenu(
            section,
            values=["30 days", "60 days", "90 days"],
            font=ctk.CTkFont(size=12),
        )
        self.sage_api_expiry_menu.set("30 days")  # Default
        self.sage_api_expiry_menu.grid(row=4, column=1, padx=(10, 15), pady=8, sticky="w")

        actions = ctk.CTkFrame(section, fg_color="transparent")
        actions.grid(row=5, column=0, columnspan=2, padx=15, pady=(8, 8), sticky="ew")

        self.sage_api_connect_btn = ctk.CTkButton(
            actions,
            text="Connect SAGE API",
            command=self._connect_sage_api,
            width=155,
        )
        self.sage_api_connect_btn.pack(side="left", padx=(0, 8))

        disconnect_btn = ctk.CTkButton(
            actions,
            text="Disconnect",
            command=self._disconnect_sage_api,
            width=110,
            fg_color="#7f1d1d",
            hover_color="#6b1515",
        )
        disconnect_btn.pack(side="left", padx=(0, 8))

        refresh_btn = ctk.CTkButton(
            actions,
            text="Refresh",
            command=self._refresh_sage_api_status,
            width=90,
            fg_color="gray35",
            hover_color="gray28",
        )
        refresh_btn.pack(side="left")

        send_btn = ctk.CTkButton(
            actions,
            text="Sync Now",
            command=self._send_sage_proof_now,
            width=130,
            fg_color="#15803d",
            hover_color="#166534",
        )
        send_btn.pack(side="left", padx=(8, 0))

        self.sage_api_status = ctk.CTkLabel(
            section,
            text=self._sage_api_status_text(),
            font=ctk.CTkFont(size=11),
            text_color="gray65",
            anchor="w",
            justify="left",
            wraplength=760,
        )
        self.sage_api_status.grid(row=6, column=0, columnspan=2, padx=15, pady=(4, 12), sticky="ew")

    def _sage_api_status_text(self) -> str:
        """Return SAGE API connection status for the settings panel."""
        try:
            from sage import telemetry

            status = telemetry.api_whoami()
        except Exception as exc:
            return f"SAGE API status error: {exc}"

        if not status.get("connected"):
            return "SAGE API: not connected. Click Connect SAGE API to create a free key automatically."
        return (
            "SAGE API: connected\n"
            f"Endpoint: {status.get('base_url')}\n"
            f"Key: {status.get('key_id')}\n"
            f"Telemetry: level {status.get('effective_level')} ({status.get('effective_level_name')})"
        )

    def _refresh_sage_api_status(self):
        """Refresh SAGE API connection status."""
        if hasattr(self, "sage_api_status"):
            self.sage_api_status.configure(text=self._sage_api_status_text())
        try:
            from sage import telemetry

            status = telemetry.api_whoami()
        except Exception:
            return
        if hasattr(self, "sage_api_github_label"):
            self.sage_api_github_label.configure(
                text=f"@{status.get('username')} (GitHub)" if status.get("connected") else "Not connected",
                text_color="#10b981" if status.get("connected") else "#6b7280",
            )
        if status.get("display_name"):
            self.config.set("profile_name", status.get("display_name"))

    def _connect_sage_api(self):
        """Connect SAGE API with GitHub OAuth."""
        display_name = None
        public_profile = self.sage_api_public_switch.get() == 1

        # 🔒 SECURITY: Get expiry days from dropdown
        expiry_text = self.sage_api_expiry_menu.get()  # "30 days", "60 days", or "90 days"
        expiry_days = int(expiry_text.split()[0])  # Extract number

        self.sage_api_connect_btn.configure(state="disabled", text="Connecting...")
        self.sage_api_status.configure(text="Checking GitHub login...", text_color="gray65")

        def worker():
            try:
                from sage import telemetry
                from sage.github_oauth import github_device_flow, github_oauth_flow
                from sage.install import install_sage_system_wide, is_sage_installed_system_wide

                result = None
                gh_error = None
                device_error = None

                try:
                    self.after(0, lambda: self.sage_api_status.configure(
                        text="Using existing GitHub CLI login...",
                        text_color="gray65",
                    ))
                    result = self._connect_sage_api_with_gh_token(
                        display_name=display_name,
                        public_profile=public_profile,
                        expiry_days=expiry_days,
                        original_error=RuntimeError("Browser OAuth was not attempted"),
                    )
                except Exception as exc:
                    gh_error = exc

                if result is None:
                    try:
                        self.after(0, lambda: self.sage_api_status.configure(
                            text="Opening GitHub device login...",
                            text_color="gray65",
                        ))

                        device_result = github_device_flow(
                            status_callback=lambda message: self.after(
                                0,
                                lambda text=message: self.sage_api_status.configure(
                                    text=text,
                                    text_color="gray65",
                                ),
                            )
                        )
                        result = telemetry.api_github_login(
                            github_access_token=device_result["access_token"],
                            display_name=display_name,
                            public_profile=public_profile,
                            expiry_days=expiry_days,
                        )
                    except Exception as exc:
                        device_error = exc

                if result is None:
                    try:
                        self.after(0, lambda: self.sage_api_status.configure(
                            text="Opening GitHub browser login...",
                            text_color="gray65",
                        ))
                        oauth_result = github_oauth_flow()

                        if not oauth_result.get("auth_code"):
                            raise RuntimeError("GitHub authentication cancelled")

                        self.after(0, lambda: self.sage_api_status.configure(
                            text="GitHub approved. Creating SAGE API key...",
                            text_color="gray65",
                        ))

                        result = telemetry.api_github_login(
                            auth_code=oauth_result["auth_code"],
                            redirect_uri=oauth_result.get("redirect_uri", ""),
                            display_name=display_name,
                            public_profile=public_profile,
                            expiry_days=expiry_days,
                        )
                    except Exception as oauth_exc:
                        raise RuntimeError(
                            "All GitHub login methods failed. "
                            f"GitHub CLI: {gh_error}. "
                            f"Device login: {device_error}. "
                            f"Browser login: {oauth_exc}"
                        ) from oauth_exc

                profile_name = result.get("display_name") or result.get("username") or ""
                if profile_name:
                    self.config.set("profile_name", profile_name)
                    self.config.save()

                # Install agent configs
                if not is_sage_installed_system_wide():
                    install_sage_system_wide()

                message = (
                    "SAGE API connected\n"
                    f"Endpoint: {result['base_url']}\n"
                    f"Key: {result['key_id']}\n"
                    f"GitHub: @{result.get('username')}\n"
                    "Local proof history sync has started in the background.\n"
                    "Safe metrics are enabled. Raw commands and output stay local."
                )
                self.after(0, lambda: self._finish_sage_api_connect(message, ok=True))
                threading.Thread(target=self._sync_sage_api_after_connect, daemon=True).start()
            except Exception as exc:
                message = f"SAGE API connect failed: {exc}"
                self.after(0, lambda: self._finish_sage_api_connect(message, ok=False))

        threading.Thread(target=worker, daemon=True).start()

    def _connect_sage_api_with_gh_token(
        self,
        *,
        display_name: str | None,
        public_profile: bool,
        expiry_days: int,
        original_error: Exception,
    ) -> dict:
        from sage import telemetry

        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        token = result.stdout.strip()
        if result.returncode != 0 or not token:
            details = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(
                "Browser OAuth failed and GitHub CLI fallback is not available. "
                f"OAuth error: {original_error}. gh output: {details or 'no token returned'}"
            )

        return telemetry.api_github_login(
            github_access_token=token,
            display_name=display_name,
            public_profile=public_profile,
            expiry_days=expiry_days,
        )

    def _sync_sage_api_after_connect(self):
        try:
            from sage import telemetry
            from sage.telemetry_sender import spawn_background_sender

            backfill = telemetry.queue_all_runs()
            spawn_background_sender()
            message = (
                "SAGE API connected\n"
                f"Queued local proof history: {backfill['queued']} of {backfill['scanned']} runs\n"
                "Automatic safe sync is running in the background."
            )
            self.after(0, lambda: self.sage_api_status.configure(text=message, text_color="#86efac"))
        except Exception as exc:
            msg = f"SAGE API connected, but background sync failed: {exc}"
            self.after(0, lambda m=msg: self.sage_api_status.configure(
                text=m,
                text_color="#fca5a5",
            ))

    def _finish_sage_api_connect(self, message: str, *, ok: bool):
        self.sage_api_connect_btn.configure(state="normal", text="Connect SAGE API")
        self.sage_api_status.configure(text=message, text_color="#86efac" if ok else "#fca5a5")
        if ok:
            self._refresh_sage_api_status()
            if hasattr(self, "_inputs") and "profile_name" in self._inputs:
                try:
                    from sage import telemetry

                    status = telemetry.api_whoami()
                    profile_name = status.get("display_name") or status.get("username") or ""
                    if profile_name:
                        self._inputs["profile_name"].delete(0, "end")
                        self._inputs["profile_name"].insert(0, profile_name)
                except Exception:
                    log.debug("suppressed", exc_info=True)
            messagebox.showinfo("SAGE API Connected", "SAGE API connected. API key saved locally.")
        else:
            messagebox.showerror("SAGE API Connect Failed", message)

    def _disconnect_sage_api(self):
        """Disconnect SAGE API credentials locally."""
        try:
            from sage import telemetry

            telemetry.api_logout()
            self.sage_api_status.configure(
                text="SAGE API disconnected. Telemetry is local-only.",
                text_color="gray65",
            )
            messagebox.showinfo("SAGE API Disconnected", "SAGE API disconnected on this PC.")
        except Exception as exc:
            self.sage_api_status.configure(text=f"Disconnect failed: {exc}", text_color="#fca5a5")
            messagebox.showerror("SAGE API Disconnect Failed", str(exc))

    def _send_sage_proof_now(self):
        """Queue all local runs and sync safe telemetry."""
        self.sage_api_status.configure(text="Syncing all safe local proof metrics...")

        def worker():
            try:
                from sage import telemetry
                result = telemetry.sync_all_runs(dry_run=False)
                queued_all = result.get("queued_all", {})
                message = (
                    "Sync complete: "
                    f"{result['sent']} sent, {result['queued']} still queued. "
                    f"Scanned {queued_all.get('scanned', 0)} local runs."
                )
                self.after(0, lambda: self._finish_sage_proof_send(message, ok=True))
            except Exception as exc:
                message = f"Sync failed: {exc}"
                self.after(0, lambda: self._finish_sage_proof_send(message, ok=False))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_sage_proof_send(self, message: str, *, ok: bool):
        self.sage_api_status.configure(text=message, text_color="#86efac" if ok else "#fca5a5")
        if ok:
            messagebox.showinfo("SAGE Sync Complete", message)
        else:
            messagebox.showerror("SAGE Sync Failed", message)

    def _create_agents_section(self, parent):
        """Show all 24 real SAGE agents as small compact role cards with icons."""
        section = self._create_section(parent, "SAGE Agents", row=3)
        try:
            from sage.agents.registry import list_default_agent_specs
            from sage.gui.widgets.agent_strip import agent_icon

            specs = list_default_agent_specs()
        except Exception as exc:
            error = ctk.CTkLabel(
                section,
                text=f"Could not load agent registry: {exc}",
                font=ctk.CTkFont(size=11),
                text_color="#fca5a5",
                anchor="w",
            )
            error.grid(row=1, column=0, columnspan=2, padx=15, pady=8, sticky="ew")
            return

        summary = ctk.CTkLabel(
            section,
            text=(
                f"All {len(specs)} real local agents. They fan out on every "
                "'sage run' command to analyze the run in parallel."
            ),
            font=ctk.CTkFont(size=11),
            text_color="gray65",
            anchor="w",
            wraplength=780,
        )
        summary.grid(row=1, column=0, columnspan=2, padx=15, pady=(4, 8), sticky="ew")

        grid = ctk.CTkFrame(section, fg_color="transparent")
        grid.grid(row=2, column=0, columnspan=2, padx=12, pady=(0, 12), sticky="ew")
        columns = 3
        for col in range(columns):
            grid.grid_columnconfigure(col, weight=1, uniform="agentcards")

        for index, spec in enumerate(specs):
            card = ctk.CTkFrame(grid, fg_color="gray20", corner_radius=8)
            card.grid(
                row=index // columns,
                column=index % columns,
                padx=4,
                pady=4,
                sticky="ew",
            )
            card.grid_columnconfigure(0, weight=1)

            name = ctk.CTkLabel(
                card,
                text=f"{agent_icon(spec['type'])}  {spec['name']}",
                font=ctk.CTkFont(size=11, weight="bold"),
                anchor="w",
            )
            name.grid(row=0, column=0, padx=8, pady=(7, 1), sticky="ew")

            role = ctk.CTkLabel(
                card,
                text=spec["description"],
                font=ctk.CTkFont(size=9),
                text_color="gray60",
                anchor="w",
                justify="left",
                wraplength=210,
            )
            role.grid(row=1, column=0, padx=8, pady=(0, 7), sticky="ew")

    def _create_git_section(self, parent):
        """Create git integration section."""
        section = self._create_section(parent, "Git Integration", row=3)

        # Git user name
        self._create_input(section, "Git User Name:", "git_user_name",
                          self.config.get("git_user_name", ""), row=0)

        # Git email
        self._create_input(section, "Git Email:", "git_user_email",
                          self.config.get("git_user_email", ""), row=1)

        # Auto-commit
        self._create_switch(section, "Auto-commit changes", "git_auto_commit",
                           self.config.get("git_auto_commit", False), row=2)

        accounts = self._github_accounts()
        self.github_accounts = accounts
        if accounts:
            account_names = [account["user"] for account in accounts]
            active = next((account["user"] for account in accounts if account["active"]), account_names[0])

            account_label = ctk.CTkLabel(
                section,
                text="GitHub Account:",
                font=ctk.CTkFont(size=12),
                anchor="w",
                width=150,
            )
            account_label.grid(row=4, column=0, padx=15, pady=8, sticky="w")

            self.github_account_menu = ctk.CTkOptionMenu(
                section,
                values=account_names,
                command=self._on_github_account_selected,
                width=220,
            )
            self.github_account_menu.set(active)
            self.github_account_menu.grid(row=4, column=1, padx=(10, 15), pady=8, sticky="w")

        self.github_status = ctk.CTkLabel(
            section,
            text=self._github_status_text(),
            font=ctk.CTkFont(size=11),
            text_color="gray65",
            anchor="w",
            justify="left",
        )
        self.github_status.grid(row=5, column=0, columnspan=2, padx=15, pady=(8, 4), sticky="ew")

        actions = ctk.CTkFrame(section, fg_color="transparent")
        actions.grid(row=6, column=0, columnspan=2, padx=15, pady=(4, 12), sticky="ew")

        connect_btn = ctk.CTkButton(
            actions,
            text="Connect GitHub",
            command=self._connect_github,
            width=150,
        )
        connect_btn.pack(side="left", padx=(0, 8))

        refresh_btn = ctk.CTkButton(
            actions,
            text="Refresh",
            command=self._refresh_github_status,
            width=90,
            fg_color="gray35",
            hover_color="gray28",
        )
        refresh_btn.pack(side="left")

        set_remote_btn = ctk.CTkButton(
            actions,
            text="Set Remote to Account",
            command=self._set_remote_to_selected_account,
            width=170,
            fg_color="#1d4ed8",
            hover_color="#1e40af",
        )
        set_remote_btn.pack(side="left", padx=(8, 0))

        create_repo_btn = ctk.CTkButton(
            actions,
            text="Create Repo + Set Remote",
            command=self._create_repo_and_set_remote,
            width=185,
            fg_color="#15803d",
            hover_color="#166534",
        )
        create_repo_btn.pack(side="left", padx=(8, 0))

    def _github_accounts(self) -> list[dict]:
        """Return logged-in GitHub accounts from gh auth status."""
        try:
            auth = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=8,
            )
        except Exception:
            return []

        text = f"{auth.stdout}\n{auth.stderr}"
        accounts = []
        current = None
        for line in text.splitlines():
            match = re.search(r"Logged in to .* account ([^\s]+)", line)
            if match:
                current = {"user": match.group(1), "active": False}
                accounts.append(current)
                continue
            if current and "Active account: true" in line:
                current["active"] = True

        return accounts

    def _on_github_account_selected(self, user: str):
        """Switch active GitHub account."""
        try:
            result = subprocess.run(
                ["gh", "auth", "switch", "--hostname", "github.com", "--user", user],
                capture_output=True,
                text=True,
                timeout=20,
            )
            if result.returncode == 0:
                self.config.set("github_account", user)
                self._refresh_github_status()
            elif hasattr(self, "github_status"):
                self.github_status.configure(text=f"Could not switch GitHub account:\n{result.stderr.strip()}")
        except Exception as e:
            if hasattr(self, "github_status"):
                self.github_status.configure(text=f"Could not switch GitHub account: {e}")

    def _active_github_user(self) -> str:
        accounts = self._github_accounts()
        return next((account["user"] for account in accounts if account["active"]), accounts[0]["user"] if accounts else "")

    def _selected_github_user(self) -> str:
        if hasattr(self, "github_account_menu"):
            return self.github_account_menu.get()
        return self._active_github_user()

    def _git_remote_url(self) -> str:
        try:
            remote = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                cwd=os.getcwd(),
                timeout=5,
            )
            return remote.stdout.strip() if remote.returncode == 0 else ""
        except Exception:
            return ""

    def _remote_owner(self, remote_url: str) -> str:
        match = re.search(r"github\.com[:/]+([^/]+)/", remote_url)
        return match.group(1) if match else ""

    def _current_repo_name(self) -> str:
        folder = os.path.basename(os.getcwd()) or "sage-project"
        return re.sub(r"[^A-Za-z0-9_.-]+", "-", folder).strip("-") or "sage-project"

    def _target_repo_url(self) -> str:
        user = self._selected_github_user()
        repo = self._current_repo_name()
        return f"https://github.com/{user}/{repo}.git"

    def _repo_exists(self, owner: str, repo: str) -> bool:
        result = subprocess.run(
            ["gh", "repo", "view", f"{owner}/{repo}"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.returncode == 0

    def _set_origin_remote(self, url: str):
        remote = self._git_remote_url()
        if remote:
            cmd = ["git", "remote", "set-url", "origin", url]
        else:
            cmd = ["git", "remote", "add", "origin", url]
        return subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd(), timeout=15)

    def _set_remote_to_selected_account(self):
        """Point local origin to the selected account when the repo exists."""
        user = self._selected_github_user()
        repo = self._current_repo_name()
        if not user:
            self.github_status.configure(text="Select or connect a GitHub account first.")
            return
        if not self._repo_exists(user, repo):
            self.github_status.configure(
                text=f"Repo does not exist yet: {user}/{repo}\nClick 'Create Repo + Set Remote' to create it."
            )
            return

        url = self._target_repo_url()
        result = self._set_origin_remote(url)
        if result.returncode == 0:
            self._refresh_github_status()
        else:
            self.github_status.configure(text=f"Could not update git remote:\n{result.stderr.strip()}")

    def _create_repo_and_set_remote(self):
        """Create repo under selected account if missing, then set origin."""
        user = self._selected_github_user()
        repo = self._current_repo_name()
        if not user:
            self.github_status.configure(text="Select or connect a GitHub account first.")
            return

        if self._active_github_user() != user:
            switch = subprocess.run(
                ["gh", "auth", "switch", "--hostname", "github.com", "--user", user],
                capture_output=True,
                text=True,
                timeout=20,
            )
            if switch.returncode != 0:
                self.github_status.configure(text=f"Could not switch GitHub account:\n{switch.stderr.strip()}")
                return

        if not self._repo_exists(user, repo):
            create = subprocess.run(
                ["gh", "repo", "create", f"{user}/{repo}", "--private"],
                capture_output=True,
                text=True,
                cwd=os.getcwd(),
                timeout=60,
            )
            if create.returncode != 0 and "already exists" not in create.stderr.lower():
                self.github_status.configure(text=f"Could not create repo:\n{create.stderr.strip()}")
                return

        result = self._set_origin_remote(self._target_repo_url())
        if result.returncode == 0:
            self._refresh_github_status()
        else:
            self.github_status.configure(text=f"Could not update git remote:\n{result.stderr.strip()}")

    def _github_status_text(self) -> str:
        """Return GitHub CLI and current repository status text."""
        try:
            auth = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=8,
            )
            auth_text = "GitHub: connected" if auth.returncode == 0 else "GitHub: not connected"
        except FileNotFoundError:
            return "GitHub CLI not found. Install gh first: https://cli.github.com/"
        except Exception as e:
            return f"GitHub status error: {e}"

        remote_url = self._git_remote_url()
        repo_text = remote_url or "No git remote found for this folder"

        accounts = self._github_accounts()
        if accounts:
            active = next((account["user"] for account in accounts if account["active"]), accounts[0]["user"])
            account_text = f"Active account: {active}"
            if len(accounts) > 1:
                account_text += f" ({len(accounts)} accounts available)"
        else:
            account_text = "Active account: unknown"

        warning = ""
        selected_or_active = self._selected_github_user() or self._active_github_user()
        remote_owner = self._remote_owner(remote_url)
        if remote_owner and selected_or_active and remote_owner.lower() != selected_or_active.lower():
            warning = f"\nWARNING: remote owner is {remote_owner}, not selected account {selected_or_active}."

        return f"{auth_text}\n{account_text}\nRepository: {repo_text}{warning}"

    def _refresh_github_status(self):
        """Refresh GitHub connection status."""
        if hasattr(self, "github_status"):
            self.github_status.configure(text=self._github_status_text())
        if hasattr(self, "github_account_menu"):
            accounts = self._github_accounts()
            if accounts:
                self.github_account_menu.configure(values=[account["user"] for account in accounts])
                active = next((account["user"] for account in accounts if account["active"]), accounts[0]["user"])
                self.github_account_menu.set(active)

    def _connect_github(self):
        """Connect GitHub using the GitHub CLI."""
        try:
            auth = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=8,
            )
            if auth.returncode == 0:
                self._refresh_github_status()
                return
        except FileNotFoundError:
            if hasattr(self, "github_status"):
                self.github_status.configure(text="GitHub CLI not found. Install gh first: https://cli.github.com/")
            return

        try:
            subprocess.Popen(
                ["powershell", "-NoExit", "-Command", "gh auth login"],
                cwd=os.getcwd(),
            )
            if hasattr(self, "github_status"):
                self.github_status.configure(
                    text="GitHub login opened in a PowerShell window. Finish login there, then click Refresh."
                )
        except Exception as e:
            if hasattr(self, "github_status"):
                self.github_status.configure(text=f"Could not start GitHub login: {e}")

    def _create_api_keys_section(self, parent):
        """Create API keys section."""
        section = self._create_section(parent, "API Keys", row=3)

        import os

        # Anthropic API Key
        self._create_input(section, "Anthropic (Claude):", "anthropic_api_key",
                          os.getenv("ANTHROPIC_API_KEY", ""), row=0)

        # OpenAI API Key. Codex uses `codex login`; this is only for API-backed GPT modes.
        self._create_input(section, "OpenAI API (GPT):", "openai_api_key",
                          os.getenv("OPENAI_API_KEY", ""), row=1)

        # Google API Key
        self._create_input(section, "Google (Gemini):", "google_api_key",
                          os.getenv("GOOGLE_API_KEY", ""), row=2)

        # Note
        note = ctk.CTkLabel(
            section,
            text="API keys are stored in environment variables. Codex uses codex login.",
            font=ctk.CTkFont(size=10),
            text_color="gray60"
        )
        note.grid(row=4, column=0, columnspan=2, padx=15, pady=(0, 10), sticky="w")

    # -----------------------------------------------------------------------
    # AI Agent Credentials
    # -----------------------------------------------------------------------

    def _create_custom_endpoint_section(self, parent):
        """AI Agent Credentials — per-agent key/token/URL store with mode selector."""
        from sage.gui.credential_store import AGENT_SPECS, using_keyring

        section = self._create_section(parent, "AI Agent Credentials", row=4)
        section.grid_columnconfigure(1, weight=1)

        storage_note = "🔒 Windows Credential Manager" if using_keyring() else "📄 ~/.sage/.credentials (base64)"
        desc = ctk.CTkLabel(
            section,
            text=(
                f"Store API keys, tokens, and URLs for any AI agent. "
                f"Injected into the environment on every SAGE launch.  Storage: {storage_note}"
            ),
            font=ctk.CTkFont(size=11),
            text_color="gray60",
            anchor="w",
            justify="left",
            wraplength=800,
        )
        desc.grid(row=0, column=0, columnspan=3, padx=15, pady=(6, 10), sticky="ew")

        # ── Agent selector ──────────────────────────────────────────────────
        agent_frame = ctk.CTkFrame(section, fg_color="transparent")
        agent_frame.grid(row=1, column=0, columnspan=3, padx=15, pady=(0, 4), sticky="ew")

        ctk.CTkLabel(agent_frame, text="Agent:", font=ctk.CTkFont(size=12), width=110, anchor="w").pack(side="left")

        agent_names = list(AGENT_SPECS.keys())
        self._cred_agent_var = ctk.StringVar(value=agent_names[0])
        agent_menu = ctk.CTkOptionMenu(
            agent_frame,
            values=agent_names,
            variable=self._cred_agent_var,
            command=self._on_cred_agent_changed,
            width=260,
            font=ctk.CTkFont(size=12),
        )
        agent_menu.pack(side="left", padx=(6, 0))

        # ── Auth mode selector (hidden when only one mode) ───────────────────
        self._cred_mode_frame = ctk.CTkFrame(section, fg_color="transparent")
        self._cred_mode_frame.grid(row=2, column=0, columnspan=3, padx=15, pady=(0, 4), sticky="ew")

        ctk.CTkLabel(self._cred_mode_frame, text="Auth mode:", font=ctk.CTkFont(size=12), width=110, anchor="w").pack(side="left")

        self._cred_mode_var = ctk.StringVar()
        self._cred_mode_menu = ctk.CTkOptionMenu(
            self._cred_mode_frame,
            variable=self._cred_mode_var,
            command=self._on_cred_mode_changed,
            width=260,
            font=ctk.CTkFont(size=12),
        )
        self._cred_mode_menu.pack(side="left", padx=(6, 0))

        # ── Dynamic fields container ─────────────────────────────────────────
        self._cred_fields_frame = ctk.CTkFrame(section, fg_color="transparent")
        self._cred_fields_frame.grid(row=3, column=0, columnspan=3, padx=15, pady=(4, 4), sticky="ew")
        self._cred_fields_frame.grid_columnconfigure(1, weight=1)

        # ── Action row ───────────────────────────────────────────────────────
        action_row = ctk.CTkFrame(section, fg_color="transparent")
        action_row.grid(row=4, column=0, columnspan=3, padx=15, pady=(6, 10), sticky="ew")

        self._cred_status = ctk.CTkLabel(
            action_row, text="", font=ctk.CTkFont(size=11), text_color="gray60", anchor="w",
        )
        self._cred_status.pack(side="left", fill="x", expand=True)

        clear_btn = ctk.CTkButton(
            action_row, text="Clear", width=80,
            fg_color="gray35", hover_color="gray28",
            command=self._clear_agent_creds,
        )
        clear_btn.pack(side="right", padx=(6, 0))

        save_btn = ctk.CTkButton(
            action_row, text="Save & Apply", width=130,
            command=self._save_agent_creds,
        )
        save_btn.pack(side="right")

        self._cred_field_vars: dict[str, ctk.StringVar] = {}
        self._cred_field_entries: dict[str, ctk.CTkEntry] = {}
        self._rebuild_cred_ui()

    def _on_cred_agent_changed(self, _agent: str) -> None:
        self._rebuild_cred_ui()

    def _on_cred_mode_changed(self, _mode: str) -> None:
        self._rebuild_cred_fields()

    def _rebuild_cred_ui(self) -> None:
        from sage.gui.credential_store import AGENT_SPECS
        agent = self._cred_agent_var.get()
        modes = list(AGENT_SPECS[agent]["modes"].keys())
        if len(modes) > 1:
            self._cred_mode_menu.configure(values=modes)
            self._cred_mode_var.set(modes[0])
            self._cred_mode_frame.grid()
        else:
            self._cred_mode_var.set(modes[0])
            self._cred_mode_frame.grid_remove()
        self._rebuild_cred_fields()

    def _rebuild_cred_fields(self) -> None:
        from sage.gui.credential_store import AGENT_SPECS, get_credential

        # clear old widgets
        for w in self._cred_fields_frame.winfo_children():
            w.destroy()
        self._cred_field_vars.clear()
        self._cred_field_entries.clear()
        self._cred_status.configure(text="")

        agent = self._cred_agent_var.get()
        mode = self._cred_mode_var.get()
        spec = AGENT_SPECS[agent]["modes"][mode]
        fields = spec.get("fields", [])

        if not fields:
            # OAuth / CLI / Web Login mode — show description + optional launch button
            desc_text = spec.get("description", "")
            if desc_text:
                ctk.CTkLabel(
                    self._cred_fields_frame, text=desc_text,
                    font=ctk.CTkFont(size=11), text_color="gray60",
                    anchor="w", wraplength=740,
                ).grid(row=0, column=0, columnspan=3, pady=(4, 6), sticky="ew")

            action = spec.get("action")
            if action:
                def _launch(a=action):
                    import subprocess
                    try:
                        subprocess.Popen(
                            ["powershell", "-NoLogo", "-NoExit", "-Command", a],
                            creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
                        )
                        self._cred_status.configure(
                            text=f"Opened: {a}", text_color="gray60"
                        )
                    except Exception as exc:
                        self._cred_status.configure(text=str(exc), text_color="#fca5a5")

                ctk.CTkButton(
                    self._cred_fields_frame, text=f"Open Login Terminal  →  {action}",
                    command=_launch, width=340,
                ).grid(row=1, column=0, columnspan=3, pady=(4, 4), sticky="w")
            return

        for i, field in enumerate(fields):
            label_text = field["label"] + ("  (optional)" if field.get("optional") else "") + ":"
            ctk.CTkLabel(
                self._cred_fields_frame, text=label_text,
                font=ctk.CTkFont(size=12), anchor="w", width=180,
            ).grid(row=i, column=0, padx=(0, 8), pady=5, sticky="w")

            stored = get_credential(agent, field["env"])
            var = ctk.StringVar(value=stored)
            self._cred_field_vars[field["env"]] = var

            entry = ctk.CTkEntry(
                self._cred_fields_frame,
                textvariable=var,
                show="•" if field.get("secret") else "",
                placeholder_text=field.get("placeholder", ""),
                font=ctk.CTkFont(size=12),
            )
            entry.grid(row=i, column=1, padx=(0, 6), pady=5, sticky="ew")
            self._cred_field_entries[field["env"]] = entry

            if field.get("secret"):
                sv = ctk.BooleanVar(value=False)
                ctk.CTkCheckBox(
                    self._cred_fields_frame, text="Show", variable=sv, width=60,
                    font=ctk.CTkFont(size=11),
                    command=lambda e=entry, s=sv: e.configure(show="" if s.get() else "•"),
                ).grid(row=i, column=2, pady=5, sticky="w")

    def _save_agent_creds(self) -> None:
        from sage.gui.credential_store import AGENT_SPECS, delete_credential, set_credential

        agent = self._cred_agent_var.get()
        mode = self._cred_mode_var.get()
        spec = AGENT_SPECS[agent]["modes"][mode]
        inject = spec.get("inject", False)
        saved = []

        for field in spec.get("fields", []):
            env = field["env"]
            val = self._cred_field_vars.get(env, ctk.StringVar()).get().strip()
            if val:
                set_credential(agent, env, val)
                if inject:
                    os.environ[env] = val
                saved.append(env)
            else:
                delete_credential(agent, env)
                os.environ.pop(env, None)

        if saved:
            self._cred_status.configure(
                text=f"✅ Saved {len(saved)} field(s) — active immediately",
                text_color="#4ade80",
            )
        else:
            self._cred_status.configure(text="➖ All fields cleared", text_color="gray60")

    def _clear_agent_creds(self) -> None:
        from sage.gui.credential_store import AGENT_SPECS, delete_credential

        agent = self._cred_agent_var.get()
        mode = self._cred_mode_var.get()
        spec = AGENT_SPECS[agent]["modes"][mode]

        for field in spec.get("fields", []):
            env = field["env"]
            delete_credential(agent, env)
            os.environ.pop(env, None)
            if env in self._cred_field_vars:
                self._cred_field_vars[env].set("")

        self._cred_status.configure(text="➖ Cleared", text_color="gray60")

    def _create_api_travel_section(self, parent):
        """API-Travel — auto-select best available agent per message."""
        section = self._create_section(parent, "API-Travel", row=5)

        desc = ctk.CTkLabel(
            section,
            text=(
                "API-Travel automatically routes each message to the best available agent, "
                "sharing session memory across all connected AI tools. "
                "Falls back silently to the selected AI if routing fails."
            ),
            font=ctk.CTkFont(size=11),
            text_color="gray65",
            anchor="w",
            wraplength=780,
            justify="left",
        )
        desc.grid(row=1, column=0, columnspan=2, padx=15, pady=(0, 8), sticky="ew")

        enabled = getattr(self.parent_app, "_api_travel_enabled", True)
        self._api_travel_switch = ctk.CTkSwitch(
            section,
            text="Enable API-Travel  (auto-select best available agent)",
            font=ctk.CTkFont(size=12),
            command=self._on_api_travel_toggle,
        )
        if enabled:
            self._api_travel_switch.select()
        self._api_travel_switch.grid(row=2, column=0, columnspan=2, padx=15, pady=(0, 8), sticky="w")

        status_row = ctk.CTkFrame(section, fg_color="transparent")
        status_row.grid(row=3, column=0, columnspan=2, padx=15, pady=(0, 12), sticky="ew")
        status_row.grid_columnconfigure(0, weight=1)

        self._api_travel_status = ctk.CTkLabel(
            status_row,
            text="Checking agents…",
            font=ctk.CTkFont(size=11),
            text_color="gray55",
            anchor="w",
            justify="left",
        )
        self._api_travel_status.grid(row=0, column=0, sticky="w")

        refresh_btn = ctk.CTkButton(
            status_row,
            text="Check Now",
            width=90,
            fg_color="gray35",
            hover_color="gray28",
            font=ctk.CTkFont(size=11),
            command=lambda: threading.Thread(
                target=self._refresh_api_travel_status, daemon=True
            ).start(),
        )
        refresh_btn.grid(row=0, column=1, padx=(8, 0), sticky="e")

        threading.Thread(target=self._refresh_api_travel_status, daemon=True).start()

    def _on_api_travel_toggle(self):
        try:
            self.parent_app._api_travel_enabled = bool(self._api_travel_switch.get())
        except Exception:
            pass

    def _refresh_api_travel_status(self):
        """Run in a background thread — schedules all widget updates on the main thread."""
        try:
            from sage.gui import api_travel
            available = api_travel.detect_available(force=True)
            if available:
                parts = [f"\U0001f7e2 {name.capitalize()}" for name in available]
                text = "Available:   " + "    ·    ".join(parts)
            else:
                text = "⚫ No agents detected — check that at least one AI tool is running"
            color = "gray65"
        except Exception as exc:
            text = f"Detection failed: {exc}"
            color = "#fca5a5"
        # Must update Tkinter widgets on the main thread
        try:
            self.after(0, lambda t=text, c=color: self._api_travel_status.configure(
                text=t, text_color=c
            ))
        except Exception:
            pass

    def _create_mcp_section(self, parent):
        """Create MCP servers section with a real 'connect to any MCP server' input."""
        section = self._create_section(parent, "MCP Servers", row=6)

        # SAGE's own MCP server command (exposes SAGE tools to clients).
        self._create_input(section, "SAGE MCP Command:", "mcp_server_cmd",
                          self.config.get("mcp_server_cmd", "sage mcp"), row=0)
        self._create_switch(section, "Auto-start SAGE MCP server", "mcp_auto_start",
                           self.config.get("mcp_auto_start", True), row=1)

        note = ctk.CTkLabel(
            section,
            text=(
                "Connect to ANY external MCP server. Use a stdio command "
                "(e.g. npx -y @modelcontextprotocol/server-filesystem .) or an "
                "http(s):// endpoint. SAGE runs the real initialize + tools/list "
                "handshake and shows the discovered tools."
            ),
            font=ctk.CTkFont(size=11),
            text_color="gray60",
            anchor="w",
            justify="left",
            wraplength=780,
        )
        note.grid(row=3, column=0, columnspan=2, padx=15, pady=(6, 6), sticky="ew")

        name_label = ctk.CTkLabel(
            section, text="Server Name:", font=ctk.CTkFont(size=12), anchor="w", width=150
        )
        name_label.grid(row=4, column=0, padx=15, pady=6, sticky="w")
        self.mcp_new_name_entry = ctk.CTkEntry(section, placeholder_text="my-server", font=ctk.CTkFont(size=12))
        self.mcp_new_name_entry.grid(row=4, column=1, padx=(10, 15), pady=6, sticky="ew")

        target_label = ctk.CTkLabel(
            section, text="Command / URL:", font=ctk.CTkFont(size=12), anchor="w", width=150
        )
        target_label.grid(row=5, column=0, padx=15, pady=6, sticky="w")
        self.mcp_new_target_entry = ctk.CTkEntry(
            section,
            placeholder_text="python -m sage.mcp.server  |  npx -y @modelcontextprotocol/server-filesystem .  |  https://host/mcp",
            font=ctk.CTkFont(size=12),
        )
        self.mcp_new_target_entry.grid(row=5, column=1, padx=(10, 15), pady=6, sticky="ew")

        actions = ctk.CTkFrame(section, fg_color="transparent")
        actions.grid(row=6, column=0, columnspan=2, padx=15, pady=(4, 6), sticky="ew")

        self.mcp_connect_btn = ctk.CTkButton(
            actions, text="Test & Connect", command=self._connect_mcp_server, width=150
        )
        self.mcp_connect_btn.pack(side="left", padx=(0, 8))

        remove_btn = ctk.CTkButton(
            actions,
            text="Remove Selected",
            command=self._remove_selected_mcp_server,
            width=150,
            fg_color="#7f1d1d",
            hover_color="#6b1515",
        )
        remove_btn.pack(side="left")

        saved = self.config.get("mcp_servers", {})
        self.mcp_saved_menu = ctk.CTkOptionMenu(
            actions,
            values=list(saved.keys()) or ["(none saved)"],
            width=200,
        )
        self.mcp_saved_menu.set(next(iter(saved), "(none saved)"))
        self.mcp_saved_menu.pack(side="left", padx=(8, 0))

        self.mcp_status = ctk.CTkLabel(
            section,
            text=self._mcp_status_text(),
            font=ctk.CTkFont(size=11),
            text_color="gray65",
            anchor="w",
            justify="left",
            wraplength=780,
        )
        self.mcp_status.grid(row=7, column=0, columnspan=2, padx=15, pady=(4, 12), sticky="ew")

    def _mcp_status_text(self) -> str:
        saved = self.config.get("mcp_servers", {})
        if not saved:
            return "No external MCP servers connected yet."
        lines = ["Connected MCP servers:"]
        for name, info in saved.items():
            tools = info.get("tool_count", 0)
            lines.append(f"  {name} [{info.get('transport', '?')}] — {tools} tools")
        return "\n".join(lines)

    def _connect_mcp_server(self):
        """Run the real MCP handshake in a worker thread and save on success."""
        name = self.mcp_new_name_entry.get().strip()
        target = self.mcp_new_target_entry.get().strip()
        if not target:
            self.mcp_status.configure(text="Enter a command or URL to connect.", text_color="#fca5a5")
            return
        if not name:
            name = target.split()[0].rsplit("/", 1)[-1].rsplit("\\", 1)[-1] or "mcp-server"

        self.mcp_connect_btn.configure(state="disabled", text="Connecting...")
        self.mcp_status.configure(text=f"Connecting to '{name}'...", text_color="gray65")

        def worker():
            try:
                from sage.mcp.client import connect_and_list

                result = connect_and_list(target, timeout=12.0)
            except Exception as exc:
                message = str(exc)
                self.after(0, lambda msg=message: self._finish_mcp_connect(name, target, None, msg))
                return
            self.after(0, lambda: self._finish_mcp_connect(name, target, result, ""))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_mcp_connect(self, name: str, target: str, result, error: str):
        self.mcp_connect_btn.configure(state="normal", text="Test & Connect")
        if error or result is None or not result.ok:
            reason = error or (result.error if result else "unknown error")
            transport = getattr(result, "transport", None) or "MCP"
            self.mcp_status.configure(
                text=(
                    f"Could not connect to '{name}' ({transport}): {reason}\n"
                    "Check that the target is a real MCP server command or URL supported by the connected AI client."
                ),
                text_color="#fca5a5",
            )
            return

        servers = dict(self.config.get("mcp_servers", {}))
        servers[name] = {
            "target": target,
            "transport": result.transport,
            "server_name": result.server_name,
            "server_version": result.server_version,
            "tool_count": len(result.tools),
            "tools": result.tool_names[:64],
        }
        self.config.set("mcp_servers", servers)

        tool_preview = ", ".join(result.tool_names[:8]) or "(no tools advertised)"
        self.mcp_status.configure(
            text=(
                f"Connected '{name}' via {result.transport} — "
                f"{result.server_name or 'server'} {result.server_version}\n"
                f"{len(result.tools)} tools: {tool_preview}"
            ),
            text_color="#86efac",
        )
        if hasattr(self, "mcp_saved_menu"):
            self.mcp_saved_menu.configure(values=list(servers.keys()))
            self.mcp_saved_menu.set(name)

    def _remove_selected_mcp_server(self):
        if not hasattr(self, "mcp_saved_menu"):
            return
        name = self.mcp_saved_menu.get()
        servers = dict(self.config.get("mcp_servers", {}))
        if name in servers:
            servers.pop(name)
            self.config.set("mcp_servers", servers)
            self.mcp_saved_menu.configure(values=list(servers.keys()) or ["(none saved)"])
            self.mcp_saved_menu.set(next(iter(servers), "(none saved)"))
            self.mcp_status.configure(text=self._mcp_status_text(), text_color="gray65")

    def _create_ai_commands_section(self, parent):
        """Create AI commands section."""
        section = self._create_section(parent, "AI Commands", row=5)

        ai_commands = self.config.get("ai_commands", {})
        for i, (ai_name, cmd) in enumerate(ai_commands.items()):
            self._create_input(section, f"{ai_name.upper()}:", f"ai_cmd_{ai_name}",
                              cmd, row=i)

    def _create_prompts_section(self, parent):
        """Create system prompts section."""
        section = self._create_section(parent, "System Prompts", row=7)

        # Claude prompts
        prompts = self.config.get_system_prompts("claude")
        prompt_text = "\n".join(prompts) if prompts else ""
        self._create_textarea(section, "Claude Prompts:", "claude_prompts",
                             prompt_text, row=0)

    def _create_runtime_section(self, parent):
        """Create runtime behavior settings."""
        section = self._create_section(parent, "Runtime", row=8)
        self._create_switch(
            section,
            "Run AI inside SAGE terminal",
            "run_in_embedded_terminal",
            self.config.get("run_in_embedded_terminal", True),
            row=0,
        )
        self._create_switch(
            section,
            "Run AI in separate terminal window",
            "run_in_external_terminal",
            self.config.get("run_in_external_terminal", False),
            row=1,
        )

        note = ctk.CTkLabel(
            section,
            text="Embedded terminal streams the real SAGE CLI output inside the desktop. Separate terminal opens a PowerShell window instead.",
            font=ctk.CTkFont(size=11),
            text_color="gray60",
            anchor="w",
            justify="left",
            wraplength=760,
        )
        note.grid(row=3, column=0, columnspan=2, padx=15, pady=(0, 12), sticky="ew")

    def _create_danger_zone_section(self, parent):
        """Create reset/delete controls for local SAGE data."""
        section = self._create_section(parent, "Reset / Delete", row=9)

        note = ctk.CTkLabel(
            section,
            text=(
                "Reset clears only the visible dashboard counters. "
                "Delete removes the local SAGE profile and database after confirmation."
            ),
            font=ctk.CTkFont(size=11),
            text_color="gray60",
            anchor="w",
            justify="left",
            wraplength=760,
        )
        note.grid(row=1, column=0, columnspan=2, padx=15, pady=(0, 10), sticky="ew")

        actions = ctk.CTkFrame(section, fg_color="transparent")
        actions.grid(row=2, column=0, columnspan=2, padx=15, pady=(0, 15), sticky="ew")

        reset_btn = ctk.CTkButton(
            actions,
            text="Reset Dashboard Cards to 0",
            command=self._reset_dashboard,
            width=210,
            fg_color="#52525b",
            hover_color="#3f3f46",
        )
        reset_btn.pack(side="left", padx=(0, 10))

        delete_btn = ctk.CTkButton(
            actions,
            text="Delete Profile + Database",
            command=self._delete_profile_database,
            width=210,
            fg_color="#b91c1c",
            hover_color="#991b1b",
        )
        delete_btn.pack(side="left")

        self.danger_status = ctk.CTkLabel(
            section,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray65",
            anchor="w",
        )
        self.danger_status.grid(row=3, column=0, columnspan=2, padx=15, pady=(0, 12), sticky="ew")

    def _reset_dashboard(self):
        """Ask the main app to reset dashboard data."""
        if hasattr(self.parent_app, "reset_dashboard_data") and self.parent_app.reset_dashboard_data():
            self.danger_status.configure(text="Dashboard cards reset to 0.")

    def _delete_profile_database(self):
        """Ask the main app to delete local profile/database data."""
        if hasattr(self.parent_app, "delete_all_profile_data") and self.parent_app.delete_all_profile_data():
            self.danger_status.configure(text="Profile and database deleted. Closing settings.")
            self.after(700, self.destroy)

    def _create_section(self, parent, title: str, row: int):
        """Create a settings section."""
        section = ctk.CTkFrame(parent, fg_color="gray15", corner_radius=10)
        section.grid(row=row, column=0, padx=10, pady=(0, 15), sticky="ew")
        section.grid_columnconfigure(1, weight=1)

        # Section header
        header = ctk.CTkLabel(
            section,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        header.grid(row=0, column=0, columnspan=2, padx=15, pady=(15, 10), sticky="w")

        return section

    def _create_input(self, parent, label: str, key: str, value: str, row: int):
        """Create a label + input field."""
        label_widget = ctk.CTkLabel(
            parent,
            text=label,
            font=ctk.CTkFont(size=12),
            anchor="w",
            width=150
        )
        label_widget.grid(row=row+1, column=0, padx=15, pady=8, sticky="w")

        entry = ctk.CTkEntry(
            parent,
            placeholder_text=label,
            font=ctk.CTkFont(size=12)
        )
        entry.insert(0, value)
        entry.grid(row=row+1, column=1, padx=(10, 15), pady=8, sticky="ew")

        # Store reference
        if not hasattr(self, '_inputs'):
            self._inputs = {}
        self._inputs[key] = entry

    def _create_textarea(self, parent, label: str, key: str, value: str, row: int):
        """Create a label + textarea."""
        label_widget = ctk.CTkLabel(
            parent,
            text=label,
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        label_widget.grid(row=row+1, column=0, columnspan=2, padx=15, pady=(8, 5), sticky="w")

        textbox = ctk.CTkTextbox(
            parent,
            height=80,
            font=ctk.CTkFont(size=11)
        )
        textbox.insert("1.0", value)
        textbox.grid(row=row+2, column=0, columnspan=2, padx=15, pady=(0, 10), sticky="ew")

        # Store reference
        if not hasattr(self, '_textareas'):
            self._textareas = {}
        self._textareas[key] = textbox

    def _create_switch(self, parent, label: str, key: str, value: bool, row: int):
        """Create a label + switch."""
        switch = ctk.CTkSwitch(
            parent,
            text=label,
            font=ctk.CTkFont(size=12)
        )
        if value:
            switch.select()
        switch.grid(row=row+1, column=0, columnspan=2, padx=15, pady=8, sticky="w")

        # Store reference
        if not hasattr(self, '_switches'):
            self._switches = {}
        self._switches[key] = switch

    def _create_buttons(self):
        """Create Save and Cancel buttons."""
        buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        buttons_frame.grid(row=2, column=0, padx=30, pady=(10, 20), sticky="ew")

        # Cancel button
        cancel_btn = ctk.CTkButton(
            buttons_frame,
            text="Cancel",
            command=self.destroy,
            width=120,
            fg_color="gray40",
            hover_color="gray30"
        )
        cancel_btn.pack(side="right", padx=5)

        # Save button
        save_btn = ctk.CTkButton(
            buttons_frame,
            text="Save Settings",
            command=self._save_settings,
            width=120,
            font=ctk.CTkFont(weight="bold")
        )
        save_btn.pack(side="right", padx=5)

    def _save_settings(self):
        """Save all settings to config."""
        import os

        # Save input fields
        if hasattr(self, '_inputs'):
            for key, entry in self._inputs.items():
                value = entry.get()

                # Handle API keys - set env vars
                if key == "anthropic_api_key" and value:
                    os.environ["ANTHROPIC_API_KEY"] = value
                elif key == "openai_api_key" and value:
                    os.environ["OPENAI_API_KEY"] = value
                elif key == "google_api_key" and value:
                    os.environ["GOOGLE_API_KEY"] = value
                # Handle AI commands
                elif key.startswith("ai_cmd_"):
                    ai_name = key.replace("ai_cmd_", "")
                    ai_commands = self.config.get("ai_commands", {})
                    ai_commands[ai_name] = value
                    self.config.set("ai_commands", ai_commands)
                else:
                    self.config.set(key, value)

        # Save textareas
        if hasattr(self, '_textareas'):
            for key, textbox in self._textareas.items():
                value = textbox.get("1.0", "end-1c")
                if key == "claude_prompts":
                    prompts = [p.strip() for p in value.split("\n") if p.strip()]
                    system_prompts = self.config.get("system_prompts", {})
                    system_prompts["claude"] = prompts
                    self.config.set("system_prompts", system_prompts)

        # Save switches
        if hasattr(self, '_switches'):
            for key, switch in self._switches.items():
                self.config.set(key, switch.get() == 1)

        self.config.save()
        self.destroy()
