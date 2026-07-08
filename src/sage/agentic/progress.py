"""Progress reporter — sends loop status updates via LSP or terminal."""

from __future__ import annotations

import json
import logging
import sys
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class ProgressSink(Protocol):
    """Interface for receiving progress updates."""
    def report(self, event: str, data: dict) -> None: ...


class TerminalProgress:
    """Reports progress directly to the terminal."""

    ICONS = {
        "running": "▶",
        "analyzing": "🔍",
        "fixing": "🔧",
        "verifying": "✓",
        "done": "✅",
        "failed": "✗",
        "warn": "⚠",
        "loop_detected": "🔄",
        "circuit_break": "⛔",
    }

    def report(self, event: str, data: dict) -> None:
        icon = self.ICONS.get(event, "•")
        message = data.get("message", "")
        print(f"  {icon} [sage-loop] {message}", file=sys.stderr)


class LSPProgress:
    """Reports progress via LSP notifications to connected editor."""

    def __init__(self, notify_fn):
        self._notify = notify_fn

    def report(self, event: str, data: dict) -> None:
        self._notify("sage/progress", {
            "event": event,
            **data,
        })


class MultiProgress:
    """Fan-out to multiple progress sinks."""

    def __init__(self, sinks: list[ProgressSink]):
        self._sinks = sinks

    def report(self, event: str, data: dict) -> None:
        for sink in self._sinks:
            try:
                sink.report(event, data)
            except Exception as e:
                logger.debug(f"Progress sink error: {e}")


def make_progress_handler(lsp_notify=None) -> callable:
    """Create a progress callback suitable for AgenticLoop.on_progress."""
    sinks: list[ProgressSink] = [TerminalProgress()]
    if lsp_notify:
        sinks.append(LSPProgress(lsp_notify))
    multi = MultiProgress(sinks)

    def handler(event: str, message: str):
        multi.report(event, {"message": message})

    return handler
