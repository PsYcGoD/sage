# SAGE npm launcher - Smart Agent Guidance Engine
[![npm](https://img.shields.io/npm/v/psycgod-sage-js)](https://www.npmjs.com/package/psycgod-sage-js)

This npm package is a Node-friendly launcher for the canonical Python package `psycgod-sage`.
It installs/updates the PyPI SAGE core and forwards commands to `python -m sage`, so npm/npx
and PyPI behavior stay identical. ML V1 is included. ML V2 remains optional.

## Installation

```bash
npm install -g psycgod-sage-js
```

One-shot npx usage:

```bash
npx -y psycgod-sage-js run -- npm test
```

Equivalent Python install:

```bash
pip install psycgod-sage
sage run -- npm test
```

## Usage

```bash
npx -y psycgod-sage-js run -- npm test
npx -y psycgod-sage-js history
npx -y psycgod-sage-js explain --failed
npx -y psycgod-sage-js suggest --failed
npx -y psycgod-sage-js predict rm -rf node_modules
npx -y psycgod-sage-js ml setup
```

If installed from PyPI, AI agents should use:

```bash
sage run -- <command>
```

If installed from npm/npx, AI agents should use:

```bash
npx -y psycgod-sage-js run -- <command>
```

## Notes

- npm/npx SAGE delegates to PyPI `psycgod-sage`.
- There is no separate JS database, runner, compressor, or ML implementation in the active CLI path.
- ML V1 is included through PyPI SAGE.
- Optional ML V2 can be installed later with `npx -y psycgod-sage-js ml setup`.

Links:

- Python: https://pypi.org/project/psycgod-sage/
- Repo: https://github.com/PsYcGoD/sage
- Dashboard: https://sage.api.marketingstudios.in/
- License: MIT
