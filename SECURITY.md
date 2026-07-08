# Security Policy

## Supported Version

The public CLI package is currently supported on the `2.x` line.

## Reporting a Vulnerability

Please report suspected vulnerabilities privately by opening a GitHub security advisory for this repository when available, or by contacting the maintainer through the repository owner profile.

Do not include live API keys, OAuth tokens, raw command logs, or private terminal output in public issues.

## Credential Handling

- New SAGE API keys are stored in the operating system keyring when available.
- If a headless environment has no usable keyring backend, SAGE falls back to a clearly marked local file entry so CI and test machines can still run.
- `sage logout` clears local API connection metadata and attempts to delete the keyring secret.

## Telemetry and Proof Metrics

- Telemetry level `0` is local-only.
- Level `1` sends aggregate counters only.
- Higher levels are opt-in and constrained by account/key policy.
- Public dashboard proof is aggregate-only and must not include raw commands, raw outputs, file paths, or local logs.

## Command Safety

SAGE CLI evaluates commands against a safety policy before execution. The denylist is intended to block destructive or high-risk commands in protected modes, such as irreversible file deletion, credential exposure, and unsafe repository resets.

## Secret Redaction

SAGE CLI redacts common credential patterns before storing captured output. Redacted patterns include GitHub tokens, OpenAI-style API keys, AWS access keys, bearer tokens, password assignments, private key blocks, `.env`-style secrets, and other high-risk token shapes.

Redaction is a defense-in-depth layer, not permission to paste secrets into public issues or logs.

## What SAGE CLI Will Not Do

- Upload raw command text or raw command output in local-only mode.
- Publish source code, file paths, `.env` contents, private logs, or secrets to the dashboard.
- Guarantee that every secret shape is detected.
- Claim a command is safe solely because redaction ran.
