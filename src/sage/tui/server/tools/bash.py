"""Bash tool for executing commands."""
from __future__ import annotations
import asyncio
import subprocess
import time
from typing import Any

from .base import BaseTool


class BashTool(BaseTool):
    """Execute bash commands through sage run, with ML prediction."""

    @property
    def name(self) -> str:
        return "bash"

    @property
    def description(self) -> str:
        return "Execute shell commands. Runs through 'sage run --' for safety."

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The shell command to execute",
                        }
                    },
                    "required": ["command"],
                },
            },
        }

    @staticmethod
    def _predict(command: str) -> dict[str, Any] | None:
        """Query the ML daemon for a failure prediction."""
        try:
            from sage.ml.client import predict_fast
            return predict_fast(command, timeout=0.5)
        except Exception:
            pass
        return None

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute a command through sage run."""
        command = input_data.get("command", "")
        if not command:
            return {"error": "No command provided", "exit_code": 1}

        # ML prediction before execution
        prediction = self._predict(command)

        started = time.perf_counter()

        try:
            # Run through sage run --
            process = await asyncio.create_subprocess_shell(
                f"sage run -- {command}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()
            duration_ms = int((time.perf_counter() - started) * 1000)

            return {
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "exit_code": process.returncode or 0,
                "duration_ms": duration_ms,
                "prediction": prediction,
            }

        except Exception as e:
            duration_ms = int((time.perf_counter() - started) * 1000)
            return {
                "stdout": "",
                "stderr": str(e),
                "exit_code": 1,
                "duration_ms": duration_ms,
                "error": str(e),
            }
