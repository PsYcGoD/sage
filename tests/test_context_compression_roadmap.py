"""Roadmap coverage for token and context compression."""

from sage.context.compression import ContextCompressor
from sage.context.benchmarks import run_benchmark
from sage.context.tracker import TokenTracker


def test_compressor_and_tracker_share_token_counts():
    text = "pytest failed with AssertionError and traceback\n" * 20
    assert ContextCompressor().estimate_tokens(text) == TokenTracker().estimate_tokens(text)


def test_compression_floor_and_correctness_anchors():
    text = "\n".join(
        [
            "Traceback (most recent call last):",
            "  File \"app.py\", line 1, in <module>",
            "ValueError: first error",
            "noise line " * 20,
            "RuntimeError: last error",
            "exit code 1",
        ]
    )
    compressed = ContextCompressor().compress(text, strategy="generic")
    assert compressed.strip()
    assert "First error:" in compressed
    assert "Last error:" in compressed
    assert "exit code 1" in compressed


def test_package_build_progress_and_diff_strategy_metrics():
    samples = {
        "package_manager": "npm WARN deprecated left-pad\nnpm ERR! missing script build\n" * 30,
        "build_log": "vite building...\nERROR failed to compile TypeScript\n" * 30,
        "progress": "Downloading package [########      ] 70%\nDownloading package [##############] 100%\n" * 30,
        "diff": "diff --git a/app.py b/app.py\n@@ -1,2 +1,2 @@\n-def old(): pass\n+def new(): return 1\n" * 20,
    }
    compressor = ContextCompressor()
    for strategy, text in samples.items():
        compressed = compressor.compress(text, strategy=strategy)
        assert compressed.strip()
        assert compressor.estimate_tokens(compressed) < compressor.estimate_tokens(text)

    stats = compressor.get_stats()
    for strategy in samples:
        assert strategy in stats["by_strategy"]
        assert stats["by_strategy"][strategy]["saved_tokens"] > 0
    assert stats["verified_tokenizer"] in {"tiktoken", "fallback"}


def test_golden_outputs_preserve_key_failure_lines():
    compressor = ContextCompressor()
    samples = [
        ("stacktrace", "Traceback (most recent call last):\n  File \"x.py\", line 1\nValueError: boom\n"),
        ("test_output", "tests/test_x.py::test_a FAILED\nAssertionError: nope\n===== 1 failed in 0.1s =====\n"),
        ("package_manager", "pip install demo\nERROR: Could not find a version that satisfies the requirement demo\n"),
        ("package_manager", "npm ERR! code ERESOLVE\nnpm ERR! unable to resolve dependency tree\n"),
        ("build_log", "webpack compiled with 1 error\nERROR in ./src/app.ts\n"),
        ("diff", "diff --git a/a.py b/a.py\n@@ -1 +1 @@\n-def old(): pass\n+def new(): return 1\n"),
    ]
    for strategy, text in samples:
        compressed = compressor.compress(text, strategy=strategy)
        assert compressed.strip()
        assert any(token in compressed.lower() for token in ["error", "err", "failed", "diff", "tests:", "build", "def new"])


def test_benchmark_fixture_generator_hits_target_and_saves_tokens():
    result = run_benchmark(5_000)
    assert result.original_tokens >= 5_000
    assert result.compressed_tokens < result.original_tokens
    assert result.saved_tokens > 0
