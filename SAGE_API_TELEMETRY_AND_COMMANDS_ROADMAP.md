# SAGE API Telemetry and Command Compression Roadmap

## Execution Status - 2026-07-04

| Phase | Status | Evidence |
|---|---|---|
| 1. Command classification | **Completed** | `src/sage/classify.py` (pure, never blocks); runs store command_kind/family/caller/workspace_hash; `sage history --kind read\|grep\|test\|...`; tests green. |
| 2. `sage read` | **Completed** | `src/sage/reader.py`: exact small reads, `--lines START:END`, `--symbols`, `--raw`, `--max-tokens`; large files -> outline + head with line refs; stored as runs. Live: README.md read at 98.6% compression. |
| 3. `sage grep` | **Completed** | `src/sage/searcher.py`: rg when available + Python fallback, grouped/capped results with exact paths+lines, hidden-match counts, grep exit-code semantics. |
| 4. `sage call` | **Completed** | Same execution core as `sage run` (no duplicate path) + `--purpose/--agent/--task-id/--caller`, agent_tasks linkage. |
| 5. Raw artifact store | **Completed** | `src/sage/artifacts.py`: >64KB outputs go to files with SHA-256, `sage show --raw/--compressed/--summary`, `sage artifacts prune --days/--max-gb` (preview-first). |
| 6. API key / account bootstrap | **Server v1 live** | Local anonymous install/config exists; Cloudflare `POST /v1/keys` now creates free API keys and stores only hashes. CLI `sage login/whoami` wiring remains next. |
| 7. Safe telemetry sync | **Server v1 live** | Client-side queue/redaction exists; Cloudflare `POST /v1/telemetry` accepts bearer-auth Level 1 metrics, enforces idempotency, and rejects raw command/output/path fields. CLI real-send wiring remains next. |
| 7A. Account/data management | **Server v1 live** | Local account registry exists; Cloudflare D1 stores key profile fields, privacy max, public profile flag, and aggregate counters. Org/team policy backend remains next. |
| 8. Public proof dashboard | **API proof live** | `GET /v1/proof` returns aggregate runs, tokens processed/compressed/saved, compression %, success rate, failure-prediction stats, and opt-in public contributor username/profile name. |
| 9. Cloud ML pipeline | **Blocked: needs server** | Local training + honest temporal validation (`sage ml validate`) already shipped. |
| 10. Enterprise readiness | Not started | Depends on server + docs pack. |
| 11. GUI integration | Not started | Deferred to a GUI-focused session. |
| 12. MCP and agent integration | **Completed** | MCP tools `sage_read_file`, `sage_grep`, `sage_call`, `sage_show_raw` registered and tested (`tests/test_mcp_sage_tools.py`). |
| 13. Rollout | **Local-first items shipped** | Build-order items 1-7 (read, grep, artifact store, show --raw, classification, telemetry preview) all local-only and live. Cloud items follow the server. |

**Added beyond the original roadmap (2026-07-04):** `sage write` (create/overwrite/append with sha256 confirmation instead of echoing content — the whole file's tokens are never spent twice), `sage edit` (exact string replacement with uniqueness check, compact change preview, `--json-stdin` for multiline), `sage restore-file` (undo — every write-over/edit snapshots the prior content to `file-snapshots/`), `sage glob` (newest-first, junk-dirs ignored, capped), and `sage tree` (depth-limited outline). All recorded as runs with kinds write/edit/glob/tree, all exposed as MCP tools (`sage_write_file`, `sage_edit_file`, `sage_glob`, `sage_tree`), covered by `tests/test_fileops.py` (18 tests). Suite total: 114 passing.

Design decisions applied (differ from original text, deliberately): default telemetry level is **0 (local-only)**, not 1 — nothing is ever uploaded until the user both raises the level and configures an endpoint; `sage call` shares the `run` execution core instead of duplicating it; Level 1 payloads carry `ml_model_version` so weak-model predictions can be filtered server-side later. Verified: 96 tests passing, ruff clean.

## Cloudflare API Deployment Status - 2026-07-04

Status: first live SAGE public API deployed.

| Item | Status | Evidence |
|---|---|---|
| Worker | **Live** | `sage-api` deployed to `https://sage-api.pascoaldsouza28.workers.dev` and custom domain `https://sage.api.marketingstudios.in`. |
| D1 | **Live** | `sage_telemetry`, ID `30dce3a3-6f7f-423c-9f29-4ff812685752`, schema applied remotely. |
| Queue | **Live** | `sage-telemetry-queue` bound as `TELEMETRY_QUEUE`. |
| R2 | **Live** | `sage-redacted-artifacts` bound as `ARTIFACTS` for future explicit opt-in redacted artifacts. |
| API key creation | **Live** | `POST /v1/keys`; key is shown once, only SHA-256 hash is stored. |
| Telemetry ingest | **Live** | `POST /v1/telemetry`; bearer auth, idempotency key, Level 1 raw-field rejection. |
| Public proof | **Live** | `GET /v1/proof`; totals include runs, tokens processed/compressed/saved, compression %, success rate, prediction stats, and public contributor display names/usernames when opted in. |
| Verification seed | **Completed** | Founder/test event inserted: 100,000 processed, 12,000 compressed, 88,000 saved, 88.0% compression, public contributor `PsYcGoD`. |
| Local login CLI | **Live** | `sage login`, `sage whoami`, `sage logout`, and `sage api status` now create/store a key locally and default to `https://sage.api.marketingstudios.in`. |
| Real CLI telemetry send | **Live** | `sage run` now auto-queues safe Level 1 telemetry and starts a detached background sender when connected. `sage telemetry send --for-real` remains as manual retry. Live check: queue drained to 0 and public proof reached 73 runs / 1,572,809 saved tokens. |
| GUI API controls | **Live** | Settings now has `SAGE Cloud API` with Connect, Disconnect, Refresh, and Sync Now. Connect shows a visible success/error dialog, stores the API key locally, and automatic safe sync is on after connection. |

Custom domain note: Cloudflare public DNS resolves `sage.api.marketingstudios.in`; this Windows resolver may temporarily cache the earlier NXDOMAIN. Forced public-DNS verification passed with `curl --resolve sage.api.marketingstudios.in:443:104.21.45.222 https://sage.api.marketingstudios.in/health`.

## Goal

Build SAGE into a local-first developer tool that can prove real token and context savings at scale while protecting private code by default.

The system should support:

- Local command compression for `run`, `read`, `grep`, and `call`.
- A free SAGE API key used for activation, anonymous proof metrics, and optional sync.
- A public proof dashboard showing aggregate usage, tokens processed, tokens saved, compression rate, success rate, and failure-prediction results.
- ML training from safe telemetry first, with deeper opt-in data only when users approve it.
- Exact raw command output retained locally so SAGE can compress context without changing what the command actually does.

## Product Principle

SAGE must not become a tool that secretly uploads source code.

Default mode:

```text
Raw output stays local.
Compressed summaries can be used locally by agents.
Only safe telemetry is uploaded.
```

Every sync level must be explicit and visible.

## Core Architecture

```text
Developer machine
  |
  | sage run/read/grep/call
  v
Local SAGE engine
  - executes command
  - stores raw output locally
  - compresses context locally
  - categorizes command/result
  - writes local DB proof
  |
  | safe telemetry only
  v
SAGE API
  - auth/API key
  - aggregate metrics
  - team/project dashboards
  - ML training store
  - public proof counters
```

## Public API Deployment Decision

Recommended hosting path:

```text
GitHub
  - source code
  - docs
  - releases
  - optional scheduled public proof snapshot

Cloudflare
  - Workers API for login, API keys, telemetry ingest, and dashboard reads
  - D1 for account, key, policy, aggregate, and idempotency metadata
  - Queues for telemetry ingest buffering
  - R2 for optional redacted reports/artifacts only
  - Analytics/Durable Objects if live counters or rate limits need stronger coordination

Local SQLite
  - source of truth for raw runs, raw output pointers, local proof, and local ML
  - outbound telemetry queue
  - account aliases and active policy cache
```

GitHub should not receive live per-command telemetry. Live command telemetry belongs in Cloudflare or another API backend. GitHub can publish source, docs, release notes, and an optional scheduled proof file such as `public-proof.json` or a README badge snapshot generated from aggregate Cloudflare counters. This avoids noisy commits, prevents private command leakage into Git history, and keeps revocation/deletion practical.

Cloudflare should receive live updates only after the user opts into telemetry and configures an endpoint/API key. The local DB remains useful without the cloud path.

Research basis checked 2026-07-04:

- Cloudflare Workers storage options: https://developers.cloudflare.com/workers/platform/storage-options/
- Cloudflare Queues: https://developers.cloudflare.com/changelog/product/queues/
- Cloudflare R2 asset storage: https://developers.cloudflare.com/workers/tutorials/upload-assets-with-r2/
- Cloudflare API token permissions: https://developers.cloudflare.com/fundamentals/api/reference/permissions/
- Cloudflare Workers metrics and analytics: https://developers.cloudflare.com/workers/observability/metrics-and-analytics/

### API Key Generation

API keys should be generated server-side by the SAGE API, not inside GitHub and not by trusting a user-provided key.

Required design:

- Generate at least 32 random bytes with a cryptographic random source.
- Encode with a clear prefix, for example `sage_live_<key_id>_<secret>` or `sage_test_<key_id>_<secret>`.
- Show the full key exactly once.
- Store only a keyed hash of the secret, never the secret itself.
- Store key metadata separately: key ID, owner user ID, optional org ID, scope, privacy max, created time, last used time, revoked time, and rate limit.
- Let the local client store the key in the OS credential store when available, with encrypted/local config as fallback.
- Authenticate telemetry with the key and require an idempotency key for every uploaded event batch.
- Allow key revocation to stop future sync without deleting local SQLite data.

### Clean Local-to-Cloud Data Flow

```text
1. Command runs locally through sage run/read/grep/call/write/edit/glob/tree.
2. Local SQLite stores the durable run record and token proof.
3. Large raw output is stored as a local artifact pointer, not copied into public telemetry.
4. Redaction builds an outbound event according to the active telemetry level.
5. The local telemetry queue stores the event, idempotency key, account context, and sync status.
6. Cloudflare ingest validates the API key, policy, schema version, payload size, and idempotency key.
7. D1 stores account/key/policy metadata plus aggregate-safe event facts.
8. Public dashboard reads aggregate counters only.
9. ML training jobs can use only rows whose policy explicitly allows training.
```

Default Level 0 behavior:

- No cloud upload.
- No API key required.
- Raw output remains local.
- Local proof and compression still work.

Level 1 cloud behavior:

- Upload aggregate metrics only.
- Do not upload raw commands, raw stdout/stderr, file contents, repo names, absolute paths, secrets, emails, or private URLs.
- Use salted workspace hashes and run fingerprints for dedupe.
- Count tokens saved, command kind, duration, exit code bucket, success/failure, compression strategy, and agent metadata.

Higher levels must be explicit opt-in and must remain separable by account, organization, installation, workspace hash, API key, and permission policy.

## New Command Surface

### 1. `sage run -- <command>`

Purpose: general command execution with token accounting and compression.

Examples:

```powershell
sage run -- python -m pytest
sage run -- npm test
sage run -- git status --short
```

Must preserve:

- Exit code.
- Stdout.
- Stderr.
- Working directory.
- Duration.
- Raw output access.
- Existing command behavior.

SAGE adds:

- Token count before compression.
- Token count after compression.
- Saved tokens.
- Compression ratio.
- Error category.
- ML failure prediction features.
- Agent task records.

### 2. `sage read -- <file>`

Purpose: safe replacement for `cat`, `type`, and `Get-Content` when an AI agent needs to read files.

Examples:

```powershell
sage read -- README.md
sage read -- src/sage/gui/app.py
sage read -- --lines 120:220 src/sage/gui/app.py
sage read -- --symbols src/sage/gui/app.py
```

Must preserve:

- Ability to read exact content.
- Ability to read line ranges.
- Ability to fetch raw output.
- Correct encoding handling.

SAGE adds:

- File metadata: bytes, lines, extension, language guess.
- Token count for full file.
- Compressed view for AI context.
- Important sections first: imports, classes, functions, errors, TODOs, config blocks.
- Stable line references.
- Optional raw mode:

```powershell
sage read --raw -- src/sage/gui/app.py
```

### 3. `sage grep -- <pattern> <path>`

Purpose: safe replacement for `rg`, `grep`, and `Select-String` when searching code or logs.

Examples:

```powershell
sage grep -- "def _build_contextual_prompt" src
sage grep -- --glob "*.py" "context_compression" src tests
sage grep -- --context 2 "invalid_api_key" .
```

Must preserve:

- Matching file paths.
- Line numbers.
- Match text.
- Exit code semantics.
- Raw output access.

SAGE adds:

- Deduplicated result summaries.
- Result grouping by file.
- Top matches first.
- Noisy repetition trimming.
- Match count and affected files count.
- Token saved proof for search output.

### 4. `sage call -- <command>`

Purpose: explicit "tool-call" wrapper for agents and integrations.

Examples:

```powershell
sage call -- gh pr check
sage call -- python scripts/audit.py
sage call -- powershell -NoProfile -Command "Get-Process"
```

Difference from `run`:

- `run` is for normal user terminal commands.
- `call` marks the execution as an agent/tool/API call.
- This helps train ML on which tool calls are useful, slow, failing, or noisy.

SAGE adds:

- Caller identity: CLI, GUI, MCP, agent, CI, API.
- Tool purpose: read, search, test, build, deploy, network, unknown.
- Tool result usefulness score.
- Agent feedback fields.

### 5. Raw Output Recovery

Every compressed command must support raw recovery:

```powershell
sage show --raw <run_id>
sage show --compressed <run_id>
sage show --summary <run_id>
sage export --run <run_id> --raw
```

This is mandatory because compression must not destroy the original job result.

## API Telemetry Model

## Account, API Key, and Data Ownership Model

SAGE must support many users, machines, repos, companies, and API keys without mixing private data incorrectly.

Core rule:

```text
Metrics can be aggregated.
Private data ownership must stay separate.
Raw data must never be merged across accounts unless an admin explicitly allows it.
```

### Identity Layers

| Layer | Example | Purpose |
|---|---|---|
| User account | `user_123` | Personal dashboard, API keys, settings |
| Organization | `org_456` | Company/team billing, policies, aggregate proof |
| Installation | `install_abc` | One local SAGE install on one machine |
| Workspace | `workspace_hash` | One repo/project, hashed locally |
| API key | `sk_sage_...` | Auth and permission scope |
| Device session | `session_uuid` | Current GUI/CLI session |
| Run | `run_local_id` + hash | One command/read/grep/call |

This allows SAGE to answer:

- How much did this user save?
- How much did this machine save?
- How much did this repo save?
- How much did this team save?
- How much did SAGE save globally?
- Which API key sent which telemetry?
- Which data is allowed to train ML?

### API Key Types

| Key Type | Scope | Use |
|---|---|---|
| Personal key | One user | Individual SAGE sync |
| Installation key | One machine | Anonymous or local install tracking |
| Organization key | One org/team | Team metrics and policies |
| CI key | One pipeline/repo | CI command telemetry |
| Read-only dashboard key | Dashboard only | Display metrics, no event upload |
| Research opt-in key | Explicit datasets | Higher-detail ML training |

Each key should have:

- Owner ID.
- Organization ID, optional.
- Scope.
- Privacy level maximum.
- Created timestamp.
- Last used timestamp.
- Revoked timestamp.
- Rate limit.
- Allowed event types.

### Clean Data Separation

SAGE should store telemetry in separate logical tables/collections:

```text
accounts
organizations
api_keys
installations
workspaces
runs
compression_metrics
agent_metrics
ml_labels
sync_events
privacy_policies
```

Raw or sensitive data should never be in the same table as public aggregate counters.

Recommended split:

| Store | Contains | Access |
|---|---|---|
| Metrics store | counts, tokens, ratios, durations, exit codes | Safe aggregate queries |
| Redacted summary store | sanitized errors/summaries | Opt-in analytics and ML |
| Raw artifact store | raw logs/code snippets | Local only by default or explicit team/research opt-in |
| Policy store | privacy level, org rules, key scopes | Auth and enforcement |
| Aggregate store | public counters | Public dashboard |

Recommended physical storage:

| System | Tables/Objects | Rule |
|---|---|---|
| Local SQLite | `runs`, `token_usage`, `context_compression`, `agent_tasks`, `telemetry_queue`, local account cache, migration ledger | Durable local proof and raw-output pointers. Works offline. |
| Local artifact directory | Large raw stdout/stderr artifacts keyed by SHA-256 | Local only by default. Pruned by policy. |
| Cloudflare D1 | `accounts`, `organizations`, `api_keys`, `installations`, `workspaces`, `event_facts`, `aggregate_counters`, `privacy_policies`, `idempotency_keys` | Aggregate-safe API data and key metadata. No raw output at Level 1. |
| Cloudflare Queues | Pending telemetry batches | Buffers ingest and protects the API from spikes. |
| Cloudflare R2 | Optional redacted reports or approved research artifacts | Explicit opt-in only. Not used for default raw command logs. |
| GitHub | Source code, docs, release artifacts, optional scheduled proof snapshot | No live per-run telemetry writes. |

### Combining Data Correctly

SAGE should combine data by aggregation, not by mixing raw records.

Examples:

```text
User total = sum(metrics where user_id = X)
Org total = sum(metrics where org_id = Y and policy_allows_org_aggregate = true)
Global total = sum(metrics where privacy_level >= 1 and event_validated = true)
ML training set = only events where ml_training_allowed = true
Public proof = aggregate counters only
```

Never do:

```text
Combine raw logs from many users into one shared raw dataset by default.
Use private repo names as public grouping keys.
Expose file paths in global proof.
Train on Level 1 data as if it had raw error content.
```

### Workspace and Repo Identity

Repos/projects should be identified with hashes unless users opt into names.

Local value:

```text
D:\work\sage
```

Uploaded value:

```text
workspace_hash = sha256(salt + normalized_path_or_git_remote)
```

For organizations, use org-controlled salt so the company can group its own repos, but SAGE global systems cannot reverse names.

### Deduplication Rules

The API must avoid double-counting.

Each telemetry event should include:

- `installation_id`
- `workspace_hash`
- `local_run_id`
- `run_fingerprint`
- `started_at`
- `completed_at`
- `command_hash`

Server dedupe key:

```text
sha256(installation_id + workspace_hash + local_run_id + run_fingerprint)
```

If the same run is retried for sync, the API updates the same event instead of adding a duplicate.

### Data Merge Examples

#### User With Two Machines

```text
User account: Sensei
Machine A installation: laptop
Machine B installation: desktop

Personal dashboard:
  total_saved_tokens = laptop_saved + desktop_saved

Machine dashboard:
  shows each install separately
```

#### User Belongs to Company

```text
Personal account: user_123
Org account: org_456
Org policy: Level 1 anonymous metrics only

Personal dashboard:
  can show user's local totals

Org dashboard:
  can show aggregate team totals

Global dashboard:
  can count org metrics only as anonymous aggregate
```

#### Same Repo, Multiple Developers

```text
Dev A workspace hash: org_salt + repo_remote
Dev B workspace hash: org_salt + repo_remote

Org dashboard:
  combines both under one repo bucket

Global dashboard:
  only sees anonymized aggregate category
```

#### Research Opt-In

```text
Normal users:
  Level 1 metrics only

Research users:
  selected runs can upload redacted summaries or raw snippets

ML training:
  uses Level 1 for numeric models
  uses Level 2/3 only for text/error models
```

### Account Switching

SAGE local CLI should support:

```powershell
sage account list
sage account use personal
sage account use my-company
sage account status
sage account unlink
```

Each local run should be tagged with the active account context:

```json
{
  "account_context": "personal",
  "user_id": "user_123",
  "org_id": null,
  "policy_id": "policy_personal_default",
  "telemetry_level": 1
}
```

If a user switches accounts, old local data does not move automatically. SAGE should ask before reassigning or syncing old runs.

### Policy Resolution Order

When multiple policies exist, use the strictest applicable rule.

Order:

1. Local user setting.
2. Workspace `.sage/policy.yml`.
3. Organization policy.
4. API key max scope.
5. SAGE global safety minimum.

Example:

```text
User wants Level 3.
Org allows max Level 1.
API key allows max Level 2.

Effective telemetry level = Level 1.
```

### Clean Combine Rules for ML

ML datasets should be built from typed feature tables, not raw telemetry blobs.

Recommended feature tables:

```text
command_features
compression_features
failure_features
agent_features
environment_features
label_events
```

Each feature row should include:

- Data permission level.
- Source account/org/install.
- Whether it can be used for global ML.
- Whether it can be used for org-only ML.
- Whether it can be displayed publicly.

ML training filters:

```text
Global model:
  ml_training_allowed = true
  privacy_level >= 1
  raw_content_present = false

Org model:
  org_id = selected_org
  org_policy_allows_training = true

Local model:
  local DB only
```

### User Controls

Users should be able to run:

```powershell
sage privacy status
sage privacy set local-only
sage privacy set anonymous-metrics
sage telemetry preview <run_id>
sage telemetry delete-local-queue
sage telemetry delete-cloud --before 2026-08-01
sage account export-metrics
```

Dashboard controls:

- Current active account.
- Current telemetry level.
- Last sync status.
- Queued events count.
- Data sent preview.
- Revoke API key.
- Delete cloud telemetry.

### Privacy Levels

| Level | Name | Uploads | Default |
|---|---|---|---|
| 0 | Local only | Nothing | Allowed |
| 1 | Anonymous metrics | Counts, timings, token stats, exit code, categories | Recommended default |
| 2 | Redacted summaries | Level 1 plus redacted error summaries and compressed command summaries | Opt-in |
| 3 | Team diagnostics | Level 2 plus team-approved raw snippets or selected artifacts | Team opt-in only |
| 4 | Research/full logs | Full logs for selected repos/runs | Never default |

### Level 1 Payload

```json
{
  "schema_version": "1.0",
  "event_type": "command_completed",
  "client_id": "anonymous-or-account-id",
  "installation_id": "uuid",
  "run_id_local_hash": "sha256",
  "timestamp": "2026-07-04T00:00:00Z",
  "command_kind": "test",
  "command_family": "pytest",
  "caller": "gui",
  "language": "python",
  "framework": "pytest",
  "duration_ms": 12345,
  "exit_code": 0,
  "original_tokens": 50000,
  "compressed_tokens": 4200,
  "saved_tokens": 45800,
  "compression_ratio": 0.916,
  "stdout_bytes": 120000,
  "stderr_bytes": 3000,
  "error_category": null,
  "agent_count": 4,
  "ml_prediction": {
    "predicted_failure": false,
    "confidence": 0.78
  }
}
```

### Level 2 Payload Additions

```json
{
  "redacted_command": "python -m pytest tests/<redacted>",
  "compressed_summary": "24 tests passed. No failures.",
  "redacted_error": null,
  "detected_dependencies": ["pytest"],
  "detected_files_hashed": ["sha256:file-a", "sha256:file-b"]
}
```

## Phase 1: Local Command Classification Foundation

Status: Completed 2026-07-04

Goal: make SAGE recognize what kind of work a command is doing before syncing anything.

Tasks:

- [ ] Add a command classifier for `run`, `read`, `grep`, `call`, `test`, `build`, `install`, `lint`, `git`, `network`, `unknown`.
- [ ] Store `command_kind`, `command_family`, `caller`, and `workspace_hash` in the local DB.
- [ ] Detect read-like commands inside `sage run --`, including `cat`, `type`, `Get-Content`, `sed`, and `python -c` file reads where reasonably safe.
- [ ] Detect search-like commands inside `sage run --`, including `rg`, `grep`, `Select-String`, `findstr`.
- [ ] Detect tool-call source: GUI, CLI, MCP, agent executor, workflow, direct API.
- [ ] Add unit tests for command classification.
- [ ] Add migration-safe DB columns with defaults.
- [ ] Add `sage history --kind read|grep|test|build`.

Acceptance criteria:

- Existing `sage run -- <command>` behavior stays unchanged.
- Every run gets classified.
- Unknown commands still execute normally.
- No command is blocked because classification fails.

## Phase 2: `sage read`

Status: Completed 2026-07-04

Goal: make file reads measurable, compressible, and raw-recoverable.

Tasks:

- [ ] Add CLI command `sage read -- <file>`.
- [ ] Add `--raw`, `--compressed`, `--summary`, `--lines START:END`, `--max-tokens N`.
- [ ] Add file metadata extraction: bytes, lines, extension, language, encoding.
- [ ] Add line-numbered output mode.
- [ ] Add symbol extraction for Python, JavaScript/TypeScript, Markdown headings, JSON keys, YAML keys.
- [ ] Add large-file strategy: show outline plus important ranges instead of dumping the entire file to AI context.
- [ ] Store raw file content locally as a run artifact when size is reasonable.
- [ ] Store compressed read output in `context_compression`.
- [ ] Add redaction for secrets before any optional telemetry sync.
- [ ] Add tests for small file exact read.
- [ ] Add tests for large file compressed read.
- [ ] Add tests for raw recovery.

Acceptance criteria:

- `sage read -- file` can replace `Get-Content file` for AI workflows.
- Small files show exact content by default.
- Large files show useful compressed content with line refs.
- Raw content remains available locally.

## Phase 3: `sage grep`

Status: Completed 2026-07-04

Goal: make search output useful for AI and measurable for token savings.

Tasks:

- [ ] Add CLI command `sage grep -- <pattern> <path>`.
- [ ] Use `rg` internally when available.
- [ ] Fall back to Python search when `rg` is unavailable.
- [ ] Preserve file path, line number, and match text.
- [ ] Add `--context N`, `--glob`, `--ignore-case`, `--files-with-matches`, `--count`.
- [ ] Compress repeated matches by grouping by file.
- [ ] Cap noisy results with clear continuation hints.
- [ ] Store full raw match output locally.
- [ ] Store compressed match summary in `context_compression`.
- [ ] Track `matched_files`, `match_count`, `hidden_matches`, and `saved_tokens`.
- [ ] Add tests for match parity against `rg` on fixtures.
- [ ] Add tests for compressed noisy output.
- [ ] Add tests for zero-match behavior and exit codes.

Acceptance criteria:

- `sage grep` produces enough information to navigate to exact matches.
- AI context gets compressed output, not giant repeated logs.
- Raw output can be recovered by run ID.

## Phase 4: `sage call`

Status: Completed 2026-07-04

Goal: give agents and integrations a clear execution lane that records tool-call quality.

Tasks:

- [ ] Add CLI command `sage call -- <command>`.
- [ ] Store caller metadata: CLI, GUI, MCP, API, agent, workflow.
- [ ] Add optional `--purpose read|search|test|build|deploy|audit|unknown`.
- [ ] Add optional `--agent <name>` and `--task-id <id>`.
- [ ] Link call runs to `agent_tasks` when available.
- [ ] Add usefulness fields: `produced_answer`, `produced_error`, `retry_count`, `followup_required`.
- [ ] Add timeout and cancellation handling.
- [ ] Add tests that `sage call -- echo hi` behaves like `sage run -- echo hi`.
- [ ] Add tests for caller metadata.
- [ ] Add tests for agent-task linkage.

Acceptance criteria:

- `sage call` does the same execution job as `sage run`.
- It records richer metadata for agent and ML evaluation.
- It never uploads raw output unless opt-in policy allows it.

## Phase 5: Local Raw Artifact Store

Status: Completed 2026-07-04

Goal: keep exact original output locally while sending compressed output to AI context.

Tasks:

- [ ] Create local artifact directory under `.sage/artifacts` or the existing SAGE data dir.
- [ ] Store raw stdout/stderr for large commands in files instead of bloating SQLite.
- [ ] Store artifact hashes and paths in DB.
- [ ] Add `sage show --raw <run_id>`.
- [ ] Add `sage show --compressed <run_id>`.
- [ ] Add `sage show --summary <run_id>`.
- [ ] Add retention settings: keep forever, keep last N GB, keep last N days.
- [ ] Add cleanup command: `sage artifacts prune`.
- [ ] Add tests for raw recovery after compression.
- [ ] Add tests for artifact pruning.

Acceptance criteria:

- Compression is reversible from the user's perspective because raw output is recoverable locally.
- SQLite stays fast.
- Large logs do not freeze the GUI.

## Phase 6: Free API Key and Account Bootstrap

Status: Local parts completed 2026-07-04; login/key endpoints blocked on server

Goal: allow global proof metrics without forcing paid signup or private-code upload.

Tasks:

- [ ] Add `sage login` backed by deployed SAGE API.
- [x] Add `sage logout` for local account/key removal.
- [ ] Add `sage whoami`.
- [x] Add anonymous install ID for users who skip login.
- [ ] Add free API key creation endpoint.
- [ ] Store API key in OS credential store where available.
- [x] Fall back to local config where OS store is unavailable.
- [x] Add API health check: `sage api status`.
- [x] Add clear local setting: telemetry level 0/1/2/3/4.
- [ ] Add first-run privacy notice.
- [x] Add tests for local API/account config handling.
- [x] Add tests for telemetry disabled/local-only behavior.

Acceptance criteria:

- Users can use SAGE with no account.
- Users can opt into free API sync.
- Telemetry level is visible and changeable.

## Phase 7: Safe Telemetry Sync

Status: Client-side completed 2026-07-04; live send blocked on server endpoint

Goal: upload proof metrics without leaking private code.

Tasks:

- [x] Define telemetry schema version `1.0`.
- [x] Add local outbound queue table.
- [ ] Add background sync worker.
- [ ] Add retry with exponential backoff.
- [ ] Add payload signing or API-key auth.
- [x] Add payload size limits.
- [x] Add redaction pass before queueing telemetry.
- [x] Add workspace/repo hashing.
- [x] Add command redaction: paths, secrets, tokens, emails, URLs with secrets.
- [x] Add `sage telemetry preview <run_id>`.
- [x] Add `sage telemetry send --dry-run`.
- [x] Add tests for redaction.
- [x] Add tests proving raw output is not present in Level 1 telemetry.

Acceptance criteria:

- Level 1 telemetry contains no raw code or raw stdout.
- Users can preview exactly what would be sent.
- Sync failures do not break local SAGE.

## Phase 7A: Account and API Data Management

Status: Local registry and policy resolution completed 2026-07-04; server-side aggregates blocked on server

Goal: cleanly manage multiple accounts, API keys, installations, repos, teams, and privacy policies without mixing private data.

Tasks:

- [x] Add local account registry with account alias, user ID, org ID, API key ID, and active policy.
- [x] Add `sage account list`.
- [x] Add `sage account use <alias>`.
- [x] Add `sage account status`.
- [x] Add `sage account unlink <alias>`.
- [ ] Add API key scopes: personal, org, CI, dashboard, research.
- [x] Add local installation ID that survives app restarts but can be reset.
- [x] Add workspace hash generation with per-user or per-org salt.
- [x] Add run dedupe fingerprint.
- [ ] Add server-side idempotency key for telemetry events.
- [x] Add policy resolution across local, workspace, org, API key, and SAGE global rules.
- [x] Add strictest-policy-wins enforcement.
- [x] Add telemetry event ownership fields: user, org, install, workspace, key, run.
- [ ] Add aggregate query design for user totals, org totals, install totals, workspace totals, and global totals.
- [x] Add ML permission fields: global training allowed, org training allowed, local only, public display allowed.
- [x] Add tests that personal and org metrics do not leak into each other.
- [x] Add tests for local account switching and active policy behavior.
- [ ] Add tests that duplicate sync events are not double-counted.
- [x] Add tests that stricter org policy overrides user setting.
- [x] Add tests that Level 1 payloads contain no raw output or file content.

Acceptance criteria:

- One user can have multiple machines and see combined personal proof.
- One organization can combine team metrics without exposing raw code.
- Global proof can count anonymous safe metrics from all accounts.
- ML can train only on rows that explicitly allow training.
- API key revocation stops future sync without deleting local data.

## Phase 8: Public Proof Dashboard

Status: Planned

Goal: show global proof without exposing user data.

Tasks:

- [ ] Add aggregate counters: total commands, original tokens, compressed tokens, saved tokens.
- [ ] Add compression-rate charts by command kind.
- [ ] Add language/framework breakdown.
- [ ] Add failure-prediction stats.
- [ ] Add agent-use stats.
- [ ] Add install count and active users.
- [ ] Add public "privacy mode" explanation.
- [ ] Add public API endpoint for aggregate proof counters.
- [ ] Add anti-spam and fake-metric checks.
- [ ] Add anomaly detection for impossible token claims.
- [ ] Add exportable proof badge:

```text
SAGE has saved X tokens across Y developer commands.
```

Acceptance criteria:

- Public page can show billion-token proof when scale reaches it.
- No private code appears on the public dashboard.
- Metrics are explainable and auditable.

## Phase 9: ML Training Pipeline

Status: Planned

Goal: train the best failure-prediction and compression-selection ML from safe real-world usage.

Tasks:

- [ ] Define ML feature schema.
- [ ] Extract features from Level 1 telemetry: command kind, family, duration, token volume, exit code, compression ratio.
- [ ] Add labels: failed/succeeded, retried/not retried, fixed/not fixed, agent helpful/not helpful.
- [ ] Build first cloud training dataset from anonymous metrics.
- [ ] Keep local training path for private users.
- [ ] Add federated-style option later: train local, upload model deltas or metrics only.
- [ ] Train command failure predictor.
- [ ] Train compression strategy selector.
- [ ] Train noisy-output detector.
- [ ] Train fix-suggestion ranker.
- [ ] Add evaluation dashboard: precision, recall, ROC AUC, false positives, false negatives.
- [ ] Add model versioning.
- [ ] Add rollback.

Acceptance criteria:

- ML improves from aggregate telemetry without requiring source-code upload.
- Users can still train locally only.
- Every model has measurable evaluation metrics.

## Phase 10: Enterprise Readiness

Status: Planned

Goal: make big companies comfortable using SAGE.

Tasks:

- [ ] Add organization accounts.
- [ ] Add team policy files.
- [ ] Add admin-controlled telemetry level.
- [ ] Add "no raw code upload" enforcement mode.
- [ ] Add audit logs for every sync payload.
- [ ] Add data retention controls.
- [ ] Add region controls.
- [ ] Add self-hosted API option.
- [ ] Add SSO later.
- [ ] Add legal/privacy documentation.
- [ ] Add security whitepaper.
- [ ] Add SOC2-ready controls roadmap.

Acceptance criteria:

- A company can prove SAGE saves tokens without exposing source code.
- Admins can enforce telemetry limits.
- SAGE can be used in regulated environments with local-only mode.

## Phase 11: GUI Integration

Status: Planned

Goal: make all of this visible and understandable inside SAGE Desktop.

Tasks:

- [ ] Add API status indicator: Local only, Anonymous sync, Team sync.
- [ ] Add privacy level selector in Settings.
- [ ] Add "Preview telemetry" button.
- [ ] Add all-time proof cards: commands, original tokens, compressed tokens, saved tokens.
- [ ] Add this-session cards separately.
- [ ] Add command-kind charts.
- [ ] Add read/grep/call history filters.
- [ ] Add raw/compressed toggle for any run.
- [ ] Add "copy proof" button.
- [ ] Add "export proof report" button.
- [ ] Add warnings when telemetry is disabled or local-only.

Acceptance criteria:

- Users can understand what is local and what is synced.
- Proof numbers match CLI.
- Dashboard reset never hides all-time proof numbers.

## Phase 12: MCP and Agent Integration

Status: Completed 2026-07-04

Goal: make AI agents naturally use compressed SAGE tools.

Tasks:

- [ ] Add MCP tool `sage_read_file`.
- [ ] Add MCP tool `sage_grep`.
- [ ] Add MCP tool `sage_call`.
- [ ] Add MCP tool `sage_show_raw`.
- [ ] Add agent policy: use `sage read` instead of raw `cat/Get-Content`.
- [ ] Add agent policy: use `sage grep` instead of direct `rg` when output may be large.
- [ ] Track which agent called each tool.
- [ ] Store agent usefulness metrics.
- [ ] Add tests for MCP tool outputs.
- [ ] Add tests that raw recovery still works.

Acceptance criteria:

- Agents save context by default.
- Users can still inspect exact raw results.
- Agent learning gets cleaner data.

## Phase 13: Rollout Plan

Status: Local-first items shipped 2026-07-04; cloud items follow the server

Goal: ship safely without breaking existing users.

Tasks:

- [ ] Ship local-only `sage read`.
- [ ] Ship local-only `sage grep`.
- [ ] Ship local-only `sage call`.
- [ ] Ship raw recovery commands.
- [ ] Add GUI proof cards matching CLI all-time totals.
- [ ] Add telemetry preview command.
- [ ] Add Level 1 anonymous telemetry behind opt-in.
- [ ] Add free API key login.
- [ ] Add public aggregate dashboard.
- [ ] Add Level 2 redacted summaries after redaction tests are strong.
- [ ] Add team policies.
- [ ] Add enterprise controls.

Acceptance criteria:

- Local features are useful before any API exists.
- API adds proof and ML scale, not dependency lock-in.
- Users trust SAGE because it works without uploading private code.

## Risks and Controls

| Risk | Control |
|---|---|
| Users fear code upload | Local-first default, telemetry preview, Level 1 only by default |
| Bad compression hides important output | Raw recovery, error-first compression, tests against exact output |
| Fake metrics pollute public proof | Signed clients, anomaly detection, rate limits |
| ML trains on noisy data | Schema validation, command classification, confidence scores |
| Enterprise rejection | Admin policy, local-only mode, self-hosted option |
| API outage breaks SAGE | Local queue, offline mode, never block commands on sync |
| Privacy mistake | Redaction tests, payload preview, strict schema, no raw Level 1 |

## Success Metrics

Local product metrics:

- 90%+ of command output recoverable as raw artifact.
- 80%+ average compression on noisy commands.
- `sage read` and `sage grep` reduce AI context use without reducing navigability.
- GUI totals match `sage context stats`.

API proof metrics:

- Total original tokens processed.
- Total compressed tokens shown to AI.
- Total saved tokens.
- Average compression rate.
- Commands processed.
- Active installs.
- Failures predicted.
- Fixes suggested.
- Agent tasks completed.

ML metrics:

- Failure prediction precision.
- Failure prediction recall.
- ROC AUC.
- False positive rate.
- Fix suggestion acceptance rate.
- Compression strategy win rate.

## Recommended First Build Order

1. Local `sage read`.
2. Local `sage grep`.
3. Raw artifact store.
4. `sage show --raw`.
5. Command classification.
6. GUI all-time proof cards.
7. Telemetry preview.
8. Free API key.
9. Anonymous Level 1 sync.
10. Public proof dashboard.

This order gives value before cloud, builds trust, then uses API scale for proof and ML.
