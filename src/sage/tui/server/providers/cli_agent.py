"""CLI Agent Provider — pipe messages through installed AI CLIs (claude, opencode, codex, aider)."""

from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator

from .base import BaseProvider, StreamEvent

log = logging.getLogger(__name__)


class CLIAgentProvider(BaseProvider):
    """Stream responses by piping through a CLI agent's run command."""

    def __init__(self, binary: str = "claude"):
        self.binary = binary

    async def stream(
        self, messages: list[dict], tools: list[dict], model: str
    ) -> AsyncIterator[StreamEvent]:
        """Send the last user message through the CLI and stream output."""
        # Get the last user message
        user_msg = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_msg = msg.get("content", "")
                break

        if not user_msg:
            yield StreamEvent(type="error", content="No user message to send")
            return

        # Build command based on which CLI
        cmd = self._build_command(user_msg)

        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Stream stdout line by line
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace")
                yield StreamEvent(type="token", content=text)

            await process.wait()

            # Check for errors
            if process.returncode != 0:
                stderr = await process.stderr.read()
                err_text = stderr.decode("utf-8", errors="replace").strip()
                if err_text:
                    yield StreamEvent(type="error", content=err_text)

            yield StreamEvent(type="done")

        except FileNotFoundError:
            yield StreamEvent(type="error", content=f"CLI '{self.binary}' not found in PATH")
        except Exception as e:
            yield StreamEvent(type="error", content=str(e))

    def _build_command(self, message: str) -> str:
        """Build the CLI command for the given message."""
        # Escape quotes in message
        safe_msg = message.replace('"', '\\"')

        if self.binary == "claude":
            return f'claude -p "{safe_msg}"'
        elif self.binary == "opencode":
            return f'opencode run "{safe_msg}"'
        elif self.binary == "codex":
            return f'codex -q "{safe_msg}"'
        elif self.binary == "aider":
            return f'aider --message "{safe_msg}" --no-git'
        else:
            return f'{self.binary} "{safe_msg}"'

    def count_tokens(self, text: str) -> int:
        return len(text) // 4
