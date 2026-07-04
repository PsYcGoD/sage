"""Unit tests for context compression."""

import pytest
from sage.context.compression import ContextCompressor


class TestContextCompressor:
    """Test context compression functionality."""

    def test_pytest_output_compression(self):
        """Test compression of pytest output achieves >50%."""
        test_output = """================================ test session starts ================================
platform win32 -- Python 3.11.0
collected 45 items

tests/test_one.py::test_one PASSED                      [  2%]
tests/test_two.py::test_two PASSED                      [  4%]
tests/test_three.py::test_three PASSED                  [  6%]

======================== 45 passed in 12.34s ========================"""

        compressor = ContextCompressor()
        compressed = compressor.compress(test_output, 'test_output')
        
        original_tokens = compressor.estimate_tokens(test_output)
        compressed_tokens = compressor.estimate_tokens(compressed)
        ratio = ((original_tokens - compressed_tokens) / original_tokens * 100)
        
        assert ratio > 50, f"Expected >50% compression, got {ratio:.1f}%"
        assert 'Tests:' in compressed or 'PASSED' in compressed

    def test_token_estimation(self):
        """Test token estimation accuracy."""
        compressor = ContextCompressor()
        
        assert compressor.estimate_tokens('') == 0
        assert compressor.estimate_tokens('hello world') > 0
        assert compressor.estimate_tokens('a' * 100) >= 1  # 100 'a's = 1 word token

    def test_compression_stats(self):
        """Test compression statistics tracking."""
        compressor = ContextCompressor()
        
        compressor.compress('test output', 'auto')
        compressor.compress('more test', 'auto')
        
        stats = compressor.get_stats()
        
        assert stats['compressions'] == 2
        assert stats['original_tokens'] > 0
        assert 'avg_ratio' in stats
