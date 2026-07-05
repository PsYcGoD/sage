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
