# SAGE CLI

[![CI](https://github.com/PsYcGoD/sage/actions/workflows/ci.yml/badge.svg)](https://github.com/PsYcGoD/sage/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://github.com/PsYcGoD/sage/blob/main/pyproject.toml)
[![License](https://img.shields.io/github/license/PsYcGoD/sage.svg)](https://github.com/PsYcGoD/sage/blob/main/LICENSE)
[![Release](https://img.shields.io/github/v/release/PsYcGoD/sage?include_prereleases)](https://github.com/PsYcGoD/sage/releases)

Local-first terminal wrapper for AI coding agents.

SAGE CLI wraps commands, compresses noisy output, keeps raw logs local, and tracks privacy-safe context savings.

Package name: `psycgod-sage`
CLI command: `sage`

## Install

```bash
pip install psycgod-sage
sage --version
```

## Quick Start

```bash
sage run -- python -m pytest
sage context report
```

By default, SAGE CLI runs locally. Raw logs stay on your machine. GitHub login is optional and only needed for public proof/dashboard sync.

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

## Local-Only Mode

Local-only mode does not require GitHub OAuth and does not send data.

| Mode | Requires GitHub OAuth? | Sends data? | What leaves the machine? |
|---|---:|---:|---|
| Local-only | No | No | Nothing |
| Connected proof | Yes | Yes | Aggregate counters only |
| Debug/advanced telemetry | Optional | Opt-in only | Redacted diagnostic summaries only |

Use connected mode only when you want optional public proof/dashboard sync:

```bash
sage connect
sage whoami
sage api status
```

To disable sync in connected mode:

```bash
sage telemetry off
set SAGE_AUTO_SEND_TELEMETRY=0
```

## Live Public Proof Dashboard

Live dashboard: [sage.api.marketingstudios.in/dashboard](https://sage.api.marketingstudios.in/dashboard)

![SAGE Live Public Proof Dashboard](https://raw.githubusercontent.com/PsYcGoD/sage/main/docs/assets/sage-live-dashboard.png)

Current public proof includes:

- Total commands processed through SAGE CLI
- Tokens processed, compressed, and saved
- Estimated savings by model/provider
- Compression rate and command success rate
- ML prediction scoring from local command history

Latest verified snapshot:

| Metric | Value |
|--------|------:|
| Commands processed | 6,288 |
| Tokens processed | 16,742,284 |
| Tokens compressed | 1,429,155 |
| Tokens saved | 15,314,377 |
| Estimated savings | $45.94 |
| Compression rate | 91.47% |
| Success rate | 99.5% |

These stats reflect live dashboard metrics as of July 7, 2026. Raw commands, outputs, file paths, and logs stay local by default. Public proof uses aggregate counters only.

## Run Commands Through SAGE

```bash
sage run -- python -m pytest
sage run -- npm test
sage run -- git status
```

SAGE CLI stores full raw command output locally, summarizes noisy output for AI context, tracks compression, and sends only allowed aggregate proof metrics when connected mode is enabled.

## System-Wide Installation for AI Agents

```bash
sage install
```

This installs SAGE instructions for Claude Code, Codex, Cursor, and Aider where those agent config files are available. For per-project setup:

```bash
sage init
```

## Useful CLI Commands

```bash
sage context stats
sage context report
sage history --limit 10
sage explain
sage suggest
sage fix
sage fix --apply --confidence 0.9
sage savings --agent claude-sonnet
sage firewall status
sage firewall rules list
sage mcp install
sage dashboard start --port 8765
```

## Screenshots

| Command | Preview |
|---|---|
| `sage run --` | ![sage run terminal capture](https://raw.githubusercontent.com/PsYcGoD/sage/main/docs/assets/sage-run.svg) |
| `sage context report` | ![sage context report terminal capture](https://raw.githubusercontent.com/PsYcGoD/sage/main/docs/assets/sage-context-report.svg) |
| `sage mcp install` | ![sage mcp install terminal capture](https://raw.githubusercontent.com/PsYcGoD/sage/main/docs/assets/sage-mcp-install.svg) |
| Dashboard proof | ![SAGE Live Public Proof Dashboard](https://raw.githubusercontent.com/PsYcGoD/sage/main/docs/assets/sage-live-dashboard.png) |

Starter demo GIFs:

- [demo-sage-run.gif](https://raw.githubusercontent.com/PsYcGoD/sage/main/docs/assets/demo-sage-run.gif)
- [demo-sage-savings.gif](https://raw.githubusercontent.com/PsYcGoD/sage/main/docs/assets/demo-sage-savings.gif)
- [demo-github-bot.gif](https://raw.githubusercontent.com/PsYcGoD/sage/main/docs/assets/demo-github-bot.gif)

## Agents and ML

SAGE CLI includes local agent analysis and ML features in the base install. They run during command execution to classify output, choose compression strategies, and improve local predictions from command history.

### Active Agent Types

- Security Agent: detects secrets, credentials, and security risks.
- Code Agent: checks syntax, scope, and file changes.
- Debug Agent: analyzes errors and suggests fixes.
- Test Agent: identifies test patterns and coverage.
- Dependency Agent: tracks package installations and versions.
- Research Agent: analyzes code patterns.
- Frontend Agent: reviews UI/browser-related output.
- Performance Agent: tracks performance signals.
- Workflow Agent: supports multi-step task orchestration.
- Red Team Agent: performs adversarial security checks.

### ML V2 - Neural Command Center

SAGE V2 adds semantic embedding-based prediction using `all-MiniLM-L6-v2` (384-dimensional vectors, 90 MB, Apache 2.0). The Neural Command Center coordinates specialized predictors for syntax, dependency, auth, timeout, permission, context, compression, and agent-ranking signals.

Benchmarks on 7,654 real commands with an 80/20 temporal split:

| Metric | V1 (sklearn) | V2 (embeddings) | Improvement |
|--------|:---:|:---:|:---:|
| Accuracy | 58% | 76% | +31% |
| Precision | n/a | 87% | New |
| Recall | n/a | 85% | New |
| F1 Score | n/a | 86% | New |

These ML signals are experimental guidance, not a guarantee that a command will succeed or fail. See [docs/ML_V2.md](https://github.com/PsYcGoD/sage/blob/main/docs/ML_V2.md) for architecture and benchmarks.

### LSP Server + Agentic Loop (v2.1.0)

SAGE now includes a Language Server Protocol (LSP) server and an agentic retry loop that any editor or AI agent can connect to natively.

```bash
sage lsp                    # Start LSP server (stdio for editors)
sage lsp --tcp --port 19473 # Start LSP server (TCP for AI agents)
```

**Agentic Loop** — when a command fails, SAGE automatically:
1. Analyzes the error against known patterns
2. Suggests or applies a fix (configurable autonomy)
3. Verifies the fix by re-running the original command
4. Circuit breaker stops infinite retry loops

MCP tools for AI agents: `sage_agentic_run`, `sage_agentic_fix`, `sage_agentic_session`

Configure in `sage.toml`:
```toml
[agentic]
autonomy = "suggest"  # suggest | ask | auto
max_retries = 3

[lsp]
transport = "stdio"
tcp_port = 19473
```

## Team View Preview

Team Dashboard is not published yet. It will open by invite after SAGE CLI reaches 100 users.

![SAGE Team View Preview](https://raw.githubusercontent.com/PsYcGoD/sage/main/docs/assets/team-dashboard-preview.png)

The planned Team View will show aggregate workspace proof only: tokens saved, success rate, safety events, and protected secrets. It will not publish raw commands, source code, file paths, `.env` data, or raw logs.

## GUI Status

The desktop GUI is not available in this public repo right now.

```bash
sage gui
```

This command prints the roadmap status instead of launching a desktop app. The GUI will be released later after it is stable enough for public use.

## Known Limitations

- The GUI is not public yet and is intentionally absent from the CLI package.
- GitHub OAuth / a SAGE API key is required for API-backed commands and public proof sync.
- Telemetry level `0` is local-only; higher levels are opt-in and constrained by account/key policy.
- The public dashboard is aggregate-only and does not expose raw commands, raw outputs, file paths, or local logs.
- ML training and agent quality improve with usage volume; fresh installations have minimal training data initially.
- ML V2 embeddings download a roughly 90 MB model on first use. First prediction can take a few minutes to build the index; later predictions use the local cache.

## Privacy and Security

- Raw commands and full outputs stay local by default.
- Public dashboard data is aggregate proof only.
- API connection is handled through GitHub OAuth.
- Higher telemetry is opt-in.
- API keys are stored in the OS keyring when available.

See [Privacy](https://github.com/PsYcGoD/sage/blob/main/PRIVACY.md), [Security](https://github.com/PsYcGoD/sage/blob/main/SECURITY.md), [Contributing](https://github.com/PsYcGoD/sage/blob/main/CONTRIBUTING.md), and [Code of Conduct](https://github.com/PsYcGoD/sage/blob/main/CODE_OF_CONDUCT.md) for the detailed project model.

## Development

```bash
git clone https://github.com/PsYcGoD/sage.git
cd sage
pip install -e .[all]
python -m compileall -q src/sage
python -m pytest -q
```

The public package is CLI-first. GUI source, GUI tests, and GUI-only dependencies are intentionally not shipped in this repo at this time.
