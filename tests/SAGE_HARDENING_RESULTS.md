# 🧠 SAGE Hardening Results

Date: 2026-07-03

## Outcome Table

| Area | Result | Evidence |
| --- | --- | --- |
| Heavy ML model | ✅ Added persisted sklearn ensemble model | `sage ml train` trained `failure_predictor.joblib` |
| 1M ML training | ✅ Completed | `1,000,000` rows trained in about `235s` |
| ML metrics | ✅ Strong on synthetic-heavy bootstrap holdout | Accuracy `1.000`, Precision `1.000`, Recall `1.000`, ROC AUC `1.000` |
| ML prediction | ✅ Uses trained model when available | `sage predict -- pytest tests` returned `likely to fail` at `68%` |
| Safe command prediction | ✅ Working | `sage predict -- python --version` returned `likely to succeed` at `2%` |
| ML features | ✅ Expanded | Feature count increased from `13` to `22` |
| Agent system | ✅ 12 default agents seeded | `sage agents status` showed `12` total, `12` idle |
| Agent routing | ✅ Command-based planner added | Test selects relevant agents for pytest/database/debug requests |
| Agent execution | ✅ Connected to real runs | `sage run` now executes selected agents after each command |
| Agent persistence | ✅ Stored per run | `agent_tasks.run_id` links every agent result to its SAGE run |
| Agent inspection | ✅ CLI and GUI inspection added | `sage agents tasks --run-id 226` showed stored Code Agent output |
| Agent strength | ✅ Improved | Results now include severity, confidence, token strategy, and action lists |
| GUI embedded terminal | ✅ Smoke tested | GUI reports embedded terminal enabled |
| GUI PTY support | ✅ Detected and displayed | GUI output includes `Windows ConPTY available` when `pywinpty` is installed |
| GUI memory/context | ✅ Existing paths verified by smoke test | Recent turns, context compression status, chat helpers remain importable |
| Token saving | ✅ Existing 10k tests still pass | `10,011` tokens compress to `6` and client context to `892` |
| Repo tests | ✅ Focused suite passing | `24 passed in 6.13s` |
| Syntax/imports | ✅ Package compile passed | `python -m compileall src/sage` completed |

## Commands Run

```powershell
sage run -- python -m sage ml train --target-samples 1000000 --synthetic-floor 1000000
sage run -- python -m sage ml status
sage run -- python -m sage agents status
sage run -- python -m sage agents tasks --run-id 226
sage run -- python -m sage predict -- pytest tests
sage run -- python -m sage run --predict -- python --version
sage run -- python -m pytest tests\test_ml_features.py tests\test_cli.py tests\test_cli_basic.py tests\test_10k_context_compression.py -v
sage run -- python -m compileall D:\work\sage\src\sage
```

## Notes

- The 1M model is intentionally heavier than the earlier heuristic: Random Forest, Extra Trees, and histogram gradient boosting are combined in a soft-voting sklearn ensemble.
- Training uses local SAGE command history and balances sparse/imbalanced history with bootstrap priors so it does not learn only the majority class.
- The `1.000` metrics are from a synthetic-heavy bootstrap holdout, so they prove the pipeline trained successfully; they are not a guarantee of real-world production accuracy.
- GUI launch was smoke-tested by creating `SAGEApp`, checking embedded terminal/PTY/ML/agents, then destroying the window automatically.
- Existing files were not deleted.
- Broad README mojibake cleanup was not applied because the safe decode test still produced replacement characters. New report text uses clean emoji directly.
