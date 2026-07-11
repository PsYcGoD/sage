"""SAGE Audit Test - Verify compression claims"""
import sys
sys.path.insert(0, 'D:/work/sage/src')

from sage.context.compression import ContextCompressor
from sage.store import connect

print("=" * 60)
print("SAGE AUDIT - Compression Verification")
print("=" * 60)

# Test 1: Database stats
print("\n[TEST 1] Database Statistics")
with connect() as conn:
    r = conn.execute('''
        SELECT 
            COUNT(*) as records,
            SUM(original_tokens) as original,
            SUM(compressed_tokens) as compressed,
            SUM(saved_tokens) as saved
        FROM context_compression
    ''').fetchone()
    
    records, original, compressed, saved = r
    ratio = (saved / original * 100) if original else 0
    
    print(f"  Records: {records:,}")
    print(f"  Original tokens: {original:,}")
    print(f"  Compressed tokens: {compressed:,}")
    print(f"  Saved tokens: {saved:,}")
    print(f"  Compression ratio: {ratio:.1f}%")
    
# Test 2: Run statistics
print("\n[TEST 2] Run Statistics")
with connect() as conn:
    total = conn.execute('SELECT COUNT(*) FROM runs').fetchone()[0]
    success = conn.execute('SELECT COUNT(*) FROM runs WHERE exit_code=0').fetchone()[0]
    print(f"  Total runs: {total:,}")
    print(f"  Successful: {success:,}")
    print(f"  Success rate: {success/total*100:.1f}%")

# Test 3: Live compression test
print("\n[TEST 3] Live Compression Test")
compressor = ContextCompressor()

# Simulate pytest output with 1000 error lines
sample = "pytest tests/test_checkout.py FAILED\n"
sample += "\n".join([f"E AssertionError: expected 200 got 500 at line {i}" for i in range(1000)])

result = compressor.compress_with_result(sample, strategy='auto')
print(f"  Original tokens: {result.original_tokens:,}")
print(f"  Compressed tokens: {result.compressed_tokens:,}")
print(f"  Saved tokens: {result.saved_tokens:,}")
print(f"  Compression ratio: {result.ratio:.1f}%")
print(f"  Strategy: {result.strategy}")

# Test 4: Different content types
print("\n[TEST 4] Content Type Compression")
test_cases = [
    ("npm install output", "npm WARN deprecated\n" * 200 + "added 500 packages"),
    ("git status", "On branch main\n" + "modified: file.py\n" * 50),
    ("build log", "Compiling...\n" * 300 + "Build succeeded"),
    ("stack trace", "Traceback (most recent call last):\n" + '  File "app.py", line 100\n' * 50),
]

for name, sample in test_cases:
    r = compressor.compress_with_result(sample, strategy='auto')
    print(f"  {name}: {r.original_tokens:,} -> {r.compressed_tokens:,} ({r.ratio:.0f}% saved)")

print("\n" + "=" * 60)
print("AUDIT COMPLETE")
print("=" * 60)
