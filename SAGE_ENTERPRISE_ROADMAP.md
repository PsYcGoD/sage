# SAGE Enterprise Readiness Roadmap

## Current Assessment (v2.1.0)

| Dimension | Score | Status | Gap |
|-----------|:-----:|--------|-----|
| Functionality | 8/10 | ✅ Strong | LSP + Agentic needs production mileage |
| Reliability | 7/10 | ⚠ Good | No long-duration soak testing |
| Security | 8/10 | ✅ Strong | Missing team-level auth/RBAC |
| Scalability | 6/10 | ⚠ Weak | Single-machine only, no multi-tenant |
| Observability | 7/10 | ⚠ Good | No SIEM/APM integration |
| Documentation | 7/10 | ⚠ Good | No dedicated docs site or API reference |
| Configuration | 8/10 | ✅ Strong | Missing schema validation |
| Integration | 9/10 | ✅ Excellent | MCP, LSP, VS Code, all major AI agents |

---

## Weaknesses & Fix Plan

| # | Weakness | Impact | Risk Level | Fix Phase |
|---|----------|--------|:----------:|:---------:|
| W1 | No multi-tenant / team auth | Can't share across org securely | 🔴 High | Phase 1 |
| W2 | No centralized logging | Ops teams can't monitor fleet | 🔴 High | Phase 1 |
| W3 | No HA / process supervision | Daemon dies silently, no auto-restart | 🟡 Medium | Phase 2 |
| W4 | Agentic loop untested at scale | Unknown failure modes in production | 🟡 Medium | Phase 2 |
| W5 | No audit trail export | Compliance teams need evidence | 🔴 High | Phase 1 |
| W6 | Auto-fix covers only 9 patterns | Most errors still unmatched | 🟡 Medium | Phase 3 |
| W7 | VS Code extension not published | Users can't install from marketplace | 🟢 Low | Phase 3 |
| W8 | No rate limiting on LSP/MCP | DoS risk from malicious clients | 🟡 Medium | Phase 2 |
| W9 | No OS-level service management | Daemon doesn't survive reboots | 🟡 Medium | Phase 2 |
| W10 | Config validation minimal | Silent fallback on bad config | 🟢 Low | Phase 3 |
| W11 | No SSO/SAML/OIDC support | Enterprise identity systems blocked | 🔴 High | Phase 1 |
| W12 | No admin console / fleet view | No visibility across org installs | 🟡 Medium | Phase 4 |
| W13 | No SLA / uptime monitoring | Can't guarantee reliability to customers | 🟡 Medium | Phase 4 |
| W14 | No data retention policies | Compliance (GDPR/SOC2) requires time-bound | 🔴 High | Phase 1 |

---

## Phase 1: Security, Auth & Compliance Foundation

**Goal:** Make SAGE deployable in a SOC2/GDPR-compliant org with team access controls.

**Timeline target:** 3-4 weeks

### Task 1.1: Team Authentication & RBAC
- [ ] Design team/org model: Org → Teams → Users → Roles (admin, member, viewer)
- [ ] Create `src/sage/auth/team.py` — team membership, role checks
- [ ] Add API key scoping: keys belong to a team, inherit team permissions
- [ ] Implement `sage team create <name>` / `sage team invite <email>` CLI commands
- [ ] Add `X-Sage-Team` header to all API requests for team-scoped data
- [ ] Store team config in `~/.sage/teams.toml` with encrypted secrets
- [ ] Tests: role enforcement (member can't delete, viewer can't write), key revocation

### Task 1.2: SSO / SAML / OIDC Integration
- [ ] Create `src/sage/auth/sso.py` — SAML 2.0 and OIDC flows
- [ ] Support Azure AD, Okta, Google Workspace as identity providers
- [ ] `sage connect --sso <provider-url>` CLI flow
- [ ] Auto-provision users on first SSO login (JIT provisioning)
- [ ] Map IdP groups → SAGE teams automatically
- [ ] Session token refresh without re-login (refresh token rotation)
- [ ] Tests: mock IdP, test token exchange, test group mapping

### Task 1.3: Centralized Logging & SIEM Export
- [ ] Create `src/sage/telemetry/export.py` — structured log shipping
- [ ] Support targets: Datadog, Splunk, ELK (via syslog/HTTP), CloudWatch
- [ ] Log format: JSON Lines with `timestamp`, `event`, `user`, `team`, `command_hash`, `exit_code`
- [ ] Never log raw commands or outputs to remote (hashes only by default)
- [ ] Config in `sage.toml`:
  ```toml
  [logging.remote]
  target = "datadog"
  api_key_env = "DD_API_KEY"
  include_command_hashes = true
  include_raw_commands = false  # opt-in only
  ```
- [ ] Implement buffered async sender (batch every 10s or 100 events)
- [ ] Add `sage telemetry export --target datadog --test` to verify connectivity
- [ ] Tests: mock endpoints, verify payload format, verify no raw data leaks

### Task 1.4: Audit Trail & Compliance Export
- [ ] Create `src/sage/compliance/audit.py` — immutable local audit log
- [ ] Every command execution → append-only audit entry (tamper-evident with hash chain)
- [ ] Fields: timestamp, user, team, command_hash, exit_code, agents_used, fix_applied, duration
- [ ] `sage audit export --format csv --from 2026-01-01 --to 2026-07-01` CLI command
- [ ] `sage audit export --format json --compliance soc2` — SOC2-specific report format
- [ ] Audit log rotation: compress after 30 days, delete after retention period
- [ ] Tamper detection: SHA-256 chain, `sage audit verify` checks integrity
- [ ] Tests: chain verification, rotation, export format validation

### Task 1.5: Data Retention Policies
- [ ] Create `src/sage/compliance/retention.py` — policy-based data lifecycle
- [ ] Configurable retention per data type:
  ```toml
  [retention]
  command_history = "90d"    # Delete after 90 days
  raw_output = "30d"        # Raw logs purged after 30 days
  audit_trail = "7y"        # Compliance: keep 7 years
  ml_training_data = "1y"   # Model training data: 1 year
  ```
- [ ] `sage retention run` — apply policies, delete expired data
- [ ] `sage retention status` — show what's due for deletion
- [ ] Schedule automatic runs via OS cron/task scheduler
- [ ] GDPR right-to-erasure: `sage privacy purge --user <email>` removes all user data
- [ ] Tests: mock clock, verify deletion timing, verify purge completeness

---

## Phase 2: Reliability, Hardening & Scale Testing

**Goal:** Make SAGE survive in harsh production: crashes, reboots, abuse, high load.

**Timeline target:** 2-3 weeks

### Task 2.1: OS-Level Service Management
- [ ] Create `src/sage/service/install.py` — cross-platform service installer
- [ ] Windows: register as Windows Service via `sc create` or NSSM
- [ ] Linux: generate systemd unit file, `sage service install` enables it
- [ ] macOS: generate launchd plist, auto-start on login
- [ ] `sage service install` / `sage service uninstall` / `sage service status`
- [ ] Auto-restart on crash with exponential backoff (1s, 2s, 4s, max 60s)
- [ ] Health check endpoint: `GET /health` returns `{ok: true, uptime: ...}`
- [ ] Tests: simulate crash, verify restart, verify backoff timing

### Task 2.2: Process Supervision & Watchdog
- [ ] Create `src/sage/service/watchdog.py` — monitors daemon + LSP health
- [ ] Heartbeat check every 30s: ping ML daemon + LSP server
- [ ] If unresponsive for 3 consecutive checks → kill and restart
- [ ] Log all restart events to audit trail
- [ ] Memory limit: if daemon exceeds 500MB RSS, graceful restart
- [ ] File descriptor leak detection: warn if fd count grows unbounded
- [ ] `sage doctor --deep` checks all services, reports issues
- [ ] Tests: simulate hang, simulate OOM, verify restart

### Task 2.3: Rate Limiting & Connection Security
- [ ] Create `src/sage/lsp/security.py` — connection-level protections
- [ ] Rate limit: max 100 requests/second per client connection
- [ ] Connection limit: max 10 concurrent LSP connections
- [ ] Auth token required for TCP connections (generated on first start)
- [ ] Token stored in `~/.sage/lsp-token` with 0600 permissions
- [ ] IP allowlist (default: 127.0.0.1 only, configurable for remote)
- [ ] Request size limit: reject messages > 1MB
- [ ] Slow client detection: disconnect if response not read within 30s
- [ ] Tests: verify rate limit triggers, verify auth rejection, fuzz with random payloads

### Task 2.4: Agentic Loop Soak Testing & Telemetry
- [ ] Create `tests/soak/test_agentic_soak.py` — long-running stress tests
- [ ] Test: 1000 rapid commands with mixed success/failure patterns
- [ ] Test: agentic loop running for 1 hour continuously
- [ ] Test: deliberate error injection (kill daemon mid-fix, corrupt state)
- [ ] Test: concurrent sessions (5 terminals running sage simultaneously)
- [ ] Measure: memory growth over time (must be < 10% after 1000 commands)
- [ ] Measure: p99 latency under load (must be < 200ms)
- [ ] Add internal telemetry: track fix success rate, false positive rate, loop depth
- [ ] Weekly report: `sage agentic report` — show fix rate, common failures, improvements
- [ ] Tests: automated CI soak test (10 min run, assert no crashes/leaks)

### Task 2.5: Graceful Degradation
- [ ] ML daemon down → fall back to heuristic prediction (already works)
- [ ] LSP server crash → MCP tools still work directly (already works)
- [ ] Database locked → queue writes, retry with backoff
- [ ] Disk full → warn, stop storing raw output, continue running commands
- [ ] Network down → all local operations continue unaffected
- [ ] Config file corrupted → use defaults, log warning, don't crash
- [ ] Tests: simulate each degradation scenario, verify no data loss

---

## Phase 3: Feature Expansion & Polish

**Goal:** Grow auto-fix coverage, publish extensions, validate config.

**Timeline target:** 2-3 weeks

### Task 3.1: Expand Auto-Fix Pattern Library
- [ ] Add 20+ new fix patterns covering:
  - Docker errors (image not found, port mapping, volume perms)
  - Node.js (node_modules missing, version mismatch, ENOMEM)
  - Python (virtualenv not activated, pip version conflict, path issues)
  - Git (detached HEAD, upstream gone, stale locks, LFS errors)
  - Network (DNS resolution, proxy config, SSL cert expired)
  - Database (connection refused, auth failed, migration pending)
  - Build tools (CMake missing, compiler not found, link errors)
  - Cloud CLI (aws/gcloud/az auth expired, region mismatch)
- [ ] Create `src/sage/agentic/patterns/` directory with one file per category
- [ ] Each pattern file exports a list of (regex, handler) tuples
- [ ] Auto-discovery: scan patterns/ directory at startup, register all
- [ ] Community contribution guide: how to add new patterns
- [ ] Tests: at least 2 test cases per new pattern

### Task 3.2: ML-Based Fix Suggestion (when patterns don't match)
- [ ] Create `src/sage/agentic/ml_fixer.py` — embedding-similarity fix lookup
- [ ] Build vector store of (error_text → successful_fix) pairs from history
- [ ] When no pattern matches: search for similar past errors that were fixed
- [ ] Confidence threshold: only suggest ML fixes above 0.7 similarity
- [ ] Learn from user: when user manually fixes, record the pair
- [ ] `sage agentic learn` — explicitly teach SAGE a new fix
- [ ] Tests: mock vector store, verify suggestion quality threshold

### Task 3.3: VS Code Extension Publishing
- [ ] Set up `editors/vscode/` build pipeline (webpack + vsce)
- [ ] Add icon, screenshots, marketplace description
- [ ] Create `.vsixmanifest` with proper metadata
- [ ] Test on VS Code Insiders: connect, predict, fix, explain all work
- [ ] Publish to VS Code Marketplace under `marketingstudios` publisher
- [ ] Add auto-update: extension checks for new SAGE versions
- [ ] Create JetBrains plugin stub (LSP client config for IntelliJ)
- [ ] Tests: extension activation, LSP handshake, command execution

### Task 3.4: Configuration Schema & Validation
- [ ] Create JSON Schema for `sage.toml` (all valid keys, types, ranges)
- [ ] Validate config on load: report specific errors with line numbers
- [ ] `sage config validate` — check current config, show warnings
- [ ] `sage config init` — generate annotated default sage.toml
- [ ] Auto-complete: LSP provides completion for sage.toml editing
- [ ] Migration: when config format changes, auto-upgrade old configs
- [ ] Tests: invalid config → clear error, missing optional → default, unknown key → warning

### Task 3.5: Documentation Site
- [ ] Set up docs site (MkDocs or Docusaurus) at docs.sage-cli.dev
- [ ] Pages: Getting Started, Configuration, LSP Setup, Agentic Loop, MCP Tools
- [ ] API reference: auto-generated from tool specs
- [ ] Tutorials: "Set up SAGE with Claude Code", "VS Code integration", "Team setup"
- [ ] Architecture diagrams (Mermaid or SVG)
- [ ] Deploy via GitHub Pages or Cloudflare Pages
- [ ] Tests: link checker, build validation in CI

---

## Phase 4: Enterprise Features & Fleet Management

**Goal:** Multi-org fleet visibility, SLA monitoring, admin controls.

**Timeline target:** 4-5 weeks

### Task 4.1: Admin Console (Web)
- [ ] Create web dashboard for team admins at admin.sage-cli.dev
- [ ] Views: team members, usage stats, compliance status, active alerts
- [ ] User management: invite, revoke, change roles
- [ ] Enforce policies: required autonomy level, blocked commands, required agents
- [ ] Push config to team members: admin sets sage.toml → syncs to all machines
- [ ] Built on existing Cloudflare Workers infrastructure
- [ ] Tests: role-based access, policy enforcement, config push

### Task 4.2: Fleet Monitoring & Alerts
- [ ] Create `src/sage/fleet/reporter.py` — phone-home health metrics
- [ ] Metrics reported: uptime, commands/day, fix rate, error rate, version
- [ ] Admin sees fleet health: which machines are online, which are outdated
- [ ] Alerts: machine offline > 24h, fix rate drops below threshold, version too old
- [ ] Alert channels: email, Slack webhook, PagerDuty integration
- [ ] All reporting is aggregate — no raw commands leave the machine
- [ ] `sage fleet status` — show my machine's reporting status
- [ ] Tests: mock reporter, verify aggregate-only data, verify alert triggers

### Task 4.3: SLA Monitoring & Uptime
- [ ] Define SLA targets:
  - Command overhead: p99 < 150ms
  - Prediction latency: p99 < 50ms
  - Daemon uptime: 99.9% (< 8.7h downtime/year)
  - Fix success rate: > 60% of attempted fixes resolve the error
- [ ] Internal SLA tracker: measure against targets continuously
- [ ] `sage sla report` — show current SLA compliance
- [ ] Weekly email to team admin with SLA summary
- [ ] Breach alerting: if any SLA violated, immediate notification
- [ ] Tests: simulate SLA breach, verify alert fires

### Task 4.4: Enterprise Licensing & Deployment
- [ ] Create license key system for paid enterprise tier
- [ ] License gates: team size, fleet size, advanced features
- [ ] Air-gapped deployment guide (no internet required after initial setup)
- [ ] MSI/deb/rpm package generation for enterprise deployment tools
- [ ] Group Policy / MDM support for Windows enterprise deployment
- [ ] Docker image for containerized environments
- [ ] Helm chart for Kubernetes-based dev environments
- [ ] Tests: license validation, offline mode, package installation

### Task 4.5: Enterprise Support Infrastructure
- [ ] Dedicated support channel (email + Slack)
- [ ] `sage support bundle` — collect diagnostics (sanitized) for support tickets
- [ ] Remote debugging consent flow: admin can enable temporary diagnostic access
- [ ] Runbook: common enterprise deployment issues and fixes
- [ ] On-call rotation documentation for SAGE service
- [ ] Customer success metrics dashboard (internal)

---

## Phase 5: Certification & Compliance

**Goal:** Achieve formal compliance certifications for enterprise sales.

**Timeline target:** 6-8 weeks (overlaps with Phase 4)

### Task 5.1: SOC 2 Type II Preparation
- [ ] Document all data flows (what goes where, who has access)
- [ ] Implement change management process (PRs, reviews, approvals)
- [ ] Access control audit: verify RBAC works as documented
- [ ] Incident response plan: what happens when something goes wrong
- [ ] Penetration test: hire external firm, fix any findings
- [ ] Evidence collection: automated SOC 2 evidence gathering
- [ ] Tests: verify evidence is complete and current

### Task 5.2: GDPR Compliance
- [ ] Data Processing Agreement (DPA) template for customers
- [ ] Right to access: `sage privacy export --user <email>` — all data about a user
- [ ] Right to erasure: `sage privacy purge --user <email>` — complete deletion
- [ ] Right to portability: export in standard format (JSON/CSV)
- [ ] Data minimization: document what data is collected and why
- [ ] Consent management: clear opt-in/opt-out for all telemetry
- [ ] Tests: verify purge completeness, verify export includes all data

### Task 5.3: Security Hardening Review
- [ ] Code audit: review all auth/crypto code paths
- [ ] Dependency audit: no known CVEs in dependency tree
- [ ] Secrets scanning: CI blocks any committed secrets
- [ ] Binary signing: sign all releases (GPG + Sigstore)
- [ ] Supply chain: pin dependencies, verify checksums
- [ ] SBOM generation: Software Bill of Materials with each release
- [ ] Tests: CVE scan in CI, reproducible builds verification

### Task 5.4: ISO 27001 Alignment
- [ ] Information Security Management System (ISMS) documentation
- [ ] Risk assessment: identify and score all security risks
- [ ] Control mapping: map SAGE controls to ISO 27001 Annex A
- [ ] Internal audit: verify controls are implemented and effective
- [ ] Management review: document executive sign-off
- [ ] Continuous improvement: process for addressing new risks

---

## Implementation Timeline

```
Phase 1 (Auth/Compliance) ──── Weeks 1-4   ████████░░░░░░░░░░░░
Phase 2 (Reliability)     ──── Weeks 3-6   ░░░░████████░░░░░░░░
Phase 3 (Polish)          ──── Weeks 5-8   ░░░░░░░░████████░░░░
Phase 4 (Fleet/Admin)     ──── Weeks 7-12  ░░░░░░░░░░░░████████
Phase 5 (Certification)   ──── Weeks 8-16  ░░░░░░░░░░░░░░██████
```

Phases overlap — work can proceed in parallel where tasks are independent.

---

## Success Criteria for "Enterprise Ready"

| Criteria | Target | How to Measure |
|----------|--------|----------------|
| Team auth works | 50+ user org can deploy | Load test with 50 concurrent users |
| Logs ship to SIEM | Datadog/Splunk receives events | E2E test: command → event appears in dashboard |
| Daemon survives reboot | 99.9% uptime | 30-day monitoring with auto-restart |
| Agentic loop stable | 0 crashes in 7-day soak | Continuous integration soak test |
| Audit exportable | SOC2 auditor accepts report | External auditor review |
| Data retention works | GDPR-compliant deletion | Automated retention test with time mock |
| Rate limits hold | No DoS possible | Fuzz testing with 10K req/s |
| Config validated | Zero silent failures | CI test: every invalid config → clear error |
| Fleet visible | Admin sees all machines | Deploy to 10 machines, verify all report |
| SOC 2 Type II | Certificate issued | External audit passes |

---

## Priority Order (What to Build First)

1. **Task 1.1 + 1.5** — Team auth + retention (blocks everything else)
2. **Task 1.3** — Centralized logging (enterprises won't deploy without it)
3. **Task 1.4** — Audit trail (compliance teams ask first)
4. **Task 2.1 + 2.2** — Service management + watchdog (reliability)
5. **Task 2.3** — Rate limiting (security hardening)
6. **Task 3.1** — More fix patterns (user value)
7. **Task 4.1** — Admin console (enterprise sales enabler)
8. Everything else in order

---

## Current vs Enterprise-Ready Gap

```
CURRENT STATE (v2.1.0)                    ENTERPRISE TARGET
┌─────────────────────┐                   ┌─────────────────────┐
│ Single user         │ ──────────────►   │ Multi-tenant orgs   │
│ Local SQLite        │ ──────────────►   │ + Central logging   │
│ No service mgmt    │ ──────────────►   │ OS service + watchdog│
│ 9 fix patterns     │ ──────────────►   │ 50+ patterns + ML   │
│ No audit export    │ ──────────────►   │ SOC2/GDPR compliant │
│ No rate limiting   │ ──────────────►   │ Hardened endpoints  │
│ No fleet view      │ ──────────────►   │ Admin console       │
│ No SSO             │ ──────────────►   │ SAML/OIDC/Azure AD  │
└─────────────────────┘                   └─────────────────────┘
        ▲                                          ▲
    Individual dev                          50+ seat enterprise
    Ready TODAY                             ~16 weeks out
```
