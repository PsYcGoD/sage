"""FastAPI server for dashboard."""

from __future__ import annotations

import asyncio
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
            from fastapi.responses import FileResponse

            self.app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

            @self.app.get("/")
            async def root():
                return FileResponse(str(static_dir / "index.html"))
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
