"""SAGE TUI main application."""
from __future__ import annotations

import os
import logging
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding

from .widgets.output import OutputPanel
from .widgets.input_bar import InputBar, InputSubmitted
from .widgets.status_bar import StatusBar
from .widgets.sidebar import Sidebar, SessionSelected, NewSessionRequested, SessionDeleteRequested, SettingsRequested
from .server.session_store import SessionStore
from .server.tools import ToolRegistry
from .server.context import ContextManager as ChatContext
from .server.providers.anthropic import AnthropicProvider
from .server.loop import AgenticLoop
from .server.migrate import migrate_if_needed
from .server import router

log = logging.getLogger(__name__)


def _get_display_name() -> str:
    """Get user's primary display name from SAGE config."""
    try:
        from sage.telemetry import load_config
        config = load_config()
        profile = config.get("api_profile", {})
        return (
            profile.get("display_name")
            or profile.get("username")
            or profile.get("github_username")
            or profile.get("email", "").split("@")[0]
            or "Me"
        )
    except Exception:
        return "Me"


class SAGETUIApp(App):
    """SAGE Terminal User Interface."""

    TITLE = "SAGE"
    CSS = """
    Screen {
        background: #1a1b26;
    }

    OutputPanel {
        background: #1a1b26;
        padding: 0 2;
    }

    OutputPanel .user-message {
        background: #1a1b26;
        color: #c084fc;
        padding: 0 0 1 0;
        margin: 1 0 0 0;
        border: none;
    }

    OutputPanel .assistant-message {
        background: #1a1b26;
        color: #ededec;
        padding: 0 0 1 0;
        margin: 0;
        border: none;
    }

    OutputPanel .thinking {
        color: #9b87f5;
        margin: 0;
        text-style: italic;
    }

    OutputPanel .error-message {
        background: #2d1b1b;
        border-left: thick #f87171;
        padding: 1 2;
        margin: 1 0;
        color: #f87171;
    }

    OutputPanel .sage-summary {
        color: #4ade80;
        margin: 0;
        padding: 0;
    }

    InputBar {
        dock: bottom;
        height: 3;
        border-top: solid #333648;
        border-bottom: none;
        border-left: none;
        border-right: none;
        background: #16161e;
    }

    InputBar:focus {
        border-top: solid #8b5cf6;
    }

    StatusBar {
        dock: bottom;
        height: 1;
        background: #16161e;
        color: #6b6b6b;
        content-align: center middle;
        border-top: solid #333648;
    }

    Sidebar {
        dock: left;
        width: 28;
        background: #16161e;
        border-right: solid #333648;
        padding: 0;
    }

    Sidebar .header {
        text-align: center;
        text-style: bold;
        color: #8b5cf6;
        padding: 1;
    }

    Sidebar #new-chat-btn {
        width: 100%;
        margin: 0 1 1 1;
        min-width: 10;
        background: #8b5cf6;
        color: #ededec;
        border: none;
        height: 1;
    }

    Sidebar #settings-btn {
        width: 100%;
        margin: 0 1 1 1;
        min-width: 10;
        background: #333648;
        color: #a0a0a0;
        border: none;
        height: 1;
    }

    Sidebar ListView {
        height: 1fr;
        background: #16161e;
        border: none;
    }

    Sidebar ListItem {
        padding: 0 1;
        height: 2;
        background: #16161e;
        border: none;
    }

    Sidebar ListItem:hover {
        background: #24283b;
    }

    Sidebar ListItem.--active {
        background: #24283b;
        border-left: thick #8b5cf6;
    }

    Collapsible {
        margin: 0;
        padding: 0;
        border: none;
        background: #1f2335;
    }

    CollapsibleTitle {
        color: #6b6b6b;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", priority=True),
        Binding("ctrl+d", "quit", "Quit", priority=True),
        Binding("ctrl+l", "clear_output", "Clear", priority=True),
        Binding("ctrl+c", "cancel", "Cancel", priority=True),
        Binding("ctrl+n", "new_session", "New Session", priority=True),
        Binding("escape", "try_quit", "Quit", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        
        # UI components
        self.output_panel = None
        self.input_bar = None
        self.status_bar = None
        self.sidebar = None
        
        # Server components
        self._store = SessionStore()
        self._tools = ToolRegistry()
        self._chat_context = ChatContext("claude-sonnet-4.6")
        self._provider = None
        self._loop = None
        self._current_session_id = None
        self._worker = None
        
        # Project context
        self._project_path = Path(os.getcwd()).resolve()
        self._project_name = self._project_path.name
        
        # Migrate old sessions on startup
        migrate_if_needed(self._store)

    def compose(self) -> ComposeResult:
        """Compose the app layout."""
        self.sidebar = Sidebar(self._project_name)
        self.output_panel = OutputPanel()
        self.input_bar = InputBar()
        self.status_bar = StatusBar()

        yield self.sidebar
        yield self.output_panel
        yield self.input_bar
        yield self.status_bar

    def on_mount(self) -> None:
        """Initialize the app on mount."""
        # Set provider info in status bar
        resolved = router.resolve_provider()
        label = resolved.get("label", "")
        model = resolved.get("model", "")
        self.status_bar.set_model(f"{label}" + (f" ({model})" if model else ""))

        # Load or create session for this project
        self._load_or_create_session()
        
        # Update sidebar
        self._refresh_sidebar()
        
        # Check ML daemon status
        self._check_daemon_status()
        
        # Focus the input bar
        self.input_bar.focus()

    def _load_or_create_session(self):
        """Load most recent session for this project, or create one."""
        sessions = self._store.list_sessions(limit=1)
        if sessions:
            session = sessions[0]
            self._current_session_id = session.id
            messages = self._store.get_messages(session.id)
            if messages:
                self._replay_messages(messages)
                self.status_bar.set_session(session.title)
                return

        # No existing session — create new
        resolved = router.resolve_provider()
        session = self._store.create_session(
            model=resolved.get("model", "auto"),
            agent="coder",
            title=f"Chat – {self._project_name}",
        )
        self._current_session_id = session.id
        self.status_bar.set_session(session.title)
        self._show_welcome()

    def _show_welcome(self):
        """Show SAGE ASCII welcome banner."""
        from sage.tui.server.router import resolve_provider
        resolved = resolve_provider()
        provider_label = resolved.get("label", "Not configured")
        model = resolved.get("model", "")

        banner = """[bold #8b5cf6]
    ███████╗ █████╗  ██████╗ ███████╗
    ██╔════╝██╔══██╗██╔════╝ ██╔════╝
    ███████╗█████████║  ███╗█████╗
    ╚════██║██╔══██║██║   ██║██╔══╝
    ███████║██║  ██║╚██████╔╝███████╗
    ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝
[/bold #8b5cf6]
[dim #a0a0a0]    Smart Agent Guidance Engine V2.0[/dim #a0a0a0]
[dim #6b6b6b]    ═══════════════════════════════════════[/dim #6b6b6b]
"""
        banner += f"\n[#3b82f6]    Connected:[/#3b82f6] [#ededec]{provider_label}[/#ededec]"
        if model:
            banner += f" [dim]({model})[/dim]"
        banner += f"\n[#3b82f6]    ML Daemon:[/#3b82f6] [#4ade80]active[/#4ade80]"
        banner += f"\n[#3b82f6]    Project:[/#3b82f6]  [#ededec]{self._project_name}[/#ededec]"
        banner += "\n"
        banner += "\n[dim #6b6b6b]    Enter → send | Shift+Enter → newline | Ctrl+Q → quit[/dim #6b6b6b]\n"

        from textual.widgets import Static
        welcome = Static(banner, markup=True)
        self.output_panel.mount(welcome)
        self.output_panel.scroll_end(animate=False)

    def _replay_messages(self, messages: list):
        """Replay message history into the output panel."""
        for msg in messages:
            if msg.role == "user":
                self.output_panel.add_user_message(msg.content)
            elif msg.role == "assistant":
                self.output_panel.add_assistant_message(msg.content)

    def _refresh_sidebar(self):
        """Refresh the sidebar with current sessions."""
        sessions = self._store.list_sessions(limit=50)
        
        # Build session list with previews
        session_list = []
        for s in sessions:
            # Get last message for preview
            messages = self._store.get_messages(s.id)
            preview = ""
            if messages:
                last_msg = messages[-1]
                preview = last_msg.content[:100]
            
            session_list.append({
                "id": s.id,
                "title": s.title,
                "updated_at": s.updated_at,
                "preview": preview,
            })
        
        self.sidebar.set_sessions(session_list, self._current_session_id)

    def _check_daemon_status(self):
        """Check ML daemon status and update status bar."""
        try:
            from sage.ml.daemon import _check_socket_status
            status = _check_socket_status()
            if status.get("ok"):
                state = "sleeping" if status.get("sleeping") else "active"
                self.status_bar.set_daemon_status(state)
            else:
                self.status_bar.set_daemon_status("off")
        except Exception:
            self.status_bar.set_daemon_status("off")

    async def on_input_submitted(self, message: InputSubmitted) -> None:
        """Handle input submission from the input bar."""
        text = message.text
        
        if not text.strip():
            return
        
        # Disable input during processing
        self.input_bar.disable()
        self.status_bar.set_streaming(True)
        
        # Add user message to output
        self.output_panel.add_user_message(text)
        
        # Save to session
        self._store.add_message(self._current_session_id, "user", text)
        
        # Add to context
        self._chat_context.add_user_message(text)
        
        # Resolve provider
        resolved = router.resolve_provider()
        if resolved.get("error"):
            self.output_panel.add_error(resolved["error"])
            self.input_bar.enable()
            self.status_bar.set_streaming(False)
            return

        self.status_bar.set_model(f"{resolved['label']} / {resolved['model']}")
        log.info("Using provider: %s (%s)", resolved["name"], resolved["model"])

        # Get provider instance
        provider = self._get_provider(resolved)

        # Run agentic loop in background worker
        self._worker = self.run_worker(self._run_loop(provider), exclusive=True)

    def _get_provider(self, resolved: dict):
        """Get or create a provider instance based on resolved config."""
        ptype = resolved.get("type", "api")
        name = resolved["name"]

        # CLI agents — pipe through the CLI's stdin/stdout
        if ptype == "cli":
            from .server.providers.cli_agent import CLIAgentProvider
            self._provider = CLIAgentProvider(binary=resolved["binary"])
            return self._provider

        # Anthropic direct API
        if name == "anthropic":
            if not self._provider or not isinstance(self._provider, AnthropicProvider):
                self._provider = AnthropicProvider()
            return self._provider

        # All other API providers use OpenAI-compatible endpoint
        from .server.providers.openai_compat import OpenAICompatProvider
        self._provider = OpenAICompatProvider(
            base_url=resolved.get("base_url", ""),
            api_key=resolved.get("api_key", ""),
            model=resolved.get("model", "auto"),
        )
        return self._provider

    async def _run_loop(self, provider):
        """Run the agentic loop and stream events to UI."""
        loop = AgenticLoop(provider, self._tools, max_iterations=25)
        self._loop = loop
        
        accumulated_text = ""
        tool_count = 0
        
        try:
            # Begin streaming
            self.output_panel.begin_assistant_stream()
            
            async for event in loop.run(self._chat_context.get_messages(), self._chat_context.model):
                if event.type == "token":
                    self.output_panel.stream_token(event.content)
                    accumulated_text += event.content
                
                elif event.type == "thinking":
                    self.output_panel.add_thinking_block(event.content)
                
                elif event.type == "tool_execution_start":
                    # Tool execution started - could show in UI
                    tool_count += 1
                    log.debug("Tool execution started: %s", event.tool_name)
                
                elif event.type == "tool_execution_end":
                    # Tool execution completed
                    self.output_panel.add_tool_call(
                        name=event.tool_name,
                        input_text="",  # TODO: capture input
                        output_text=event.content,
                        duration_ms=0,  # TODO: capture duration
                        status="success",
                    )
                    log.debug("Tool execution completed: %s", event.tool_name)
                
                elif event.type == "tool_execution_error":
                    # Tool execution failed
                    self.output_panel.add_tool_call(
                        name=event.tool_name,
                        input_text="",  # TODO: capture input
                        output_text=event.error,
                        duration_ms=0,  # TODO: capture duration
                        status="error",
                    )
                    log.error("Tool execution error: %s", event.error)
                
                elif event.type == "error":
                    self.output_panel.add_error(event.content)
                    break
                
                elif event.type == "done":
                    # Update token counts
                    self.status_bar.set_tokens(event.tokens_in, event.tokens_out)
                    break
            
            # End streaming
            self.output_panel.end_assistant_stream()
            
            # Save assistant response
            if accumulated_text:
                self._chat_context.add_assistant_message(accumulated_text)
                self._store.add_message(
                    self._current_session_id,
                    "assistant",
                    accumulated_text,
                )
            
        except Exception as e:
            log.exception("Error in agentic loop")
            self.output_panel.add_error(f"Error: {str(e)}")
        
        finally:
            # Re-enable input
            self.input_bar.enable()
            self.status_bar.set_streaming(False)
            self._loop = None
            
            # Refresh sidebar to update session timestamp
            self._refresh_sidebar()

    def on_session_selected(self, message: SessionSelected) -> None:
        """Handle session selection from sidebar."""
        if message.session_id == self._current_session_id:
            return
        
        # Save current context
        # (Already saved in real-time, so nothing to do)
        
        # Load selected session
        self._current_session_id = message.session_id
        session = self._store.get_session(message.session_id)
        
        if session:
            # Update model
            self._chat_context = ChatContext(session.model)
            
            # Clear output
            self.output_panel.clear()
            
            # Replay messages
            messages = self._store.get_messages(message.session_id)
            self._replay_messages(messages)
            
            # Update sidebar
            self.sidebar.set_active_session(message.session_id)
            
            # Update status bar
            self.status_bar.set_session(session.title)
            self.status_bar.set_model(session.model)

    def on_new_session_requested(self, message: NewSessionRequested) -> None:
        """Handle new session request from sidebar."""
        self.action_new_session()

    def on_session_delete_requested(self, message: SessionDeleteRequested) -> None:
        """Handle session deletion request."""
        # Delete from store
        self._store.delete_session(message.session_id)
        
        # If it was the current session, create a new one
        if message.session_id == self._current_session_id:
            self._load_or_create_session()
        
        # Refresh sidebar
        self._refresh_sidebar()

    def action_clear_output(self) -> None:
        """Clear the output panel."""
        self.output_panel.clear()

    def action_new_session(self) -> None:
        """Create a new session."""
        # Create new session
        session = self._store.create_session(
            model="claude-sonnet-4.6",
            agent="coder",
            title=f"New Chat - {self._project_name}",
        )
        
        # Switch to it
        self._current_session_id = session.id
        self._chat_context = ChatContext(session.model)
        
        # Clear output and show welcome
        self.output_panel.clear()
        self._show_welcome()
        
        # Refresh sidebar
        self._refresh_sidebar()
        
        # Update status bar
        self.status_bar.set_session(session.title)
        self.status_bar.set_model(session.model)

    def action_cancel(self) -> None:
        """Cancel the current operation."""
        if self._loop:
            self._loop.cancel()
        if self._worker:
            self._worker.cancel()
        
        self.input_bar.enable()
        self.status_bar.set_streaming(False)

    def on_settings_requested(self, message: SettingsRequested) -> None:
        """Show settings info."""
        from .server.router import detect_cli_agents, detect_api_providers, resolve_provider
        cli = detect_cli_agents()
        api = detect_api_providers()
        resolved = resolve_provider()

        info = "[bold #8b5cf6]━━━ Settings ━━━[/bold #8b5cf6]\n\n"
        info += "[#3b82f6]Active:[/#3b82f6] "
        info += f"[#ededec]{resolved['label']}[/#ededec]"
        if resolved.get("model"):
            info += f" ({resolved['model']})"
        info += "\n\n"

        info += "[#3b82f6]CLI Agents (auto-detected):[/#3b82f6]\n"
        if cli:
            for a in cli:
                marker = "[#4ade80]●[/#4ade80]" if a["name"] == resolved["name"] else "[dim]○[/dim]"
                info += f"  {marker} {a['label']} ({a['binary']})\n"
        else:
            info += "  [dim]None found[/dim]\n"

        info += f"\n[#3b82f6]API Keys:[/#3b82f6]\n"
        if api:
            for p in api:
                marker = "[#4ade80]●[/#4ade80]" if p["name"] == resolved.get("name") else "[dim]○[/dim]"
                info += f"  {marker} {p['label']}\n"
        else:
            info += "  [dim]None configured[/dim]\n"

        info += "\n[dim]Set SAGE_LLM_PROVIDER=<name> to force a provider.[/dim]\n"
        info += "[dim]Set SAGE_LLM_BASE_URL for custom endpoints.[/dim]"

        from textual.widgets import Static
        self.output_panel.mount(Static(info, markup=True))
        self.output_panel.scroll_end(animate=False)

    def action_try_quit(self) -> None:
        """Escape — quit if input is empty, otherwise let input handle it."""
        if not self.input_bar.text.strip():
            self.exit()

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()
