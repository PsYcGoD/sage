"""Base provider interface for LLM streaming."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, Any


@dataclass
class StreamEvent:
    """A single event from the LLM stream."""

    type: str  # "token", "tool_call_start", "tool_call_delta", "tool_call_end", "thinking", "done", "error"
    content: str = ""
    tool_name: str = ""
    tool_id: str = ""
    tool_input: str = ""
    error: str = ""
    tokens_in: int = 0
    tokens_out: int = 0


class BaseProvider(ABC):
    """Base class for LLM providers."""

    @abstractmethod
    async def stream(
        self, messages: list[dict], tools: list[dict], model: str
    ) -> AsyncIterator[StreamEvent]:
        """Stream a response from the LLM."""
        ...

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        ...
