"""Single source of truth for token counting across SAGE.

Uses the real `tiktoken` tokenizer when available (the same BPE family the
Claude/OpenAI-class models use), and falls back to a character heuristic only
if tiktoken cannot be loaded. Every part of SAGE should call `count_tokens`
so the numbers shown in the GUI, CLI, and stored metrics are consistent.
"""

from __future__ import annotations

from functools import lru_cache

# Approx characters per token for the fallback path (English text/code average).
_FALLBACK_CHARS_PER_TOKEN = 4

_ENCODER = None
_ENCODER_LOADED = False
USING_REAL_TOKENIZER = False


def _get_encoder():
    """Lazily load and cache the tiktoken encoder (None if unavailable)."""
    global _ENCODER, _ENCODER_LOADED, USING_REAL_TOKENIZER
    if _ENCODER_LOADED:
        return _ENCODER
    _ENCODER_LOADED = True
    try:
        import tiktoken

        _ENCODER = tiktoken.get_encoding("cl100k_base")
        USING_REAL_TOKENIZER = True
    except Exception:
        _ENCODER = None
        USING_REAL_TOKENIZER = False
    return _ENCODER


def _fallback_count(text: str) -> int:
    """Character-based estimate used only when tiktoken is unavailable."""
    return max(1, len(text) // _FALLBACK_CHARS_PER_TOKEN)


@lru_cache(maxsize=2048)
def _count_cached(text: str) -> int:
    encoder = _get_encoder()
    if encoder is None:
        return _fallback_count(text)
    try:
        return len(encoder.encode(text))
    except Exception:
        return _fallback_count(text)


def count_tokens(text: str) -> int:
    """Return the token count for `text` (0 for empty)."""
    if not text:
        return 0
    # Cache on reasonably sized strings; skip the cache for very large inputs
    # so we don't retain big strings in memory.
    if len(text) <= 20000:
        return _count_cached(text)
    encoder = _get_encoder()
    if encoder is None:
        return _fallback_count(text)
    try:
        return len(encoder.encode(text))
    except Exception:
        return _fallback_count(text)


def is_real_tokenizer() -> bool:
    """True if the accurate tiktoken tokenizer is active (not the fallback)."""
    _get_encoder()
    return USING_REAL_TOKENIZER
