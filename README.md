# SAGE

[![CI](https://github.com/PsYcGoD/sage/actions/workflows/ci.yml/badge.svg)](https://github.com/PsYcGoD/sage/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![License](https://img.shields.io/github/license/PsYcGoD/sage.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/PsYcGoD/sage?include_prereleases)](https://github.com/PsYcGoD/sage/releases)

SAGE is a local-first command wrapper for AI coding agents that compresses terminal output, preserves raw logs locally, and proves token savings with privacy-safe metrics.

The public package is CLI-first. The desktop GUI is not included in this public repository yet.

## Live Public Proof Dashboard

Live dashboard: https://sage.api.marketingstudios.in/dashboard

![SAGE Live Public Proof Dashboard](docs/assets/sage-live-dashboard.png)

Current public proof includes:

- Total commands processed through SAGE
- Tokens processed, compressed, and saved
- Estimated savings by model/provider
- Compression rate and command success rate
- ML prediction scoring from local command history

Latest verified snapshot:

| Metric | Value |
|--------|------:|
| Commands processed | 5,650 |
| Tokens processed | 17,614,532 |
| Tokens compressed | 1,378,116 |
| Tokens saved | 16,236,416 |
| Estimated savings | $93.36 |
| Compression rate | 92.18% |
| Success rate | 99.01% |

These stats reflect the public CLI proof snapshot after the hosted dashboard went live.
Raw commands, outputs, file paths, and logs stay local by default. Public proof uses aggregate counters only.

## Install From GitHub Until PyPI Is Live

PyPI publishing is prepared but still blocked by the Trusted Publisher project-name mismatch. Until the PyPI project is live, install the public CLI directly from GitHub:

```bash
pip install git+https://github.com/PsYcGoD/sage.git
sage --version
```

After PyPI is live, the install command will be:

```bash
pip install psycgod-sage
sage --version
```

For local development:

```bash
git clone https://github.com/PsYcGoD/sage.git
cd sage
pip install -e .
sage --version
```

The prepared PyPI distribution is `psycgod-sage`; the installed CLI command is still `sage`.

## Connect Your Account

Most public API-backed commands require GitHub OAuth:

```bash
sage connect
sage whoami
sage api status
```

SAGE stores the API key in the operating system keyring when available. Local command history and raw outputs remain on your machine.

## System-Wide Installation for AI Agents

Make SAGE mandatory for all AI agents on your system:

```bash
sage install
```

This automatically installs SAGE instructions into:
- `~/.claude/CLAUDE.md` - Claude Code
- `~/.claude/settings.json` - MCP server registration
- `~/.cursorrules` - Cursor IDE
- `~/.codex/AGENTS.md` - Codex
- `~/.aider.conf.yml` - Aider (if exists)

After running `sage install`, all AI agents will automatically:
- Route commands through `sage run -- <command>`
- Use SAGE MCP tools for file operations
- Benefit from context compression and tracking

For per-project setup:

```bash
sage init
```

This writes `SAGE.md` in the current project with the mandatory wrapper rule.

## Run Commands Through SAGE

```bash
sage run -- python -m pytest
sage run -- npm test
sage run -- git status
```

SAGE stores full raw command output locally, summarizes noisy output for AI context, tracks compression, and sends only allowed aggregate proof metrics to the dashboard.

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
sage github-bot comment --kind summary
sage mcp install
sage dashboard start --port 8765
```

## Team View Preview

Team Dashboard is not published yet. It will open by invite after SAGE reaches 100 users.

![SAGE Team View Preview](docs/assets/team-dashboard-preview.png)

The planned Team View will show aggregate workspace proof only: tokens saved, success rate, safety events, and protected secrets. It will not publish raw commands, source code, file paths, `.env` data, or raw logs.

## Screenshots

| Command | Preview |
|---|---|
| `sage run --` | ![sage run terminal capture](docs/assets/sage-run.svg) |
| `sage context report` | ![sage context report terminal capture](docs/assets/sage-context-report.svg) |
| `sage mcp install` | ![sage mcp install terminal capture](docs/assets/sage-mcp-install.svg) |
| Dashboard proof | ![SAGE Live Public Proof Dashboard](docs/assets/sage-live-dashboard.png) |

Starter demo GIFs:

- [`demo-sage-run.gif`](docs/assets/demo-sage-run.gif)
- [`demo-sage-savings.gif`](docs/assets/demo-sage-savings.gif)
- [`demo-github-bot.gif`](docs/assets/demo-github-bot.gif)

## GUI Status

The desktop GUI is not available in this public repo right now.

```bash
sage gui
```

This command prints the roadmap status instead of launching a desktop app. The GUI will be released later with AI agents and ML workflows after it is stable enough for public use.

## Known Limitations

- The GUI is not public yet and is intentionally absent from the CLI package.
- GitHub OAuth / a SAGE API key is required for most API-backed commands and public proof sync.
- Telemetry level `0` is local-only; higher levels are opt-in and constrained by account/key policy.
- The public dashboard is aggregate-only and does not expose raw commands, raw outputs, file paths, or local logs.
- Local ML and agent features depend on local history volume and optional provider credentials.

## Privacy

- Raw commands and full outputs stay local by default.
- Public dashboard data is aggregate proof only.
- API connection is handled through GitHub OAuth.
- Higher telemetry is opt-in.
- API keys are stored in the OS keyring when available.

See [PRIVACY.md](PRIVACY.md) and [SECURITY.md](SECURITY.md) for the detailed data and security model.

## Development

```bash
python -m pytest -q
```

The public package is CLI-first. GUI source, GUI tests, and GUI-only dependencies are intentionally not shipped in this repo at this time.
