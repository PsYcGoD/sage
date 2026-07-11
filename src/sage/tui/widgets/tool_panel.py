"""Collapsible tool call panel widget for SAGE TUI."""

from textual.widgets import Collapsible, Static
from rich.syntax import Syntax


class ToolPanel(Collapsible):
    """A collapsible panel showing tool call details."""

    DEFAULT_CSS = """
    ToolPanel {
        margin: 0 1;
        border: solid $primary-lighten-1;
    }

    ToolPanel > Static {
        padding: 1;
    }
    """

    def __init__(
        self,
        name: str,
        input_text: str,
        output_text: str,
        duration_ms: int,
        status: str,
    ) -> None:
        """Initialize the tool panel.

        Args:
            name: Tool name
            input_text: Tool input (arguments)
            output_text: Tool output
            duration_ms: Duration in milliseconds
            status: Status - 'running', 'success', or 'error'
        """
        # Choose status icon
        if status == "running":
            icon = "⏳"
        elif status == "success":
            icon = "✓"
        else:
            icon = "✗"

        # Build title
        title = f"{icon} {name} ({duration_ms}ms)"

        super().__init__(title=title, collapsed=True)

        # Build content
        content_parts = []

        if input_text.strip():
            content_parts.append("[bold cyan]Input:[/bold cyan]")
            content_parts.append("")
            # Render as code
            content_parts.append(f"[dim]{input_text}[/dim]")
            content_parts.append("")

        if output_text.strip():
            content_parts.append("[bold green]Output:[/bold green]")
            content_parts.append("")
            # Render as code
            content_parts.append(f"[dim]{output_text}[/dim]")

        content = "\n".join(content_parts)

        # Add content widget
        self._content_widget = Static(content, markup=True)

    def compose(self):
        """Compose the collapsible content."""
        yield self._content_widget
