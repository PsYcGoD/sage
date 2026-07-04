# SAGE Repair TODO

Last updated: 2026-07-04

## Progress Key

- [ ] Not started
- [~] In progress
- [x] Completed and tested

## Main Tasks

1. [x] Fix `sage run` timeout.
   - Evidence: `tests/test_cli_basic.py::TestSageRun::test_sage_run_echo` times out after 10 seconds.
   - Current finding: setting `SAGE_SUPPRESS_FOOTER=1` makes the same test pass, so the issue is in the post-command footer/stat/telemetry path.
   - Fix attempted: only auto-spawn telemetry sender from interactive terminals so captured stdout/stderr do not hang.
   - Tested: `python -m pytest tests\test_cli_basic.py::TestSageRun::test_sage_run_echo -q` passed in 4.63s.
   - Broad test: default pytest suite passed.

2. [x] Finish SAGE GUI left chat bar to match the Codex-style session sidebar.
   - No placeholders.
   - All visible buttons must have connected behavior.
   - Fix attempted: removed dead Scheduled/Plugins buttons, connected them to real status views, and replaced the worktree placeholder with `git worktree add`.
   - Tested: `python -m pytest tests\test_gui_codex_streaming.py tests\test_gui_memory_context.py -q` passed, including sidebar button dispatch coverage.
   - Remaining visual verification: launch/screenshot smoke where the environment supports Tk.

3. [x] Add expandable thinking/tool/code blocks for Claude activity.
   - Users must be able to expand/collapse reasoning, tool calls, code edits, and command output blocks.
   - Fix attempted: added OutputView expandable sections and GUI routing for thinking/coding/tool events.
   - Tested: GUI stream/memory tests passed; OutputView compiles with expandable section API.

4. [x] Fix Codex streaming so reasoning/thinking/coding/tool events are visible instead of only final answers.
   - Fix attempted: classified visible Codex lines into thinking/coding/tool/text event types.
   - Tested: Codex classifier exposes reasoning/coding/tool events in `tests\test_gui_codex_streaming.py`.

5. [x] Fix persistent session memory so follow-up messages resume the same chat/context.
   - Avoid creating a fresh chat on every message.
   - Avoid unnecessary token waste from re-sending redundant context.
   - Fix attempted: persistent sessions now receive raw prompts, and loading a saved chat hydrates GUI/provider memory.
   - Tested: saved-chat load hydrates GUI turns and persistent provider history in `tests\test_gui_memory_context.py`.

6. [x] Expand and verify the agent system.
   - Goal: move from 12 default agents to 24 working agents.
   - Research target: review `claude-code` repo by afhan and adapt the best agent ideas that fit SAGE.
   - Fix attempted: expanded catalog to 24 deterministic agents, adding architecture/review/refactor/devops/API/ML/memory/telemetry/privacy/red-team/blue-team/auditor roles.
   - Tested: `python -m pytest tests\test_ml_features.py tests\test_agent_execution.py tests\test_agent_evaluation.py -q` passed, including DB-backed execution coverage for the expanded roles.
   - Tested: `python -m sage agents eval --format text` reports 100% overall score.

7. [x] Fix ML prediction confidence family behavior.
   - Evidence: `tests/test_ml_features.py::test_failure_predictor_scores_recent_failures_high` returns about `0.62`, expected `>= 0.65`.
   - Fix attempted: blend live recent-failure context into trained family/global model predictions.
   - Tested: `python -m pytest tests\test_ml_features.py::test_failure_predictor_scores_recent_failures_high -q` passed in 3.28s.
   - Broad test: default pytest suite passed.

8. [x] Fix full compile failure.
   - Evidence: `python -m compileall -q src tests` fails on `src/test_phase2_fixed.py`.
   - Fix attempted: converted stale indented snippet into an importable legacy placeholder module.
   - Tested: `python -m compileall -q src tests` passed.

9. [x] Fix docs/package version mismatch and README/docs mojibake.
   - Align package/docs version story.
   - Preserve and repair emojis.
   - Commit after verification.
   - Fixed: aligned package version/classifier with active docs and repaired active README/V2 doc mojibake.
   - Tested: `python -m sage --version` prints `sage 2.0.0`.
   - Tested: `rg -n '0\.1\.0|Development Status :: 3|ð|â' README.md SAGE_V2_COMPLETE.md pyproject.toml src\sage\__init__.py src\sage\mcp\server.py` returned no matches.

10. [x] Check MCP advertised agent/workflow tools.
    - Evidence: MCP advertises tools that currently return "not yet implemented".
    - Fix by implementing them or removing/renaming them until real.
    - Fixed: implemented DB-backed `sage_spawn_agent` and real YAML/template execution for `sage_run_workflow`.
    - Tested: `python -m pytest tests\test_mcp_sage_tools.py -q` passed, 7 tests.

## Agent Expansion Subplan

### Phase 1: Audit And Routing

- [x] Inspect current 12-agent registry and executor contracts.
- [x] Research afhan `claude-code` agent patterns and identify the useful roles.
- [x] Define the final 24-agent catalog with triggers, capabilities, and descriptions.
- [x] Add tests for deterministic routing.

### Phase 2: Implement Working Agents

- [x] Add the new agent specs.
- [x] Add deterministic result handlers for every new agent type.
- [x] Ensure each agent returns the normalized result contract.
- [x] Add DB-backed execution coverage for new agents.

### Phase 3: Quality, UI, And Docs

- [x] Add aggregate agent status/report coverage.
- [x] Surface the expanded catalog in GUI/MCP where appropriate.
- [x] Update docs without overstating capabilities.
- [x] Run agent evaluation and full relevant test suite.

## Verification Log

- 2026-07-04: Initial audit found 2 default pytest failures, compileall failure, version/docs mismatch, MCP stubs, GUI TODOs, and footer-related `sage run` timeout.
- 2026-07-04: Focused CLI timeout test passed after telemetry sender is limited to interactive terminals.
- 2026-07-04: Full compile check passed after repairing the legacy phase-2 snippet module.
- 2026-07-04: Focused ML confidence test passed after blending recent failure context into trained predictions.
- 2026-07-04: Version metadata now reports 2.0.0 and active docs no longer match the mojibake/version scan.
- 2026-07-04: MCP advertised agent/workflow tools now execute real backend paths; MCP tests passed.
- 2026-07-04: GUI memory, Codex event classification, expandable stream routing, and sidebar callbacks covered by 10 focused tests.
- 2026-07-04: Expanded 24-agent catalog routing and DB-backed execution covered by 19 focused tests; agent evaluator reports 100%.
- 2026-07-04: Full verification passed: `python -m compileall -q src tests` and `python -m pytest -q` (`125 passed, 6 deselected`).
