# SAGE npm security review notes

## Current npm package posture

The npm package `psycgod-sage` is intended to be a safe launcher for the canonical PyPI package `psycgod-sage`.

As of npm package version `1.0.12`:

- `npm install -g psycgod-sage` is passive.
- There is no `preinstall`, `install`, or `postinstall` lifecycle script.
- Install does not connect to any SAGE API.
- Install does not write AI-agent config files or hooks.
- Install does not install/update Python packages during npm install.
- Setup is explicit via `sage setup`.

## Why this changed

Earlier npm versions attempted to make onboarding one-step by using `postinstall` to:

- install/update the Python SAGE core,
- run setup,
- connect to the SAGE API,
- print API identity,
- write AI-agent instructions/hooks.

That was too much behavior for install time and could be classified by automated security systems as unsafe install-time execution or persistence.

## Explicit setup behavior

Users now run setup intentionally:

```bash
sage setup
```

Setup may:

- install/update the Python SAGE core when needed,
- connect to the SAGE API,
- print connection status,
- install local AI-agent instructions/hooks.

This happens after the user explicitly invokes SAGE, not during package installation.

## npm appeal summary

The package has been changed to remove lifecycle install scripts and install-time side effects. The maintainer requests review/reinstatement of `psycgod-sage` as a passive CLI launcher package.
