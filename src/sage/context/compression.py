"""Output compression for context efficiency."""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from typing import Dict

from .tokens import count_tokens, is_real_tokenizer


@dataclass(frozen=True)
class CompressionResult:
    original_text: str
    compressed_text: str
    strategy: str
    original_tokens: int
    compressed_tokens: int

    @property
    def saved_tokens(self) -> int:
        return max(0, self.original_tokens - self.compressed_tokens)

    @property
    def ratio(self) -> float:
        return (self.saved_tokens / self.original_tokens * 100) if self.original_tokens else 0.0


class ContextCompressor:
    """Context compressor with tiktoken-based accounting and strategy metrics."""

    def __init__(self):
        self.compression_stats = {
            "total_original": 0,
            "total_compressed": 0,
            "compressions": 0,
            "by_strategy": {},
        }
        self.last_result: CompressionResult | None = None

    def compress(self, text: str, strategy: str = "auto") -> str:
        """Compress text using a named strategy and keep a non-empty correctness floor."""
        return self.compress_with_result(text, strategy=strategy).compressed_text

    def compress_with_result(self, text: str, strategy: str = "auto") -> CompressionResult:
        if not text or not text.strip():
            result = CompressionResult(text, text, strategy, self.estimate_tokens(text), self.estimate_tokens(text))
            self.last_result = result
            return result

        original_tokens = self.estimate_tokens(text)
        resolved_strategy = self._detect_strategy(text) if strategy == "auto" else strategy
        compressed = self._compress_by_strategy(text, resolved_strategy)
        compressed = self._protect_correctness(text, compressed)
        compressed = self._compression_floor(text, compressed)
        compressed_tokens = self.estimate_tokens(compressed)

        result = CompressionResult(text, compressed, resolved_strategy, original_tokens, compressed_tokens)
        self._record_stats(result)
        self.last_result = result
        return result

    def estimate_tokens(self, text: str) -> int:
        """Count tokens through the shared tokenizer source of truth."""
        return count_tokens(text)

    def get_stats(self) -> Dict:
        """Get aggregate and per-strategy compression statistics."""
        original = self.compression_stats["total_original"]
        compressed = self.compression_stats["total_compressed"]
        if original == 0:
            return {
                "compressions": 0,
                "total_savings": 0,
                "avg_ratio": "0.0%",
                "by_strategy": {},
                "verified_tokenizer": "tiktoken" if is_real_tokenizer() else "fallback",
            }

        saved = max(0, original - compressed)
        by_strategy = {}
        for strategy, values in self.compression_stats["by_strategy"].items():
            strategy_original = values["original_tokens"]
            strategy_saved = max(0, strategy_original - values["compressed_tokens"])
            by_strategy[strategy] = {
                **values,
                "saved_tokens": strategy_saved,
                "ratio": f"{(strategy_saved / strategy_original * 100) if strategy_original else 0:.1f}%",
            }
        return {
            "compressions": self.compression_stats["compressions"],
            "original_tokens": original,
            "compressed_tokens": compressed,
            "total_savings": saved,
            "avg_ratio": f"{(saved / original * 100):.1f}%",
            "by_strategy": by_strategy,
            "verified_tokenizer": "tiktoken" if is_real_tokenizer() else "fallback",
        }

    def _record_stats(self, result: CompressionResult) -> None:
        self.compression_stats["total_original"] += result.original_tokens
        self.compression_stats["total_compressed"] += result.compressed_tokens
        self.compression_stats["compressions"] += 1
        bucket = self.compression_stats["by_strategy"].setdefault(
            result.strategy,
            {"compressions": 0, "original_tokens": 0, "compressed_tokens": 0},
        )
        bucket["compressions"] += 1
        bucket["original_tokens"] += result.original_tokens
        bucket["compressed_tokens"] += result.compressed_tokens

    def _detect_strategy(self, text: str) -> str:
        lowered = text.lower()
        if _looks_like_diff(text):
            return "diff"
        if _looks_like_test_output(lowered):
            return "test_output"
        if "traceback" in lowered or "exception" in lowered:
            return "stacktrace"
        if _looks_like_package_log(lowered):
            return "package_manager"
        if _looks_like_build_log(lowered):
            return "build_log"
        if _looks_like_progress(lowered):
            return "progress"
        if re.search(r"^\d{4}-\d{2}-\d{2}.*\[.*\]", text, re.MULTILINE):
            return "logs"
        if text.startswith(("import ", "from ", "class ", "def ")):
            return "code"
        return "generic"

    def _compress_by_strategy(self, text: str, strategy: str) -> str:
        if strategy == "test_output":
            return self._compress_test_output(text)
        if strategy == "logs":
            return self._compress_logs(text)
        if strategy == "code":
            return compress_file_content(text, max_lines=100)
        if strategy == "stacktrace":
            return extract_stacktrace(text)
        if strategy == "package_manager":
            return self._compress_package_manager(text)
        if strategy == "build_log":
            return self._compress_build_log(text)
        if strategy == "progress":
            return self._compress_progress(text)
        if strategy == "diff":
            return self._compress_diff(text)
        return compress_output(text)

    def _compression_floor(self, original: str, compressed: str) -> str:
        if compressed and compressed.strip():
            return compressed
        first = next((line.strip() for line in original.splitlines() if line.strip()), "")
        if first:
            return f"[compressed output preserved first line]\n{first[:500]}"
        return "[compressed non-empty output]"

    def _protect_correctness(self, original: str, compressed: str) -> str:
        anchors = _correctness_anchors(original)
        if not anchors:
            return compressed
        existing = compressed.lower()
        missing = []
        for line in anchors:
            probe = line.split(": ", 1)[1] if ": " in line else line
            if probe.lower() not in existing:
                missing.append(line)
        if not missing:
            return compressed
        protected = ["Preserved correctness anchors:"]
        protected.extend(f"- {line}" for line in missing[:12])
        return "\n".join([compressed.strip(), "", *protected]).strip()

    def _compress_test_output(self, text: str) -> str:
        lines = text.splitlines()
        passed = _count_pattern(text, r"\bPASSED\b|\bpassed\b")
        failed_lines = _failed_lines(text)
        skipped = _count_pattern(text, r"\bSKIPPED\b|\bskipped\b")
        summary = _last_matching_line(lines, ["passed", "failed", "error", "skipped"])

        result = [f"Tests: passed={passed} failed={len(failed_lines)} skipped={skipped}"]
        if summary:
            result.append(f"Summary: {summary}")
        if failed_lines:
            result.append("Failed:")
            result.extend(f"  - {line}" for line in failed_lines[:12])
            if len(failed_lines) > 12:
                result.append(f"  ... +{len(failed_lines) - 12} more")
        return "\n".join(result)

    def _compress_logs(self, text: str) -> str:
        lines = text.splitlines()
        errors = [line for line in lines if _is_error(line)]
        warnings = [line for line in lines if _is_warning(line)]
        result = [f"Log lines: {len(lines)}"]
        if errors:
            result.append(f"Errors ({len(errors)}):")
            result.extend(f"  - {_strip_log_prefix(line)}" for line in errors[:6])
        if warnings:
            result.append(f"Warnings ({len(warnings)}):")
            result.extend(f"  - {_strip_log_prefix(line)}" for line in warnings[:4])
        if len(result) == 1:
            result.append("No error/warning lines detected.")
        return "\n".join(result)

    def _compress_package_manager(self, text: str) -> str:
        lines = text.splitlines()
        managers = [name for name in ["npm", "pip", "uv", "poetry", "pnpm", "yarn"] if name in text.lower()]
        important = [
            line.strip()
            for line in lines
            if any(token in line.lower() for token in ["error", "warn", "failed", "conflict", "missing", "not found", "eresolve", "enoent"])
        ]
        installs = _count_pattern(text, r"\b(installed|downloaded|resolved|added|updated)\b")
        result = [f"Package manager log: managers={','.join(managers) or 'unknown'} lines={len(lines)} installs={installs}"]
        if important:
            result.append("Important package lines:")
            result.extend(f"  - {line[:240]}" for line in _dedupe(important)[:12])
        return "\n".join(result)

    def _compress_build_log(self, text: str) -> str:
        lines = text.splitlines()
        tools = [name for name in ["webpack", "vite", "flutter", "gradle", "maven", "docker", "typescript", "tsc"] if name in text.lower()]
        important = [
            line.strip()
            for line in lines
            if any(token in line.lower() for token in ["error", "failed", "warning", "built", "compiled", "exception", "cannot"])
        ]
        result = [f"Build log: tools={','.join(tools) or 'unknown'} lines={len(lines)}"]
        result.extend(f"  - {line[:240]}" for line in _dedupe(important)[:14])
        return "\n".join(result)

    def _compress_progress(self, text: str) -> str:
        lines = text.splitlines()
        important = [line.strip() for line in lines if _is_error(line) or _is_warning(line)]
        percentages = re.findall(r"(\d{1,3})%", text)
        result = [f"Progress output: lines={len(lines)} updates={len(percentages)}"]
        if percentages:
            result.append(f"Progress range: {percentages[0]}% -> {percentages[-1]}%")
        result.extend(f"  - {line[:240]}" for line in _dedupe(important)[:8])
        return "\n".join(result)

    def _compress_diff(self, text: str) -> str:
        lines = text.splitlines()
        result = []
        kept_hunks = 0
        for line in lines:
            if line.startswith(("diff --git", "Index:", "+++ ", "--- ")):
                result.append(line[:240])
            elif line.startswith("@@"):
                kept_hunks += 1
                if kept_hunks <= 12:
                    result.append(line[:240])
            elif kept_hunks <= 12 and line.startswith(("+", "-")) and not line.startswith(("+++", "---")):
                clean = line[:240]
                if any(token in clean.lower() for token in ["error", "test", "def ", "class ", "import ", "return", "todo"]):
                    result.append(clean)
        if not result:
            return compress_output(text, max_lines=50)
        return "\n".join(_dedupe(result))


def compress_output(output: str, max_lines: int = 50) -> str:
    """Generic command-output compression with correctness preservation."""
    if not output:
        return ""
    lines = [line for line in output.splitlines() if not _is_noise(line)]
    anchors = _correctness_anchors(output)

    seen = set()
    unique_lines = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            unique_lines.append(line)

    if len(unique_lines) > max_lines:
        keep = max(1, max_lines // 2)
        compressed = unique_lines[:keep]
        compressed.append(f"... [{len(unique_lines) - max_lines} lines hidden] ...")
        compressed.extend(unique_lines[-keep:])
    else:
        compressed = unique_lines

    for anchor in anchors:
        if anchor not in compressed:
            compressed.append(anchor)
    return "\n".join(compressed)


def smart_diff(file_before: str, file_after: str, context_lines: int = 3) -> str:
    before_lines = file_before.splitlines()
    after_lines = file_after.splitlines()
    diff = difflib.unified_diff(before_lines, after_lines, lineterm="", n=context_lines)
    return "\n".join(diff)


def summarize_long_output(output: str, max_chars: int = 1000) -> str:
    if len(output) <= max_chars:
        return output
    lines = output.splitlines()
    errors = [line for line in lines if _is_error(line)]
    warnings = [line for line in lines if _is_warning(line)]
    summary_parts = []
    if errors:
        summary_parts.append(f"Errors ({len(errors)}):")
        summary_parts.extend(errors[:8])
    if warnings:
        summary_parts.append(f"Warnings ({len(warnings)}):")
        summary_parts.extend(warnings[:5])
    summary_parts.append(f"[Full output: {len(output)} chars, {len(lines)} lines]")
    return "\n".join(summary_parts)


def extract_stacktrace(output: str) -> str:
    lines = output.splitlines()
    starts = [i for i, line in enumerate(lines) if any(token in line for token in ["Traceback", "Error", "Exception"])]
    if not starts:
        return output
    start = starts[0]
    end = min(len(lines), start + 60)
    return "\n".join(lines[start:end])


def compress_file_content(content: str, max_lines: int = 100) -> str:
    lines = content.splitlines()
    if len(lines) <= max_lines:
        return content

    imports = []
    code = []
    in_imports = True
    for line in lines:
        if in_imports and (line.startswith("import ") or line.startswith("from ")):
            imports.append(line)
        else:
            in_imports = False
            code.append(line)

    budget = max(10, max_lines - len(imports))
    if len(code) > budget:
        keep = max(1, budget // 2)
        code = code[:keep] + [f"... [{len(code) - (keep * 2)} lines hidden] ..."] + code[-keep:]
    return "\n".join(imports + code)


def _correctness_anchors(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    error_lines = [line for line in lines if _is_error(line) or "traceback" in line.lower()]
    summary_lines = []
    for line in lines:
        lowered = line.lower()
        if " passed" in line or line.endswith("PASSED"):
            continue
        if line.startswith(("=", "-", "*")) and re.search(r"\b(failed|passed|errors?|warnings?|skipped)\b", lowered):
            summary_lines.append(line)
        elif re.search(r"\b(exit code|summary|errors?|warnings?)\b", lowered):
            summary_lines.append(line)
    anchors = []
    if error_lines:
        anchors.append(f"First error: {error_lines[0][:300]}")
        anchors.append(f"Last error: {error_lines[-1][:300]}")
    anchors.extend(line[:300] for line in summary_lines[:5])
    return _dedupe(anchors)


def _is_noise(line: str) -> bool:
    return any(
        re.match(pattern, line)
        for pattern in [
            r"^\s*$",
            r"^DEBUG:",
            r"^TRACE:",
            r"^\[.*\] DEBUG",
            r"^\s*at .*\(internal/",
        ]
    )


def _is_error(line: str) -> bool:
    lowered = line.lower()
    return any(token in lowered for token in ["error", "exception", "failed", "fatal", "traceback"])


def _is_warning(line: str) -> bool:
    lowered = line.lower()
    return "warning" in lowered or "warn:" in lowered or "npm warn" in lowered


def _strip_log_prefix(line: str) -> str:
    parts = line.split("]", 1)
    return parts[1].strip() if len(parts) > 1 else line.strip()


def _failed_lines(text: str) -> list[str]:
    return _dedupe(
        [
            line.strip()
            for line in text.splitlines()
            if re.search(r"\bFAILED\b|\bfailed\b", line) and not line.strip().startswith(("=", "-", "*"))
        ]
    )


def _last_matching_line(lines: list[str], keywords: list[str]) -> str:
    for line in reversed(lines):
        if any(keyword in line.lower() for keyword in keywords):
            return line.strip()[:300]
    return ""


def _count_pattern(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, flags=re.IGNORECASE))


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _looks_like_test_output(text: str) -> bool:
    return any(token in text for token in ["pytest", "test session starts", " passed", " failed", "unittest", "jest"])


def _looks_like_package_log(text: str) -> bool:
    return any(token in text for token in ["npm warn", "npm err", "pip install", "collecting ", "uv pip", "poetry", "pnpm", "yarn"])


def _looks_like_build_log(text: str) -> bool:
    return any(token in text for token in ["webpack", "vite", "flutter", "gradle", "maven", "docker build", "typescript", "tsc "])


def _looks_like_progress(text: str) -> bool:
    return bool(re.search(r"(\d{1,3}%|\[[=>#.\-\s]{8,}\]|spinner|downloading)", text))


def _looks_like_diff(text: str) -> bool:
    return text.startswith("diff --git") or "\n@@ " in text or "\n+++ " in text and "\n--- " in text
