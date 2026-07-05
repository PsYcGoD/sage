"""FastAPI server for dashboard."""

from __future__ import annotations

import asyncio
import html
import webbrowser
from pathlib import Path
from typing import Optional

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    import uvicorn
except ImportError:
    FastAPI = None
    uvicorn = None


class DashboardServer:
    """Dashboard web server."""

    def __init__(self, host: str = "localhost", port: int = 8765):
        if FastAPI is None:
            raise ImportError(
                "FastAPI not installed. Run: pip install fastapi uvicorn[standard]"
            )
        
        self.host = host
        self.port = port
        self.app = FastAPI(title="SAGE Dashboard")
        self._setup_routes()
        self._setup_cors()

    def _setup_cors(self):
        """Setup CORS middleware."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _setup_routes(self):
        """Setup API routes."""
        from .api.commands import router as commands_router
        from .api.metrics import router as metrics_router
        from .api.agents import router as agents_router

        self.app.include_router(commands_router, prefix="/api/v1")
        self.app.include_router(metrics_router, prefix="/api/v1")
        self.app.include_router(agents_router, prefix="/api/v1")

        # Mount static files (HTML frontend)
        static_dir = Path(__file__).parent / "static"
        if static_dir.exists():
            from fastapi.staticfiles import StaticFiles
            from fastapi.responses import HTMLResponse

            self.app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

            @self.app.get("/")
            async def root():
                return HTMLResponse(_render_dashboard_html(static_dir / "index.html"))
        else:
            @self.app.get("/")
            async def root():
                return {
                    "name": "SAGE Dashboard API",
                    "version": "2.0",
                    "status": "running"
                }

    def start(self, open_browser: bool = True):
        """Start the dashboard server."""
        url = f"http://{self.host}:{self.port}"
        print(f"[SAGE] Dashboard starting at {url}")
        
        if open_browser:
            webbrowser.open(url)
        
        uvicorn.run(self.app, host=self.host, port=self.port, log_level="info")

    async def start_async(self):
        """Start server asynchronously."""
        config = uvicorn.Config(self.app, host=self.host, port=self.port)
        server = uvicorn.Server(config)
        await server.serve()


def _render_dashboard_html(template_path: Path) -> str:
    """Render initial dashboard data into the static HTML template."""
    from .data import dashboard_snapshot

    template = template_path.read_text(encoding="utf-8")
    snapshot = dashboard_snapshot(limit=10)
    metrics = snapshot["metrics"]
    success_rate = round(float(metrics["success_rate"]) * 100)

    replacements = {
        '<div class="stat-value" id="total-commands">-</div>': (
            f'<div class="stat-value" id="total-commands">{_format_int(metrics["total_commands"])}</div>'
        ),
        '<div class="stat-value" id="token-savings">-</div>': (
            f'<div class="stat-value" id="token-savings">{_format_int(metrics["total_tokens_saved"])} tokens</div>'
        ),
        '<div class="stat-value" id="active-agents">-</div>': (
            f'<div class="stat-value" id="active-agents">{_format_int(metrics["active_agents"])}</div>'
        ),
        '<div class="stat-value" id="success-rate">-</div>': (
            f'<div class="stat-value" id="success-rate">{success_rate}%</div>'
        ),
        '<li class="loading">Loading commands...</li>': _render_command_items(snapshot["commands"]),
        '<div class="loading">Loading agents...</div>': _render_agent_items(snapshot["agents"]),
    }
    rendered = template
    for old, new in replacements.items():
        rendered = rendered.replace(old, new)
    return rendered


def _render_command_items(commands: list[dict]) -> str:
    if not commands:
        return '<li class="loading">No commands yet. Run: sage run -- python --version</li>'
    items = []
    for command in commands:
        succeeded = int(command["exit_code"]) == 0
        status_class = "status-success" if succeeded else "status-error"
        item_class = "success" if succeeded else "failure"
        status_text = "SUCCESS" if succeeded else "FAILED"
        items.append(
            "\n".join(
                [
                    f'<li class="command-item {item_class}">',
                    '  <div class="command-header">',
                    f'    <span><strong>#{int(command["id"])}</strong> - {html.escape(str(command["timestamp"]))}</span>',
                    f'    <span class="status-badge {status_class}">{status_text}</span>',
                    "  </div>",
                    f'  <div class="command-text">{html.escape(str(command["command"]))}</div>',
                    f'  <div style="font-size: 0.85em; opacity: 0.7; margin-top: 5px;">Duration: {int(command["duration_ms"])}ms | Exit: {int(command["exit_code"])}</div>',
                    "</li>",
                ]
            )
        )
    return "\n".join(items)


def _render_agent_items(agents: list[dict]) -> str:
    if not agents:
        return '<div class="loading">No agents running</div>'
    items = []
    for agent in agents:
        items.append(
            "\n".join(
                [
                    '<div class="agent-item">',
                    f'  <div class="agent-name">{html.escape(str(agent["name"]))}</div>',
                    f'  <div style="font-size: 0.9em; opacity: 0.8; margin-bottom: 8px;">{html.escape(str(agent["type"]))}</div>',
                    f'  <span class="agent-status">{html.escape(str(agent["status"]))}</span>',
                    "</div>",
                ]
            )
        )
    return "\n".join(items)


def _format_int(value: object) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"
