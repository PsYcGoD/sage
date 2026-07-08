"""SAGE Agentic Loop — autonomous command retry, fix, and verification engine.

Quick usage:

    from sage.agentic.loop import AgenticLoop
    from sage.agentic.engine import Autonomy

    loop = AgenticLoop(autonomy=Autonomy.AUTO, max_retries=3)
    result = loop.run("python -m pytest")

    if result.state.value == "done":
        print("Command succeeded")
    else:
        print(f"Failed after {result.attempts} attempts: {result.message}")

Autonomy levels:
    - SUGGEST: only report fix suggestions, never auto-run
    - ASK: suggest fix and wait for confirmation
    - AUTO: automatically apply non-destructive fixes and retry

Configuration via sage.toml:

    [agentic]
    autonomy = "suggest"
    max_retries = 3
    auto_fix_patterns = ["missing_module", "permission", "port_in_use"]
    never_auto_fix = ["git_force_push", "rm_rf", "drop_table"]
"""
