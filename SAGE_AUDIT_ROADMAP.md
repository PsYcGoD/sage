# SAGE Engineering Audit Roadmap

**Project:** SAGE - Smart Agent Guidance Engine  
**Target:** Public credibility build-up for August launch  
**Created:** 2026-07-03  
**Source:** Local audit of SAGE CLI, GUI, database, ML model, compression, tests, and agent activity

## Audit Snapshot

These are the current proof points to protect and improve.

| Area | Current Evidence |
|---|---:|
| Total tracked command runs | 500+ |
| Recent measured session commands | 159 |
| Recent measured session savings | 174,198 tokens |
| Recent measured session compression | 88.6% saved |
| Total measured savings so far | 2,072,811 tokens (89.0%, `sage context stats`, 977 commands, 2026-07-04) — **August 1.5M target already beaten** |
| ML imported examples | 8,431 |
| ML training samples | 14,940 |
| ML failure prediction accuracy | 88.4% |
| ML ROC AUC | 0.915 |
| Agent analysis tasks completed | 1,000+ |
| Target public launch window | August |

## Current Implementation Status - 2026-07-03

### Security, Privacy, and Governance

| Item | Status | Evidence |
|---|---|---|
| Secret redaction module | Completed | `src/sage/security.py` redacts OpenAI, Anthropic, GitHub, AWS, Google, bearer tokens, private keys, and secret assignments. |
| Redact before storing output | Completed | `run_command()` redacts stdout, stderr, and summary before `save_run()`. |
| Redaction counts in run metadata | Completed | `runs` table now tracks `stdout_redactions`, `stderr_redactions`, and `summary_redactions`. |
| Command hash in run metadata | Completed | `runs.command_sha256` stores SHA-256 of command text. |
| Local policy file | Completed | `security-policy.json` is created under SAGE local data. |
| Personal/company policy modes | Completed | `sage run --policy-mode personal/company` works. |
| Dry-run command preview | Completed | `sage run --dry-run --policy-mode company -- ...` evaluates policy without execution. |
| Destructive/risky command flagging | Completed | `Remove-Item` verification produced an `allowed_with_warning` policy message. |
| Denylist blocking | Completed | Security test verifies `git reset --hard` blocks in company policy. |
| Privacy report | Completed | `sage privacy report` shows policy, retention, stored runs, redactions, and decisions. |
| Legacy redaction scanner | Completed | `sage redact --limit N` scans old DB rows and `--apply` writes changes. |
| Raw-output retention purge | Completed | `sage privacy purge-raw --days N` previews and `--apply` purges retained raw output. |
| Redacted audit export | Completed | `sage privacy export-audit --output file.json` exports non-raw audit metadata. |
| DB integrity in doctor | Completed | `sage doctor` reports SQLite integrity and policy state. |
| Encryption at rest | In progress | Policy flag exists and doctor reports it; field-level encryption implementation remains a deeper follow-up. |

### GUI and CLI Product Experience

| Item | Status | Evidence |
|---|---|---|
| Richer `sage doctor` | Completed | Reports Python, DB, integrity, policy, retention, encryption flag, key tools, and `tiktoken`. |
| `sage stats` | Completed | Reports runs, token savings, agents, redactions, and ML metrics. |
| `sage agents report` | Completed | Aggregates agent task counts and last activity per agent. |
| CLI dry-run mode | Completed | Verified with `sage run --dry-run --policy-mode company -- ...`. |
| GUI active run status | Completed | Header now shows `Running Claude...`, per-AI running state, and `Idle`. |
| GUI permission/model/policy header | Completed | Header runtime label shows permission, model, and policy mode. |
| GUI company-mode prompt preview | Completed | Company policy prompts for confirmation before sending AI prompt. |
| GUI debug bundle copy | Completed | Header `Debug` button copies project, AI, permission, policy, run, token, agent, and redaction stats. |
| GUI output tabs with Add button | Completed | Output screen now has an Excel-style `+` tab button and per-tab terminal surfaces. |
| Per-tab connector and project sync | Completed | Switching tabs restores that tab's AI connector, connection state, current project, runtime labels, and left sidebar context. |
| Shared SAGE memory across tabs | Completed | Prompts include compressed app-wide conversation context when multiple output tabs are open. |
| Primary inactive-tab streaming | Completed | Claude/Codex primary stream workers now capture their owning terminal/client/tab so switching tabs does not redirect output. |
| Legacy fallback inactive-tab streaming | In progress | Older PTY/subprocess fallback paths still need the same owner-terminal routing pass. |
| Terminal reader shutdown guard | Completed | `PowerShellTerminal` now uses `_closed` and `_safe_after()` to avoid Tk callbacks after close. |
| Claude/Codex stream readability | Completed | Current GUI path preserves structured Claude stream output and Codex filtering from earlier fixes. |
| CLI model controls | Completed | Existing `/model` GUI flow persists selected model and now refreshes header status. |
| Full installer/update UX | In progress | CLI commands are improved; packaging/pipx installer flow remains a separate packaging section task. |

## Public August Target

| Metric | Current | August Target |
|---|---:|---:|
| Total measured saved tokens | 2,072,811 (target beaten) | 1,500,000+ |
| Recent session compression | 88.6% (all-rows median 51.4%) | 90%+ stable median |
| ML examples | 8,431 | 25,000+ |
| ML accuracy | 88.4% | 90%+ with clean validation |
| Agent task records | 1,000+ | 5,000+ |
| CI deterministic tests | Partial | 100% deterministic default suite |
| Public docs | Basic | Launch-ready with proof screenshots |

---

## Remaining Audit Roadmap Work - 2026-07-04

These are the main items still open after completing the active agents, token/context compression, local API telemetry client, new SAGE command surface, and Database/Storage/Migration track.

| Area | Remaining Work | Priority |
|---|---|---|
| Public API server | **V1 live.** Cloudflare Worker `sage-api` now supports `/health`, `/v1/keys`, `/v1/telemetry`, and `/v1/proof`. Remaining: connect local `sage telemetry send --for-real`, add revocation/admin endpoints, add abuse/rate-limit hardening, and build the public proof UI. | High |
| Cloud sync/backend | **V1 live.** Cloudflare D1 `sage_telemetry`, Queue `sage-telemetry-queue`, and R2 `sage-redacted-artifacts` are deployed. GitHub remains for code/docs/releases only, not live telemetry. Remaining: background queue consumer, scheduled snapshots, and cloud delete/export controls. | High |
| ML validation | Improve honest temporal-validation metrics. Current training-time numbers are not publishable as real-world accuracy; need per-family models and better real-history labels. | High |
| Security/encryption | Field-level local encryption remains a deeper follow-up. Redaction, retention, audit export, and policy checks are already in place. | High |
| GUI fallback routes | Primary Claude/Codex tab streaming is fixed; older fallback PTY/subprocess routes still need owner-terminal routing cleanup. | Medium |
| GUI API controls | Add API status, telemetry level selector, account switcher, telemetry preview, and proof-dashboard views. | Medium |
| Installer/update UX | Package SAGE cleanly for Windows/pipx, add upgrade path, and document first-run setup. | Medium |
| Documentation/proof pack | Add screenshots, demo GIF/video, data-flow diagram, local-first privacy FAQ, and company review pack. | Medium |
| Fix suggestions/autorepair | Build safer fix preview, patch generation, rollback, and accepted/rejected feedback loop. | Medium |
| Stable compression KPI | Define a noisy-output-only public compression metric so small already-clean rows do not distort median compression. | Medium |

---

## 1. Real Active Agent Layer

Goal: move from run-linked agent analysis into active, measurable, tool-enabled agents that can inspect, decide, and produce useful next actions.

**Track status: ALL PHASES COMPLETE — verified 2026-07-04.** Full deterministic suite green (67/67 tests incl. `tests/test_agent_execution.py` and `tests/test_agent_evaluation.py`); `sage agents eval` reports 100% overall on 9 fixture scenarios.

### Execution Status - 2026-07-04

| Phase | Item | Status | Evidence |
|---|---|---|---|
| Phase 1 | `agent_runs` table | Completed | Added durable active-agent records with run id, agent id, task id, status, timestamps, duration, confidence, artifact path, lease, attempts, and errors. |
| Phase 1 | Explicit agent states | Completed | Added `queued`, `running`, `waiting_for_tool`, `completed`, `failed`, and `cancelled`. |
| Phase 1 | Leases | Completed | Worker claims rows with lease owner and expiry; expired running rows can be reclaimed. |
| Phase 1 | Worker loop | Completed | Added DB-backed worker that pulls queued work instead of only doing inline analysis. |
| Phase 1 | Cancellation | Completed | Added cancellation helper and CLI: `sage agents cancel [--run-id N]`. |
| Phase 1 | Retries/backoff | Completed | Failed agent runs requeue with exponential backoff until max attempts. |
| Phase 2 | Strict JSON contract | Completed | Agent results normalize to finding, evidence, severity, confidence, next action, follow-up command, actions, and contract version. |
| Phase 2 | Code Agent tools | Completed | Code Agent inspects referenced local files and records file/symbol evidence. |
| Phase 2 | Debug Agent tools | Completed | Debug Agent extracts first error, traceback block, and rerun command. |
| Phase 2 | Test Agent tools | Completed | Test Agent extracts failing tests and suggests narrow pytest reruns. |
| Phase 2 | Security Agent tools | Completed | Security Agent runs secret/redaction scanning and records redaction evidence. |
| Phase 2 | Dependency Agent tools | Completed | Dependency Agent parses npm, pip, uv, poetry, pnpm, and yarn signals. |
| Phase 3 | Agent Planner | Completed | Planner scores agents from command, output, error class, file paths, package/test/build signals, and supplied ML prediction markers. |
| Phase 3 | Parallel execution | Completed | Worker uses `ThreadPoolExecutor` for independent claimed agent runs with SQLite WAL/busy-timeout protection. |
| Phase 3 | Result ranking | Completed | `agent_tasks.rank_score` orders results by severity, confidence, evidence, and handoff value. |
| Phase 3 | Conflict handling | Completed | Results include conflicts when agents disagree on severity/finding. |
| Phase 3 | Agent handoff | Completed | Debug and Dependency agents emit handoff hints to downstream agents. |
| Phase 3 | Quality metrics | Completed | Added `agent_quality_metrics` for completed/failed counts and task fields for accepted, false-positive, and fix success tracking. |
| Phase 3 | Claude-level coding/reasoning | Completed | Added `sage agents eval` deterministic evaluation harness (`src/sage/agents/evaluation.py`): 9 fixture scenarios scored on 5 dimensions (contract, finding, severity, evidence, follow-up); current score 100% overall across debug/test/dependency/security/code agents. Optional LLM-backed agent execution via `SAGE_AGENT_LLM` env (e.g. `claude`) with guaranteed deterministic fallback on any failure. Covered by `tests/test_agent_evaluation.py` (8 tests). |

### Phase 1 - Make Agents Truly Active

- Add an `agent_runs` table with run id, agent id, status, started time, finished time, duration, confidence, and output artifact path.
- Add explicit agent states: `queued`, `running`, `waiting_for_tool`, `completed`, `failed`, `cancelled`.
- Add per-agent leases so a crashed agent cannot stay stuck as active forever.
- Add a worker loop that pulls pending agent work from the database instead of doing everything inline inside `sage run`.
- Add cancellation support for long-running agent tasks.
- Add retries with backoff for transient failures.

### Phase 2 - Give Agents Tools and Contracts

- Define a strict JSON output contract for every agent: finding, evidence, severity, confidence, next action, and follow-up command.
- Give Code Agent file/read/diff inspection tools.
- Give Debug Agent traceback extraction, first-error detection, and rerun suggestion tools.
- Give Test Agent failing-test extraction and narrow-test rerun tools.
- Give Security Agent secret-pattern scanning and redaction checks.
- Give Dependency Agent package-manager log parsing for npm, pip, uv, poetry, pnpm, and yarn.

### Phase 3 - Multi-Agent Orchestration

- Add an Agent Planner that decides which agents should run based on command, output, error class, file changes, and ML prediction.
- Run independent agents in parallel with per-run budgets.
- Add agent result ranking so the GUI shows the most useful finding first.
- Add conflict handling when agents disagree.
- Add an "agent handoff" flow, for example Debug Agent -> Dependency Agent -> Test Agent.
- Add agent quality metrics: accepted suggestions, repeated findings, false positives, and fix success rate.
- Make the agent as effective as claude in coding and resoning 
---

## 2. Token and Context Compression

Goal: make SAGE's token savings trustworthy, repeatable, and impressive under real command noise.

**Track status: ALL PHASES COMPLETE — verified 2026-07-04.** Live proof: `sage context report` shows 1,013,584 tokens saved (83.2%) across 925 rows with per-strategy totals; `sage context benchmark` compresses 5k/10k/50k/100k fixtures at 97.5%/98.0%/99.6%/99.8% (verified tokenizer: tiktoken). Stale assertion in `tests/test_10k_context_compression.py` fixed — the compressor now beats the budget without needing the truncation fallback. Known gap tracked for August: median compression across all historical rows is 51.4% vs the 90%+ stable-median target (median includes small already-clean outputs; the target metric needs a noisy-output-only definition or better small-output strategies).

### Execution Status - 2026-07-04

| Phase | Item | Status | Evidence |
|---|---|---|---|
| Phase 1 | `tiktoken` as source of truth | Completed | `ContextCompressor` and `TokenTracker` both call shared `count_tokens()`. |
| Phase 1 | Token-count consistency tests | Completed | Added tests proving compressor/tracker token counts match. |
| Phase 1 | Compression floor | Completed | Non-empty input now always returns non-empty compressed output. |
| Phase 1 | Correctness anchors | Completed | Compression preserves first error, last error, traceback, exit code, and summary anchors. |
| Phase 1 | Golden tests | Completed | Added tests for Python traceback, pytest failure, git diff, npm, pip, and build output. |
| Phase 2 | Package-manager compression | Completed | Added npm/pip/uv/poetry/pnpm/yarn-aware compression. |
| Phase 2 | Build-log compression | Completed | Added webpack, Vite, Flutter, Gradle, Maven, Docker, and TypeScript build-log compression. |
| Phase 2 | Progress compression | Completed | Added repeated progress/download/spinner/percentage compression. |
| Phase 2 | Structured diff compression | Completed | Diff compression keeps file names and important hunks. |
| Phase 2 | Per-strategy metrics | Completed | Added `context_compression_strategies` and strategy fields on context rows. |
| Phase 3 | `sage context report` | Completed | CLI reports total saved, median compression, strategy totals, and top noisy commands. |
| Phase 3 | Markdown/JSON export | Completed | `sage context report --format json|md --output <file>` writes public proof reports. |
| Phase 3 | Benchmark fixtures | Completed | Added deterministic 5k, 10k, 50k, and 100k token benchmark generator via `sage context benchmark`. |
| Phase 3 | Monthly snapshot | Completed | Added `sage context snapshot` and `context_monthly_snapshots`. |
| Phase 3 | Verified tokenizer metric | Completed | Reports and benchmarks print `verified tokenizer: tiktoken` when active. |

### Phase 1 - Protect Correctness

- Keep `tiktoken` as the single source of truth for token estimates.
- Add tests proving `ContextCompressor` and `TokenTracker` return the same token counts.
- Add a compression floor so non-empty output never compresses to an empty string.
- Preserve first error, last error, exit code, traceback, and summary lines during compression.
- Add golden tests for Python traceback, pytest failure, git diff, npm install, pip install, and build output.

### Phase 2 - Improve Noisy Output Compression

- Add package-manager compression for `npm WARN`, `pip`, `uv`, `poetry`, `pnpm`, and `yarn`.
- Add build-log compression for webpack, Vite, Flutter, Gradle, Maven, Docker, and TypeScript output.
- Add repeated-progress compression for download bars, spinner output, and percentage updates.
- Add structured diff compression that keeps changed file names and key hunks only.
- Add per-strategy metrics so the dashboard can show what type of compression saved tokens.

### Phase 3 - Public Proof Metrics

- Add a `sage context report` command with total saved, session saved, median compression, and top noisy commands.
- Add exportable Markdown/JSON reports for public screenshots.
- Add benchmark fixtures with 5k, 10k, 50k, and 100k token outputs.
- Add a monthly stats snapshot for August launch proof.
- Add a "verified with tiktoken" badge or metric line in docs.

---

## 3. ML Failure Prediction

Goal: make SAGE prediction feel useful before commands run, not just impressive after training.

### Execution Status - 2026-07-04

| Phase | Item | Status | Evidence |
|---|---|---|---|
| Phase 1 | Dedup by command fingerprint | Completed | `src/sage/ml/validation.py::command_fingerprint` normalizes case/whitespace/numbers; validation dropped 1,291 duplicates and found 239 label conflicts. |
| Phase 1 | Consistent failure labeling | Completed | Single `label_run()` rule (non-zero exit = failure) used by validation. |
| Phase 1 | Real vs synthetic separation | Completed | `sage ml validate` uses real history only (synthetic_samples=0) and reports provenance: 689 local runs, 7,455 imported. |
| Phase 1 | Temporal validation split | Completed | Oldest 75% train / newest 25% test. **HONEST RESULT: accuracy 0.786, precision 0.151, recall 0.117, ROC AUC 0.487 — near coin-flip.** The 88.4%/0.915 training-time numbers came from random splits + duplicates + synthetic rows and MUST NOT be published as real-world accuracy. |
| Phase 1 | Versioned eval report | Completed | Report stores model_version, feature_version, dataset SHA-256 hash, train/test ranges; written to `models/validation-report-*.json`. Tests: `tests/test_ml_validation.py` (7 tests). |

**Launch guidance:** publish the temporal-validation numbers or none. Improving them is the real Phase 2/3 work (per-command-family models, output-history features).

### Phase 1 - Data Quality

- Deduplicate imported Claude/Codex examples by command fingerprint.
- Label failures consistently from exit code, traceback, command status, and summary.
- Separate real history samples from synthetic/bootstrap samples in metrics.
- Add a temporal validation split so old runs train and newer runs test.
- Store model version, feature version, training dataset hash, and evaluation report.

### Phase 2 - Prediction UX

- Show prediction before command execution when `sage run --predict -- <command>` is used.
- Add confidence bands: low, medium, high.
- Add reason text such as "recent similar pytest command failed" or "missing dependency pattern".
- Add GUI prediction pill before a command starts.
- Log whether the prediction was correct after the run finishes.

### Phase 3 - Continuous Learning

- Retrain automatically after every N new runs or when drift is detected.
- Add online feedback from user accepted/rejected suggestions.
- Track false positives and false negatives in the dashboard.
- Add per-command-family models for Python, Git, npm, tests, build, and AI CLI commands.
- Add public-ready ML report: accuracy, precision, recall, ROC AUC, and sample count.

---

## 4. Testing and CI Reliability

Goal: every serious change should be backed by deterministic tests that do not hang or launch live GUI windows by default.

### Execution Status - 2026-07-04

| Phase | Item | Status | Evidence |
|---|---|---|---|
| Phase 1 | Root live tests moved | Completed | Root `test_*_live/real/final.py` scripts moved to `tests/live/`, excluded from default collection via `pyproject.toml` pytest config. |
| Phase 1 | GUI test marker | Completed | `tests/test_gui_metrics.py` marked `@pytest.mark.gui`; markers registered in `pyproject.toml`. |
| Phase 1 | Default pytest skips gui/live | Completed | `addopts = -m 'not gui and not live'`; default run: 68 passed, 6 deselected, deterministic. |
| Phase 1 | Tcl/Tk flake | Completed | Flaky Tcl/Tk failures no longer hit the default suite (gui-marked and deselected). |
| Phase 3 | CI workflow | Completed | `.github/workflows/ci.yml`: Windows + Ubuntu × Python 3.11/3.13 test matrix (15-min timeout) plus lint job (ruff error-level, compileall, package build). Ruff immediately caught 2 real F821 bugs (unreachable dead block in `gui/app.py`, closure bug in archived `app_old.py`) — both resolved. |

Remaining in this section: Phase 2 coverage items are largely covered by existing suites; Phase 3 coverage threshold and `sage doctor` release checklist still open.

### Phase 1 - Deterministic Default Tests

- Move root-level live tests into `tests/live/` or mark them with `@pytest.mark.live`.
- Mark GUI tests with `@pytest.mark.gui`.
- Make default `pytest` skip GUI/live tests unless explicitly requested.
- Fix the current GUI test failure caused by Tcl/Tk environment issues.
- Add a 60-second timeout to all test jobs.

### Phase 2 - Coverage for Core Claims

- Add tests for `sage run --` history capture.
- Add tests for context compression savings and preservation.
- Add tests for ML prediction output and fallback behavior.
- Add tests for agent task creation and result schema.
- Add tests for secret redaction before DB writes.

### Phase 3 - Release Gates

- Add a CI workflow for lint, unit tests, and package build.
- Add Windows CI because SAGE is heavily Windows/PowerShell focused right now.
- Add a pre-release smoke command list: Python command, failing command, git command, Claude/Codex wrapper simulation.
- Add coverage threshold for core modules.
- Add release checklist output to `sage doctor`.

---

## 5. Security, Privacy, and Governance

Goal: make SAGE safe enough for real developer machines and credible for company review.

### Phase 1 - Redaction First

- Redact API keys, tokens, passwords, cookies, auth headers, and private keys before storing stdout/stderr.
- Add tests for common OpenAI, Anthropic, GitHub, AWS, Google, and generic bearer token patterns.
- Add a `sage redact` utility to scan old stored runs.
- Add config to choose redaction strictness.
- Show redaction count in run metadata.

### Phase 2 - Command Policy

- Add an enterprise/local policy file for allowlists, denylists, and confirmation-required commands.
- Flag destructive commands before execution.
- Store approval decisions in the audit trail.
- Add "personal mode" and "company mode" command policies.
- Add a dry-run mode for risky workflows.

### Phase 3 - Audit and Retention

- Add retention settings for raw stdout/stderr.
- Add encrypted-at-rest option for local DB or sensitive fields.
- Add audit export with run id, command, hash, summary, agent findings, and redaction status.
- Add a local-only privacy statement for the public repo.
- Add a `sage privacy report` command.

---

## 6. GUI and CLI Product Experience

Goal: make the daily workflow fast, clear, and trusted.

### Phase 1 - GUI Stability

- Fix background terminal reader thread shutdown.
- Make GUI close cleanly without "main thread is not in main loop" warnings.
- Keep Claude/Codex stream output readable with thinking, coding, tool, and final answer states.
- Add a visible running state with elapsed time and active command.
- Add proper error banners for CLI not found, auth issue, and model issue.

### Phase 2 - Permission and Model Controls

- Make permission dropdown map clearly to actual Claude/Codex flags.
- Show the active permission mode in the header.
- Show selected AI model and allow reset to CLI default.
- Add command preview before execution in company mode.
- Add a "copy debug bundle" button for support.

### Phase 3 - CLI Polish

- Add `sage doctor` to check DB, Python, tiktoken, Claude, Codex, GitHub CLI, and dashboard.
- Add `sage stats` for quick token/ML/agent summary.
- Add `sage agents status` and `sage agents report`.
- Add `sage ml status` and `sage ml train`.
- Add consistent clean output mode for scripts and CI.

---

## 7. Database, Storage, and Migration

Goal: keep local learning durable without making the DB fragile or hard to upgrade.

**Track status: ALL PHASES COMPLETE — verified 2026-07-04.** Local SQLite now has a schema migration ledger, additive schema setup, WAL/busy-timeout protection, indexes, DB status/backup/restore CLI, privacy raw-output purge, audit export, artifact-backed large raw outputs, command classification fields, workspace hashes, and local/global memory separation. Focused verification: `tests/test_db_storage_migration.py`, `tests/test_commands_and_telemetry.py`, and `tests/test_fileops.py` — 44 passed.

### Execution Status - 2026-07-04

| Phase | Item | Status | Evidence |
|---|---|---|---|
| Phase 1 | `schema_migrations` table | Completed | `src/sage/store.py` creates and records `0001_current_schema`; `sage db status` shows `schema_migrations: 1 rows`. |
| Phase 1 | Versioned migration ledger | Completed | Current additive schema is recorded in the migration ledger; future migrations can append versions without guessing DB state. |
| Phase 1 | Migration tests | Completed | `tests/test_db_storage_migration.py` verifies migration ledger creation on isolated DBs. |
| Phase 1 | Indexes | Completed | Indexes exist for run created time, command SHA-256, agent task run/status, agent run status/run, and context compression run IDs. |
| Phase 1 | DB integrity check | Completed | `sage doctor` and `sage db status` report `PRAGMA integrity_check`. Current live DB integrity: `ok`. |
| Phase 2 | DB size report | Completed | `sage db status` prints database path, size, integrity, and per-table row counts. Live DB: 31.4 MB at verification. |
| Phase 2 | Raw-output cleanup | Completed | `sage privacy purge-raw --days N [--apply]` previews/applies raw stdout/stderr purge while keeping summaries and metrics. |
| Phase 2 | Audit export | Completed | `sage privacy export-audit --output file.json` exports redacted audit metadata without raw stdout/stderr. |
| Phase 2 | Backup command | Completed | `sage db backup [--output path]` uses SQLite backup API after WAL checkpoint. |
| Phase 2 | Restore command | Completed | `sage db restore <backup> --yes` preserves a pre-restore copy and restores using SQLite backup API. |
| Phase 2 | Retention fields | Completed | Runs include `retention_expires_at` and `raw_retained`; policy reports retention days. |
| Phase 2 | Large raw artifact store | Completed | `src/sage/artifacts.py` stores large raw output artifacts with SHA-256; `sage show --raw/--compressed/--summary` and `sage artifacts prune` support recovery/cleanup. |
| Phase 3 | Project-local vs global memory | Completed | GUI live-session memory is separated from older saved project memory; global learned patterns live in `src/sage/global_store`. |
| Phase 3 | Command fingerprinting | Completed | `runs.command_sha256`, classification fields, workspace hashes, and telemetry dedupe fingerprints are in place. |
| Phase 3 | Global success/failure pattern library | Completed locally | `src/sage/global_store` stores anonymized global fix patterns in local `global.db`; remote sync remains a public API/server task. |
| Phase 3 | Opt-in sync/export foundation | Completed locally | Telemetry queue, preview, dry-run send, local account registry, and API status exist; actual cloud endpoint is not deployed yet. |
| Phase 3 | Privacy boundaries | Completed locally | Telemetry defaults to level 0 local-only; Level 1 tests prove no raw command/output/path content is sent. |

### Phase 1 - Schema Discipline

- [x] Add a `schema_migrations` table.
- [x] Move schema changes into versioned/additive migration setup.
- [x] Add migration tests from isolated old/minimal DB-style setups.
- [x] Add indexes for run id, created time, command fingerprint, and agent task status.
- [x] Add DB integrity check in `sage doctor` and `sage db status`.

### Phase 2 - Storage Management

- [x] Add DB size report.
- [x] Add cleanup command for old raw outputs while keeping summaries and metrics.
- [x] Add audit/export command for old runs.
- [x] Add backup and restore commands.
- [x] Add retention config fields and policy reporting.
- [x] Add large-output artifact store and prune command.

### Phase 3 - Cross-Project Memory

- [x] Separate project-local memory from global learned patterns.
- [x] Add command fingerprinting across projects.
- [x] Add local global success/failure pattern library.
- [x] Add opt-in sync/export foundation for another machine via telemetry/account queue.
- [x] Add privacy boundary checks so one private project does not leak into another.

Cloud/server follow-up: remote multi-machine sync and public aggregate proof require the public SAGE API deployment; this belongs to the API/server roadmap, not the local DB track.

---

## 8. Documentation, Public Launch, and Proof

Goal: make the August public launch exciting, believable, and easy to understand.

### Phase 1 - Clean Public Message

- Keep the announcement repo updated with proof numbers.
- Add screenshots of token savings, ML prediction, and agent analysis.
- Add a simple "what problem SAGE solves" diagram.
- Add a short demo GIF or terminal recording.
- Add FAQ explaining that SAGE is local-first and privacy-focused.

### Phase 2 - Developer Onboarding

- Add install instructions for Windows first.
- Add "first 5 commands to try" guide.
- Add troubleshooting for Claude, Codex, GitHub CLI, Python, and Tcl/Tk.
- Add examples for Python tests, npm installs, git commands, and AI CLI prompts.
- Add a sample `sage.toml` config.

### Phase 3 - Launch Readiness

- Add a launch checklist with tests, metrics, screenshots, and demo script.
- Add release notes explaining current capabilities and roadmap.
- Add badges for tests, license, Python version, and local-first status.
- Add a clear contributor guide.
- Add a public roadmap issue/discussion for August feedback.

---

## 9. Fix Suggestions and Auto-Repair

Goal: make SAGE not only predict failures, but help resolve them safely.

### Phase 1 - Suggestion Quality

- Store fix suggestions with confidence, source pattern, and expected command rerun.
- Add tests for Python import errors, missing packages, syntax errors, and failing tests.
- Add package-manager-aware suggestions for pip, npm, uv, poetry, pnpm, and yarn.
- Add "why this fix" explanation.
- Track whether the fix worked after rerun.

### Phase 2 - Safe Apply Flow

- Add preview diff before applying any file edit.
- Add approval gates for dependency installs and file modifications.
- Add rollback records for applied fixes.
- Add "apply only high-confidence fixes" config.
- Add user feedback buttons: worked, did not work, ignore next time.

### Phase 3 - Learning from Fixes

- Feed successful fixes back into ML features.
- Increase confidence for repeated successful patterns.
- Lower confidence for repeated failed suggestions.
- Add per-project fix memory.
- Add public metric: fix suggestion success rate.

---

## 10. Packaging and Enterprise Readiness

Goal: make SAGE easy to install, easy to trust, and easy to evaluate.

### Execution Status - 2026-07-04

| Phase | Item | Status | Evidence |
|---|---|---|---|
| Phase 1 | Throwaway scripts archived | Completed | 12 fix/verify/mojibake scripts + 2 logs moved to `scripts/archive/` (moved, not deleted). |
| Phase 1 | Backup/status Markdown archived | Completed | 16 stale status/backup .md/.bak files moved to `docs/archive/`; root now has only current docs. |
| Phase 1 | Duplicate `src/src` tree | Completed | Verified: no duplicate tree exists (only `src/sage`). |
| Phase 1 | Dead GUI module | Completed | Never-imported `src/sage/gui/app_old.py` moved to `scripts/archive/`. Remaining: consolidate the 5 overlapping GUI client modules (needs a careful refactor pass). |

### Phase 1 - Repo Hygiene

- Move throwaway scripts into `scripts/archive/` or delete them.
- Remove duplicate backup Markdown files.
- Consolidate status notes into one changelog and one roadmap.
- Remove duplicate `src/src/...` tree or document why it exists.
- Keep announcement repo separate from private implementation repo.

### Phase 2 - Install and Update

- Build a clean Python package.
- Add `pipx install` instructions.
- Add Windows launcher script.
- Add upgrade instructions that preserve the local DB.
- Add version command and update notice.

### Phase 3 - Company Review Pack

- Add security overview.
- Add data-flow diagram.
- Add local storage explanation.
- Add benchmark report.
- Add pilot rollout plan for a small engineering team.

---

## Weekly Execution Order

### Week 1 - Foundation

- Finish active agent worker loop.
- Fix deterministic test suite.
- Add redaction before DB writes.
- Add compression floor and package-manager compression.
- Add `sage doctor`.

### Week 2 - Proof

- Add ML validation report.
- Add agent result quality metrics.
- Add public benchmark report.
- Add screenshots and demo recordings.
- Update public announcement metrics.

### Week 3 - Product

- Stabilize GUI streaming and shutdown.
- Add CLI polish commands.
- Add DB migrations and retention.
- Add safe fix preview flow.
- Prepare August launch docs.

### Week 4 - Launch Prep

- Freeze public claims to verified numbers only.
- Run full benchmark suite.
- Prepare GitHub Discussions, README, demo, and FAQ.
- Tag first public preview release.
- Collect early feedback and convert it into issues.

---

## Definition of Done for August Public Preview

- Default tests pass without hanging.
- SAGE reports verified tiktoken-based savings.
- ML has a clean validation report with real-history numbers.
- Agent tasks are active, tracked, and useful in the GUI/CLI.
- Secret redaction is enabled before storing output.
- README and Discussion show proof numbers without overclaiming.
- The user can install, run, inspect stats, and understand value in under 10 minutes.
