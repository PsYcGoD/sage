"""Context management system."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from .compression import (
    ContextCompressor,
    compress_output,
    smart_diff,
    summarize_long_output,
    extract_stacktrace,
    compress_file_content,
)
from .tracker import TokenTracker


class ContextManager:
    """Manage context to minimize token usage."""

    def __init__(self):
        self.tracker = TokenTracker()
        self.compressor = ContextCompressor()
        self.compression_enabled = True
        self.max_output_lines = 50

    def process_command_output(
        self,
        stdout: str,
        stderr: str,
        exit_code: int,
        run_id: Optional[int] = None,
    ) -> Dict[str, str]:
        """
        Process command output for context efficiency.
        
        Returns dict with:
        - summary: Short summary for local assistant
        - full_output: Original output (stored in DB)
        - compressed_output: Context-efficient version
        - token_estimate: Estimated tokens saved
        """
        combined = f"{stdout}\n{stderr}".strip()
        
        if not self.compression_enabled:
            return {
                'summary': combined,
                'full_output': combined,
                'compressed_output': combined,
                'token_estimate': 0,
            }

        result = self.compressor.compress_with_result(combined, strategy="auto")
        compressed = result.compressed_text

        if len(compressed) > 4000:
            compressed = summarize_long_output(compressed, max_chars=4000)
            compressed_tokens = self.tracker.estimate_tokens(compressed)
        else:
            compressed_tokens = result.compressed_tokens

        original_tokens = result.original_tokens
        if compressed_tokens > original_tokens:
            compressed_tokens = original_tokens
        token_savings = max(0, original_tokens - compressed_tokens)

        # Record usage
        if run_id:
            self.tracker.record_usage(run_id, original_tokens, compressed_tokens)

        return {
            'summary': compressed,
            'full_output': combined,
            'compressed_output': compressed,
            'token_savings': token_savings,
            'compression_ratio': f"{(token_savings / original_tokens) * 100:.1f}%" if original_tokens > 0 else "0%",
            'original_tokens': original_tokens,
            'compressed_tokens': compressed_tokens,
            'strategy': result.strategy,
            'verified_tokenizer': self.compressor.get_stats().get("verified_tokenizer", "unknown"),
        }

    def smart_file_read(
        self,
        file_path: Path,
        previous_content: Optional[str] = None,
    ) -> str:
        """
        Smart file reading that shows only changes if file was read before.
        
        This is HUGE for saving context!
        """
        try:
            current_content = file_path.read_text(encoding='utf-8')
        except Exception:
            return "[Error reading file]"

        # If no previous version, compress the content
        if previous_content is None:
            return compress_file_content(current_content, max_lines=100)

        # If file unchanged, just say so
        if current_content == previous_content:
            return "[File unchanged since last read]"

        # Show only the diff!
        diff = smart_diff(previous_content, current_content, context_lines=3)
        return f"Changes to {file_path.name}:\n{diff}"

    def get_token_stats(self) -> Dict:
        """Get token usage statistics."""
        return self.tracker.get_stats()

    def suggest_context_optimizations(self, output: str) -> list[str]:
        """
        Analyze output and suggest ways to reduce context.
        
        Returns list of suggestions.
        """
        suggestions = []
        lines = output.splitlines()

        if len(lines) > 100:
            suggestions.append(
                f"Output has {len(lines)} lines. Consider piping through grep or head."
            )

        if len(output) > 10000:
            suggestions.append(
                f"Output is {len(output)} chars. Use --quiet or redirect to file."
            )

        # Check for repeated patterns
        unique_lines = len(set(lines))
        if len(lines) > 50 and unique_lines < len(lines) * 0.5:
            suggestions.append(
                f"Output has many duplicates ({unique_lines}/{len(lines)} unique). Consider deduplicating."
            )

        # Check for verbose logging
        debug_count = sum(1 for line in lines if 'DEBUG' in line or 'TRACE' in line)
        if debug_count > 10:
            suggestions.append(
                f"Output has {debug_count} debug lines. Disable debug logging to save context."
            )

        return suggestions

    def compress_for_client(
        self,
        text: str,
        max_tokens: int = 1000,
    ) -> str:
        """
        Compress text specifically for client context.
        
        Target a specific token budget.
        """
        current_tokens = self.tracker.estimate_tokens(text)

        if current_tokens <= max_tokens:
            return text

        compressed = self.compressor.compress(text, strategy="auto")
        if self.tracker.estimate_tokens(compressed) <= max_tokens:
            return compressed

        lines = compressed.splitlines()
        keep_ratio = max_tokens / max(1, self.tracker.estimate_tokens(compressed))
        keep_lines = int(len(lines) * keep_ratio)
        if keep_lines < 10:
            keep_lines = 10

        compressed_lines = lines[:keep_lines // 2]
        compressed_lines.append(f"... [{len(lines) - keep_lines} lines hidden] ...")
        compressed_lines.extend(lines[-(keep_lines // 2):])

        return "\n".join(compressed_lines)


