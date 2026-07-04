# 10k Context Compression Test Results

Date: 2026-07-03

Command:

```powershell
sage run -- powershell -NoProfile -Command "Set-Location -LiteralPath 'D:\work\sage'; python -m pytest tests\test_10k_context_compression.py -v -s"
```

## Results

| Test | Original Tokens | Compressed Tokens | Saved Tokens | Savings |
| --- | ---: | ---: | ---: | ---: |
| 10k token test-output compression | 10,011 | 6 | 10,005 | 99.9% |
| 10k token client context budget | 10,011 | 892 | 9,119 | 91.1% |

Pytest result: 2 passed in 2.73s.

## Compressed Context Output

```text
Tests: 1296\u2713 (total 1296)
```

## Coverage

The test file `tests/test_10k_context_compression.py` verifies:

- a deterministic pytest-like transcript with at least 10,000 estimated tokens
- aggressive `ContextCompressor` token savings for command/test output
- `ContextManager.compress_for_client` fitting the same transcript into a 1,000-token client context budget
