# SAGE npm security review notes

## Current npm package posture

The npm package `psycgod-sage` is intended to be a safe launcher for the canonical PyPI package `psycgod-sage`.

As of npm package version `1.0.19`:

- `npm install -g psycgod-sage` is passive.
- There is no `preinstall`, `install`, or `postinstall` lifecycle script.
- Install does not connect to any SAGE API.
- Install does not write AI-agent config files or hooks.
- Install does not install/update Python packages during npm install.
- Activation is explicit via a user's first `sage` / `npx -y psycgod-sage ...` command.
- Agent hook installation is best-effort and non-blocking for normal command execution.
- Hook denials do not print the blocked command, to avoid leaking secrets from command lines into AI context or logs.
- Hook installation merges with existing hook settings instead of replacing a user's existing hooks.

## Why this changed

Earlier npm versions attempted to make onboarding one-step by using `postinstall` to:

- install/update the Python SAGE core,
- run setup,
- connect to the SAGE API,
- print API identity,
- write AI-agent instructions/hooks.

That was too much behavior for install time and could be classified by automated security systems as unsafe install-time execution or persistence.

## Explicit activation behavior

Users now activate SAGE intentionally by running a SAGE command:

```bash
sage doctor --activation
sage run -- npm test
npx -y psycgod-sage run -- npm test
```

On that explicit invocation, SAGE may:

- install/update the Python SAGE core when needed,
- connect to the SAGE API,
- print connection status,
- install local AI-agent instructions/hooks.

This happens after the user explicitly invokes SAGE, not during package installation.

If local AI-agent config files cannot be updated because of file permissions or locks, SAGE prints a warning but does not fail the user's wrapped command. Users can repair enforcement explicitly with:

```bash
sage install
npx -y psycgod-sage install
```

## Hook safety posture

SAGE hooks are designed to enforce wrapper usage without exposing sensitive command text:

- They check only the command prefix.
- They do not send command contents to a remote service.
- They do not print blocked command contents.
- They do not delete, move, or rewrite project files.
- They merge hook settings where possible and preserve existing user hooks.

## npm appeal summary

The package has been changed to remove lifecycle install scripts and install-time side effects. The maintainer requests review/reinstatement of `psycgod-sage` as a passive CLI launcher package.
