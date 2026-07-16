# SAGE npm launcher - Smart Agent Guidance Engine
[![npm](https://img.shields.io/npm/v/psycgod-sage)](https://www.npmjs.com/package/psycgod-sage)

This npm package is a Node-friendly launcher for the canonical Python package `psycgod-sage`.
It installs/updates the PyPI SAGE core and forwards commands to `python -m sage`, so npm/npx
and PyPI behavior stay identical. ML V1 is included. ML V2 remains optional.

## Installation

```bash
npm install -g psycgod-sage
npx -y psycgod-sage activate
```

`activate` is compulsory before you expect Claude, Codex, Cursor, Windsurf, OpenCode, Cline, or other AI agents to use SAGE automatically. It writes/repairs local AI-agent memory files and supported shell-wrapper hooks, then prints a verification report. It does **not** auto-enable SAGE MCP. Restart open AI-agent sessions after activation.

One-shot npx usage:

```bash
npx -y psycgod-sage activate
npx -y psycgod-sage run -- npm test
```

Equivalent Python install:

```bash
pip install psycgod-sage
sage activate
sage run -- npm test
```

## Usage

```bash
npx -y psycgod-sage activate
npx -y psycgod-sage run -- npm test
npx -y psycgod-sage history
npx -y psycgod-sage explain --failed
npx -y psycgod-sage suggest --failed
npx -y psycgod-sage predict rm -rf node_modules
npx -y psycgod-sage ml setup
```

If installed from PyPI, AI agents should use:

```bash
sage run -- <command>
```

If installed from npm/npx, AI agents should use:

```bash
npx -y psycgod-sage run -- <command>
```

## Notes

- npm/npx SAGE delegates to PyPI `psycgod-sage`.
- There is no separate JS database, runner, compressor, or ML implementation in the active CLI path.
- ML V1 is included through PyPI SAGE.
- Optional ML V2 can be installed later with `npx -y psycgod-sage ml setup`.
- Optional MCP tools are manual: use `npx -y psycgod-sage mcp install` only if you explicitly want an MCP server.

Links:

- Python: https://pypi.org/project/psycgod-sage/
- Repo: https://github.com/PsYcGoD/sage
- Dashboard: https://sage.api.marketingstudios.in/
- License: MIT
