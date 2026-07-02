"""Inter-agent communication protocol."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Message:
    """Message between agents."""
    from_agent: str
    to_agent: str
    message_type: str
    payload: dict[str, Any]


class MessageBus:
    """Simple message bus for agent communication."""

    def __init__(self):
        self.messages: list[Message] = []

    def send(self, message: Message) -> None:
        """Send a message."""
        self.messages.append(message)
        print(f"[SAGE] Message: {message.from_agent} -> {message.to_agent}")

    def receive(self, agent_name: str) -> list[Message]:
        """Receive all messages for an agent."""
        agent_messages = [
            msg for msg in self.messages if msg.to_agent == agent_name
        ]
        # Remove received messages
        self.messages = [
            msg for msg in self.messages if msg.to_agent != agent_name
        ]
        return agent_messages
