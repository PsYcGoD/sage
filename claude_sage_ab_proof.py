from __future__ import annotations

import json
import os
from anthropic import Anthropic

# pip install anthropic
# set ANTHROPIC_API_KEY=your_key_here

MODEL = os.environ.get("CLAUDE_PROOF_MODEL", "claude-3-5-sonnet-20241022")

sample = "pytest tests/test_payments.py::test_checkout_flow FAILED\n" + "\n".join(
    [
        f"E AssertionError: expected status 200 got 500 | request_id=req_{i:04d} "
        f"| stack frame app/payments.py:{120 + i % 30}"
        for i in range(1800)
    ]
)

sage_compressed = (
    "Tests: passed=0 failed=1 skipped=0\n"
    "Summary: E AssertionError: expected status 200 got 500 | "
    "request_id=req_1799 | stack frame app/payments.py:149\n"
    "Failed:\n"
    "  - pytest tests/test_payments.py::test_checkout_flow FAILED"
)

PROMPT_PREFIX = "Reply with exactly OK. Terminal output follows:\n"


def call_claude(label: str, text: str) -> dict:
    client = Anthropic()
    msg = client.messages.create(
        model=MODEL,
        max_tokens=5,
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": PROMPT_PREFIX + text,
            }
        ],
    )
    usage = msg.usage
    return {
        "label": label,
        "model": MODEL,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0),
        "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0),
        "response_text": "".join(
            block.text for block in msg.content if getattr(block, "type", "") == "text"
        ),
    }


raw = call_claude("without_sage_raw_output", sample)
compressed = call_claude("with_sage_compressed_output", sage_compressed)

saved_input_tokens = raw["input_tokens"] - compressed["input_tokens"]

# Change this if you test Opus.
# Sonnet input pricing example: $3 per 1M input tokens.
price_per_million_input = float(os.environ.get("CLAUDE_INPUT_PRICE_PER_MILLION", "3.00"))
saved_usd = saved_input_tokens / 1_000_000 * price_per_million_input

result = {
    "raw": raw,
    "with_sage": compressed,
    "saved_input_tokens": saved_input_tokens,
    "input_token_reduction_percent": round(saved_input_tokens / raw["input_tokens"] * 100, 2),
    "price_per_million_input_usd": price_per_million_input,
    "estimated_input_savings_usd": round(saved_usd, 6),
}

print(json.dumps(result, indent=2))