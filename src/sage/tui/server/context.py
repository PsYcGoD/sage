"""Conversation context management."""
from __future__ import annotations
from typing import Any

SYSTEM_PROMPT = """You are SAGE, a coding assistant running in the terminal. You have access to tools for reading, writing, and searching files, and executing bash commands.

Rules:
- Be concise and direct
- Use tools to accomplish tasks
- Show your reasoning when making decisions
- Route all commands through sage run --
- When you use a tool, explain what you're doing and why
"""


class ContextManager:
    """Manage conversation context and messages."""

    def __init__(self, model: str, max_tokens: int = 200000):
        self.model = model
        self.max_tokens = max_tokens
        self._messages: list[dict[str, Any]] = []
        self._system_prompt = SYSTEM_PROMPT

    def set_system_prompt(self, prompt: str):
        """Set the system prompt."""
        self._system_prompt = prompt

    def add_user_message(self, content: str):
        """Add a user message."""
        self._messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str, tool_calls: list[dict] | None = None):
        """Add an assistant message."""
        msg: dict[str, Any] = {"role": "assistant", "content": content}
        if tool_calls:
            msg["tool_calls"] = tool_calls
        self._messages.append(msg)

    def add_tool_result(self, tool_call_id: str, content: str):
        """Add a tool result message."""
        self._messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
        })

    def get_messages(self) -> list[dict[str, Any]]:
        """Get all messages including system prompt."""
        messages = []
        
        # Add system prompt first
        if self._system_prompt:
            messages.append({"role": "system", "content": self._system_prompt})
        
        # Add conversation messages
        messages.extend(self._messages)
        
        return messages

    def token_count(self) -> int:
        """Estimate total token count."""
        # Rough approximation: 4 chars per token
        total_chars = len(self._system_prompt)
        for msg in self._messages:
            total_chars += len(str(msg.get("content", "")))
            if "tool_calls" in msg:
                total_chars += len(str(msg["tool_calls"]))
        return total_chars // 4

    def compact(self):
        """Summarize old messages when approaching limit."""
        # Simple strategy: keep first message and last N messages
        if self.token_count() > self.max_tokens * 0.8:
            if len(self._messages) > 10:
                # Keep first user message and last 8 messages
                self._messages = [self._messages[0]] + self._messages[-8:]

    def clear(self):
        """Clear all messages."""
        self._messages = []
