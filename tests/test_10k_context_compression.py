"""10k-token context compression verification."""

from sage.context.compression import ContextCompressor
from sage.context.manager import ContextManager


def _build_pytest_output(min_tokens: int = 10_000) -> tuple[str, int]:
    """Build deterministic pytest-like output at or above min_tokens."""
    compressor = ContextCompressor()
    lines = [
        "============================= test session starts =============================",
        "platform win32 -- Python 3.11.0, pytest-7.4.0",
        "rootdir: D:/work/sage",
        "collected 0 items",
        "",
    ]

    index = 0
    while compressor.estimate_tokens("\n".join(lines)) < min_tokens:
        module = index // 25
        case = index % 25
        lines.append(
            f"tests/test_context_window_{module:03d}.py::"
            f"test_repeated_context_payload_{case:02d} PASSED"
            f"                      [ {index % 100:3d}%]"
        )
        index += 1

    lines[3] = f"collected {index} items"
    lines.append(f"========================== {index} passed in 31.42s ==========================")
    text = "\n".join(lines)
    return text, compressor.estimate_tokens(text)


def test_10k_token_context_compression_saves_tokens():
    """Verify a 10k-token command transcript compresses aggressively."""
    compressor = ContextCompressor()
    transcript, original_tokens = _build_pytest_output()

    compressed = compressor.compress(transcript, strategy="test_output")
    compressed_tokens = compressor.estimate_tokens(compressed)
    saved_tokens = original_tokens - compressed_tokens
    savings_percent = saved_tokens / original_tokens * 100

    print("\n10k token compression result:")
    print(f"  original_tokens={original_tokens}")
    print(f"  compressed_tokens={compressed_tokens}")
    print(f"  saved_tokens={saved_tokens}")
    print(f"  savings_percent={savings_percent:.1f}%")
    print(f"  compressed_context={compressed!r}")

    assert original_tokens >= 10_000
    assert compressed_tokens < original_tokens
    assert saved_tokens >= 9_000
    assert savings_percent >= 90.0
    assert "Tests:" in compressed


def test_10k_token_client_context_budget():
    """Verify client-facing context compression can fit a 10k-token transcript."""
    manager = ContextManager()
    transcript, original_tokens = _build_pytest_output()

    compressed = manager.compress_for_client(transcript, max_tokens=1_000)
    compressed_tokens = manager.tracker.estimate_tokens(compressed)
    saved_tokens = original_tokens - compressed_tokens
    savings_percent = saved_tokens / original_tokens * 100

    print("\n10k token client context result:")
    print(f"  original_tokens={original_tokens}")
    print(f"  compressed_tokens={compressed_tokens}")
    print(f"  saved_tokens={saved_tokens}")
    print(f"  savings_percent={savings_percent:.1f}%")

    assert original_tokens >= 10_000
    assert compressed_tokens <= 1_100
    assert saved_tokens >= 8_900
    assert savings_percent >= 89.0
    # Budget met either by strategy compression alone (summary anchors kept)
    # or by the head/tail truncation fallback (marker present).
    assert "Tests:" in compressed or "lines hidden" in compressed
