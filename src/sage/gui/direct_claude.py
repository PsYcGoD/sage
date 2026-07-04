"""Direct Claude API integration for SAGE GUI - No subprocess needed"""

import os
import anthropic
from typing import Generator, Optional
from pathlib import Path


class DirectClaudeClient:
    """Direct Claude API client using Anthropic SDK"""

    def __init__(self, system_prompts: list[str] | None = None):
        """Initialize direct Claude client with system prompts"""
        self.system_prompts = system_prompts or []
        self.api_key = self._get_api_key()
        if not self.api_key:
            raise ValueError("No Anthropic API key found. Set ANTHROPIC_API_KEY or configure in ~/.claude/config")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"  # Latest Sonnet 4.5

    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment or config"""
        # Try environment variable first
        if os.environ.get("ANTHROPIC_API_KEY"):
            return os.environ["ANTHROPIC_API_KEY"]

        # Try Claude Code config
        config_path = Path.home() / ".claude" / "config"
        if config_path.exists():
            try:
                import json
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    return config.get("anthropic", {}).get("apiKey")
            except Exception:
                pass

        return None

    def _build_system_prompt(self) -> str:
        """Build combined system prompt from files"""
        parts = []
        for prompt_file in self.system_prompts:
            prompt_path = Path(prompt_file)
            if prompt_path.exists():
                try:
                    parts.append(prompt_path.read_text(encoding="utf-8"))
                except Exception:
                    pass
        return "\n\n".join(parts) if parts else ""

    def stream_response(self, prompt: str) -> Generator[tuple[str, str], None, None]:
        """
        Stream Claude response directly from API.

        Yields tuples of (status, content):
        - ("status", "Thinking...") - Status updates
        - ("thinking", "...") - Extended thinking content
        - ("text", "...") - Response text
        - ("tool", "tool_name") - Tool usage
        - ("complete", "stats") - Completion info
        """
        system_prompt = self._build_system_prompt()

        try:
            # Show working state
            yield ("status", "[Working...] Connecting to Claude API...")

            # Create streaming request
            stream = self.client.messages.create(
                model=self.model,
                max_tokens=8192,
                system=system_prompt if system_prompt else anthropic.NOT_GIVEN,
                messages=[{"role": "user", "content": prompt}],
                stream=True
            )

            yield ("status", "[Working...] Claude is thinking...")
            seen_thinking = False
            seen_answer = False

            for event in stream:
                event_type = getattr(event, 'type', None)

                # Message start
                if event_type == "message_start":
                    yield ("status", "[Working...] Receiving response...")

                # Content block start
                elif event_type == "content_block_start":
                    block = getattr(event, 'content_block', None)
                    if block:
                        block_type = getattr(block, 'type', None)
                        if block_type == "thinking" and not seen_thinking:
                            seen_thinking = True
                            yield ("thinking", "\n[Thinking]\n")
                        elif block_type == "text" and not seen_answer:
                            seen_answer = True
                            yield ("status", "[Working...] Generating answer...")
                        elif block_type == "tool_use":
                            tool_name = getattr(block, 'name', 'unknown')
                            yield ("tool", f"\n[Using tool: {tool_name}]\n")

                # Content deltas (streaming text)
                elif event_type == "content_block_delta":
                    delta = getattr(event, 'delta', None)
                    if delta:
                        delta_type = getattr(delta, 'type', None)
                        if delta_type == "thinking_delta":
                            thinking = getattr(delta, 'thinking', '')
                            if thinking:
                                yield ("thinking", thinking)
                        elif delta_type == "text_delta":
                            text = getattr(delta, 'text', '')
                            if text:
                                yield ("text", text)

                # Message complete
                elif event_type == "message_stop":
                    yield ("complete", "\n")

        except anthropic.APIError as e:
            yield ("error", f"\n[ERROR] API Error: {e}\n")
        except Exception as e:
            yield ("error", f"\n[ERROR] {e}\n")

    def is_available(self) -> bool:
        """Check if API key is configured"""
        return self.api_key is not None


def check_direct_claude_available() -> bool:
    """Check if direct Claude API is available"""
    try:
        client = DirectClaudeClient()
        return client.is_available()
    except Exception:
        return False
