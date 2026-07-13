# SAGE activation funnel audit

Generated from GitHub CLI, package APIs, and the SAGE admin API on 2026-07-13.

## What the numbers say

GitHub traffic API only exposes the last 14 days, not a true 30-day history.

| Signal | Value | Meaning |
|---|---:|---|
| GitHub clones | 1,554 total / 369 unique | Repo was fetched; includes humans, bots, forks, CI, scanners, and package/index automation. |
| GitHub views | 360 total / 71 unique | People or bots opened GitHub pages. |
| GitHub stars | 9 | Real interest signal. |
| GitHub forks | 6 | Real interest signal, but not necessarily runtime usage. |
| PyPI downloads, 2026-07-06..2026-07-12 | 2,661 | Package was downloaded; includes reinstalls, CI, mirrors/scanners excluded, and automated environments. |
| npm package status | E404 not found | Current npm install/npx flow is unavailable until npm reinstates the package. |
| SAGE connected API users/keys | 29 | Machines/users created API keys. |
| SAGE telemetry machines | 2 | Only machines that actually ran SAGE commands and sent telemetry. |
| SAGE active telemetry machines, 24h | 1 | Current real usage is mostly one active machine. |
| SAGE command telemetry events | 15k+ | SAGE itself works; activation/conversion is the leak. |

## Likely funnel leaks

1. **npm was the first install command, but npm package is currently unavailable.**
   A user following `npm install -g psycgod-sage` or `npx -y psycgod-sage ...` currently gets E404 and may leave.

2. **Install is not usage.**
   `pip install psycgod-sage` downloads the package, but telemetry only starts after the first explicit `sage` or `sage run -- ...` command.

3. **GitHub clone counts are noisy.**
   The repo had many CI/release runs and public scans. GitHub clone counts can include automation and are not a reliable user count.

4. **Connected users are not active users.**
   Many API rows have `runs 0`, so they connected or were created by tests/automation but never wrapped a command.

5. **Users may not understand the required next command.**
   The first line of the README must lead with a working PyPI install and a copy-paste command that visibly proves activation.

## Immediate fixes

- Lead README with PyPI install until npm is restored.
- Keep npm install passive to avoid another ban.
- Add `sage doctor --activation` as the visible proof command.
- Show `sage api visitors` as a funnel, not just raw counters.
- Add dashboard wording that clones/downloads are external interest, not active installs.

## Next product fixes

- Add an admin report that separates:
  - connected keys,
  - machines with installs,
  - machines with at least one command,
  - active machines in the last 24h,
  - dead installs with zero runs.
- Add stricter admin cleanup for obvious junk/test identities.
- Add a first-run success banner that says:
  `SAGE is active. Your next commands should use: sage run -- <command>`.
- Add a README "30-second proof" block:
  `python -m pip install --upgrade psycgod-sage`
  then
  `sage doctor --activation`.
