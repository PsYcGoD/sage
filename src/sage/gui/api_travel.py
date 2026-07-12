"""API-Travel — classify query complexity, pick cheapest capable agent.

Routing order (cheapest first):
  Ollama (local/free) → handles simple queries
  Codex CLI           → handles medium queries
  Claude API          → handles complex queries

Session context is always shared: the caller must inject conversation history
into the picked client via client.load_history() before sending.
"""

from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path

log = logging.getLogger(__name__)

SIMPLE  = "simple"
MEDIUM  = "medium"
COMPLEX = "complex"

_TIER = {SIMPLE: 0, MEDIUM: 1, COMPLEX: 2}

# (agent_name, max_complexity_it_handles, friendly_label) — cheapest first
_PROVIDERS: list[tuple[str, str, str]] = [
    ("ollama",      SIMPLE,  "Ollama (local)"),
    ("groq",        MEDIUM,  "Groq"),
    ("gemini",      MEDIUM,  "Gemini"),
    ("openrouter",  MEDIUM,  "OpenRouter"),
    ("codex",       MEDIUM,  "Codex CLI"),
    ("claude",      COMPLEX, "Claude"),
]

_COMPLEX_KW = frozenset({
    "implement", "refactor", "architect", "build a", "create a full",
    "write a complete", "migrate", "full implementation", "entire",
    "throughout", "every file", "test suite", "multiple files",
    "rewrite", "overhaul", "redesign", "all tests", "production ready",
    "add feature", "new feature", "deploy", "end to end",
})

_SIMPLE_KW = frozenset({
    "what is", "what's", "what are", "why is", "how do i",
    "explain briefly", "define ", "list the", "list all",
    "hi ", "hello", "thanks", "thank you", "what does",
    "how does", "tell me about",
})


def classify(prompt: str, history: list[dict] | None = None) -> str:
    """Classify message complexity using local heuristics — no API call."""
    words  = len(prompt.split())
    blocks = prompt.count("```")
    frefs  = len(re.findall(
        r'\b\w+\.(py|ts|tsx|js|go|rs|java|cpp|c|cs|yaml|json|toml|sql)\b',
        prompt,
    ))
    depth  = len(history or [])
    text   = prompt.lower()

    # Hard complex signals
    if (words > 150 or blocks >= 2 or frefs >= 3 or depth >= 10 or
            any(kw in text for kw in _COMPLEX_KW)):
        return COMPLEX

    # Hard simple signals
    if (words <= 40 and blocks == 0 and frefs == 0 and
            any(kw in text for kw in _SIMPLE_KW)):
        return SIMPLE

    return MEDIUM


# ---------------------------------------------------------------------------
# Availability detection (cached 30 s so repeated sends don't hammer localhost)
# ---------------------------------------------------------------------------

_cache: dict[str, bool] = {}
_cache_ts: float = 0.0
_CACHE_TTL = 30.0


def _ollama_up() -> bool:
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=1)
        return True
    except Exception:
        return False


def _groq_up() -> bool:
    return bool(os.getenv("GROQ_API_KEY"))


def _gemini_up() -> bool:
    return bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))


def _openrouter_up() -> bool:
    return bool(os.getenv("OPENROUTER_API_KEY"))


def _codex_up() -> bool:
    import shutil
    return shutil.which("codex") is not None


def _claude_up() -> bool:
    if os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_BASE_URL"):
        return True
    return (Path.home() / ".claude" / "credentials.json").exists()


_CHECKS: dict[str, object] = {
    "ollama":     _ollama_up,
    "groq":       _groq_up,
    "gemini":     _gemini_up,
    "openrouter": _openrouter_up,
    "codex":      _codex_up,
    "claude":     _claude_up,
}


def detect_available(force: bool = False) -> list[str]:
    """Return names of available agents, cheapest first. Cached for 30 s."""
    global _cache, _cache_ts
    now = time.monotonic()
    if not force and (now - _cache_ts) < _CACHE_TTL and _cache:
        return [n for n, _, _ in _PROVIDERS if _cache.get(n)]

    fresh: dict[str, bool] = {}
    for name, _, _ in _PROVIDERS:
        fn = _CHECKS.get(name)
        try:
            fresh[name] = bool(fn and fn())
        except Exception:
            fresh[name] = False
            log.debug("suppressed availability check for %s", name, exc_info=True)

    _cache    = fresh
    _cache_ts = now
    log.debug("API-Travel available: %s", [n for n, v in fresh.items() if v])
    return [n for n, _, _ in _PROVIDERS if fresh.get(n)]


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def route(
    prompt: str,
    history: list[dict] | None = None,
    available: list[str] | None = None,
    force_agent: str | None = None,
) -> tuple[str, str, str]:
    """
    Pick the cheapest agent capable of handling this message.

    Returns (agent_name, complexity, ui_label).
    Falls back gracefully if no agents are available.
    """
    if force_agent:
        label = next((lbl for n, _, lbl in _PROVIDERS if n == force_agent),
                     force_agent.capitalize())
        return force_agent, COMPLEX, label

    if available is None:
        available = detect_available()

    complexity = classify(prompt, history)
    level      = _TIER[complexity]

    for name, max_c, label in _PROVIDERS:
        if name in available and _TIER[max_c] >= level:
            return name, complexity, label

    # Nothing capable found — return first available regardless of tier
    if available:
        name  = available[0]
        label = next((lbl for n, _, lbl in _PROVIDERS if n == name),
                     name.capitalize())
        return name, complexity, label

    # Absolute fallback
    return "claude", complexity, "Claude API"
