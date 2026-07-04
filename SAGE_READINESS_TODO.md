# SAGE — Get-It-Ready TODO

**Audience:** You (GUI-first user). Priorities are ranked for the **SAGE Desktop GUI** as the product, not the web dashboard.
**Last audited:** 2026-07-03, against live system + real DB (252 runs).
**Legend:** 🔴 blocker · 🟠 important · 🟡 polish · ⚪ nice-to-have

---

## Reality check (what the audit proved)
- ✅ The engine is **real**: compression, sklearn ML, fix suggestions, agents, MCP tools all work when run live.
- ⚠️ The problems are **stability, honesty of numbers, and cleanup** — not "does it work."
- ℹ️ The GUI does **not** start the :8765 web server, so the dashboard-auth issue barely affects you.

---

## 🔴 P0 — Blockers (product is unusable/misleading without these)

### 1. ~~Claude CLI is not logged in~~ — ❌ AUDITOR ERROR, RETRACTED
- **Correction:** This was WRONG. The user IS logged in; the GUI replies fine. DB proof: run #303 `claude --print` → exit 0 → `HELLO SENSEI`; Claude runs succeed 37/43. The "Not logged in" only appeared in the auditor's own sandboxed subprocess, which strips auth env vars — it never reflected the real GUI. **No action needed.**

### 2. Test suite has collection errors
- **What:** `pytest` can't even collect 2 files → CI would be red. Current real state: **53 passed, 4 failed, 2 collection errors.**
- **Why:** `src/test_phase2_fixed.py` has an `IndentationError`; `tests/test_gui_metrics.py` fails to import.
- **How:**
  1. Fix the `IndentationError` in `src/test_phase2_fixed.py` (or delete it — stray test file in `src/`).
  2. Fix the import in `tests/test_gui_metrics.py`.
  3. Triage the 4 real failures: `sage run -- python -m pytest -q --continue-on-collection-errors`.
  4. Move all `test_*.py` files out of `src/` and repo root into `tests/`.
- **Effort:** 2–3 hours.

---

## 🟠 P1 — Important (works, but wrong or fragile)

### 3. ~~Token/compression numbers are overstated~~ — ✅ DONE (2026-07-03)
- **What was wrong:** Two disagreeing estimators (`words×1.3` and `chars/4`), off by 20–200%; "99.3%/149→1" cherry-picked.
- **Fixed:**
  1. Installed `tiktoken` (added to `pyproject.toml`); created `src/sage/context/tokens.py` as the single source of truth (cl100k_base, cached, graceful fallback if tiktoken missing).
  2. Both `ContextCompressor.estimate_tokens` and `TokenTracker.estimate_tokens` now delegate to it — verified they match tiktoken exactly and agree with each other.
  3. Reworded README (3 places), SAGE-INTEGRATION.md (2 places) to "up to ~98% on repetitive output, typically 85–95%, measured with tiktoken."
- **Verified:** 17 compression/token tests pass; fallback path tested.
- ℹ️ **New gap found while measuring:** `npm install` warning noise compresses **0%** — the compressor has no strategy for `npm WARN`/`pip` lines. Logged as new item #10.

### 4. Compression can delete all output
- **What:** 50 duplicate log lines compressed to an **empty string** (285→0 tokens).
- **Why:** A user could lose output they needed; "100% compression" that returns nothing is a bug, not a feature.
- **How:** In `src/sage/context/compression.py`, add a floor: if compressed output is empty but input was non-empty, keep the first + last line and a `[N identical lines omitted]` marker.
- **Effort:** 1 hour.

### 5. GUI "tokens saved" metric is padded with empty records
- **What:** 110 of 206 `context_compression` rows are `(0,0,0)` — first-turn prompts with nothing to compress. They inflate the count and skew the "82.9%" ratio.
- **Why:** The headline metric card shows a misleadingly padded ratio.
- **How:** In `_record_context_compression` (app.py), skip inserting rows where `original_tokens == 0`; and in the metric query, filter `WHERE original_tokens > 0` for the ratio.
- **Effort:** 45 min.

### 6. ML model is trained on synthetic data
- **What:** Model reports 0.9999 accuracy from **1,000,000 synthetic training samples** — almost certainly overfit; real predictive value is unproven.
- **Why:** "ML-powered" is technically true but the accuracy claim is not trustworthy.
- **How:** Retrain primarily on the 202 real runs (`sage ml train`), report honest cross-validated accuracy, and stop advertising 0.9999.
- **Effort:** 2 hours.

---

## 🟡 P2 — Polish (maintainability & trust)

### 7. Dead / duplicate code in the GUI
- **What:** `app.py` has **unreachable code** after `return` statements (e.g. lines after `return True` around 836–855 and 694+), plus 5 overlapping run paths (`native_cli_client`, `direct_ai_client`, `direct_claude`, `pty_terminal`, embedded, external). Only 1–2 are actually used.
- **Why:** Every dead path is a place bugs hide and a reason the next fix takes 3x longer.
- **How:** Delete unreachable blocks; keep the embedded-PowerShell path (the one the GUI uses) + external-terminal fallback; remove `app_old.py`, `direct_*.py`, `native_cli_client.py` if unreferenced (grep first).
- **Effort:** 3–4 hours.

### 8. Repo is littered with throwaway files
- **What:** ~15 `fix_*.py` mojibake scripts, `*.bak`, `*_backup.md`, duplicate status docs (`FINAL_FIX.md`, `REAL_FIX.md`, `FIXES_COMPLETE.md`, etc.) in the repo root.
- **Why:** Looks unmaintained; a reviewer/contributor can't tell what's real.
- **How:** Move one-off scripts to `scripts/archive/` or delete; consolidate the status docs into one `CHANGELOG.md`; add the patterns to `.gitignore`.
- **Effort:** 1 hour.

### 9. Dashboard has no authentication
- **What:** `/api/v1/*` serves full prompts/commands with zero auth.
- **Why (for you):** LOW — the GUI never starts it. Only matters if you run `sage dashboard start` manually or expose it.
- **How:** Bind to `127.0.0.1` only + add an API-key `Depends` check (roadmap task 1.3). Do this **only if** you ever plan to use or ship the dashboard.
- **Effort:** 3 hours. **Skip unless you use the dashboard.**

---

### 10. Compressor ignores npm/pip install noise
- **What:** `npm WARN deprecated ...` × 40 lines compressed **0%** (measured with real tokens). The strategy detector doesn't recognize package-manager output.
- **Why:** "Removes noisy logs (npm install, pip install)" is a stated feature that doesn't fire for these.
- **How:** Add an `install_output` strategy in `compression.py` that collapses `WARN`/`deprecated`/progress lines, keeping the final `added N packages` summary + any errors.
- **Effort:** 1.5 hours.

## ⚪ P3 — Nice-to-have
- Pin the GUI to a specific model via `--model` in the command config (right now it uses account default → showed `opus-4-8`).
- Add a visible "not logged in" banner in the GUI header (I added an orange dot + warning; a full banner is friendlier).
- Package for `pip install` so setup isn't manual (roadmap Phase 2).

---

## Suggested order of attack (GUI-first)
1. `/login` (2 min) → unblocks daily use.
2. Fix test collection errors (#2) → know what's actually broken.
3. Compression floor (#4) + metric de-padding (#5) → numbers become trustworthy.
4. Honest messaging (#3) + ML retrain (#6) → claims match reality.
5. Dead-code + repo cleanup (#7, #8) → maintainable.
6. Dashboard auth (#9) only if you decide to use the dashboard.

**Rough total to "honestly shippable GUI": ~2 focused days** (excluding the optional dashboard work).
