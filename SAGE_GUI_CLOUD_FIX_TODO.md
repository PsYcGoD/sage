# SAGE GUI, Agents, and Cloud Proof Fix To-Do

Date: 2026-07-04

## Completed

- [x] Verified local proof totals are much higher than public proof totals.
  - Local: 1,275+ commands, 5.1M+ processed tokens, 4.69M+ saved tokens, 91.8% compression.
  - Public API before backfill: 87 runs, 1.61M saved tokens, 97.9% compression.
- [x] Added `sage telemetry sync-all` so historical local runs can be queued and sent, not only the latest run.
- [x] Changed GUI `Connect SAGE API` to save the key, enable safe level-1 metrics, queue local history, start background sync, and show a success popup.
- [x] Changed GUI `Sync Now` to sync all safe local history instead of only the newest run.
- [x] Added a real `SAGE Agents` section in Settings so the 12 registered local agents are visible.
- [x] Changed the dashboard Agents card to show registered agents plus executed agent tasks.
- [x] Added per-tab parked prompt queueing so users can type/send while Claude or Codex is still running.
- [x] Added automatic queue draining when the active tab finishes a response.
- [x] Reduced waiting spam to one live status notice after a backend delay.

## In Progress

- [ ] Backfill all existing local history to `https://sage.api.marketingstudios.in` using the saved API key.
- [ ] Verify the public dashboard reflects the local proof totals after sync completes.
- [ ] Launch the GUI and manually confirm:
  - Connect button says connected and API saved.
  - Sync Now reports scanned/sent/queued counts.
  - Agents card shows 12 registered agents and task counts.
  - A second prompt can be parked while a response is running.
  - Switching tabs during a running response does not freeze the app.

## Remaining Hardening

- [ ] Store API keys in the OS credential store instead of only local config.
- [ ] Add a settings toggle for “Require SAGE API before cloud proof mode” instead of blocking local-only installs by default.
- [ ] Add a public dashboard freshness timestamp and “last synced run” count.
- [ ] Add retry/backoff telemetry sender metrics so failed sync is visible in the GUI.
- [ ] Add automated GUI tests for queued prompts, tab switching, and Settings API connect feedback.
- [ ] Clean any remaining mojibake display strings in older experimental GUI paths.
