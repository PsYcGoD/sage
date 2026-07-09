# SAGE — Stop AI Coding Agents From Burning Tokens

[![CI](https://github.com/PsYcGoD/sage/actions/workflows/ci.yml/badge.svg)](https://github.com/PsYcGoD/sage/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://github.com/PsYcGoD/sage/blob/main/pyproject.toml)
[![License](https://img.shields.io/github/license/PsYcGoD/sage.svg)](https://github.com/PsYcGoD/sage/blob/main/LICENSE)
[![Release](https://img.shields.io/github/v/release/PsYcGoD/sage?include_prereleases)](https://github.com/PsYcGoD/sage/releases)

A local-first CLI wrapper for Claude Code, Codex, Cursor, and other AI coding agents.

SAGE routes terminal commands through `sage run --`, compresses noisy output before it enters the agent context, keeps raw logs on your machine, and proves token savings with privacy-safe metrics.

## Live Proof

| Metric | Value |
|--------|------:|
| Commands processed | 6,288 |
| Tokens processed | 16.7M |
| Tokens saved | 15.3M |
| Compression rate | 91.47% |
| Estimated savings | $45.94 |
| Success rate | 99.5% |

Live dashboard: [sage.api.marketingstudios.in](https://sage.api.marketingstudios.in/)

## Install

```bash
pip install psycgod-sage
sage --version
sage install
```

Package name: `psycgod-sage` | CLI command: `sage`

Run `sage install` once per machine to install mandatory SAGE instructions, MCP registration, and Claude Code hook settings for supported local AI agents. Run `sage init` inside a project to add project-local `AGENTS.md`, `CLAUDE.md`, `SAGE.md`, and Claude hook files.

### First Run

On first use, SAGE walks you through setup:

```
1. Install ML V2 dependencies? [y/N]     ← neural predictions (optional, ~2 GB)
2. Local AI-agent enforcement             ← `sage install` / `sage init`
3. Hardware auth / GitHub OAuth           ← optional public proof sync
```

- Type `y` for ML V2: torch + sentence-transformers + faiss (76% prediction accuracy)
- Type `n` to skip: ML V1 (scikit-learn) is already included and learns from your usage over time
- You can install ML V2 later with `pip install psycgod-sage[ml]` or `sage ml setup`

## Quick Start

```bash
sage run -- python -m pytest
sage run -- npm test
sage run -- git status
sage install
sage init
sage context report
```

## 15-Second Demo

![SAGE CLI demo](https://raw.githubusercontent.com/PsYcGoD/sage/main/docs/assets/demo-sage-run.gif)

```text
$ sage run -- python -m pytest
[sage] saved run #42 exit=0 time=1180ms
[sage] context: saved 8,214 tokens (91.2% compression)
[sage] summary:
144 passed

$ sage context report
SAGE context compression report
Original tokens: 120,450
Compressed tokens: 12,831
Saved tokens: 107,619 (89.3%)
```

## Why SAGE Exists

AI coding agents waste context and money by reading huge terminal logs, repeated failures, stack traces, test noise, build noise, and dependency output.

SAGE sits between your terminal and your AI coding workflow. It keeps full raw logs locally but sends only compressed, useful output to the agent context.

| Without SAGE | With SAGE |
|---|---|
| Agent sees full noisy terminal logs | Agent sees compressed useful output |
| Context gets wasted fast | Context lasts longer |
| Repeated failures burn tokens | Failures are summarized clearly |
| Hard to prove AI-agent savings | Dashboard shows proof metrics |
| Raw logs may be copied into prompts | Raw logs stay local |

## Local-Only Mode

Local-only mode does not require GitHub OAuth and does not send data.

| Mode | Requires OAuth? | Sends data? | What leaves the machine? |
|---|---:|---:|---|
| Local-only | No | No | Nothing |
| Connected proof | Yes | Yes | Aggregate counters only |
| Debug telemetry | Optional | Opt-in only | Redacted diagnostic summaries only |

Use connected mode for optional public proof/dashboard sync:

```bash
sage connect
```

## CLI Commands

```bash
sage run -- <command>              # Wrap any command
sage context stats                # Token savings summary
sage context report               # Full compression report
sage history --limit 10           # Recent command history
sage explain                      # Explain last error
sage suggest                      # Get fix suggestions
sage fix --apply                  # Auto-fix errors
sage savings --agent claude-sonnet # Savings by provider
sage firewall status              # Safety policy status
sage firewall rules list          # View blocked patterns
sage ml setup                     # Install ML V2 (optional)
sage ml train                     # Retrain on your history
sage install                      # System-wide AI agent enforcement
sage init                         # Per-project AGENTS.md/CLAUDE.md/hooks
sage mcp install                  # MCP server for AI agents
sage dashboard start              # Local proof dashboard
```

## Screenshots

| Command | Preview |
|---|---|
| `sage run --` | ![sage run](https://raw.githubusercontent.com/PsYcGoD/sage/main/docs/assets/sage-run.svg) |
| `sage context report` | ![context report](https://raw.githubusercontent.com/PsYcGoD/sage/main/docs/assets/sage-context-report.svg) |
| `sage mcp install` | ![mcp install](https://raw.githubusercontent.com/PsYcGoD/sage/main/docs/assets/sage-mcp-install.svg) |
| Dashboard | ![dashboard](https://raw.githubusercontent.com/PsYcGoD/sage/main/docs/assets/sage-live-dashboard.png) |

## ML — Learns From Your Usage

SAGE ML trains on your local command history. More commands = better predictions.

### ML V1 (included)

Scikit-learn based failure prediction. Trains with `sage ml train`. Improves as your command history grows. Lightweight, no GPU needed.

### ML V2 — Neural Command Center (optional)

> Install: `pip install psycgod-sage[ml]` or `sage ml setup`

Adds semantic embedding-based prediction using `all-MiniLM-L6-v2` (384-dim vectors, 90 MB model, Apache 2.0). Specialized predictors for syntax, dependency, auth, timeout, permission, context, compression, and agent-ranking.

| Metric | V1 (sklearn) | V2 (embeddings) |
|--------|:---:|:---:|
| Accuracy | 58% | 76% |
| Precision | n/a | 87% |
| Recall | n/a | 85% |
| F1 Score | n/a | 86% |

ML signals are experimental guidance, not guarantees. See [docs/ML_V2.md](https://github.com/PsYcGoD/sage/blob/main/docs/ML_V2.md) for architecture.

## Agent Firewall

SAGE blocks destructive commands, detects secret exposure, and prevents infinite retry loops.

```bash
sage firewall status
sage firewall enable
sage firewall rules list
sage firewall allow "npm install"
sage firewall block "rm -rf"
sage firewall audit
```

## LSP Server + Agentic Loop

```bash
sage lsp                    # Start LSP server (stdio for editors)
sage lsp --tcp --port 19473 # Start LSP server (TCP for AI agents)
```

When a command fails, SAGE automatically analyzes the error, suggests or applies a fix, and verifies by re-running. Circuit breaker stops infinite loops.

Configure in `sage.toml`:
```toml
[agentic]
autonomy = "suggest"  # suggest | ask | auto
max_retries = 3

[lsp]
transport = "stdio"
tcp_port = 19473
```

## Privacy and Security

- Raw commands and full outputs stay local by default.
- Public dashboard data is aggregate proof only.
- No source code, `.env`, secrets, or raw logs are uploaded.
- API keys are stored in the OS keyring when available.
- Higher telemetry is opt-in and policy-constrained.

See [PRIVACY.md](PRIVACY.md) | [SECURITY.md](SECURITY.md) | [CONTRIBUTING.md](CONTRIBUTING.md) | [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

## Known Limitations

- The desktop GUI is not public yet.
- GitHub OAuth is only required for connected proof/dashboard sync.
- ML V2 requires `pip install psycgod-sage[ml]` (~2 GB for torch).
- ML accuracy improves with usage; fresh installs have minimal training data.
- The public dashboard is aggregate-only.

## Development

```bash
git clone https://github.com/PsYcGoD/sage.git
cd sage
pip install -e .[all]
python -m compileall -q src/sage
python -m pytest -q
```

The public package is CLI-first. GUI source is not shipped in this repo.
