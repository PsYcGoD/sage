import sys
sys.path.insert(0, 'src')

from sage.context.compression import ContextCompressor

# Test 1: Pytest output
test_output = """================================ test session starts ================================
platform win32 -- Python 3.11.0, pytest-7.4.0
collected 45 items

tests/test_auto_fix.py::test_python_syntax_error PASSED                      [  2%]
tests/test_auto_fix.py::test_import_error PASSED                             [  4%]
tests/test_multi_agent.py::test_orchestrator_init PASSED                     [  8%]
tests/test_workflow.py::test_yaml_parser PASSED                              [ 13%]
tests/test_context.py::test_compression PASSED                               [ 17%]

======================== 45 passed in 12.34s ========================"""

compressor = ContextCompressor()
compressed = compressor.compress(test_output, 'test_output')
original = compressor.estimate_tokens(test_output)
compressed_tokens = compressor.estimate_tokens(compressed)
ratio = ((original - compressed_tokens) / original * 100) if original > 0 else 0

print('=' * 80)
print('TEST 1: PYTEST OUTPUT')
print('=' * 80)
print(f'Original: {len(test_output)} chars, {original} tokens')
print(f'Compressed: {len(compressed)} chars, {compressed_tokens} tokens')
print(f'Savings: {original - compressed_tokens} tokens ({ratio:.1f}%)')
print(f'\nCOMPRESSED OUTPUT:\n{compressed}\n')

# Test 2: Verbose logs
log_output = """2026-07-03 14:32:15 [INFO] Starting SAGE runner...
2026-07-03 14:32:15 [DEBUG] Loading config
2026-07-03 14:32:16 [DEBUG] Registering agents
2026-07-03 14:32:18 [WARNING] File has no docstring
2026-07-03 14:32:19 [ERROR] SyntaxError at line 12
2026-07-03 14:32:19 [INFO] Auto-fix suggested
2026-07-03 14:32:20 [WARNING] No tests found"""

compressed = compressor.compress(log_output, 'logs')
original = compressor.estimate_tokens(log_output)
compressed_tokens = compressor.estimate_tokens(compressed)
ratio = ((original - compressed_tokens) / original * 100) if original > 0 else 0

print('=' * 80)
print('TEST 2: LOG COMPRESSION')
print('=' * 80)
print(f'Original: {len(log_output)} chars, {original} tokens')
print(f'Compressed: {len(compressed)} chars, {compressed_tokens} tokens')
print(f'Savings: {original - compressed_tokens} tokens ({ratio:.1f}%)')
print(f'\nCOMPRESSED OUTPUT:\n{compressed}\n')

# Overall stats
stats = compressor.get_stats()
print('=' * 80)
print('OVERALL STATS')
print('=' * 80)
print(f"Compressions: {stats['compressions']}")
print(f"Original tokens: {stats['original_tokens']}")
print(f"Compressed tokens: {stats['compressed_tokens']}")
print(f"Total saved: {stats['total_savings']} tokens")
print(f"Average ratio: {stats['avg_ratio']}")
