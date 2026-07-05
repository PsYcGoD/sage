"""Secure credential storage for SAGE AI agent keys.

Uses keyring (Windows Credential Manager / macOS Keychain / Linux SecretService)
when available; falls back to a base64-encoded ~/.sage/.credentials file.

All stored env-var names are injected into os.environ at app startup via
inject_all(), so every subprocess (claude, codex, …) inherits them.
"""

from __future__ import annotations

import base64
import json
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

_SERVICE = "SAGE"
_SEP = "::"  # separates agent name from env-var name in the storage key


# ---------------------------------------------------------------------------
# Agent definitions — what each AI tool needs and how many auth modes it has
# ---------------------------------------------------------------------------

AGENT_SPECS: dict[str, dict] = {
    "Claude (Anthropic)": {
        "icon": "🟣",
        "modes": {
            "API Key": {
                "inject": True,
                "fields": [
                    {"label": "API Key",  "env": "ANTHROPIC_API_KEY",  "secret": True,  "placeholder": "sk-ant-..."},
                    {"label": "Base URL", "env": "ANTHROPIC_BASE_URL", "secret": False, "placeholder": "https://api.anthropic.com  (leave blank for default)", "optional": True},
                ],
            },
            "CLI Login (OAuth)": {
                "inject": False,
                "description": "Opens the Claude browser login flow. No key is stored here.",
                "action": "claude auth login",
                "fields": [],
            },
            "AWS Bedrock": {
                "inject": True,
                "fields": [
                    {"label": "Access Key ID",     "env": "AWS_ACCESS_KEY_ID",     "secret": True},
                    {"label": "Secret Access Key", "env": "AWS_SECRET_ACCESS_KEY", "secret": True},
                    {"label": "Region",            "env": "AWS_REGION",            "secret": False, "placeholder": "us-east-1"},
                    {"label": "Session Token",     "env": "AWS_SESSION_TOKEN",     "secret": True,  "optional": True, "placeholder": "optional — for STS/assumed roles"},
                ],
            },
            "Google Vertex AI": {
                "inject": True,
                "fields": [
                    {"label": "Project ID",          "env": "ANTHROPIC_VERTEX_PROJECT_ID", "secret": False},
                    {"label": "Region",              "env": "CLOUD_ML_REGION",             "secret": False, "placeholder": "us-east5"},
                    {"label": "Credentials JSON path", "env": "GOOGLE_APPLICATION_CREDENTIALS", "secret": False, "placeholder": "path/to/service-account.json"},
                ],
            },
            "Custom Provider (Anthropic-compatible)": {
                "inject": True,
                "fields": [
                    {"label": "API Key",  "env": "ANTHROPIC_API_KEY",  "secret": True,  "placeholder": "your provider's key"},
                    {"label": "Base URL", "env": "ANTHROPIC_BASE_URL", "secret": False, "placeholder": "https://capi.aerolink.lat/"},
                ],
            },
        },
    },
    "Codex (OpenAI)": {
        "icon": "⬛",
        "modes": {
            "API Key": {
                "inject": True,
                "fields": [
                    {"label": "API Key",  "env": "OPENAI_API_KEY",  "secret": True,  "placeholder": "sk-..."},
                    {"label": "Base URL", "env": "OPENAI_BASE_URL", "secret": False, "placeholder": "https://api.openai.com  (optional)", "optional": True},
                ],
            },
            "CLI Login (OAuth)": {
                "inject": False,
                "description": "Opens the Codex / OpenAI browser login flow.",
                "action": "codex login",
                "fields": [],
            },
        },
    },
    "Cursor": {
        "icon": "🖱️",
        "modes": {
            "Web Login": {
                "inject": False,
                "description": "Log in at cursor.sh — Cursor manages its own auth, no key is stored here.",
                "action": None,
                "fields": [],
            },
        },
    },
    "Ollama (Local)": {
        "icon": "🦙",
        "modes": {
            "Local (No Auth)": {
                "inject": True,
                "fields": [
                    {"label": "Base URL",      "env": "OLLAMA_BASE_URL", "secret": False, "placeholder": "http://localhost:11434"},
                    {"label": "Default Model", "env": "OLLAMA_MODEL",    "secret": False, "placeholder": "qwen2.5-coder:7b"},
                ],
            },
        },
    },
    "Gemini (Google)": {
        "icon": "🔵",
        "modes": {
            "API Key": {
                "inject": True,
                "fields": [
                    {"label": "API Key", "env": "GEMINI_API_KEY", "secret": True, "placeholder": "AI..."},
                ],
            },
            "Application Default Credentials": {
                "inject": False,
                "description": "Opens the gcloud ADC login flow — saves credentials locally via gcloud.",
                "action": "gcloud auth application-default login",
                "fields": [],
            },
        },
    },
    "GitHub Copilot": {
        "icon": "🐙",
        "modes": {
            "GitHub OAuth": {
                "inject": False,
                "description": "Opens GitHub login in your browser. Requires an active Copilot subscription.",
                "action": "gh auth login",
                "fields": [],
            },
        },
    },
    "Mistral AI": {
        "icon": "🌊",
        "modes": {
            "API Key": {
                "inject": True,
                "fields": [
                    {"label": "API Key",  "env": "MISTRAL_API_KEY",  "secret": True},
                    {"label": "Base URL", "env": "MISTRAL_BASE_URL", "secret": False, "optional": True, "placeholder": "https://api.mistral.ai  (optional)"},
                ],
            },
        },
    },
    "Grok (xAI)": {
        "icon": "⚡",
        "modes": {
            "API Key": {
                "inject": True,
                "fields": [
                    {"label": "API Key", "env": "XAI_API_KEY", "secret": True, "placeholder": "xai-..."},
                ],
            },
        },
    },
    "OpenRouter": {
        "icon": "🔀",
        "modes": {
            "API Key": {
                "inject": True,
                "fields": [
                    {"label": "API Key", "env": "OPENROUTER_API_KEY", "secret": True, "placeholder": "sk-or-..."},
                ],
            },
        },
    },
    "Azure OpenAI": {
        "icon": "☁️",
        "modes": {
            "API Key": {
                "inject": True,
                "fields": [
                    {"label": "API Key",         "env": "AZURE_OPENAI_API_KEY",         "secret": True},
                    {"label": "Endpoint URL",    "env": "AZURE_OPENAI_ENDPOINT",        "secret": False, "placeholder": "https://<resource>.openai.azure.com/"},
                    {"label": "Deployment Name", "env": "AZURE_OPENAI_DEPLOYMENT_NAME", "secret": False},
                    {"label": "API Version",     "env": "OPENAI_API_VERSION",           "secret": False, "placeholder": "2024-02-01"},
                ],
            },
        },
    },
    "Together AI": {
        "icon": "🤝",
        "modes": {
            "API Key": {
                "inject": True,
                "fields": [
                    {"label": "API Key", "env": "TOGETHER_API_KEY", "secret": True},
                ],
            },
        },
    },
    "Perplexity": {
        "icon": "🔍",
        "modes": {
            "API Key": {
                "inject": True,
                "fields": [
                    {"label": "API Key", "env": "PERPLEXITY_API_KEY", "secret": True, "placeholder": "pplx-..."},
                ],
            },
        },
    },
    "Groq": {
        "icon": "⚡",
        "modes": {
            "API Key": {
                "inject": True,
                "fields": [
                    {"label": "API Key", "env": "GROQ_API_KEY", "secret": True, "placeholder": "gsk_..."},
                ],
            },
        },
    },
    "DeepSeek": {
        "icon": "🔬",
        "modes": {
            "API Key": {
                "inject": True,
                "fields": [
                    {"label": "API Key",  "env": "DEEPSEEK_API_KEY",  "secret": True},
                    {"label": "Base URL", "env": "DEEPSEEK_BASE_URL", "secret": False, "optional": True},
                ],
            },
        },
    },
    "Hugging Face": {
        "icon": "🤗",
        "modes": {
            "Access Token": {
                "inject": True,
                "fields": [
                    {"label": "Token", "env": "HUGGINGFACE_TOKEN", "secret": True, "placeholder": "hf_..."},
                ],
            },
        },
    },
    "LM Studio (Local)": {
        "icon": "🖥️",
        "modes": {
            "Local Server": {
                "inject": True,
                "fields": [
                    {"label": "Base URL", "env": "LM_STUDIO_BASE_URL", "secret": False, "placeholder": "http://localhost:1234"},
                ],
            },
        },
    },
    "LLaMA.cpp (Local)": {
        "icon": "🦙",
        "modes": {
            "Local Server": {
                "inject": True,
                "fields": [
                    {"label": "Base URL", "env": "LLAMACPP_BASE_URL", "secret": False, "placeholder": "http://localhost:8080"},
                ],
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Backend — keyring preferred, file fallback
# ---------------------------------------------------------------------------

def _try_keyring():
    try:
        import keyring  # noqa: PLC0415
        return keyring
    except ImportError:
        return None


_keyring = _try_keyring()


def _creds_path() -> Path:
    p = Path.home() / ".sage"
    p.mkdir(exist_ok=True)
    return p / ".credentials"


def _load_file() -> dict[str, str]:
    p = _creds_path()
    if not p.exists():
        return {}
    try:
        raw = p.read_bytes()
        return json.loads(base64.b64decode(raw).decode("utf-8"))
    except Exception:
        return {}


def _save_file(data: dict[str, str]) -> None:
    try:
        _creds_path().write_bytes(base64.b64encode(json.dumps(data).encode("utf-8")))
    except Exception as exc:
        log.warning("Could not save credentials file: %s", exc)


def _key(agent: str, env_var: str) -> str:
    return f"{agent}{_SEP}{env_var}"


def set_credential(agent: str, env_var: str, value: str) -> None:
    """Persist a credential. Uses OS keychain when available."""
    k = _key(agent, env_var)
    if _keyring:
        try:
            _keyring.set_password(_SERVICE, k, value)
            return
        except Exception as exc:
            log.debug("keyring.set_password failed, using file: %s", exc)
    data = _load_file()
    data[k] = value
    _save_file(data)


def get_credential(agent: str, env_var: str) -> str:
    """Retrieve a stored credential."""
    k = _key(agent, env_var)
    if _keyring:
        try:
            val = _keyring.get_password(_SERVICE, k)
            if val is not None:
                return val
        except Exception as exc:
            log.debug("keyring.get_password failed, using file: %s", exc)
    return _load_file().get(k, "")


def delete_credential(agent: str, env_var: str) -> None:
    """Remove a stored credential."""
    k = _key(agent, env_var)
    if _keyring:
        try:
            _keyring.delete_password(_SERVICE, k)
        except Exception:
            pass
    data = _load_file()
    data.pop(k, None)
    _save_file(data)


def inject_all() -> None:
    """Inject every stored env-var credential into os.environ.

    Called at app startup so all child processes (claude, codex, …) inherit them.
    Only non-empty values are injected; existing env vars already set by the user
    are NOT overwritten — the shell always wins.
    """
    if _keyring:
        # keyring has no list API, read from file as index, values from keyring
        raw = _load_file()
        keys_to_read = list(raw.keys())
    else:
        raw = _load_file()
        keys_to_read = list(raw.keys())

    for k in keys_to_read:
        if _SEP not in k:
            continue
        agent, env_var = k.split(_SEP, 1)
        value = get_credential(agent, env_var)
        if value and env_var not in os.environ:
            os.environ[env_var] = value
            log.debug("injected %s from stored credentials (%s)", env_var, agent)


def using_keyring() -> bool:
    return _keyring is not None
