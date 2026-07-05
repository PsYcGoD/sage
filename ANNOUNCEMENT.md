# SAGE V2.0 Public Release: CLI First

SAGE is now being prepared as a public CLI-first repository.

The public release focuses on the stable command-line path:

- Connect with GitHub OAuth using `sage connect`
- Install SAGE locally with `pip install -e .`
- Bind agent instructions with `sage init`
- Route terminal commands through `sage run -- <command>`
- Compress noisy output before it burns AI context
- Keep raw command logs local by default
- Report privacy-safe aggregate proof metrics to the live public dashboard

Live dashboard: https://sage.api.marketingstudios.in/dashboard

## Current Proof Snapshot

| Metric | Value |
|--------|------:|
| Commands processed | 4,023 |
| Tokens processed | 16,242,678 |
| Tokens compressed | 1,133,424 |
| Tokens saved | 15,109,254 |
| Compression rate | 93.02% |
| Success rate | 96.69% |

## Quick Start

```bash
git clone https://github.com/PsYcGoD/sage.git
cd sage
pip install -e .
sage connect
sage init
sage run -- python -m pytest
sage context stats
```

## GUI Status

The GUI is in the making and will be released soon with AI agents and ML workflows.

For now, the public repo does not include GUI source code, GUI tests, or GUI-only dependencies. The `sage gui` command prints the roadmap status so old instructions do not crash.

## What Is Public Now

SAGE currently gives developers the CLI path needed to connect their system API, install the `sage` command, bind agent instructions, and make terminal agents use SAGE for command execution.

The rest remains focused on local privacy, compression proof, token/context reporting, and the public dashboard.
