# SAGE Repository Instructions

## Mandatory Shell Wrapper

SAGE is installed in this repository. Route every shell command through:

```powershell
sage run -- <command>
```

Examples:

```powershell
sage run -- git status
sage run -- python -m pytest
sage run -- npm install
```

If `sage run --` fails before the target command starts, stop and report the SAGE wrapper failure instead of bypassing it.

## Commit Checklist

Before every Git commit that changes public copy, dashboard behavior, telemetry, proof metrics, or release material:

1. Refresh `docs/assets/sage-live-dashboard.png` from the live public dashboard.
2. Update README/announcement proof stats when visible numbers changed.
3. Verify there is no broken UTF-8/mojibake text.
4. Commit only relevant files; do not include local databases, caches, secrets, or unrelated user edits.
