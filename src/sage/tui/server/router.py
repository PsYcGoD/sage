"""Provider router — resolve which model/endpoint to use.

Priority:
1. CLI agents (already authenticated, have tool access): Claude Code → OpenCode → Codex → Aider
2. Direct API keys as fallback: ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.
3. Custom base_url endpoint: SAGE_LLM_BASE_URL
"""

from __future__ import annotations

import os
import shutil
from typing import Any


# CLI agents — checked first, already have auth + tools
CLI_AGENTS = [
    {"name": "claude", "binary": "claude", "label": "Claude Code"},
    {"name": "opencode", "binary": "opencode", "label": "OpenCode"},
    {"name": "codex", "binary": "codex", "label": "Codex"},
    {"name": "aider", "binary": "aider", "label": "Aider"},
]

# API providers — fallback when no CLI is available
API_PROVIDERS: dict[str, dict[str, str]] = {
    "anthropic": {
        "base_url": "https://api.anthropic.com",
        "env_key": "ANTHROPIC_API_KEY",
        "label": "Claude API",
        "default_model": "claude-sonnet-4-6",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "env_key": "OPENAI_API_KEY",
        "label": "OpenAI",
        "default_model": "gpt-4.1",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "env_key": "DEEPSEEK_API_KEY",
        "label": "DeepSeek",
        "default_model": "deepseek-chat",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "env_key": "OPENROUTER_API_KEY",
        "label": "OpenRouter",
        "default_model": "anthropic/claude-sonnet-4.6",
    },
    "nvidia": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "env_key": "NVIDIA_API_KEY",
        "label": "NVIDIA NIM",
        "default_model": "nvidia/nemotron-3-ultra",
    },
    "kimi": {
        "base_url": "https://api.moonshot.cn/v1",
        "env_key": "MOONSHOT_API_KEY",
        "label": "Kimi (Moonshot)",
        "default_model": "moonshot-v1-128k",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "env_key": "GROQ_API_KEY",
        "label": "Groq",
        "default_model": "llama-3.3-70b-versatile",
    },
    "together": {
        "base_url": "https://api.together.xyz/v1",
        "env_key": "TOGETHER_API_KEY",
        "label": "Together AI",
        "default_model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    },
    "freemodel": {
        "base_url": "https://api.freemodel.dev/v1",
        "env_key": "FREEMODEL_API_KEY",
        "label": "FreeModel",
        "default_model": "auto",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "env_key": "",
        "label": "Ollama (local)",
        "default_model": "qwen2.5-coder:7b",
    },
}


def detect_cli_agents() -> list[dict]:
    """Detect installed CLI agents."""
    available = []
    for agent in CLI_AGENTS:
        if shutil.which(agent["binary"]):
            available.append(agent)
    return available


def detect_api_providers() -> list[dict]:
    """Detect API providers with keys configured."""
    available = []
    for name, info in API_PROVIDERS.items():
        env_key = info["env_key"]
        if not env_key and name == "ollama":
            if _ollama_up():
                available.append({"name": name, **info})
            continue
        if env_key and os.getenv(env_key):
            available.append({"name": name, **info})

    # Custom endpoint
    custom_base = os.getenv("SAGE_LLM_BASE_URL") or os.getenv("LLM_BASE_URL")
    if custom_base:
        available.append({
            "name": "custom",
            "base_url": custom_base,
            "env_key": "",
            "label": f"Custom ({custom_base.split('//')[1].split('/')[0]})",
            "default_model": os.getenv("SAGE_LLM_MODEL", "auto"),
        })

    return available


def resolve_provider(force: str | None = None) -> dict[str, Any]:
    """Resolve which provider to use.

    Priority:
    1. force parameter (user explicitly selected via settings)
    2. SAGE_LLM_PROVIDER env var
    3. CLI agents (Claude Code → OpenCode → Codex → Aider)
    4. API keys (first available)
    5. Error — nothing configured
    """
    provider_name = force or os.getenv("SAGE_LLM_PROVIDER", "")

    # Forced provider
    if provider_name:
        # Check if it's a CLI agent
        for agent in CLI_AGENTS:
            if agent["name"] == provider_name and shutil.which(agent["binary"]):
                return {
                    "name": agent["name"],
                    "type": "cli",
                    "binary": agent["binary"],
                    "label": agent["label"],
                    "model": "",
                }
        # Check API providers
        info = API_PROVIDERS.get(provider_name)
        if info:
            api_key = os.getenv(info["env_key"]) if info["env_key"] else ""
            return {
                "name": provider_name,
                "type": "api",
                "base_url": info["base_url"],
                "api_key": api_key,
                "label": info["label"],
                "model": info["default_model"],
            }

    # Auto-detect: CLI agents first
    cli_agents = detect_cli_agents()
    if cli_agents:
        agent = cli_agents[0]
        return {
            "name": agent["name"],
            "type": "cli",
            "binary": agent["binary"],
            "label": agent["label"],
            "model": "",
        }

    # Fallback: API providers
    api_providers = detect_api_providers()
    if api_providers:
        prov = api_providers[0]
        api_key = os.getenv(prov.get("env_key", "")) if prov.get("env_key") else ""
        return {
            "name": prov["name"],
            "type": "api",
            "base_url": prov["base_url"],
            "api_key": api_key,
            "label": prov["label"],
            "model": prov.get("default_model", "auto"),
        }

    return {
        "name": "none",
        "type": "none",
        "label": "No provider",
        "model": "",
        "error": "No AI provider found. Install Claude Code / OpenCode / Codex, or set an API key (ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.)",
    }


def _ollama_up() -> bool:
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=1)
        return True
    except Exception:
        return False
