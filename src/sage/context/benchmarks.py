"""Deterministic compression benchmark fixtures."""

from __future__ import annotations

from dataclasses import dataclass

from .compression import ContextCompressor


@dataclass(frozen=True)
class BenchmarkResult:
    target_tokens: int
    original_tokens: int
    compressed_tokens: int
    saved_tokens: int
    compression_rate: float
    strategy: str


def build_benchmark_output(min_tokens: int) -> str:
    """Build deterministic noisy command output with at least `min_tokens` tokens."""
    compressor = ContextCompressor()
    lines = [
        "pytest test session starts",
        "platform win32 -- Python 3.13",
        "collected 240 items",
    ]
    token_count = compressor.estimate_tokens("\n".join(lines))
    index = 0
    target_with_buffer = int(min_tokens * 1.05) + 500
    while token_count < target_with_buffer:
        chunk = [
            f"tests/test_module_{index % 17}.py::test_case_{index} PASSED",
            f"npm WARN deprecated package-{index % 9}@1.0.{index % 5}: use maintained-package instead",
            f"Downloading package-{index % 13} [{'#' * ((index % 10) + 1):<10}] {index % 100}%",
            f"vite building chunk {index % 21}...",
        ]
        if index % 23 == 0:
            chunk.extend(
                [
                    f"tests/test_module_{index % 17}.py::test_edge_{index} FAILED",
                    "AssertionError: expected compressed output to preserve first error",
                    "RuntimeError: last error marker for benchmark preservation",
                ]
            )
        lines.extend(chunk)
        token_count += compressor.estimate_tokens("\n".join(chunk)) + 1
        index += 1
    return "\n".join(lines)


def run_benchmark(target_tokens: int, strategy: str = "auto") -> BenchmarkResult:
    compressor = ContextCompressor()
    original = build_benchmark_output(target_tokens)
    result = compressor.compress_with_result(original, strategy=strategy)
    return BenchmarkResult(
        target_tokens=target_tokens,
        original_tokens=result.original_tokens,
        compressed_tokens=result.compressed_tokens,
        saved_tokens=result.saved_tokens,
        compression_rate=result.ratio,
        strategy=result.strategy,
    )


def run_benchmarks(sizes: list[int] | None = None) -> list[BenchmarkResult]:
    sizes = sizes or [5_000, 10_000, 50_000, 100_000]
    return [run_benchmark(size) for size in sizes]
