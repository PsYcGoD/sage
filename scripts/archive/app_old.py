"""SAGE Desktop GUI - Main Application"""

import customtkinter as ctk
from sage.gui.widgets.metric_card import MetricCard
from sage.gui.widgets.ai_selector import AISelector
from sage.gui.widgets.input_area import InputArea
from sage.gui.widgets.output_view import OutputView
from sage.gui.config import GUIConfig
from sage.store import connect
import threading
from pathlib import Path
from PIL import Image
import subprocess
import sys


class SAGEApp(ctk.CTk):
    """Main SAGE Desktop GUI Application"""

    def __init__(self):
        super().__init__()

        # Window configuration
        self.title("SAGE Desktop - Smart Agent Guidance Engine")
        self.geometry("900x700")

        # Set window icon (Windows .ico format)
        icon_path = Path(__file__).parent / "assets" / "sage-icon.ico"
        if icon_path.exists():
            self.iconbitmap(str(icon_path))

        # Set appearance mode and color theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Configure grid layout
        self.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header label
        self.header = ctk.CTkLabel(
            self,
            text="🧠 SAGE Desktop",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.header.grid(row=0, column=0, columnspan=4, padx=20, pady=(20, 10), sticky="w")

        # Create metric cards
        self.create_metric_cards()

        # Load configuration
        self.config = GUIConfig()

        # Create AI selector
        self.ai_selector = AISelector(
            self,
            default_ai=self.config.get_default_ai(),
            callback=self.on_ai_changed
        )
        self.ai_selector.grid(row=1, column=0, columnspan=4, padx=20, pady=(10, 5), sticky="ew")

        # Create input area
        self.input_area = InputArea(
            self,
            on_send=self.on_send_command,
            on_clear=self.on_clear_output,
            on_settings=self.on_open_settings
        )
        self.input_area.grid(row=2, column=0, columnspan=4, padx=20, pady=5, sticky="ew")

        # Create output view
        self.output_view = OutputView(self)
        self.output_view.grid(row=3, column=0, columnspan=4, padx=20, pady=(5, 20), sticky="nsew")

        # Configure grid weights for output area to expand
        self.grid_rowconfigure(3, weight=1)

        # Current AI process
        self.current_process = None

        # Start periodic updates
        self.update_running = True
        self.update_metrics()

    def create_metric_cards(self):
        """Create the 4 metric cards at the top of the window"""

        # Total Commands card
        self.commands_card = MetricCard(
            self,
            label="📊 Commands",
            value="Loading...",
            subtitle="",
            width=200,
            height=120
        )
        self.commands_card.grid(row=1, column=0, padx=(20, 10), pady=20, sticky="nsew")

        # Token Savings card
        self.tokens_card = MetricCard(
            self,
            label="⚡ Tokens",
            value="Loading...",
            subtitle="",
            width=200,
            height=120
        )
        self.tokens_card.grid(row=1, column=1, padx=10, pady=20, sticky="nsew")

        # Active Agents card
        self.agents_card = MetricCard(
            self,
            label="🤖 Agents",
            value="Loading...",
            subtitle="",
            width=200,
            height=120
        )
        self.agents_card.grid(row=1, column=2, padx=10, pady=20, sticky="nsew")

        # Success Rate card
        self.success_card = MetricCard(
            self,
            label="✅ Success",
            value="Loading...",
            subtitle="",
            width=200,
            height=120
        )
        self.success_card.grid(row=1, column=3, padx=(10, 20), pady=20, sticky="nsew")

    def update_metrics(self):
        """Query database and update metric cards"""
        if not self.update_running:
            return

        try:
            # Run database queries in a separate thread to avoid blocking UI
            threading.Thread(target=self._fetch_and_update_metrics, daemon=True).start()
        except Exception as e:
            self.status_label.configure(text=f"Error: {e}")

        # Schedule next update in 2 seconds
        self.after(2000, self.update_metrics)

    def _fetch_and_update_metrics(self):
        """Fetch metrics from database and update UI (runs in separate thread)"""
        try:
            conn = connect()
            cursor = conn.cursor()

            # 1. Total Commands
            result = cursor.execute("SELECT COUNT(*) FROM runs").fetchone()
            total_commands = result[0] if result else 0

            # 2. Token Savings (Note: token_usage table doesn't exist yet in schema)
            # For now, we'll show a placeholder
            token_savings = 0
            token_rate = 0.0

            # 3. Active Agents
            result = cursor.execute("SELECT COUNT(*) FROM agents WHERE status='busy'").fetchone()
            active_agents = result[0] if result else 0

            # 4. Success Rate
            result = cursor.execute(
                "SELECT AVG(CASE WHEN exit_code=0 THEN 1.0 ELSE 0.0 END) FROM runs"
            ).fetchone()
            success_rate = result[0] if result and result[0] is not None else 0.0

            conn.close()

            # Update UI on main thread
            self.after(0, lambda: self._update_ui_metrics(
                total_commands,
                token_savings,
                token_rate,
                active_agents,
                success_rate
            ))

        except Exception as e:
            self.after(0, lambda: self.status_label.configure(text=f"DB Error: {e}"))

    def _update_ui_metrics(self, total_commands, token_savings, token_rate, active_agents, success_rate):
        """Update metric card UI elements (must run on main thread)"""

        # Update Commands card
        self.commands_card.update_value(
            value=f"{total_commands}",
            subtitle="Total"
        )

        # Update Tokens card
        if token_savings > 0:
            self.tokens_card.update_value(
                value=f"{token_savings:,}",
                subtitle=f"{token_rate:.1f}% Rate"
            )
        else:
            self.tokens_card.update_value(
                value="0",
                subtitle="Saved"
            )

        # Update Agents card
        self.agents_card.update_value(
            value=f"{active_agents}",
            subtitle="Active"
        )

        # Update Success card
        self.success_card.update_value(
            value=f"{success_rate * 100:.1f}%",
            subtitle="Success Rate"
        )

        self.status_label.configure(text=f"Updated at {self._get_timestamp()}")

    def _get_timestamp(self):
        """Get current time as string"""
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")

    def on_ai_changed(self, ai_name: str):
        """Callback when AI selection changes"""
        self.output_view.append_text(f"Switched to {ai_name}\n", "info")

    def on_send_command(self, command: str):
        """Handle send button click"""
        if not command.strip():
            return

        # Get selected AI
        ai_name = self.ai_selector.get_selected()
        self.output_view.append_text(f"\n{'='*60}\n", "info")
        self.output_view.append_thinking_block(f"Starting {ai_name}...")

        # Get AI command from config
        ai_cmd = self.config.get_ai_command(ai_name.lower())
        system_prompts = self.config.get_system_prompts(ai_name.lower())

        # Build command with system prompts
        full_cmd = [ai_cmd]
        for prompt_file in system_prompts:
            if Path(prompt_file).exists():
                full_cmd.extend(["--append-system-prompt-file", prompt_file])

        # Run AI in background thread
        threading.Thread(target=self._run_ai_process, args=(full_cmd, command), daemon=True).start()

    def _run_ai_process(self, cmd: list, prompt: str):
        """Run AI process and stream output"""
        try:
            # Start process
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )

            self.current_process = process

            # Send prompt
            process.stdin.write(prompt + "\n")
            process.stdin.flush()
            process.stdin.close()

            # Stream output
            self.output_view.append_running_block("Executing command...")
            for line in process.stdout:
                self.output_view.append_text(line, "running")

            # Wait for completion
            process.wait()

            if process.returncode == 0:
                self.output_view.append_complete_block("✓ Completed successfully")
            else:
                self.output_view.append_text(f"\nProcess exited with code {process.returncode}\n", "error")

        except Exception as e:
            self.output_view.append_text(f"\nError: {str(e)}\n", "error")
        finally:
            self.current_process = None

    def on_clear_output(self):
        """Handle clear button click"""
        self.output_view.clear()
        self.output_view.append_text("Output cleared.\n", "info")

    def on_open_settings(self):
        """Handle settings button click"""
        self.output_view.append_text("Settings panel coming soon...\n", "info")

    def on_closing(self):
        """Clean shutdown"""
        self.update_running = False
        if self.current_process:
            self.current_process.terminate()
        self.destroy()


def main():
    """Launch the SAGE Desktop GUI"""
    app = SAGEApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
