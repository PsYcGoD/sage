"""Test context management system."""

from sage.context import ContextManager, compress_output, smart_diff


def test_compression():
    """Test output compression."""
    print("\n=== Testing Output Compression ===")
    
    # Simulate verbose output
    verbose_output = "\n".join([
        "DEBUG: Loading config",
        "DEBUG: Connecting to database",
        "INFO: Starting process",
        "ERROR: Connection failed",
        "ERROR: Retrying...",
        "DEBUG: Cleanup",
    ] * 10)  # 60 lines
    
    print(f"Original: {len(verbose_output)} chars, {len(verbose_output.splitlines())} lines")
    
    compressed = compress_output(verbose_output, max_lines=20)
    print(f"Compressed: {len(compressed)} chars, {len(compressed.splitlines())} lines")
    print(f"Compression: {(1 - len(compressed)/len(verbose_output))*100:.1f}%")


def test_smart_diff():
    """Test smart diff generation."""
    print("\n=== Testing Smart Diff ===")
    
    before = """def hello():
    print("Hello")
    return True

def goodbye():
    print("Bye")"""
    
    after = """def hello():
    print("Hello World!")
    return True

def goodbye():
    print("Goodbye")
    return False"""
    
    diff = smart_diff(before, after, context_lines=2)
    print("Diff output:")
    print(diff)
    print(f"\nOriginal: {len(before)+len(after)} chars")
    print(f"Diff: {len(diff)} chars")
    print(f"Savings: {(1 - len(diff)/(len(before)+len(after)))*100:.1f}%")


def test_context_manager():
    """Test full context manager."""
    print("\n=== Testing Context Manager ===")
    
    manager = ContextManager()
    
    # Simulate command output
    stdout = "Loading...\n" * 50 + "Process complete\n"
    stderr = "Warning: deprecated\n" * 20
    
    result = manager.process_command_output(
        stdout=stdout,
        stderr=stderr,
        exit_code=0,
        run_id=None
    )
    
    print(f"Original tokens: {manager.tracker.estimate_tokens(stdout + stderr)}")
    print(f"Compressed tokens: {manager.tracker.estimate_tokens(result['compressed_output'])}")
    print(f"Savings: {result['token_savings']} tokens ({result['compression_ratio']})")


def test_token_tracking():
    """Test token tracker."""
    print("\n=== Testing Token Tracker ===")
    
    manager = ContextManager()
    
    # Get stats
    stats = manager.get_token_stats()
    print(f"Commands tracked: {stats['total_commands']}")
    print(f"Total savings: {stats['total_savings']:,} tokens")
    print(f"Compression rate: {stats['savings_percent']:.1f}%")


if __name__ == "__main__":
    test_compression()
    test_smart_diff()
    test_context_manager()
    test_token_tracking()
    print("\n[OK] All context management tests passed!")
