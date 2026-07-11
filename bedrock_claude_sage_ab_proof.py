from __future__ import annotations

import json
import os
import sys

import boto3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from sage.context.compression import ContextCompressor


RAW_MODEL_ID = os.environ.get(
    "BEDROCK_CLAUDE_PROOF_MODEL",
    os.environ.get(
        "ANTHROPIC_DEFAULT_OPUS_MODEL",
        "us.anthropic.claude-opus-4-1-20250805-v1:0",
    ),
)
MODEL_ID = RAW_MODEL_ID.split("[", 1)[0]
AWS_REGION = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
AWS_PROFILE = os.environ.get("AWS_PROFILE") or None
PRICE_PER_MILLION_INPUT = float(os.environ.get("BEDROCK_INPUT_PRICE_PER_MILLION", "15"))


def bedrock_client():
    session_kwargs = {}
    if AWS_PROFILE:
        session_kwargs["profile_name"] = AWS_PROFILE
    session = boto3.Session(**session_kwargs)
    return session.client("bedrock-runtime", region_name=AWS_REGION)


def synthetic_terminal_output() -> str:
    return "pytest tests/test_payments.py::test_checkout_flow FAILED\n" + "\n".join(
        [
            f"E AssertionError: expected status 200 got 500 | request_id=req_{i:04d} "
            f"| stack frame app/payments.py:{120 + i % 30}"
            for i in range(1800)
        ]
    )


def call_claude(client, label: str, terminal_output: str) -> dict[str, object]:
    prompt = "Reply with exactly OK. Terminal output follows:\n" + terminal_output
    response = client.converse(
        modelId=MODEL_ID,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 5, "temperature": 0},
    )
    usage = response.get("usage", {})
    text = ""
    for item in response.get("output", {}).get("message", {}).get("content", []):
        text += item.get("text", "")
    return {
        "label": label,
        "input_tokens": usage.get("inputTokens"),
        "output_tokens": usage.get("outputTokens"),
        "total_tokens": usage.get("totalTokens"),
        "response_text": text,
        "request_id": response.get("ResponseMetadata", {}).get("RequestId"),
    }


def main() -> int:
    raw_text = synthetic_terminal_output()
    compression = ContextCompressor().compress_with_result(raw_text)
    compressed_text = compression.compressed_text
    client = bedrock_client()

    raw = call_claude(client, "without_sage_raw_output", raw_text)
    with_sage = call_claude(client, "with_sage_compressed_output", compressed_text)

    raw_input = int(raw.get("input_tokens") or 0)
    sage_input = int(with_sage.get("input_tokens") or 0)
    saved = raw_input - sage_input
    saved_usd = (saved / 1_000_000) * PRICE_PER_MILLION_INPUT

    proof = {
        "provider": "aws-bedrock",
        "region": AWS_REGION,
        "profile": AWS_PROFILE or "default-chain",
        "model_id": MODEL_ID,
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
