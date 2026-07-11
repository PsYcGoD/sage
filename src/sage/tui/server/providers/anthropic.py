"""Anthropic provider for Claude streaming."""
from __future__ import annotations
import asyncio
import json
import os
from typing import AsyncIterator, Any

try:
    import httpx
except ImportError:
    httpx = None

try:
    import tiktoken
except ImportError:
    tiktoken = None

from .base import BaseProvider, StreamEvent


class AnthropicProvider(BaseProvider):
    """Provider for Claude via Anthropic API."""

    def __init__(self):
        if httpx is None:
            raise ImportError("httpx is required for AnthropicProvider. Install with: pip install httpx")
        
        self.api_key = self._get_api_key()
        self.base_url = "https://api.anthropic.com/v1"
        self._tokenizer = None
        if tiktoken:
            try:
                self._tokenizer = tiktoken.get_encoding("cl100k_base")
            except Exception:
                pass

    def _get_api_key(self) -> str:
        """Get API key from environment, keyring, or config."""
        # Try environment first
        key = os.environ.get("ANTHROPIC_API_KEY")
        if key:
            return key

        # Try keyring
        try:
            import keyring
            key = keyring.get_password("sage", "anthropic_api_key")
            if key:
                return key
        except Exception:
            pass

        # Try config file
        try:
            from pathlib import Path
            config_path = Path.home() / ".sage" / "config.json"
            if config_path.exists():
                config = json.loads(config_path.read_text())
                key = config.get("anthropic_api_key")
                if key:
                    return key
        except Exception:
            pass

        raise ValueError(
            "ANTHROPIC_API_KEY not found. Set it via environment variable, "
            "keyring, or ~/.sage/config.json"
        )

    async def stream(
        self, messages: list[dict], tools: list[dict], model: str
    ) -> AsyncIterator[StreamEvent]:
        """Stream a response from Claude."""
        # Convert messages to Anthropic format
        api_messages = []
        system_prompt = None

        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                api_messages.append(msg)

        # Build request body
        body = {
            "model": model,
            "messages": api_messages,
            "max_tokens": 8192,
            "stream": True,
        }

        if system_prompt:
            body["system"] = system_prompt

        if tools:
            body["tools"] = tools

        # Stream the response
        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/messages",
                    headers={
                        "anthropic-version": "2023-06-01",
                        "x-api-key": self.api_key,
                        "content-type": "application/json",
                    },
                    json=body,
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        yield StreamEvent(
                            type="error",
                            error=f"API error {response.status_code}: {error_text.decode()}",
                        )
                        return

                    # Parse SSE stream
                    current_tool_id = ""
                    current_tool_name = ""
                    current_tool_input = ""
                    tokens_in = 0
                    tokens_out = 0

                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue

                        if line.startswith("event:"):
                            event_type = line[6:].strip()
                            continue

                        if line.startswith("data:"):
                            data_str = line[5:].strip()
                            if not data_str:
                                continue

                            try:
                                data = json.loads(data_str)
                            except json.JSONDecodeError:
                                continue

                            event_type = data.get("type")

                            # Message start - capture token counts
                            if event_type == "message_start":
                                usage = data.get("message", {}).get("usage", {})
                                tokens_in = usage.get("input_tokens", 0)

                            # Content block start
                            elif event_type == "content_block_start":
                                block = data.get("content_block", {})
                                block_type = block.get("type")

                                if block_type == "tool_use":
                                    current_tool_id = block.get("id", "")
                                    current_tool_name = block.get("name", "")
                                    current_tool_input = ""
                                    yield StreamEvent(
                                        type="tool_call_start",
                                        tool_id=current_tool_id,
                                        tool_name=current_tool_name,
                                    )

                                elif block_type == "thinking":
                                    yield StreamEvent(type="thinking")

                            # Content block delta
                            elif event_type == "content_block_delta":
                                delta = data.get("delta", {})
                                delta_type = delta.get("type")

                                if delta_type == "text_delta":
                                    text = delta.get("text", "")
                                    yield StreamEvent(type="token", content=text)

                                elif delta_type == "input_json_delta":
                                    partial_json = delta.get("partial_json", "")
                                    current_tool_input += partial_json
                                    yield StreamEvent(
                                        type="tool_call_delta",
                                        tool_id=current_tool_id,
                                        tool_name=current_tool_name,
                                        tool_input=partial_json,
                                    )

                            # Content block stop
                            elif event_type == "content_block_stop":
                                if current_tool_id:
                                    yield StreamEvent(
                                        type="tool_call_end",
                                        tool_id=current_tool_id,
                                        tool_name=current_tool_name,
                                        tool_input=current_tool_input,
                                    )
                                    current_tool_id = ""
                                    current_tool_name = ""
                                    current_tool_input = ""

                            # Message stop - capture output tokens
                            elif event_type == "message_delta":
                                usage = data.get("usage", {})
                                tokens_out = usage.get("output_tokens", 0)

                            elif event_type == "message_stop":
                                yield StreamEvent(
                                    type="done",
                                    tokens_in=tokens_in,
                                    tokens_out=tokens_out,
                                )

            except httpx.HTTPError as e:
                yield StreamEvent(type="error", error=f"HTTP error: {str(e)}")
            except Exception as e:
                yield StreamEvent(type="error", error=f"Stream error: {str(e)}")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken approximation."""
        if self._tokenizer:
            try:
                return len(self._tokenizer.encode(text))
            except Exception:
                pass
        # Fallback: rough approximation
        return len(text) // 4
