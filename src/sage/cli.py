from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from . import __version__
from .runner import run_command
from .store import db_path, latest_run, recent_runs
from .suggestions import suggest_next_steps


ASSISTANT_INSTRUCTIONS = """# S.A.G.E Instructions

When working in this project, prefer running noisy terminal commands through S.A.G.E.

Examples:

- `sage run -- python -m unittest`
- `sage run -- npm test`
- `sage run -- pytest`
- `sage explain`
- `sage suggest`
- `sage history`

After a failed command, run `sage explain` and `sage suggest` before guessing at the fix.
S.A.G.E stores command summaries locally and helps keep AI context small.
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sage",
        description="Smart Agent Guidance Engine for AI coding assistants.",
    )
    parser.add_argument("--version", action="version", version=f"sage {__version__}")

    sub = parser.add_subparsers(dest="command_name", required=True)

    run = sub.add_parser("run", help="Run a command and remember the important output.")
    run.add_argument("command", nargs=argparse.REMAINDER, help="Command to run after --")

    sub.add_parser("explain", help="Explain the most recent command failure.")
    sub.add_parser("suggest", help="Suggest the next practical step after a command failure.")

    history = sub.add_parser("history", help="Show recent remembered commands.")
    history.add_argument("--limit", type=int, default=10)

    sub.add_parser("doctor", help="Check local setup.")
    sub.add_parser("init", help="Create S.A.G.E instructions for AI assistants.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command_name == "run":
        command = list(args.command)
        if command and command[0] == "--":
            command = command[1:]
        return run_command(command)

    if args.command_name == "explain":
        return explain()

    if args.command_name == "suggest":
        return suggest()

    if args.command_name == "history":
        return history(args.limit)

    if args.command_name == "doctor":
        return doctor()

    if args.command_name == "init":
        return init_project()

    parser.print_help()
    return 2


def explain() -> int:
    record = latest_run(only_failures=True) or latest_run()
    if record is None:
        print("S.A.G.E has no command history yet.")
        print("Try: sage run -- python --version")
        return 0

    status = "failed" if record.exit_code != 0 else "succeeded"
    print(f"Run #{record.id} {status}")
    print(f"Command: {record.command}")
    print(f"Project: {record.project}")
    print(f"Exit code: {record.exit_code}")
    print(f"Duration: {record.duration_ms}ms")
    print()
    print(record.summary)
    return 0


def suggest() -> int:
    record = latest_run(only_failures=True) or latest_run()
    if record is not None:
        print(f"Suggestions for run #{record.id}: {record.command}")
        print()
    print(suggest_next_steps(record))
    return 0


def history(limit: int) -> int:
    records = recent_runs(limit=max(1, limit))
    if not records:
        print("No command history yet.")
        return 0

    for record in records:
        mark = "OK" if record.exit_code == 0 else "FAIL"
        print(f"#{record.id} [{mark}] exit={record.exit_code} {record.command}")
    return 0


def doctor() -> int:
    print("S.A.G.E doctor")
    print(f"Database: {db_path()}")
    for name in ["python", "git", "node", "npm"]:
        found = shutil.which(name)
        print(f"{name}: {found or 'not found'}")
    return 0


def init_project() -> int:
    path = Path.cwd() / "SAGE.md"
    path.write_text(ASSISTANT_INSTRUCTIONS, encoding="utf-8")
    print(f"Created {path}")
    print("Tell Claude or Codex: read SAGE.md before running terminal commands.")
    return 0
