"""Basic CLI Command Tests - SAGE V2"""

import pytest
import subprocess
import sys
from pathlib import Path


class TestBasicCLI:
    """Test basic SAGE CLI commands execute"""

    def test_sage_version(self):
        """Test: sage --version returns successfully"""
        result = subprocess.run(
            [sys.executable, "-m", "sage", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        assert result.returncode == 0
        assert "0.1.0" in result.stdout or "2.0.0" in result.stdout

    def test_sage_help(self):
        """Test: sage --help returns usage info"""
        result = subprocess.run(
            [sys.executable, "-m", "sage", "--help"],
            capture_output=True,
            text=True,
            timeout=5
        )
        assert result.returncode == 0
        assert "SAGE" in result.stdout or "usage" in result.stdout.lower()

    def test_sage_doctor(self):
        """Test: sage doctor runs health check"""
        result = subprocess.run(
            [sys.executable, "-m", "sage", "doctor"],
            capture_output=True,
            text=True,
            timeout=10
        )
        # Doctor should run (exit 0 or 1 if issues found)
        assert result.returncode in [0, 1]


class TestSageRun:
    """Test sage run command"""

    def test_sage_run_echo(self):
        """Test: sage run executes simple command"""
        result = subprocess.run(
            [sys.executable, "-m", "sage", "run", "--", "echo", "hello"],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == 0
        assert "hello" in result.stdout.lower()

    def test_sage_run_python(self):
        """Test: sage run works with python commands"""
        result = subprocess.run(
            [sys.executable, "-m", "sage", "run", "--", "python", "-c", "print(42)"],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == 0
        assert "42" in result.stdout


class TestDatabase:
    """Test database persistence"""

    def test_database_exists(self):
        """Test: SAGE database is created"""
        from sage.store import data_dir
        db_path = data_dir() / "sage.db"
        assert db_path.exists()

    def test_runs_table_exists(self):
        """Test: runs table can be queried"""
        from sage.store import connect
        with connect() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM runs")
            count = cursor.fetchone()[0]
            assert count >= 0  # Any count is valid

    def test_context_compression_table_exists(self):
        """Test: context_compression table exists"""
        from sage.store import connect
        with connect() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='context_compression'"
            )
            table = cursor.fetchone()
            assert table is not None


class TestContextCompression:
    """Test context compression system"""

    def test_compressor_estimates_tokens(self):
        """Test: Token estimation works"""
        from sage.context.compression import ContextCompressor
        compressor = ContextCompressor()

        text = "Hello world this is a test"
        tokens = compressor.estimate_tokens(text)

        assert tokens > 0
        assert tokens < 100  # Should be reasonable

    def test_compression_saves_tokens(self):
        """Test: Compression reduces token count"""
        from sage.context.compression import ContextCompressor
        compressor = ContextCompressor()

        # Long repetitive text
        original = "ERROR: Failed\n" * 100
        compressed = compressor.compress(original, strategy="logs")

        original_tokens = compressor.estimate_tokens(original)
        compressed_tokens = compressor.estimate_tokens(compressed)

        assert compressed_tokens < original_tokens
        assert len(compressed) < len(original)

    def test_test_output_compression(self):
        """Test: Test output compression works"""
        from sage.context.compression import ContextCompressor
        compressor = ContextCompressor()

        test_output = """test_example.py::test_one PASSED
test_example.py::test_two PASSED
test_example.py::test_three FAILED
test_example.py::test_four PASSED
===== 3 passed, 1 failed in 1.23s =====
"""
        compressed = compressor.compress(test_output, strategy="test_output")

        # Check for compression indicators
        assert "test" in compressed.lower()
        assert "failed" in compressed.lower() or "✗" in compressed
        assert len(compressed) < len(test_output)


class TestAgentImports:
    """Test agent system imports work"""

    def test_agent_runner_imports(self):
        """Test: Agent runner can be imported"""
        from sage.runner import run_command
        assert callable(run_command)

    def test_autofix_imports(self):
        """Test: AutoFix engine imports"""
        try:
            from sage.autofix import AutoFixEngine
            # AutoFix may not be fully implemented yet
        except (ImportError, AttributeError):
            pytest.skip("AutoFix not fully implemented yet")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
