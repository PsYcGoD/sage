# Contributing

Thanks for working on SAGE CLI. This repository ships the public CLI-first package.

## Setup

```bash
pip install -e .[all]
python -m pytest -q
```

The published distribution name is `psycgod-sage`, but the CLI command remains `sage`.

## Branches

Use short, conventional branch names:

```text
docs/local-only-quickstart
tests/local-only-no-oauth
cli/first-run-message
```

## Development Rules

- Keep public changes scoped to the CLI package unless the GUI is explicitly being prepared for public release.
- Do not commit local databases, caches, secrets, generated credentials, or private logs.
- Preserve the local-first privacy model: raw terminal output stays local by default.
- Add or update tests for behavior changes.
- Keep README and release material honest about current public limitations.

## Pull Request Checklist

- [ ] The change is scoped and reviewable.
- [ ] Docs match actual behavior.
- [ ] Tests were added or updated for behavior changes.
- [ ] `python -m compileall -q src/sage` passes.
- [ ] `python -m pytest -q` passes, or any skipped test is explained.
- [ ] No raw logs, secrets, caches, local databases, or private data are committed.

## Good First Issues

Good starter contributions include local-only screenshots, agent-specific usage guides, Windows install notes, small privacy-doc improvements, targeted tests, and clearer safety-policy error messages. Avoid fake activity, fake testimonials, inflated stats, or whitespace-only PRs.

## Release Checklist

Before a release that changes public copy, dashboard behavior, telemetry, proof metrics, or release material:

1. Refresh `docs/assets/sage-live-dashboard.png` from the live public dashboard.
2. Update README/announcement proof stats when visible numbers changed.
3. Verify there is no broken UTF-8/mojibake text.
4. Commit only relevant files.
