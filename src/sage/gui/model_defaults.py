"""Configurable model defaults for GUI AI clients."""

from __future__ import annotations

import os


DEFAULT_CLAUDE_MODEL = "claude-sonnet-5"
# Keep Bedrock provider defaults conservative; working Bedrock deployments often
# rely on inference-profile IDs that differ from first-party Claude API IDs.
DEFAULT_BEDROCK_CLAUDE_MODEL = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
DEFAULT_OLLAMA_MODEL = "qwen2.5-coder:7b"


def claude_model() -> str:
    """Return the direct Anthropic Claude model for GUI calls."""
    return os.getenv("SAGE_CLAUDE_MODEL") or os.getenv("ANTHROPIC_MODEL") or DEFAULT_CLAUDE_MODEL


def bedrock_claude_model() -> str:
    """Return the provider-native Bedrock Claude model for GUI calls."""
    return (
        os.getenv("SAGE_BEDROCK_CLAUDE_MODEL")
        or os.getenv("ANTHROPIC_DEFAULT_SONNET_MODEL")
        or DEFAULT_BEDROCK_CLAUDE_MODEL
    )


def ollama_model() -> str:
    """Return the local Ollama model for GUI calls."""
    return os.getenv("SAGE_OLLAMA_MODEL") or DEFAULT_OLLAMA_MODEL
