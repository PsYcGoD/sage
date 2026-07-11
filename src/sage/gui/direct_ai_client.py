import logging
"""Direct AI integration - runs IN the GUI process, no subprocess"""

import os
import json
from typing import Generator, Optional
from pathlib import Path

from sage.gui.model_defaults import bedrock_claude_model, claude_model

log = logging.getLogger(__name__)

class DirectBedrockClient:
    """Direct AWS Bedrock Claude integration"""

    def __init__(self, system_prompts: list[str] | None = None):
        self.system_prompts = system_prompts or []
        self.region = os.environ.get("AWS_REGION", "us-east-1")
        self.model_id = bedrock_claude_model()

        # Check AWS credentials
        if not (os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY")):
            raise ValueError("AWS credentials not set (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)")

    def _build_system_prompt(self) -> str:
        """Build combined system prompt from files"""
        parts = []
        for prompt_file in self.system_prompts:
            prompt_path = Path(prompt_file).expanduser()
            if prompt_path.exists():
                try:
                    parts.append(prompt_path.read_text(encoding="utf-8"))
                except Exception as e:
                    print(f"[WARN] Could not read {prompt_file}: {e}")
        return "\n\n".join(parts) if parts else None

    def stream_response(self, prompt: str) -> Generator[tuple[str, str], None, None]:
        """Stream Claude response from AWS Bedrock"""
        try:
            import boto3
        except ImportError:
            yield ("error", "\n[ERROR] boto3 not installed. Run: pip install boto3\n")
            return

        system_prompt = self._build_system_prompt()

        try:
            yield ("status", "[Working...] Connecting to AWS Bedrock...")

            bedrock = boto3.client(
                service_name='bedrock-runtime',
                region_name=self.region
            )

            # Bedrock request format
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 8192,
                "messages": [{"role": "user", "content": prompt}]
            }

            if system_prompt:
                request_body["system"] = system_prompt

            yield ("status", "[Working...] Claude is responding...")

            # Invoke with streaming
            response = bedrock.invoke_model_with_response_stream(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )

            # Parse stream
            for event in response['body']:
                chunk = json.loads(event['chunk']['bytes'].decode())

                chunk_type = chunk.get('type')

                if chunk_type == 'content_block_delta':
                    delta = chunk.get('delta', {})
                    if delta.get('type') == 'text_delta':
                        text = delta.get('text', '')
                        if text:
                            yield ("text", text)

                elif chunk_type == 'message_stop':
                    yield ("complete", "\n")
                    break

        except Exception as e:
            yield ("error", f"\n[ERROR] Bedrock error: {e}\n")

class DirectClaudeClient:
    """Direct Claude API integration using requests (no SDK dependency)"""

    def __init__(self, system_prompts: list[str] | None = None):
        self.system_prompts = system_prompts or []
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        self.model = claude_model()
        base_url = (os.environ.get("ANTHROPIC_BASE_URL") or "https://api.anthropic.com").rstrip("/")
        self.api_url = f"{base_url}/v1/messages"

    def _build_system_prompt(self) -> str:
        """Build combined system prompt from files"""
        parts = []
        for prompt_file in self.system_prompts:
            prompt_path = Path(prompt_file).expanduser()
            if prompt_path.exists():
                try:
                    parts.append(prompt_path.read_text(encoding="utf-8"))
                except Exception as e:
                    print(f"[WARN] Could not read {prompt_file}: {e}")
        return "\n\n".join(parts) if parts else None

    def stream_response(self, prompt: str) -> Generator[tuple[str, str], None, None]:
        """
        Stream Claude response directly.

        Yields (event_type, content):
        - ("status", "...") - Status updates
        - ("thinking", "...") - Extended thinking
        - ("text", "...") - Response text
        - ("error", "...") - Errors
        """
        import requests

        system_prompt = self._build_system_prompt()

        headers = {
            "anthropic-version": "2023-06-01",
            "x-api-key": self.api_key,
            "content-type": "application/json",
        }

        payload = {
            "model": self.model,
            "max_tokens": 8192,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True
        }

        if system_prompt:
            payload["system"] = system_prompt

        try:
            yield ("status", "[Working...] Connecting to Claude...")

            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=120
            )

            if response.status_code != 200:
                error_text = response.text
                yield ("error", f"\n[ERROR] API returned {response.status_code}: {error_text}\n")
                return

            yield ("status", "[Working...] Claude is responding...")

            # Parse SSE stream
            for line in response.iter_lines():
                if not line:
                    continue

                line_str = line.decode('utf-8')

                # SSE format: "data: {...}"
                if not line_str.startswith("data: "):
                    continue

                data_str = line_str[6:]  # Remove "data: " prefix

                # Check for stream end
                if data_str == "[DONE]":
                    break

                try:
                    event = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                event_type = event.get("type")

                # Content block delta (streaming text)
                if event_type == "content_block_delta":
                    delta = event.get("delta", {})
                    delta_type = delta.get("type")

                    if delta_type == "text_delta":
                        text = delta.get("text", "")
                        if text:
                            yield ("text", text)

                # Message stop
                elif event_type == "message_stop":
                    yield ("complete", "\n")
                    break

                # Error handling
                elif event_type == "error":
                    error = event.get("error", {})
                    error_message = error.get("message", "Unknown error")
                    yield ("error", f"\n[ERROR] {error_message}\n")
                    break

        except requests.exceptions.Timeout:
            yield ("error", "\n[ERROR] Request timed out after 120 seconds\n")
        except requests.exceptions.ConnectionError as e:
            yield ("error", f"\n[ERROR] Connection failed: {e}\n")
        except Exception as e:
            yield ("error", f"\n[ERROR] Unexpected error: {e}\n")

class DirectOllamaClient:
    """Direct Ollama API integration (local)"""

    def __init__(self, model: str = "qwen2.5-coder:7b", system_prompts: list[str] | None = None):
        self.model = model
        self.system_prompts = system_prompts or []
        self.api_url = "http://localhost:11434/api/chat"

    def _build_system_prompt(self) -> str:
        """Build combined system prompt"""
        parts = []
        for prompt_file in self.system_prompts:
            prompt_path = Path(prompt_file).expanduser()
            if prompt_path.exists():
                try:
                    parts.append(prompt_path.read_text(encoding="utf-8"))
                except Exception:
                    log.debug("suppressed", exc_info=True)
        return "\n\n".join(parts) if parts else None

    def stream_response(self, prompt: str) -> Generator[tuple[str, str], None, None]:
        """Stream Ollama response"""
        import requests

        system_prompt = self._build_system_prompt()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True
        }

        try:
            yield ("status", "[Working...] Connecting to Ollama...")

            response = requests.post(
                self.api_url,
                json=payload,
                stream=True,
                timeout=120
            )

            if response.status_code != 200:
                yield ("error", f"\n[ERROR] Ollama returned {response.status_code}\n")
                return

            yield ("status", "[Working...] Ollama is responding...")

            for line in response.iter_lines():
                if not line:
                    continue

                try:
                    event = json.loads(line.decode('utf-8'))
                except json.JSONDecodeError:
                    continue

                # Extract message content
                message = event.get("message", {})
                content = message.get("content", "")

                if content:
                    yield ("text", content)

                # Check if done
                if event.get("done", False):
                    yield ("complete", "\n")
                    break

        except Exception as e:
            yield ("error", f"\n[ERROR] {e}\n")

def create_direct_client(ai_name: str, system_prompts: list[str] | None = None):
    """Factory to create direct AI client"""
    ai_name = ai_name.lower()

    if ai_name == "claude":
        return DirectClaudeClient(system_prompts)
    elif ai_name == "bedrock":
        return DirectBedrockClient(system_prompts)
    elif ai_name == "ollama":
        return DirectOllamaClient(system_prompts=system_prompts)
    elif ai_name == "codex":
        # Codex uses subprocess (no direct API available)
        raise ValueError("Codex requires subprocess mode")
    else:
        raise ValueError(f"Direct integration not available for {ai_name}")

def check_direct_available(ai_name: str) -> bool:
    """Check if direct integration is available"""
    ai_name = ai_name.lower()

    if ai_name == "claude":
        return bool(os.environ.get("ANTHROPIC_API_KEY"))
    elif ai_name == "bedrock":
        # Check AWS credentials
        return bool(os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY"))
    elif ai_name == "ollama":
        # Check if Ollama is running
        import requests
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    elif ai_name == "codex":
        # Codex always uses subprocess
        return False
    else:
        return False
