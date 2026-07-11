"""LLM Provider registry."""
from .base import BaseProvider, StreamEvent
from .anthropic import AnthropicProvider
from .openai_compat import OpenAICompatProvider


def get_provider(name: str = "anthropic", **kwargs) -> BaseProvider:
    """Get a provider by name or config."""
    if name == "anthropic":
        return AnthropicProvider()
    return OpenAICompatProvider(**kwargs)


__all__ = ["BaseProvider", "StreamEvent", "AnthropicProvider", "OpenAICompatProvider", "get_provider"]
