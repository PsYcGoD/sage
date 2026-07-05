# Contributing

Thanks for working on SAGE. This repository currently ships the public CLI-first package.

## Setup

```bash
pip install -e .[all]
python -m pytest -q
```

The published distribution name is `sage-cli`, but the CLI command remains `sage`.

## Development Rules

- Keep public changes scoped to the CLI package unless the GUI is explicitly being prepared for public release.
- Do not commit local databases, caches, secrets, generated credentials, or private logs.
- Preserve the local-first privacy model: raw terminal output stays local by default.
- Add or update tests for behavior changes.
- Keep README and release material honest about current public limitations.

## Release Checklist

Before a release that changes public copy, dashboard behavior, telemetry, proof metrics, or release material:

1. Refresh `docs/assets/sage-live-dashboard.png` from the live public dashboard.
2. Update README/announcement proof stats when visible numbers changed.
3. Verify there is no broken UTF-8/mojibake text.
4. Commit only relevant files.
