# Changelog

## v2.4.3

### Fixed

- Public proof success rate now uses real SAGE run counts instead of token-usage rows, fixing bogus ratios like `15/7,502 successful`.

### Added

- Ollama is now included in public model and agent savings rows.
- `sage run -- ollama ...` is attributed to the Ollama row in public proof snapshots.

## v2.4.2

### Changed

- `sage api users` now shows the saved display name or hostname by default, while still hiding hash-like internal usernames.
- Connected-user rows now show short machine/install IDs so duplicate runner machines can be distinguished.

## v2.4.1

### Fixed

- `sage api users` now hides names, usernames, hashed runner identities, and raw telemetry-install counters by default.
- The private admin users endpoint now returns sanitized connected-user rows by default; raw identity fields require `?raw=1`.
- Added regression tests so raw identity output remains opt-in.

## v2.4.0

### Added

- `sage install` now performs system-wide local AI-agent enforcement without requiring cloud connection.
- `sage init` now installs project-local `AGENTS.md`, `CLAUDE.md`, `SAGE.md`, and Claude Code hook/settings files.
- Claude Code enforcement hook blocks bare shell commands, direct file/search/edit tools, and subagents without SAGE instructions.
- Live command output is capped by default so very noisy commands do not flood agent context before the SAGE summary.
- `sage telemetry off` sets local-only telemetry level 0, and `sage telemetry preview --level 0` is accepted.

### Changed

- README now makes `sage install` and `sage init` explicit first-class setup steps.
- `sage connect` copy now describes optional public proof sync instead of implying local SAGE requires cloud auth.

## v2.3.1

### Changed

- First-run flow: ML V2 prompt (y/n) runs before `sage connect`.
- Connect ending now confirms all detected AI agents use SAGE compulsorily.
- Clearer ML prompt explains V1 keeps learning if user skips V2.
- Connect prints "sage run -- pytest" as next step after setup completes.

## v2.3.0

### Changed

- ML V2 dependencies (torch, sentence-transformers, faiss-cpu) are now optional.
- Install base SAGE without CUDA/torch: `pip install psycgod-sage`.
- Install with ML V2: `pip install psycgod-sage[ml]`.
- Post-install prompt asks users if they want ML V2 features.

### Fixed

- Fix PowerShell built-in commands not working on Windows (sage now detects PowerShell vs cmd.exe).
- Resolve version inconsistencies across README and CHANGELOG.

## v2.2.2

### Fixed

- Stability fixes for context compression stats persistence.
- Telemetry sender background thread reliability.

## v2.2.0

### Added

- File operation tools: `sage read`, `sage grep`, `sage write`, `sage edit`, `sage glob`, `sage tree`.
- `sage call` for tracked agent tool-calls.
- `sage show --raw` to recover exact stored output.
- MCP tools for file operations (`sage_read_file`, `sage_grep`, `sage_write_file`, `sage_edit_file`, `sage_glob`, `sage_tree`).

### Changed

- MCP tool surface expanded from run/explain/suggest/agents/workflow/history to include file and search tools.

## v2.1.0

### Added

- LSP server (`sage lsp`) for editor and AI agent integration.
- Agentic retry loop with circuit breaker for auto-fix workflows.
- MCP tools: `sage_agentic_run`, `sage_agentic_fix`, `sage_agentic_session`.
- `sage.toml` configuration for agentic autonomy level and LSP transport.

### Changed

- Agent firewall now supports interactive approval prompts.
- Compression strategies are selectable per-command.

## v2.0.1

### Fixed

- Package build verification for clean virtual environment installs.
- Cloudflare Worker dashboard auto-refresh interval (now 10s).
- Public proof snapshot includes `estimated_savings_usd` and `savings_by_agent`.

### Documentation

- README updated with live proof stats from public dashboard.
- Install path clarified for PyPI/npm first installs.

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
- SAGE machine authentication is required for connected proof/dashboard sync.
- Telemetry above local-only is opt-in and policy-limited.
- The public dashboard publishes aggregate proof metrics only.
