"""AI API Client for SAGE Desktop GUI."""

import os
from typing import Generator, Optional
from anthropic import Anthropic
from openai import OpenAI
import google.generativeai as genai


class AIClient:
    """Unified client for different AI APIs."""

    def __init__(self, ai_name: str, api_key: Optional[str] = None):
        """
        Initialize AI client.

        Args:
            ai_name: Name of AI (claude, codex, gpt4, gemini)
            api_key: Optional API key (falls back to env vars)
        """
        self.ai_name = ai_name.lower()
        self.api_key = api_key

        # Initialize client based on AI type
        if self.ai_name == "claude":
            self.client = Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
        elif self.ai_name in ["codex", "gpt4"]:
            self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        elif self.ai_name == "gemini":
            genai.configure(api_key=api_key or os.getenv("GOOGLE_API_KEY"))
            self.client = genai.GenerativeModel('gemini-pro')
        else:
            raise ValueError(f"Unsupported AI: {ai_name}")

    def stream_response(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        """
        Stream AI response.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt

        Yields:
            Response chunks
        """
        try:
            if self.ai_name == "claude":
                yield from self._stream_claude(prompt, system_prompt)
            elif self.ai_name in ["codex", "gpt4"]:
                yield from self._stream_openai(prompt, system_prompt)
            elif self.ai_name == "gemini":
                yield from self._stream_gemini(prompt, system_prompt)
        except Exception as e:
            yield f"\n❌ Error: {str(e)}\n"

    def _stream_claude(self, prompt: str, system_prompt: Optional[str]) -> Generator[str, None, None]:
        """Stream Claude response."""
        print(f"[DEBUG] Claude streaming: {prompt[:50]}...")
        messages = [{"role": "user", "content": prompt}]

        kwargs = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "messages": messages,
            "stream": True
        }

        if system_prompt:
            kwargs["system"] = system_prompt
            print(f"[DEBUG] System prompt length: {len(system_prompt)}")

        print(f"[DEBUG] Starting stream...")
        with self.client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                print(f"[DEBUG] Chunk: {text[:20]}")
                yield text
        print(f"[DEBUG] Stream complete")

    def _stream_openai(self, prompt: str, system_prompt: Optional[str]) -> Generator[str, None, None]:
        """Stream OpenAI response."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        model = "gpt-4" if self.ai_name == "gpt4" else "gpt-3.5-turbo"

        stream = self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def _stream_gemini(self, prompt: str, system_prompt: Optional[str]) -> Generator[str, None, None]:
        """Stream Gemini response."""
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\nUser: {prompt}"

        response = self.client.generate_content(full_prompt, stream=True)
        for chunk in response:
            if chunk.text:
                yield chunk.text


def check_api_keys() -> dict:
    """
    Check which API keys are configured.

    Returns:
        Dict mapping AI names to availability
    """
    return {
        "claude": bool(os.getenv("ANTHROPIC_API_KEY")),
        "codex": bool(os.getenv("OPENAI_API_KEY")),
        "gpt4": bool(os.getenv("OPENAI_API_KEY")),
        "gemini": bool(os.getenv("GOOGLE_API_KEY"))
    }
