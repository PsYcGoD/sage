"""OpenAI-compatible provider — works with any endpoint that speaks the OpenAI API.

Supports: OpenAI, DeepSeek, OpenRouter, NVIDIA NIM, Kimi, Groq, Together,
FreeModel, Ollama, or any custom base_url.
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

import httpx

from .base import BaseProvider, StreamEvent

log = logging.getLogger(__name__)


class OpenAICompatProvider(BaseProvider):
    """Stream from any OpenAI-compatible chat/completions endpoint."""

    def __init__(self, base_url: str, api_key: str = "", model: str = "auto"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=httpx.Timeout(120.0, connect=10.0),
            )
        return self._client

    async def stream(
        self, messages: list[dict], tools: list[dict], model: str
    ) -> AsyncIterator[StreamEvent]:
        """Stream a response from an OpenAI-compatible endpoint."""
        client = self._get_client()
        use_model = model if model != "auto" else self.model

        body: dict[str, Any] = {
            "model": use_model,
            "messages": messages,
            "stream": True,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        url = f"{self.base_url}/chat/completions"

        try:
            async with client.stream("POST", url, json=body) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    yield StreamEvent(
                        type="error",
                        content=f"HTTP {response.status_code}: {error_body.decode('utf-8', errors='replace')[:500]}",
                    )
                    return

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data == "[DONE]":
                        yield StreamEvent(type="done")
                        return

                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue

                    choices = chunk.get("choices", [])
                    if not choices:
                        continue

                    delta = choices[0].get("delta", {})

                    # Text content
                    content = delta.get("content")
                    if content:
                        yield StreamEvent(type="token", content=content)

                    # Reasoning/thinking (DeepSeek, some providers)
                    reasoning = delta.get("reasoning_content") or delta.get("thinking")
                    if reasoning:
                        yield StreamEvent(type="thinking", content=reasoning)

                    # Tool calls
                    tool_calls = delta.get("tool_calls")
                    if tool_calls:
                        for tc in tool_calls:
                            func = tc.get("function", {})
                            if tc.get("id"):
                                yield StreamEvent(
                                    type="tool_call_start",
                                    tool_id=tc["id"],
                                    tool_name=func.get("name", ""),
                                )
                            if func.get("arguments"):
                                yield StreamEvent(
                                    type="tool_call_delta",
                                    tool_id=tc.get("id", ""),
                                    tool_input=func["arguments"],
                                )

                    # Finish reason
                    finish = choices[0].get("finish_reason")
                    if finish == "tool_calls":
                        yield StreamEvent(type="tool_call_end")
                    elif finish == "stop":
                        yield StreamEvent(type="done")
                        return

        except httpx.ConnectError as e:
            yield StreamEvent(type="error", content=f"Connection failed: {e}")
        except httpx.ReadTimeout:
            yield StreamEvent(type="error", content="Request timed out")
        except Exception as e:
            yield StreamEvent(type="error", content=f"Provider error: {e}")

    def count_tokens(self, text: str) -> int:
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except Exception:
            return len(text) // 4
