# Changelog

## v2.0.0-cli-public

Public CLI-first release candidate for SAGE.

### Changed

- Rename the public PyPI distribution to `psycgod-sage` while keeping the installed command as `sage`.
- Mark the package as beta because the public package is CLI-first and the GUI is not included yet.
- Position SAGE as a local-first command wrapper for AI coding agents.
- Document the public proof model, telemetry behavior, and known limitations.

### Security

- Store new SAGE API keys in the operating system keyring when available.
- Keep raw command output and logs local by default.
- Keep public dashboard data aggregate-only.

### Documentation

- Add install instructions for `pip install psycgod-sage`.
- Add release notes for `v2.0.0-cli-public`.
- Add `SECURITY.md` and `CONTRIBUTING.md`.
- Add terminal capture assets for `sage run --`, `sage context report`, and `sage mcp install`.

### Known Limitations

- The GUI is not public yet.
- GitHub OAuth / SAGE API access is required for most API-backed commands.
- Telemetry above local-only is opt-in and policy-limited.
- The public dashboard publishes aggregate proof metrics only.
