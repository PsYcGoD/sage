# SAGE Privacy

SAGE is local-first. The default design is that raw terminal data stays on your machine.

## Local Data

SAGE stores local command history, raw output artifacts, compressed summaries, token accounting, redaction counts, and policy decisions in the local SAGE data directory.

Run:

```bash
sage privacy report
```

## Uploaded Data

Telemetry level `0` sends nothing. Level `1` sends aggregate proof counters such as total runs, token counts, compression rate, and success rate. It does not send raw commands, raw output, source code, file contents, private paths, `.env` files, or secrets.

Higher telemetry levels are opt-in and constrained by account/key policy.

## Credentials

SAGE API keys are stored in the operating system keyring when available. Headless environments without a usable keyring may fall back to a local file entry marked as fallback storage.

## Control

```bash
sage privacy set local-only
sage telemetry status
sage telemetry delete-local-queue
sage privacy purge-raw --days 30 --apply
sage logout
```

## Public Dashboard

The public dashboard is aggregate-only. It is intended to prove token savings and command success rates without exposing private project data.
