from __future__ import annotations

import json
import os
import sys

from openai import OpenAI

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from sage.context.compression import ContextCompressor


MODEL = os.environ.get("CODEX_PROOF_MODEL") or os.environ.get("OPENAI_CODEX_MODEL") or "gpt-4o-mini"
PRICE_PER_MILLION_INPUT = float(os.environ.get("CODEX_INPUT_PRICE_PER_MILLION", "1.50"))


def synthetic_terminal_output() -> str:
    return "pytest tests/test_payments.py::test_checkout_flow FAILED\n" + "\n".join(
        [
            f"E AssertionError: expected status 200 got 500 | request_id=req_{i:04d} "
            f"| stack frame app/payments.py:{120 + i % 30}"
            for i in range(1800)
        ]
    )


def response_text(response) -> str:
    text = getattr(response, "output_text", "")
    if text:
        return text
    chunks: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            value = getattr(content, "text", None)
            if value:
                chunks.append(value)
    return "".join(chunks)


def usage_value(usage, name: str) -> int:
    if usage is None:
        return 0
    if hasattr(usage, name):
        return int(getattr(usage, name) or 0)
    if isinstance(usage, dict):
        return int(usage.get(name) or 0)
    return 0


def call_openai(client: OpenAI, label: str, terminal_output: str) -> dict[str, object]:
    prompt = "Reply with exactly OK. Terminal output follows:\n" + terminal_output
    response = client.responses.create(
        model=MODEL,
        input=prompt,
        max_output_tokens=5,
        temperature=0,
    )
    usage = getattr(response, "usage", None)
    input_tokens = usage_value(usage, "input_tokens")
    output_tokens = usage_value(usage, "output_tokens")
    total_tokens = usage_value(usage, "total_tokens")
    return {
        "label": label,
        "response_id": getattr(response, "id", ""),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "response_text": response_text(response),
    }


def main() -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "OPENAI_API_KEY is not set. Set it before running this proof.",
                },
                indent=2,
            )
        )
        return 2

    raw_text = synthetic_terminal_output()
    compression = ContextCompressor().compress_with_result(raw_text)
    compressed_text = compression.compressed_text
    client = OpenAI()

    raw = call_openai(client, "without_sage_raw_output", raw_text)
    with_sage = call_openai(client, "with_sage_compressed_output", compressed_text)

    raw_input = int(raw.get("input_tokens") or 0)
    sage_input = int(with_sage.get("input_tokens") or 0)
    saved = raw_input - sage_input
    saved_usd = (saved / 1_000_000) * PRICE_PER_MILLION_INPUT

    proof = {
        "provider": "openai",
        "model": MODEL,
        "price_per_million_input_usd": PRICE_PER_MILLION_INPUT,
        "sage_local_raw_tokens": compression.original_tokens,
        "sage_local_compressed_tokens": compression.compressed_tokens,
        "sage_local_saved_tokens": compression.saved_tokens,
        "raw_provider": raw,
        "with_sage_provider": with_sage,
        "provider_input_tokens_saved": saved,
        "provider_input_reduction_percent": round((saved / raw_input) * 100, 2) if raw_input else None,
        "estimated_input_savings_usd": round(saved_usd, 6),
    }
    print(json.dumps(proof, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
