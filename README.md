# SAGE - Stop AI Coding Agents From Burning Tokens

[![CI](https://github.com/PsYcGoD/sage/actions/workflows/ci.yml/badge.svg)](https://github.com/PsYcGoD/sage/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://github.com/PsYcGoD/sage/blob/main/pyproject.toml)
[![License](https://img.shields.io/github/license/PsYcGoD/sage.svg)](https://github.com/PsYcGoD/sage/blob/main/LICENSE)
[![Release](https://img.shields.io/github/v/release/PsYcGoD/sage?include_prereleases)](https://github.com/PsYcGoD/sage/releases)

A local-first CLI wrapper for Claude Code, Codex, Cursor, and other AI coding agents.

SAGE routes terminal commands through `sage run --`, compresses noisy output before it enters the agent context, keeps raw logs on your machine, and proves token savings with privacy-safe metrics.

## Live Proof

| Metric | Value |
|--------|------:|
| Commands processed | 10,574 |
| Tokens processed | 264.5M |
| Tokens saved | 256.1M |
| Compression rate | 96.8% |
| Estimated savings | $2,753.34 |
| Success rate | 94.6% |

Live dashboard: [sage.api.marketingstudios.in](https://sage.api.marketingstudios.in/)

### Proof at Full Context

SAGE is built for the moment when an AI agent is already near the edge of its context window. In a real Claude Desktop session, SAGE was still routing commands while the agent showed a full `200.0k / 200.0k (100%)` context window.

![SAGE running at a full 200k context window](docs/assets/sage-200k-context-proof.png)

Provider-confirmed A/B tests show why this matters:

| Proof run | Raw input | SAGE input | Tokens saved | Reduction |
|---|---:|---:|---:|---:|
| Claude provider A/B | 64,833 | 91 | 64,742 | 99.86% |
| Codex provider A/B | 65,204 | 14,850 | 50,354 | 77.23% |

Even when context is already maxed out, SAGE keeps raw logs local and sends the agent a smaller, useful version instead of flooding the conversation with full terminal noise.

## Install

One pasted command installs SAGE and immediately starts setup:

```powershell
python -m pip install --upgrade psycgod-sage; if ($LASTEXITCODE -eq 0) { python -m sage }
```

Package name: `psycgod-sage` | CLI command: `sage`

**Also available on npm:**

```bash
npm install -g psycgod-sage-js
```

Or use the installer script directly from GitHub:

```powershell
irm https://raw.githubusercontent.com/PsYcGoD/sage/main/install.ps1 | iex
```
### JavaScript/npm Version

SAGE is also available as an npm package for MCP Registry compatibility:

```bash
npm install -g psycgod-sage-js

Feature	Python	JavaScript
Core compression (97%)	Yes	Yes
MCP Server	Yes	Yes
ML V1 (pattern-based)	Yes	Yes
ML V2 (neural embeddings)	Yes	No
Agents	7	4
TUI/GUI	Yes	No
MCP Registry	No	Yes
Both versions share the same database. Use Python for full features, JavaScript for MCP Registry.

See js/ folder for JavaScript source.

That one command installs the SAGE Python package, launches zero-prompt setup, uses this machine's identity, enables ML V1, connects to the Cloudflare-backed SAGE API when possible, and installs mandatory local AI-agent instructions for supported agents.

Run `sage init` inside a project to add project-local `AGENTS.md`, `CLAUDE.md`, `SAGE.md`, and Claude hook files.

```bash
sage init
```

### First Run

On first use, SAGE configures itself without prompts:

```
1. Use machine identity
2. Enable ML V1 by default
3. Connect to SAGE cloud API automatically when reachable
4. Install local AI-agent enforcement
```

- ML V1: included, light, local scikit-learn/heuristic prediction, learns from your usage over time
- ML V2: optional neural embeddings with torch + sentence-transformers + faiss
- You can install ML V2 later with `pip install psycgod-sage[ml]` or `sage ml setup`
- Safe telemetry stays queued locally if offline and syncs when the API is reachable; SAGE attempts proof sync every 10th command.

## Quick Start

```bash
sage run -- python -m pytest
sage run -- npm test
sage run -- git status
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
sage install                      # Repair/re-apply system-wide AI agent enforcement
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

## Team View Preview - Enterprise Only

Team View is an Enterprise-only SAGE workspace dashboard for organizations that need shared proof, safety monitoring, and team-level AI savings visibility.

![SAGE Team View Preview](docs/assets/team-dashboard-preview.png)

Planned Enterprise Team View features:

- Workspace-level tokens saved, compression rate, and estimated AI savings
- Team command success rate and failure trends
- Agent and ML activity across connected machines
- Safety events, blocked risky commands, and protected secret signals
- Per-machine and per-user aggregate usage without exposing raw command text
- Privacy-safe proof only: no source code, `.env` values, raw logs, private paths, or model output

Team View is not part of the free public CLI package. It is reserved for Enterprise access.

## ML - Learns From Your Usage

SAGE ML trains on your local command history. More commands = better predictions.

### ML V1 (included)

Scikit-learn based failure prediction. Trains with `sage ml train`. Improves as your command history grows. Lightweight, no GPU needed.

### ML V2 - Neural Command Center (optional)

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
