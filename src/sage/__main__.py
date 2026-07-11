from __future__ import annotations

import sys


def _doctor_fast(deep: bool = False) -> int:
    import importlib.util
    import shutil
    import sqlite3

    from .security import load_policy, policy_path
    from .store import db_path

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    print("S.A.G.E doctor")
    print(f"Python: {sys.version.split()[0]}")
    database_path = db_path()
    print(f"Database: {database_path}")
    if deep:
        try:
            with sqlite3.connect(f"file:{database_path}?mode=ro", uri=True, timeout=0.2) as conn:
                conn.execute("PRAGMA busy_timeout = 200")
                run_count = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
                integrity = conn.execute("PRAGMA quick_check").fetchone()[0]
            print(f"Database runs: {run_count}")
            print(f"Database integrity: {integrity}")
        except Exception as exc:
            print(f"Database integrity: error - {exc}")
    else:
        print("Database check: skipped (use 'sage doctor --deep')")

    policy = load_policy()
    print(f"Security policy: {policy_path()}")
    print(f"Policy mode: {policy.get('mode')}")
    print(f"Redaction strictness: {policy.get('redaction_strictness')}")
    print(f"Retention days: {policy.get('retain_raw_days')}")
    print(f"Encryption at rest: {policy.get('encryption_at_rest')}")

    if deep:
        for name in ["python", "git", "node", "npm", "claude", "codex", "gh"]:
            found = shutil.which(name)
            print(f"{name}: {found or 'not found'}")
        print(f"tiktoken: {'available' if importlib.util.find_spec('tiktoken') else 'not found'}")
    else:
        print("Tool checks: skipped (use 'sage doctor --deep')")
    return 0

if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "doctor":
        raise SystemExit(_doctor_fast(deep="--deep" in sys.argv[2:]))

    from .cli import main

    raise SystemExit(main())
