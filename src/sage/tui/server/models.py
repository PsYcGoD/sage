"""Data models for the chat server."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Session:
    id: str
    title: str
    model: str
    agent: str
    created_at: str
    updated_at: str


@dataclass
class Message:
    id: str
    session_id: str
    role: str  # "user", "assistant", "system"
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    cost: float = 0.0
    created_at: str = ""


@dataclass
class ToolCall:
    id: str
    message_id: str
    tool_name: str
    input_json: str
    output_json: str
    duration_ms: int = 0
    status: str = "pending"  # pending, running, success, error
