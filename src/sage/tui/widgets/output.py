"""Output panel widget for SAGE TUI."""

from textual.containers import ScrollableContainer
from textual.widgets import Static, Markdown, Collapsible
from rich.syntax import Syntax
from rich.console import Console
from io import StringIO
from .tool_panel import ToolPanel


class OutputPanel(ScrollableContainer):
    """Scrollable output panel showing conversation history."""

    DEFAULT_CSS = """"""

    def __init__(self) -> None:
        super().__init__()
        self._thinking_widget = None
        self._current_stream_widget = None
        self._stream_buffer = ""

    def add_user_message(self, text: str, display_name: str = "") -> None:
        """Add a user message to the output.

        Args:
            text: The user's message text
            display_name: User's display name (falls back to config)
        """
        if not display_name:
            display_name = self._get_display_name()
        widget = Static(
            f"[bold magenta]{display_name}:[/bold magenta]\n{text}",
            classes="user-message",
            markup=True,
        )
        self.mount(widget)
        self.scroll_end(animate=False)

    @staticmethod
    def _get_display_name() -> str:
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

    def add_assistant_message(self, text: str) -> None:
        """Add an assistant message to the output.

        Args:
            text: The assistant's message text (markdown supported)
        """
        # Header
        header = Static(
            "[bold cyan]Assistant:[/bold cyan]",
            classes="assistant-message",
            markup=True,
        )
        self.mount(header)

        # Markdown content
        content = Markdown(text)
        content.add_class("assistant-message")
        self.mount(content)

        self.scroll_end(animate=False)

    def add_tool_call(
        self,
        name: str,
        input_text: str,
        output_text: str,
        duration_ms: int,
        status: str,
    ) -> None:
        """Add a tool call panel to the output.

        Args:
            name: Tool name
            input_text: Tool input
            output_text: Tool output
            duration_ms: Duration in milliseconds
            status: Status - 'running', 'success', or 'error'
        """
        panel = ToolPanel(
            name=name,
            input_text=input_text,
            output_text=output_text,
            duration_ms=duration_ms,
            status=status,
        )
        self.mount(panel)
        self.scroll_end(animate=False)

    def add_thinking(self) -> None:
        """Show animated thinking indicator."""
        if self._thinking_widget is None:
            self._thinking_widget = Static(
                "[dim]Thinking...[/dim]",
                classes="thinking",
                markup=True,
            )
            self.mount(self._thinking_widget)
            self.scroll_end(animate=False)

    def remove_thinking(self) -> None:
        """Remove the thinking indicator."""
        if self._thinking_widget is not None:
            self._thinking_widget.remove()
            self._thinking_widget = None

    def clear(self) -> None:
        """Clear all output."""
        # Remove all children
        for child in list(self.children):
            child.remove()
        self._thinking_widget = None
        self._current_stream_widget = None
        self._stream_buffer = ""

    def begin_assistant_stream(self) -> None:
        """Begin streaming an assistant message.
        
        Creates a new Static widget for accumulating streamed tokens.
        """
        # Header
        header = Static(
            "[bold cyan]Assistant:[/bold cyan]",
            classes="assistant-message",
            markup=True,
        )
        self.mount(header)
        
        # Create streaming widget
        self._current_stream_widget = Static("", classes="assistant-message", markup=False)
        self._stream_buffer = ""
        self.mount(self._current_stream_widget)
        self.call_after_refresh(self.scroll_end)

    def stream_token(self, token: str) -> None:
        """Append a token to the current streaming message.
        
        Args:
            token: Text token to append
        """
        if self._current_stream_widget is not None:
            self._stream_buffer += token
            self._current_stream_widget.update(self._stream_buffer)
            self.call_after_refresh(self.scroll_end)

    def end_assistant_stream(self) -> None:
        """Finalize the streaming message and convert to Markdown."""
        if self._current_stream_widget is not None:
            # Remove the plain text widget
            self._current_stream_widget.remove()
            
            # Add a proper Markdown widget with the full content
            if self._stream_buffer.strip():
                content = Markdown(self._stream_buffer)
                content.add_class("assistant-message")
                self.mount(content)
            
            self._current_stream_widget = None
            self._stream_buffer = ""
            self.call_after_refresh(self.scroll_end)

    def add_thinking_block(self, content: str) -> None:
        """Add a collapsible thinking/reasoning block.
        
        Args:
            content: The thinking content to display
        """
        thinking_block = Collapsible(
            title="━━━ Thinking ━━━",
            collapsed=False,
        )
        thinking_block.add_class("thinking-block")
        
        # Add the thinking content
        thinking_content = Static(f"[dim]{content}[/dim]", markup=True)
        
        # Mount the collapsible, then add content to it
        self.mount(thinking_block)
        thinking_block.mount(thinking_content)
        self.call_after_refresh(self.scroll_end)

    def add_code_edit(self, file_path: str, language: str, content: str, action: str) -> None:
        """Add a code edit display panel.
        
        Args:
            file_path: Path to the file being edited
            action: Type of action - 'create', 'edit', or 'delete'
            language: Programming language for syntax highlighting
            content: Code content
        """
        # Choose icon based on action
        if action == "create":
            icon = "+"
        elif action == "delete":
            icon = "×"
        else:
            icon = "✎"
        
        # Create collapsible panel
        code_panel = Collapsible(
            title=f"{icon} {action.capitalize()} {file_path}",
            collapsed=True,
        )
        code_panel.add_class("code-edit-panel")
        
        # Create syntax-highlighted code
        syntax = Syntax(content, language, theme="monokai", line_numbers=True)
        
        # Render syntax to string using Rich console
        console = Console(file=StringIO(), force_terminal=True, width=100)
        console.print(syntax)
        rendered = console.file.getvalue()
        
        code_content = Static(rendered, markup=False)
        
        # Mount the collapsible, then add content
        self.mount(code_panel)
        code_panel.mount(code_content)
        self.call_after_refresh(self.scroll_end)

    def add_sage_summary(self, run_id: int, exit_code: int, duration_ms: int, tokens_saved: int) -> None:
        """Add SAGE execution summary footer.
        
        Args:
            run_id: SAGE run ID
            exit_code: Command exit code
            duration_ms: Execution duration in milliseconds
            tokens_saved: Number of tokens saved by compression
        """
        # Choose color based on exit code
        if exit_code == 0:
            style = "dim green"
        else:
            style = "dim red"
        
        summary_text = (
            f"[{style}][sage] saved run #{run_id} exit={exit_code} "
            f"time={duration_ms}ms | tokens saved: {tokens_saved:,}[/{style}]"
        )
        
        summary = Static(summary_text, classes="sage-summary", markup=True)
        self.mount(summary)
        self.call_after_refresh(self.scroll_end)

    def add_error(self, message: str) -> None:
        """Add an error message display.
        
        Args:
            message: Error message text
        """
        error_widget = Static(
            f"[bold red]Error:[/bold red]\n{message}",
            classes="error-message",
            markup=True,
        )
        self.mount(error_widget)
        self.call_after_refresh(self.scroll_end)
