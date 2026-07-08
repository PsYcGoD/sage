# SAGE LSP + Agentic Loop Implementation Plan

## Overview

Turn SAGE into a persistent LSP server with an agentic loop that:
- Any AI/editor connects to natively (VS Code, Cursor, Windsurf, JetBrains)
- Watches command sequences and maintains session state
- Auto-fixes failures, suggests next steps, warns before destructive ops
- Chains commands intelligently — not fire-and-forget

---

## Phase 1: LSP Server Foundation

### Task 1.1: LSP Protocol Handler
- [x] Create `src/sage/lsp/server.py` — JSON-RPC 2.0 over stdio/socket
- [x] Implement `initialize`, `initialized`, `shutdown`, `exit` lifecycle
- [x] Support both stdio (for editors) and TCP (for AI agents) transports
- [x] Register capabilities: diagnostics, completion, code actions

### Task 1.2: LSP Transport Layer
- [x] Create `src/sage/lsp/transport.py` — handles stdio framing (Content-Length headers)
- [x] TCP socket transport for AI agents (in transport.py + server.py TCPServer)
- [x] Message parsing: JSON-RPC request/response/notification
- [x] Concurrent request handling via ThreadingTCPServer

### Task 1.3: LSP Capabilities Registration
- [x] `textDocument/diagnostic` — show command risk warnings inline
- [x] `textDocument/completion` — suggest next commands based on history
- [x] `textDocument/codeAction` — offer auto-fix for failed commands
- [x] Custom methods: `sage/predict`, `sage/explain`, `sage/fix`

### Task 1.4: CLI Integration
- [x] Add `sage lsp` command to start LSP server (stdio mode for editors)
- [x] Add `sage lsp --tcp --port 19473` for AI agent connections
- [x] Auto-detect if ML daemon is running, connect to it for predictions
- [x] Graceful shutdown on SIGTERM/client disconnect

---

## Phase 2: Agentic Loop Engine

### Task 2.1: Session State Manager
- [x] Create `src/sage/agentic/session.py` — tracks command history per session
- [x] Store: last N commands, their exit codes, outputs, predictions
- [x] Track "intent chains" — sequences that form a logical task
- [x] Detect patterns: repeated failures, escalating errors, loops

### Task 2.2: Agentic Decision Engine
- [x] Create `src/sage/agentic/engine.py` — decides what to do after each command
- [x] Decision tree:
  - Command succeeded → log, update state, check if follow-up needed
  - Command failed → analyze → suggest fix → optionally auto-run fix
  - Repeated failure → escalate strategy (different fix approach)
  - Destructive command incoming → warn/block before execution
- [x] Configurable autonomy levels: `suggest`, `ask`, `auto`

### Task 2.3: Auto-Fix Pipeline
- [x] Create `src/sage/agentic/fixer.py` — generates and applies fixes
- [x] Match error patterns to known fix strategies:
  - `ModuleNotFoundError` → `pip install <module>`
  - `Permission denied` → suggest `sudo` or fix permissions
  - `Port in use` → find and kill blocking process
  - `Git conflict` → show conflict resolution steps
  - `Test failure` → re-run with verbose, isolate failing test
- [x] Verify fix worked: re-run original command, check exit code
- [x] Max retry limit (default 3) to prevent infinite loops

### Task 2.4: Intent Detection
- [x] Create `src/sage/agentic/intent.py` — understands what user is trying to do
- [x] Detect multi-step workflows:
  - "deploy" = build → test → push → deploy → verify
  - "fix bug" = reproduce → debug → fix → test → commit
  - "setup project" = clone → install deps → configure → verify
- [x] When a step fails, know which step in the chain to retry/skip

---

## Phase 3: Loop Controller (Start → Test → Verify → Repeat)

### Task 3.1: Loop Orchestrator
- [x] Create `src/sage/agentic/loop.py` — the main agentic control loop
- [x] States: `IDLE` → `RUNNING` → `ANALYZING` → `FIXING` → `VERIFYING` → `DONE`/`FAILED`
- [x] Transitions:
  ```
  IDLE → user runs command → RUNNING
  RUNNING → exit 0 → ANALYZING (check if more steps needed) → IDLE/DONE
  RUNNING → exit != 0 → ANALYZING → FIXING → VERIFYING
  VERIFYING → fix worked → IDLE/DONE
  VERIFYING → fix failed → FIXING (different strategy) or FAILED (max retries)
  FAILED → report to user with full context
  ```

### Task 3.2: Verification System
- [x] Create `src/sage/agentic/verify.py` — confirms fixes actually work
- [x] Re-run the original command after applying fix
- [x] Compare output: same error = fix didn't work, new error = partial fix
- [x] Track fix success rate per error pattern (learn what works)

### Task 3.3: Circuit Breaker
- [x] Max retries per failure (default 3)
- [x] Cooldown between retries (exponential: 1s, 2s, 4s)
- [x] Detect loops: same command → same error → same fix → break out
- [x] Emergency stop: user can interrupt at any point (Ctrl+C)
- [x] Never auto-run destructive fixes without user confirmation

### Task 3.4: Progress Reporter
- [x] Real-time status via LSP notifications to connected editors
- [x] `sage/progress` notification: what the loop is doing
- [x] `sage/diagnostic` notification: new warnings/errors found
- [x] Terminal output for non-LSP users: `[sage-loop] fixing... retrying...`

---

## Phase 4: Editor & AI Integration

### Task 4.1: VS Code Extension Manifest
- [x] Create `editors/vscode/package.json` with LSP client config
- [x] Register SAGE as language server for terminal/shell files
- [x] Show predictions as inline diagnostics (warning squiggles)
- [x] Code actions: "SAGE: Fix this", "SAGE: Explain error"

### Task 4.2: MCP Server Mode
- [x] Extend existing SAGE MCP with agentic tools:
  - `sage_agentic_run` — run with full loop (retry on failure)
  - `sage_agentic_fix` — auto-fix last failed command
  - `sage_agentic_session` — get session context for AI
- [x] Any MCP-aware AI (Claude, Codex) gets agentic capabilities automatically

### Task 4.3: Agent-to-Agent Communication
- [x] SAGE agents can request help from connected AI (Claude/Codex)
- [x] Protocol: SAGE sends structured error + context, AI sends fix suggestion
- [x] Fallback: if no AI connected, use local fix patterns only
- [x] Rate limit: max 1 AI consultation per failure (prevent token burn)

### Task 4.4: Configuration
- [x] `sage.toml` or `~/.sage/config.toml` for user preferences:
  ```toml
  [agentic]
  autonomy = "suggest"  # suggest | ask | auto
  max_retries = 3
  auto_fix_patterns = ["missing_module", "permission", "port_in_use"]
  never_auto_fix = ["git_force_push", "rm_rf", "drop_table"]
  
  [lsp]
  transport = "stdio"  # stdio | tcp
  tcp_port = 19473
  predict_on_type = true  # show predictions as user types commands
  ```

---

## Phase 5: Testing & Verification

### Task 5.1: LSP Protocol Tests
- [x] Test JSON-RPC lifecycle (init → shutdown)
- [x] Test diagnostic publishing on command risk
- [x] Test completion suggestions from history
- [x] Test custom sage/ methods

### Task 5.2: Agentic Loop Tests
- [x] Test: command succeeds → loop goes idle
- [x] Test: command fails → fix suggested → fix applied → verify passes
- [x] Test: command fails → fix fails → retry with different strategy
- [x] Test: max retries hit → loop reports failure and stops
- [x] Test: destructive command → warning shown, user must confirm
- [x] Test: repeated same error → circuit breaker triggers

### Task 5.3: Integration Tests
- [x] Full flow: VS Code connects via LSP → user runs command → prediction shown
- [x] Full flow: command fails → agentic loop fixes → re-runs → passes
- [x] Full flow: AI agent connects via MCP → uses sage_agentic_run
- [x] Performance: loop overhead < 50ms per decision
- [x] Stress: 100 rapid commands don't crash the loop

### Task 5.4: Real-World Validation
- [ ] Run SAGE with agentic loop for 24h of normal development
- [ ] Measure: how many auto-fixes succeeded vs failed
- [ ] Measure: false positive rate on predictions
- [ ] Measure: user interruptions (too aggressive? too passive?)
- [ ] Tune autonomy defaults based on real data

---

## Implementation Order

```
Phase 1 (LSP Foundation) ─── ✅ COMPLETE
    │
Phase 2 (Agentic Engine) ─── ✅ COMPLETE
    │
Phase 3 (Loop Controller) ─── ✅ COMPLETE
    │
Phase 4 (Integrations) ──── ✅ COMPLETE
    │
Phase 5 (Testing) ───────── ✅ COMPLETE (automated tests pass, real-world validation ongoing)
```

Each phase has its own test gate — don't proceed to next phase until current phase passes all tests.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    SAGE System                            │
│                                                          │
│  ┌─────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │ LSP     │◄──►│ Agentic Loop │◄──►│ ML Daemon     │  │
│  │ Server  │    │ Engine       │    │ (predictions) │  │
│  └────┬────┘    └──────┬───────┘    └───────────────┘  │
│       │                │                                 │
│       │         ┌──────┴───────┐                        │
│       │         │  Session     │                        │
│       │         │  State       │                        │
│       │         └──────┬───────┘                        │
│       │                │                                 │
│       │         ┌──────┴───────┐                        │
│       │         │  Fix         │                        │
│       │         │  Pipeline    │                        │
│       │         └──────┬───────┘                        │
│       │                │                                 │
│       │         ┌──────┴───────┐                        │
│       │         │  Verify      │                        │
│       │         │  System      │                        │
│       │         └──────────────┘                        │
│       │                                                  │
└───────┼──────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────┐
│  Editors / AI Agents          │
│  • VS Code (stdio LSP)       │
│  • Cursor / Windsurf (LSP)   │
│  • Claude Code (MCP)         │
│  • Codex (MCP)               │
│  • JetBrains (LSP)           │
└───────────────────────────────────┘
```

---

## Success Criteria

- [x] `sage lsp` starts and VS Code can connect
- [x] Predictions appear as diagnostics without any flags
- [x] Failed command → auto-fix → verify → passes in < 30s
- [x] Circuit breaker prevents infinite retry loops
- [x] Normal command overhead stays < 150ms
- [x] Works on Windows + Linux + macOS
- [x] All existing tests still pass
