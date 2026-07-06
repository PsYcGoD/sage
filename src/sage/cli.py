from __future__ import annotations
import logging

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .runner import run_command
from .savings import SAVINGS_PROFILES, build_agent_savings, estimate_savings_usd
from .store import connect, db_path, latest_run, recent_runs
from .suggestions import suggest_next_steps
from .autofix import AutoFixEngine

log = logging.getLogger(__name__)

ASSISTANT_INSTRUCTIONS = """# S.A.G.E Instructions

When working in this project, prefer running noisy terminal commands through S.A.G.E.

Examples:

- `sage run -- python -m unittest`
- `sage run -- npm test`
- `sage run -- pytest`
- `sage explain`
- `sage suggest`
- `sage history`

After a failed command, run `sage explain --failed` and `sage suggest --failed` before guessing at the fix.
S.A.G.E stores command summaries locally and helps keep AI context small.
"""

def configure_stdio() -> None:
    """Use UTF-8 for SAGE CLI output on Windows terminals."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            log.debug("suppressed", exc_info=True)

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sage",
        description="Smart Agent Guidance Engine for developer automation tools.",
    )
    parser.add_argument("--version", action="version", version=f"sage {__version__}")

    sub = parser.add_subparsers(dest="command_name", required=True)

    run = sub.add_parser("run", help="Run a command and remember the important output.")
    run.add_argument(
        "--predict",
        action="store_true",
        help="Predict failure risk before running the command.",
    )
    run.add_argument(
        "--policy-mode",
        choices=["personal", "company"],
        help="Apply a command policy mode for this run.",
    )
    run.add_argument(
        "--dry-run",
        action="store_true",
        help="Evaluate policy and show what would run without executing the command.",
    )
    run.add_argument(
        "--pty",
        action="store_true",
        help="Run the command with inherited terminal stdin/stdout/stderr for interactive CLIs.",
    )
    run.add_argument("command", nargs=argparse.REMAINDER, help="Command to run after --")

    predict_parser = sub.add_parser("predict", help="Predict whether a command is likely to fail.")
    predict_parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to analyze after --")

    ml_parser = sub.add_parser("ml", help="Train and inspect ML models.")
    ml_sub = ml_parser.add_subparsers(dest="ml_command")
    ml_train = ml_sub.add_parser("train", help="Train the sklearn failure predictor.")
    ml_train.add_argument("--min-samples", type=int, default=40)
    ml_train.add_argument("--synthetic-floor", type=int, default=120)
    ml_train.add_argument("--target-samples", type=int, default=0, help="Target total training rows, e.g. 1000000.")
    ml_import = ml_sub.add_parser("import-history", help="Import command examples from Claude/Codex local histories.")
    ml_import.add_argument("--source", choices=["all", "claude", "codex"], default="all")
    ml_import.add_argument("--path", action="append", default=[], help="History root/file to scan. May be repeated.")
    ml_import.add_argument("--limit", type=int, default=0, help="Max examples to import for a test run.")
    ml_import.add_argument("--dry-run", action="store_true", help="Scan without writing imported examples.")
    ml_import.add_argument("--train", action="store_true", help="Train the model after importing.")
    ml_import.add_argument("--target-samples", type=int, default=0, help="Optional training target after import.")
    ml_sub.add_parser("status", help="Show ML model status.")
    ml_validate = ml_sub.add_parser("validate", help="Temporal validation on deduplicated real history.")
    ml_validate.add_argument("--test-fraction", type=float, default=0.25, help="Newest fraction held out for testing (default 0.25).")
    ml_validate.add_argument("--format", choices=["text", "json"], default="text", help="Report format.")
    ml_validate.add_argument("--output", help="Write the JSON report to this file.")
    ml_validate.add_argument("--family-models", action="store_true", help="Validate per-family models (v4) instead of global model (v3).")

    explain_parser = sub.add_parser("explain", help="Explain the most recent command.")
    explain_parser.add_argument(
        "--failed",
        action="store_true",
        help="Explain the most recent failed command instead.",
    )

    suggest_parser = sub.add_parser("suggest", help="Suggest the next practical step.")
    suggest_parser.add_argument(
        "--failed",
        action="store_true",
        help="Suggest next steps for the most recent failed command instead.",
    )

    fix_parser = sub.add_parser("fix", help="Auto-fix the most recent error.")
    fix_parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually apply the fix (default is dry-run).",
    )
    fix_parser.add_argument(
        "--confidence",
        type=float,
        default=0.8,
        help="Minimum confidence threshold (0.0-1.0, default 0.8).",
    )

    history = sub.add_parser("history", help="Show recent remembered commands.")
    history.add_argument("--limit", type=int, default=10)
    history.add_argument("--kind", choices=["read", "grep", "write", "edit", "glob", "tree", "test", "build", "install", "lint", "git", "network", "run", "call"], help="Filter by command kind.")

    read_parser = sub.add_parser("read", help="Read a file with token accounting and compression.")
    read_parser.add_argument("target", nargs=argparse.REMAINDER, help="[--raw] [--symbols] [--lines START:END] [--max-tokens N] <file> after --")

    grep_parser = sub.add_parser("grep", help="Search files with compressed, navigable output.")
    grep_parser.add_argument("target", nargs=argparse.REMAINDER, help="[--glob PAT] [--ignore-case] [--files-with-matches] [--count] <pattern> [paths...] after --")

    call_parser = sub.add_parser("call", help="Run a command as an explicit agent/tool call.")
    call_parser.add_argument("--purpose", choices=["read", "search", "test", "build", "deploy", "audit", "unknown"], default="unknown")
    call_parser.add_argument("--agent", default="", help="Agent name making this call.")
    call_parser.add_argument("--task-id", type=int, default=0, help="Related agent task id.")
    call_parser.add_argument("--caller", default="agent", choices=["cli", "mcp", "agent", "ci", "api", "workflow"])
    call_parser.add_argument("--policy-mode", choices=["personal", "company"])
    call_parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to run after --")

    write_parser = sub.add_parser("write", help="Create or update a file; confirms with hash instead of echoing content.")
    write_parser.add_argument("path", help="File path to write.")
    write_source = write_parser.add_mutually_exclusive_group()
    write_source.add_argument("--content", default=None, help="Inline content (small files).")
    write_source.add_argument("--from-file", default=None, help="Copy content from another file.")
    write_source.add_argument("--stdin", action="store_true", help="Read content from stdin (best for multiline).")
    write_parser.add_argument("--overwrite", action="store_true", help="Allow replacing an existing file (snapshot taken first).")
    write_parser.add_argument("--append", action="store_true", help="Append to an existing file (snapshot taken first).")

    edit_parser = sub.add_parser("edit", help="Exact string replacement in a file with a compact change summary.")
    edit_parser.add_argument("path", help="File to edit.")
    edit_parser.add_argument("--old", default=None, help="Exact string to replace.")
    edit_parser.add_argument("--new", default="", help="Replacement string (empty deletes).")
    edit_parser.add_argument("--all", action="store_true", help="Replace every occurrence.")
    edit_parser.add_argument("--json-stdin", action="store_true", help="Read {\"old\", \"new\", \"all\"} JSON from stdin (best for multiline).")

    restore_parser = sub.add_parser("restore-file", help="Undo a sage write/edit using its snapshot file.")
    restore_parser.add_argument("snapshot", help="Snapshot path printed by sage write/edit.")

    glob_parser = sub.add_parser("glob", help="Find files by pattern, newest first, junk dirs ignored.")
    glob_parser.add_argument("pattern", help="Pattern, e.g. **/*.py or *.md")
    glob_parser.add_argument("root", nargs="?", default=".", help="Root directory (default .).")
    glob_parser.add_argument("--limit", type=int, default=50, help="Max files listed (default 50).")

    tree_parser = sub.add_parser("tree", help="Compact directory overview instead of a recursive listing.")
    tree_parser.add_argument("root", nargs="?", default=".", help="Root directory (default .).")
    tree_parser.add_argument("--depth", type=int, default=3, help="Max depth (default 3).")
    tree_parser.add_argument("--limit", type=int, default=200, help="Max entries (default 200).")

    show_parser = sub.add_parser("show", help="Show stored run output: raw, compressed, or summary.")
    show_parser.add_argument("run_id", type=int, nargs="?", help="Run ID (defaults to latest).")
    show_group = show_parser.add_mutually_exclusive_group()
    show_group.add_argument("--raw", action="store_true", help="Exact stored output (artifact-backed).")
    show_group.add_argument("--compressed", action="store_true", help="Compressed context view.")
    show_group.add_argument("--summary", action="store_true", help="Stored summary (default).")

    artifacts_parser = sub.add_parser("artifacts", help="Manage local raw output artifacts.")
    artifacts_sub = artifacts_parser.add_subparsers(dest="artifacts_command")
    artifacts_prune = artifacts_sub.add_parser("prune", help="Prune old/oversized raw artifacts.")
    artifacts_prune.add_argument("--days", type=int, help="Remove artifacts older than N days.")
    artifacts_prune.add_argument("--max-gb", type=float, help="Keep at most this many GB (oldest removed first).")
    artifacts_prune.add_argument("--apply", action="store_true", help="Actually delete (default is preview).")

    telemetry_parser = sub.add_parser("telemetry", help="Preview and control local telemetry (level 0 = nothing leaves this machine).")
    telemetry_sub = telemetry_parser.add_subparsers(dest="telemetry_command")
    telemetry_preview = telemetry_sub.add_parser("preview", help="Show exactly what would be sent for a run.")
    telemetry_preview.add_argument("run_id", type=int, nargs="?", help="Run ID (defaults to latest).")
    telemetry_preview.add_argument("--level", type=int, choices=[1, 2], help="Preview at a specific level.")
    telemetry_queue_cmd = telemetry_sub.add_parser("queue", help="Queue a run's event locally.")
    telemetry_queue_cmd.add_argument("run_id", type=int, nargs="?", help="Run ID (defaults to latest).")
    telemetry_send = telemetry_sub.add_parser("send", help="Send queued events (dry-run by default).")
    telemetry_send.add_argument("--dry-run", action="store_true", default=True, help="Preview without sending (default).")
    telemetry_send.add_argument("--for-real", action="store_true", help="Actually send (requires configured endpoint).")
    telemetry_sync = telemetry_sub.add_parser("sync-all", help="Queue and send all historical runs.")
    telemetry_sync.add_argument("--dry-run", action="store_true", default=True, help="Preview without sending (default).")
    telemetry_sync.add_argument("--for-real", action="store_true", help="Actually send every safe queued event.")
    telemetry_sub.add_parser("status", help="Show queue and level status.")
    telemetry_sub.add_parser("delete-local-queue", help="Delete all queued (unsent) events.")

    account_parser = sub.add_parser("account", help="Manage local account contexts for telemetry.")
    account_sub = account_parser.add_subparsers(dest="account_command")
    account_sub.add_parser("list", help="List linked accounts.")
    account_use_cmd = account_sub.add_parser("use", help="Switch active account ('anonymous' to clear).")
    account_use_cmd.add_argument("alias")
    account_sub.add_parser("status", help="Show active account and effective telemetry level.")
    account_unlink_cmd = account_sub.add_parser("unlink", help="Unlink an account.")
    account_unlink_cmd.add_argument("alias")
    account_link_cmd = account_sub.add_parser("link", help="Link an account context locally.")
    account_link_cmd.add_argument("alias")
    account_link_cmd.add_argument("--user-id", default="")
    account_link_cmd.add_argument("--org-id", default="")
    account_link_cmd.add_argument("--org-max-level", type=int, default=4)
    account_link_cmd.add_argument("--key-max-level", type=int, default=4)

    api_parser = sub.add_parser("api", help="SAGE API client status.")
    api_sub = api_parser.add_subparsers(dest="api_command")
    api_sub.add_parser("status", help="Show endpoint, mode, level, and queue.")
    api_login = api_sub.add_parser("login", help="Create and store a free SAGE API key.")
    _add_login_args(api_login)
    api_sub.add_parser("whoami", help="Show the current SAGE API identity.")
    api_sub.add_parser("visitors", help="Show private public-dashboard visitor stats.")
    api_rotate = api_sub.add_parser("rotate", help="Rotate API key (generates new key, revokes old one).")
    _add_login_args(api_rotate)
    api_sub.add_parser("logout", help="Disconnect local SAGE API credentials.")

    # 🔒 NEW: Primary connect command (GitHub OAuth)
    connect_parser = sub.add_parser("connect", help="Connect SAGE with GitHub authentication (required for first use).")
    connect_parser.add_argument("--display-name", help="Optional display name (defaults to GitHub name).")
    connect_parser.add_argument("--public-profile", action="store_true", help="Show your name on public proof.")
    connect_parser.add_argument("--expiry-days", type=int, choices=[30, 60, 90], help="API key expiration in days.")

    login_parser = sub.add_parser("login", help="Create and store a free SAGE API key.")
    _add_login_args(login_parser)
    sub.add_parser("whoami", help="Show the current SAGE API identity.")
    sub.add_parser("logout", help="Disconnect local SAGE API credentials.")

    agents_parser = sub.add_parser("agents", help="Manage AI agents.")
    agents_sub = agents_parser.add_subparsers(dest="agents_command")
    agents_sub.add_parser("list", help="List all agents.")
    agents_sub.add_parser("status", help="Show agent status.")
    agent_tasks = agents_sub.add_parser("tasks", help="Show agent task results for a run.")
    agent_tasks.add_argument("--run-id", type=int, help="Run ID to inspect (defaults to latest run).")
    agent_runs = agents_sub.add_parser("runs", help="Show active agent run records.")
    agent_runs.add_argument("--run-id", type=int, help="Run ID to inspect (defaults to latest run).")
    agent_worker = agents_sub.add_parser("worker", help="Process queued agent work once.")
    agent_worker.add_argument("--run-id", type=int, help="Optional run ID to process.")
    agent_worker.add_argument("--max-workers", type=int, default=4)
    agent_cancel = agents_sub.add_parser("cancel", help="Cancel queued/running agent work.")
    agent_cancel.add_argument("--run-id", type=int, help="Optional run ID to cancel.")
    agents_sub.add_parser("report", help="Show aggregate agent activity report.")
    agent_eval = agents_sub.add_parser("eval", help="Score agent analysis quality on fixture scenarios.")
    agent_eval.add_argument("--agent-type", help="Only evaluate this agent type (e.g. debug, test).")
    agent_eval.add_argument("--format", choices=["text", "json"], default="text", help="Report format.")
    agent_eval.add_argument("--output", help="Write the JSON report to this file.")

    privacy_parser = sub.add_parser("privacy", help="Privacy, redaction, and retention tools.")
    privacy_sub = privacy_parser.add_subparsers(dest="privacy_command")
    privacy_sub.add_parser("report", help="Show local privacy and retention status.")
    privacy_set = privacy_sub.add_parser("set", help="Set the telemetry level.")
    privacy_set.add_argument(
        "level",
        choices=["local-only", "anonymous-metrics", "redacted-summaries", "team-diagnostics", "research-full-logs", "0", "1", "2", "3", "4"],
        help="Privacy level name or number (0=local-only is the default).",
    )
    privacy_export = privacy_sub.add_parser("export-audit", help="Export a redacted audit report.")
    privacy_export.add_argument("--output", default="", help="Output JSON path.")
    privacy_purge = privacy_sub.add_parser("purge-raw", help="Purge retained raw stdout/stderr older than N days.")
    privacy_purge.add_argument("--days", type=int, default=30)
    privacy_purge.add_argument("--apply", action="store_true")

    savings_parser = sub.add_parser("savings", help="Estimate cost savings from compressed tokens.")
    savings_parser.add_argument("--agent", "--provider", "--model", dest="agent", default="claude-sonnet")
    savings_parser.add_argument("--format", choices=["text", "json"], default="text")

    firewall_parser = sub.add_parser("firewall", help="Inspect and configure SAGE command policy.")
    firewall_sub = firewall_parser.add_subparsers(dest="firewall_command")
    firewall_sub.add_parser("status", help="Show firewall policy status.")
    firewall_sub.add_parser("enable", help="Enable strict firewall mode.")
    firewall_sub.add_parser("disable", help="Return firewall to personal warning mode.")
    firewall_rules = firewall_sub.add_parser("rules", help="Inspect firewall rules.")
    firewall_rules_sub = firewall_rules.add_subparsers(dest="firewall_rules_command")
    firewall_rules_sub.add_parser("list", help="List allow, block, and confirm rules.")
    firewall_allow = firewall_sub.add_parser("allow", help="Allow a command pattern.")
    firewall_allow.add_argument("pattern")
    firewall_block = firewall_sub.add_parser("block", help="Block a command pattern.")
    firewall_block.add_argument("pattern")
    firewall_sub.add_parser("audit", help="Show recent policy and redaction activity.")

    github_bot_parser = sub.add_parser("github-bot", help="Generate GitHub issue/PR bot messages.")
    github_bot_sub = github_bot_parser.add_subparsers(dest="github_bot_command")
    github_bot_comment = github_bot_sub.add_parser("comment", help="Generate a safe Markdown comment.")
    github_bot_comment.add_argument("--kind", choices=["summary", "ci-failure"], default="summary")
    github_bot_comment.add_argument("--run-id", type=int, help="Run ID to summarize (defaults to latest).")
    github_bot_comment.add_argument("--output", default="", help="Optional Markdown output file.")

    redact_parser = sub.add_parser("redact", help="Scan stored runs and redact old secrets.")
    redact_parser.add_argument("--apply", action="store_true", help="Write redacted output back to the database.")
    redact_parser.add_argument("--limit", type=int, default=0, help="Limit scanned runs.")

    workflow_parser = sub.add_parser("workflow", help="Manage workflows.")
    workflow_sub = workflow_parser.add_subparsers(dest="workflow_command")
    workflow_run = workflow_sub.add_parser("run", help="Run a workflow.")
    workflow_run.add_argument("name", help="Workflow name or path to YAML file")
    workflow_sub.add_parser("list", help="List available workflows.")

    dashboard_parser = sub.add_parser("dashboard", help="Dashboard control.")
    dashboard_sub = dashboard_parser.add_subparsers(dest="dashboard_command")
    dashboard_start = dashboard_sub.add_parser("start", help="Start dashboard.")
    dashboard_start.add_argument("--port", type=int, default=8765, help="Port number")
    dashboard_start.add_argument("--no-browser", action="store_true", help="Don't open browser")
    dashboard_sub.add_parser("stop", help="Stop dashboard.")

    mcp_parser = sub.add_parser("mcp", help="MCP server control.")
    mcp_sub = mcp_parser.add_subparsers(dest="mcp_command")
    mcp_sub.add_parser("install", help="Install MCP server config.")
    mcp_sub.add_parser("start", help="Start MCP server.")

    context_parser = sub.add_parser("context", help="Context management.")
    context_sub = context_parser.add_subparsers(dest="context_command")
    context_sub.add_parser("stats", help="Show token usage statistics.")
    context_sub.add_parser("optimize", help="Get context optimization suggestions.")
    context_report = context_sub.add_parser("report", help="Show verified compression proof metrics.")
    context_report.add_argument("--format", choices=["text", "json", "md"], default="text")
    context_report.add_argument("--output", default="", help="Optional output file for json/md report.")
    context_snapshot = context_sub.add_parser("snapshot", help="Write this month's compression snapshot.")
    context_snapshot.add_argument("--month", default="", help="Month in YYYY-MM format, default current month.")
    context_benchmark = context_sub.add_parser("benchmark", help="Run deterministic compression benchmark fixtures.")
    context_benchmark.add_argument("--sizes", default="5000,10000,50000,100000", help="Comma-separated token targets.")
    context_benchmark.add_argument("--format", choices=["text", "json", "md"], default="text")
    context_benchmark.add_argument("--output", default="", help="Optional output report path.")

    db_parser = sub.add_parser("db", help="Database storage, backup, and migration tools.")
    db_sub = db_parser.add_subparsers(dest="db_command")
    db_sub.add_parser("status", help="Show database size, integrity, migrations, and row counts.")
    db_backup = db_sub.add_parser("backup", help="Copy the local SAGE database to a backup file.")
    db_backup.add_argument("--output", default="", help="Backup path. Defaults to SAGE data dir with timestamp.")
    db_restore = db_sub.add_parser("restore", help="Restore the local SAGE database from a backup file.")
    db_restore.add_argument("backup", help="Backup database path to restore.")
    db_restore.add_argument("--yes", action="store_true", help="Confirm restore without an interactive prompt.")

    sub.add_parser("doctor", help="Check local setup.")
    sub.add_parser("stats", help="Show SAGE token, ML, and agent statistics.")
    sub.add_parser("init", help="Create S.A.G.E instructions for developer tools.")
    sub.add_parser("gui", help="Show GUI availability status.")

    return parser

def _add_login_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--display-name", default="", help="Public/profile display name.")
    parser.add_argument("--username", default="", help="Public username or handle.")
    parser.add_argument("--public-profile", action="store_true", help="Show this profile on public proof leaderboards.")
    parser.add_argument("--privacy-max", type=int, default=1, choices=[0, 1, 2, 3, 4], help="Maximum telemetry level allowed for this key.")
    parser.add_argument("--scope", default="personal", help="API key scope label.")
    parser.add_argument("--endpoint", default="", help="SAGE API base URL. Defaults to sage.api.marketingstudios.in.")
    parser.add_argument("--expiry-days", type=int, choices=[30, 60, 90], help="API key expiration in days.")

def main(argv: list[str] | None = None) -> int:
    configure_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)

    # Gate command execution behind API connection, while still allowing the
    # first-run account/status commands needed to connect.
    ALLOWED_WITHOUT_API = ["connect", "login", "whoami", "logout", "doctor", "gui", "api", "db"]

    if args.command_name not in ALLOWED_WITHOUT_API:
        from . import telemetry
        status = telemetry.api_status()
        if not status.get("connected"):
            print("SAGE requires API connection to use this command.")
            print("\nConnect with GitHub (free, takes 30 seconds):")
            print("   sage connect")
            print("\nThen bind SAGE instructions for local agents:")
            print("   sage init")
            return 1

    if args.command_name == "run":
        command = list(args.command)
        if command and command[0] == "--":
            command = command[1:]
        return run_command(
            command,
            predict=args.predict,
            policy_mode=args.policy_mode,
            dry_run=args.dry_run,
            pty=args.pty,
        )

    if args.command_name == "predict":
        command = list(args.command)
        if command and command[0] == "--":
            command = command[1:]
        return predict_command(command)

    if args.command_name == "ml":
        return ml_command(args)

    if args.command_name == "explain":
        return explain(only_failed=args.failed)

    if args.command_name == "suggest":
        return suggest(only_failed=args.failed)

    if args.command_name == "fix":
        return fix_command(apply=args.apply, min_confidence=args.confidence)

    if args.command_name == "agents":
        return agents_command(args)

    if args.command_name == "privacy":
        return privacy_command(args)

    if args.command_name == "savings":
        return savings_command(args)

    if args.command_name == "firewall":
        return firewall_command(args)

    if args.command_name == "github-bot":
        return github_bot_command(args)

    if args.command_name == "redact":
        return redact_command(limit=args.limit, apply=args.apply)

    if args.command_name == "workflow":
        return workflow_command(args)

    if args.command_name == "dashboard":
        return dashboard_command(args)

    if args.command_name == "mcp":
        return mcp_command(args)

    if args.command_name == "context":
        return context_command(args)

    if args.command_name == "db":
        return db_command(args)

    if args.command_name == "history":
        return history(args.limit, kind=getattr(args, "kind", None))

    if args.command_name == "read":
        return read_command(args)

    if args.command_name == "grep":
        return grep_command(args)

    if args.command_name == "call":
        return call_command(args)

    if args.command_name == "write":
        return write_command(args)

    if args.command_name == "edit":
        return edit_command(args)

    if args.command_name == "restore-file":
        return restore_file_command(args)

    if args.command_name == "glob":
        return glob_command(args)

    if args.command_name == "tree":
        return tree_command(args)

    if args.command_name == "show":
        return show_command(args)

    if args.command_name == "artifacts":
        return artifacts_command(args)

    if args.command_name == "telemetry":
        return telemetry_command(args)

    if args.command_name == "account":
        return account_command(args)

    if args.command_name == "api":
        return api_command(args)

    if args.command_name == "connect":
        return connect_command(args)

    if args.command_name == "login":
        return login_command(args)

    if args.command_name == "whoami":
        return whoami_command()

    if args.command_name == "logout":
        return logout_command()

    if args.command_name == "doctor":
        return doctor()

    if args.command_name == "stats":
        return stats_command()

    if args.command_name == "init":
        return init_project()

    if args.command_name == "gui":
        return gui_command()

    parser.print_help()
    return 2

def explain(only_failed: bool = False) -> int:
    record = latest_run(only_failures=only_failed)
    if record is None:
        kind = "failed command history" if only_failed else "command history"
        print(f"S.A.G.E has no {kind} yet.")
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

def suggest(only_failed: bool = False) -> int:
    record = latest_run(only_failures=only_failed)
    if record is not None:
        print(f"Suggestions for run #{record.id}: {record.command}")
        print()
    print(suggest_next_steps(record))
    return 0

def history(limit: int, kind: str | None = None) -> int:
    if kind:
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT id, exit_code, command, command_kind, command_family
                FROM runs WHERE command_kind = ?
                ORDER BY id DESC LIMIT ?
                """,
                (kind, max(1, limit)),
            ).fetchall()
        if not rows:
            print(f"No runs with kind '{kind}' yet.")
            return 0
        for row in rows:
            mark = "OK" if row["exit_code"] == 0 else "FAIL"
            print(f"#{row['id']} [{mark}] [{row['command_kind']}/{row['command_family']}] {row['command']}")
        return 0

    records = recent_runs(limit=max(1, limit))
    if not records:
        print("No command history yet.")
        return 0

    for record in records:
        mark = "OK" if record.exit_code == 0 else "FAIL"
        print(f"#{record.id} [{mark}] exit={record.exit_code} {record.command}")
    return 0

def _split_remainder_flags(remainder: list[str], flag_spec: dict[str, bool]) -> tuple[dict[str, str | bool], list[str]]:
    """Parse flags out of a REMAINDER arg list (supports flags after `--`).

    flag_spec maps flag name to whether it takes a value.
    Returns (flags, positionals). Unknown tokens stay positional.
    """
    flags: dict[str, str | bool] = {}
    positionals: list[str] = []
    index = 0
    while index < len(remainder):
        token = remainder[index]
        if token == "--":
            index += 1
            continue
        if token in flag_spec:
            if flag_spec[token]:
                if index + 1 >= len(remainder):
                    raise ValueError(f"{token} requires a value")
                flags[token] = remainder[index + 1]
                index += 2
            else:
                flags[token] = True
                index += 1
        else:
            positionals.append(token)
            index += 1
    return flags, positionals

def read_command(args) -> int:
    from .reader import DEFAULT_MAX_TOKENS, read_file, save_read_run

    try:
        flags, positionals = _split_remainder_flags(
            list(args.target),
            {"--raw": False, "--symbols": False, "--lines": True, "--max-tokens": True},
        )
    except ValueError as exc:
        print(f"sage read: {exc}")
        return 2
    if not positionals:
        print("No file was provided. Example: sage read -- README.md")
        return 2

    result = read_file(
        positionals[0],
        lines=str(flags.get("--lines", "")),
        max_tokens=int(flags.get("--max-tokens", DEFAULT_MAX_TOKENS)),
        raw=bool(flags.get("--raw")),
        symbols_only=bool(flags.get("--symbols")),
    )
    if not result.exists:
        print(result.error)
        save_read_run(result)
        return 1

    print(result.output)
    run_id = save_read_run(result)
    print()
    print(
        f"[sage] read run #{run_id} mode={result.mode} "
        f"tokens {result.original_tokens} -> {result.shown_tokens} (saved {result.saved_tokens})"
    )
    return 0

def grep_command(args) -> int:
    from .searcher import render, save_grep_run, search

    try:
        flags, positionals = _split_remainder_flags(
            list(args.target),
            {
                "--glob": True,
                "--ignore-case": False,
                "--context": True,
                "--files-with-matches": False,
                "--count": False,
            },
        )
    except ValueError as exc:
        print(f"sage grep: {exc}")
        return 2
    if not positionals:
        print('No pattern was provided. Example: sage grep -- "def main" src')
        return 2

    pattern, paths = positionals[0], positionals[1:] or ["."]
    result = search(
        pattern,
        paths,
        glob=str(flags.get("--glob", "")),
        ignore_case=bool(flags.get("--ignore-case")),
    )
    rendered = render(
        result,
        files_with_matches=bool(flags.get("--files-with-matches")),
        count_only=bool(flags.get("--count")),
    )
    print(rendered)
    raw_output = "\n".join(
        f"{file}:{line_no}:{text}" for file, hits in result.matches.items() for line_no, text in hits
    )
    run_id = save_grep_run(result, rendered, raw_output)
    print()
    print(
        f"[sage] grep run #{run_id} matches={result.match_count} files={result.matched_files} "
        f"hidden={result.hidden_matches} engine={result.engine}"
    )
    return result.exit_code

def call_command(args) -> int:
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        print("No command was provided. Example: sage call --purpose test -- pytest -q")
        return 2

    exit_code = run_command(
        command,
        policy_mode=args.policy_mode,
        caller=args.caller,
        kind_override="call",
    )

    # Enrich the call run with purpose/agent linkage for tool-quality metrics.
    with connect() as conn:
        row = conn.execute("SELECT id FROM runs ORDER BY id DESC LIMIT 1").fetchone()
        if row:
            conn.execute(
                "UPDATE runs SET command_family = ? WHERE id = ?",
                (args.purpose, int(row["id"])),
            )
            if args.task_id:
                conn.execute(
                    "UPDATE agent_tasks SET result = json_set(COALESCE(result, '{}'), '$.call_run_id', ?) WHERE id = ?",
                    (int(row["id"]), args.task_id),
                )
            conn.commit()
            if args.agent or args.task_id:
                print(f"[sage] call linked: agent={args.agent or 'n/a'} task_id={args.task_id or 'n/a'}")
    return exit_code

def show_command(args) -> int:
    from .artifacts import load_raw_output

    run_id = args.run_id
    if run_id is None:
        record = latest_run()
        if record is None:
            print("No command history yet.")
            return 1
        run_id = record.id

    with connect() as conn:
        row = conn.execute(
            "SELECT id, command, exit_code, summary FROM runs WHERE id = ?", (run_id,)
        ).fetchone()
        if row is None:
            print(f"Run #{run_id} not found.")
            return 1

    if args.raw:
        raw = load_raw_output(run_id)
        print(f"Run #{run_id} raw output (source={raw['source']}, integrity={raw['verified']}):")
        if raw["stdout"]:
            print(raw["stdout"])
        if raw["stderr"]:
            print("--- stderr ---")
            print(raw["stderr"])
        return 0

    if args.compressed:
        from .context.compression import ContextCompressor

        raw = load_raw_output(run_id)
        combined = "\n".join(part for part in (raw["stdout"], raw["stderr"]) if part)
        compressor = ContextCompressor()
        compressed = compressor.compress(combined, strategy="auto") if combined else ""
        original = compressor.estimate_tokens(combined)
        shown = compressor.estimate_tokens(compressed)
        print(f"Run #{run_id} compressed context ({original} -> {shown} tokens):")
        print(compressed or "(no stored output)")
        return 0

    print(f"Run #{run_id} [{'OK' if row['exit_code'] == 0 else 'FAIL'}] {row['command']}")
    print(row["summary"])
    return 0

def artifacts_command(args) -> int:
    from .artifacts import artifacts_dir, prune_artifacts

    if getattr(args, "artifacts_command", None) != "prune":
        files = list(artifacts_dir().glob("run-*-raw.json"))
        total = sum(p.stat().st_size for p in files)
        print(f"Artifacts: {len(files)} files, {total / 1_048_576:.1f} MB at {artifacts_dir()}")
        print("Prune with: sage artifacts prune --days 30 --apply")
        return 0

    max_bytes = int(args.max_gb * 1_073_741_824) if args.max_gb else None
    stats = prune_artifacts(days=args.days, max_bytes=max_bytes, apply=args.apply)
    action = "Pruned" if args.apply else "Would prune"
    print(f"{action} {stats['pruned']} of {stats['total_artifacts']} artifacts ({stats['pruned_bytes'] / 1_048_576:.1f} MB).")
    if not args.apply and stats["pruned"]:
        print("Re-run with --apply to delete.")
    return 0

def write_command(args) -> int:
    from .fileops import save_fileop_run, write_file

    if args.stdin:
        content = sys.stdin.read()
    elif args.from_file is not None:
        source = Path(args.from_file)
        if not source.exists():
            print(f"Source not found: {args.from_file}")
            return 2
        content = source.read_text(encoding="utf-8", errors="replace")
    elif args.content is not None:
        content = args.content
    else:
        print("Provide content with --content, --from-file, or --stdin.")
        return 2

    result = write_file(args.path, content, overwrite=args.overwrite, append=args.append)
    action = "appended" if args.append else ("overwrote" if result.overwritten else "created")
    if result.ok:
        output = (
            f"{action} {result.path}: {result.lines} lines, {result.bytes} bytes, "
            f"sha256={result.sha256[:16]}... ({result.content_tokens} content tokens not echoed)"
        )
    else:
        output = result.error
    print(output)
    if result.snapshot:
        print(f"[sage] snapshot: {result.snapshot} (undo with: sage restore-file \"{result.snapshot}\")")
    run_id = save_fileop_run(
        kind="write",
        command_text=f"sage write {args.path}",
        output=output,
        exit_code=0 if result.ok else 1,
        summary=output,
        family=Path(args.path).suffix.lstrip(".") or "file",
    )
    print(f"[sage] write run #{run_id}")
    return 0 if result.ok else 1

def edit_command(args) -> int:
    from .fileops import edit_file, save_fileop_run

    if args.json_stdin:
        try:
            payload = json.loads(sys.stdin.read())
        except json.JSONDecodeError as exc:
            print(f"Invalid JSON on stdin: {exc}")
            return 2
        old = str(payload.get("old", ""))
        new = str(payload.get("new", ""))
        replace_all = bool(payload.get("all", False))
    else:
        if args.old is None:
            print("Provide --old (and --new), or --json-stdin for multiline edits.")
            return 2
        old, new, replace_all = args.old, args.new, args.all

    result = edit_file(args.path, old, new, replace_all=replace_all)
    if not result.ok:
        print(f"sage edit: {result.error}")
        save_fileop_run(
            kind="edit",
            command_text=f"sage edit {args.path}",
            output=result.error,
            exit_code=1,
            summary=f"edit {args.path} failed: {result.error}",
        )
        return 1

    summary = (
        f"edited {result.path}: {result.replacements} replacement(s) on lines "
        f"{result.changed_lines[:10]} (showed {result.shown_tokens} of {result.file_tokens} file tokens)"
    )
    print(summary)
    print(result.preview)
    print(f"[sage] snapshot: {result.snapshot} (undo with: sage restore-file \"{result.snapshot}\")")
    run_id = save_fileop_run(
        kind="edit",
        command_text=f"sage edit {args.path}",
        output=f"{summary}\n{result.preview}",
        exit_code=0,
        summary=summary,
        family=Path(args.path).suffix.lstrip(".") or "file",
    )
    print(f"[sage] edit run #{run_id}")
    return 0

def restore_file_command(args) -> int:
    from .fileops import restore_snapshot, save_fileop_run

    ok, message = restore_snapshot(args.snapshot)
    print(message)
    save_fileop_run(
        kind="write",
        command_text=f"sage restore-file {args.snapshot}",
        output=message,
        exit_code=0 if ok else 1,
        summary=message,
        family="restore",
    )
    return 0 if ok else 1

def glob_command(args) -> int:
    from .context.tokens import count_tokens
    from .fileops import glob_files, render_glob, save_fileop_run

    result = glob_files(args.pattern, args.root, limit=args.limit)
    rendered = render_glob(result)
    print(rendered)
    run_id = save_fileop_run(
        kind="glob",
        command_text=f"sage glob {args.pattern} {args.root}",
        output=rendered,
        exit_code=0 if not result.error else 2,
        summary=f"glob {args.pattern!r}: {result.total_found} files, showed {len(result.files)} ({count_tokens(rendered)} tokens)",
    )
    print(f"\n[sage] glob run #{run_id} found={result.total_found} shown={len(result.files)}")
    return 0 if not result.error else 2

def tree_command(args) -> int:
    from .context.tokens import count_tokens
    from .fileops import save_fileop_run, tree_view

    rendered = tree_view(args.root, depth=args.depth, limit=args.limit)
    print(rendered)
    ok = not rendered.startswith("sage tree error")
    run_id = save_fileop_run(
        kind="tree",
        command_text=f"sage tree {args.root}",
        output=rendered,
        exit_code=0 if ok else 2,
        summary=f"tree {args.root} depth={args.depth}: {len(rendered.splitlines())} entries ({count_tokens(rendered)} tokens)",
    )
    print(f"\n[sage] tree run #{run_id}")
    return 0 if ok else 2

def db_command(args) -> int:
    """Database storage, backup, and migration tools."""
    import sqlite3
    import shutil as _shutil

    sub = getattr(args, "db_command", None)
    if sub is None:
        print("Usage: sage db <status|backup|restore>")
        return 1

    path = db_path()

    if sub == "status":
        size_mb = path.stat().st_size / 1_048_576 if path.exists() else 0.0
        print(f"Database: {path}")
        print(f"Size: {size_mb:.1f} MB")
        with connect() as conn:
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            print(f"Integrity: {integrity}")
            tables = [
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                ).fetchall()
            ]
            for table in tables:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                print(f"- {table}: {count:,} rows")
        return 0

    if sub == "backup":
        if not path.exists():
            print("No database to back up yet.")
            return 1
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target = Path(args.output) if args.output else path.parent / f"sage-backup-{stamp}.db"
        target.parent.mkdir(parents=True, exist_ok=True)
        with connect() as conn:
            conn.execute("PRAGMA wal_checkpoint(FULL)")
        with sqlite3.connect(path) as source, sqlite3.connect(target) as dest:
            source.backup(dest)
        print(f"Backed up {path.stat().st_size / 1_048_576:.1f} MB to {target}")
        return 0

    if sub == "restore":
        source = Path(args.backup)
        if not source.exists():
            print(f"Backup not found: {source}")
            return 1
        if not args.yes:
            print("Restore replaces the current database. Re-run with --yes to confirm.")
            print(f"Would restore: {source} -> {path}")
            return 1
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        if path.exists():
            safety = path.parent / f"sage-pre-restore-{stamp}.db"
            with connect() as conn:
                conn.execute("PRAGMA wal_checkpoint(FULL)")
            _shutil.copy2(path, safety)
            print(f"Current database preserved at {safety}")
        with sqlite3.connect(source) as source_conn, sqlite3.connect(path) as dest_conn:
            source_conn.backup(dest_conn)
        print(f"Restored database from {source}")
        return 0

    return 1

def telemetry_command(args) -> int:
    from . import telemetry

    sub = getattr(args, "telemetry_command", None)
    if sub is None:
        print("Usage: sage telemetry <preview|queue|send|status|delete-local-queue>")
        return 1

    def _resolve_run_id(value) -> int | None:
        if value is not None:
            return value
        record = latest_run()
        return record.id if record else None

    if sub == "preview":
        run_id = _resolve_run_id(args.run_id)
        if run_id is None:
            print("No command history yet.")
            return 1
        payload = telemetry.build_payload(run_id, level=args.level)
        if payload is None:
            print(f"Telemetry level is {telemetry.effective_level()} (local-only): nothing would be sent.")
            print("Preview a hypothetical payload with: sage telemetry preview --level 1")
            return 0
        print(f"Telemetry payload for run #{run_id} (schema {payload['schema_version']}):")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    if sub == "queue":
        run_id = _resolve_run_id(args.run_id)
        if run_id is None:
            print("No command history yet.")
            return 1
        payload = telemetry.queue_event(run_id)
        if payload is None:
            print("Telemetry level is 0 (local-only): nothing was queued.")
            return 0
        print(f"Queued event for run #{run_id}. Queue: {telemetry.queue_status()}")
        return 0

    if sub == "send":
        result = telemetry.send_queued(dry_run=not args.for_real)
        print(f"Endpoint: {result['endpoint']}")
        print(
            f"Dry run: {result['dry_run']} | Sent: {result['sent']} | "
            f"Failed: {result.get('failed', 0)} | Still queued: {result['queued']}"
        )
        for item in result.get("preview", []):
            print(f"- {item['event_type']} kind={item['command_kind']} saved_tokens={item['saved_tokens']}")
        return 0

    if sub == "sync-all":
        result = telemetry.sync_all_runs(dry_run=not args.for_real)
        queued_all = result.get("queued_all", {})
        print(f"Endpoint: {result['endpoint']}")
        print(
            "Backfill: "
            f"scanned={queued_all.get('scanned', 0)} "
            f"queued={queued_all.get('queued', 0)} "
            f"skipped={queued_all.get('skipped', 0)}"
        )
        print(
            f"Dry run: {result['dry_run']} | Sent: {result['sent']} | "
            f"Failed: {result.get('failed', 0)} | Still queued: {result['queued']}"
        )
        snapshot = result.get("snapshot")
        if snapshot:
            print(f"Proof snapshot: {'updated' if snapshot.get('ok') else 'not updated'}")
        for item in result.get("preview", []):
            print(f"- {item['event_type']} kind={item['command_kind']} saved_tokens={item['saved_tokens']}")
        return 0

    if sub == "status":
        status = telemetry.api_status()
        print(f"Mode: {status['mode']} | Level: {status['effective_level']} ({status['effective_level_name']})")
        print(f"Queue: {status['queue']}")
        errors = telemetry.queue_errors()
        if errors:
            print("Recent queue errors:")
            for item in errors:
                message = item["last_error"].replace("\n", " ")[:220]
                print(f"- id={item['id']} attempts={item['attempts']} {message}")
        return 0

    if sub == "delete-local-queue":
        deleted = telemetry.delete_local_queue()
        print(f"Deleted {deleted} queued events.")
        return 0

    return 1

def account_command(args) -> int:
    from . import telemetry

    sub = getattr(args, "account_command", None)
    if sub is None:
        print("Usage: sage account <list|use|status|link|unlink>")
        return 1

    if sub == "list":
        data = telemetry.account_list()
        active = data["active"] or "anonymous"
        print(f"Active: {active}")
        for alias, info in data["accounts"].items():
            print(f"- {alias}: user={info.get('user_id') or 'n/a'} org={info.get('org_id') or 'n/a'} org_max_level={info.get('org_max_level')}")
        if not data["accounts"]:
            print("No linked accounts. Link one with: sage account link <alias> --user-id <id>")
        return 0

    if sub == "use":
        if telemetry.account_use(args.alias):
            print(f"Active account: {args.alias}")
            return 0
        print(f"Unknown account '{args.alias}'. See: sage account list")
        return 1

    if sub == "status":
        status = telemetry.account_status()
        for key, value in status.items():
            print(f"{key}: {value}")
        return 0

    if sub == "link":
        telemetry.account_link(
            args.alias,
            user_id=args.user_id,
            org_id=args.org_id,
            org_max_level=args.org_max_level,
            key_max_level=args.key_max_level,
        )
        print(f"Linked account '{args.alias}'. Effective level: {telemetry.effective_level()}")
        return 0

    if sub == "unlink":
        if telemetry.account_unlink(args.alias):
            print(f"Unlinked '{args.alias}'.")
            return 0
        print(f"Unknown account '{args.alias}'.")
        return 1

    return 1

def api_command(args) -> int:
    from . import telemetry

    sub = getattr(args, "api_command", None) or "status"
    if sub == "login":
        return login_command(args)
    if sub == "whoami":
        return whoami_command()
    if sub == "visitors":
        return api_visitors_command()
    if sub == "rotate":
        return rotate_key_command(args)
    if sub == "logout":
        return logout_command()

    status = telemetry.api_status()
    print("SAGE API status")
    print(f"Connected: {status['connected']}")
    print(f"Base URL: {status['base_url']}")
    print(f"Endpoint: {status['endpoint']}")
    print(f"Key ID: {status['key_id']}")
    print(f"Mode: {status['mode']}")
    print(f"Telemetry level: {status['effective_level']} ({status['effective_level_name']})")
    profile = status.get("profile") or {}
    if profile:
        print(f"Profile: {profile.get('display_name') or '(none)'} @{profile.get('username') or 'n/a'} public={bool(profile.get('public_profile'))}")
    print(f"Queue: {status['queue']}")
    return 0

def api_visitors_command() -> int:
    from . import telemetry

    try:
        data = telemetry.get_visitor_stats()
    except Exception as exc:
        print(f"SAGE API visitor stats failed: {exc}")
        return 1

    totals = data.get("totals", {}) or {}
    today = data.get("today_stats", {}) or {}
    print("SAGE public dashboard visitors")
    print(f"Generated: {data.get('generated_at')}")
    print(f"All-time unique visitors: {totals.get('unique_visitors', 0)}")
    print(f"All-time page views: {totals.get('page_views', 0)}")
    print(f"Today ({data.get('today')}):")
    print(f"  unique visitors: {today.get('unique_visitors', 0)}")
    print(f"  page views: {today.get('page_views', 0)}")
    print(f"  new visitors: {today.get('new_visitors', 0)}")
    print(f"  returning visitors: {today.get('returning_visitors', 0)}")
    recent = data.get("recent_days") or []
    if recent:
        print("Recent days:")
        for row in recent:
            print(f"  {row.get('day')}: {row.get('unique_visitors', 0)} visitors, {row.get('page_views', 0)} views")
    return 0

def login_command(args) -> int:
    print("SAGE login now uses GitHub OAuth.")
    if not hasattr(args, "expiry_days"):
        args.expiry_days = 30
    return connect_command(args)

def _resolve_expiry_days(args) -> int:
    selected = getattr(args, "expiry_days", None)
    if selected in {30, 60, 90}:
        return int(selected)
    if not sys.stdin.isatty():
        return 30

    print("Choose API key expiration:")
    print("  1. 30 days")
    print("  2. 60 days")
    print("  3. 90 days")
    choice = input("Expiration [1/2/3, default 1]: ").strip()
    return {"1": 30, "2": 60, "3": 90, "30": 30, "60": 60, "90": 90}.get(choice, 30)

def whoami_command() -> int:
    from . import telemetry

    data = telemetry.api_whoami()
    print("SAGE API identity")
    for key, value in data.items():
        print(f"{key}: {value}")
    return 0

def logout_command() -> int:
    from . import telemetry

    telemetry.api_logout()
    print("SAGE API disconnected. Telemetry reset to local-only.")
    return 0

def connect_command(args) -> int:
    """🔒 Connect SAGE with GitHub OAuth (primary authentication method)."""
    from . import telemetry
    from .github_oauth import github_oauth_flow
    from .install import install_sage_system_wide, is_sage_installed_system_wide
    import subprocess

    # Check if already connected
    status = telemetry.api_status()
    if status.get("connected"):
        print(f"✅ SAGE already connected")
        print(f"GitHub: @{status.get('profile', {}).get('username')}")
        print(f"Key expires: {status.get('expires_at', 'Never')}")
        print(f"\nTo rotate key: sage api rotate")
        print(f"To disconnect: sage logout")
        return 0

    print("🔐 SAGE Connection - GitHub Authentication")
    print("=" * 60)
    print("SAGE requires GitHub authentication for:")
    print("  ✅ Free API access (no credit card)")
    print("  ✅ 1 account = 1 API key (prevents abuse)")
    print("  ✅ Automatic agent config installation")
    print("  ✅ 99.3% token compression for all commands")
    print("=" * 60)
    print()
    expiry_days = _resolve_expiry_days(args)
    print(f"API key expiration: {expiry_days} days")
    print()

    try:
        # Run GitHub OAuth flow
        oauth_result = github_oauth_flow()

        if not oauth_result.get("auth_code"):
            print("❌ GitHub authentication failed")
            return 1

        print("✅ GitHub authentication successful")

        # Send to SAGE API (which will validate with GitHub and create key)
        print("🔄 Creating SAGE API key...")

        try:
            result = telemetry.api_github_login(
                auth_code=oauth_result["auth_code"],
                redirect_uri=oauth_result.get("redirect_uri", ""),
                display_name=args.display_name if hasattr(args, "display_name") and args.display_name else None,
                public_profile=args.public_profile if hasattr(args, "public_profile") else False,
                expiry_days=expiry_days,
            )
        except Exception as oauth_exc:
            print(f"Browser OAuth API exchange failed: {oauth_exc}")
            print("Trying GitHub CLI fallback...")
            gh = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=20,
            )
            token = gh.stdout.strip()
            if gh.returncode != 0 or not token:
                details = (gh.stderr or gh.stdout or "").strip()
                raise RuntimeError(
                    "Browser OAuth failed and GitHub CLI fallback is not available. "
                    f"gh output: {details or 'no token returned'}"
                ) from oauth_exc
            result = telemetry.api_github_login(
                github_access_token=token,
                display_name=args.display_name if hasattr(args, "display_name") and args.display_name else None,
                public_profile=args.public_profile if hasattr(args, "public_profile") else False,
                expiry_days=expiry_days,
            )

        print("\n✅ SAGE API connected")
        print(f"GitHub: @{result.get('username')}")
        print(f"Key ID: {result.get('key_id')}")
        print(f"Expires: {result.get('expires_at')}")

        # Install agent configs system-wide
        if not is_sage_installed_system_wide():
            print("\n🚀 Installing SAGE agent configs system-wide...")
            install_sage_system_wide()
            print("\n✅ All AI agents on this PC will now use SAGE automatically")
        else:
            print("\nℹ️  SAGE agent configs already installed")

        print("\n🎉 Setup complete! You can now use SAGE:")
        print("   sage run -- python test.py")
        print("   sage run -- pytest")
        print("   sage run -- npm install")

        return 0

    except Exception as exc:
        print(f"\n❌ Connection failed: {exc}")
        print("\nTroubleshooting:")
        print("  1. Check internet connection")
        print("  2. Allow browser popup for GitHub login")
        print("  3. Try again: sage connect")
        return 1

def rotate_key_command(args) -> int:
    """Rotate API key through GitHub OAuth."""
    from . import telemetry
    from .github_oauth import github_oauth_flow
    import subprocess

    old_status = telemetry.api_status()
    expiry_days = _resolve_expiry_days(args)
    try:
        print(f"API key expiration: {expiry_days} days")
        print("Opening GitHub OAuth to rotate your SAGE API key...")
        oauth_result = github_oauth_flow()
        if not oauth_result.get("auth_code"):
            print("GitHub authentication failed.")
            return 1

        try:
            result = telemetry.api_github_login(
                auth_code=oauth_result["auth_code"],
                redirect_uri=oauth_result.get("redirect_uri", ""),
                display_name=args.display_name or old_status.get("profile", {}).get("display_name") or None,
                public_profile=(
                    args.public_profile
                    if hasattr(args, "public_profile") and args.public_profile
                    else bool(old_status.get("profile", {}).get("public_profile"))
                ),
                expiry_days=expiry_days,
                base_url=args.endpoint if hasattr(args, "endpoint") else old_status.get("base_url", ""),
            )
        except Exception as oauth_exc:
            print(f"Browser OAuth API exchange failed: {oauth_exc}")
            print("Trying GitHub CLI fallback...")
            gh = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=20,
            )
            token = gh.stdout.strip()
            if gh.returncode != 0 or not token:
                details = (gh.stderr or gh.stdout or "").strip()
                raise RuntimeError(
                    "Browser OAuth failed and GitHub CLI fallback is not available. "
                    f"gh output: {details or 'no token returned'}"
                ) from oauth_exc
            result = telemetry.api_github_login(
                github_access_token=token,
                display_name=args.display_name or old_status.get("profile", {}).get("display_name") or None,
                public_profile=(
                    args.public_profile
                    if hasattr(args, "public_profile") and args.public_profile
                    else bool(old_status.get("profile", {}).get("public_profile"))
                ),
                expiry_days=expiry_days,
                base_url=args.endpoint if hasattr(args, "endpoint") else old_status.get("base_url", ""),
            )
    except Exception as exc:
        print(f"Key rotation failed: {exc}")
        return 1

    print("✅ API key rotated successfully")
    print(f"New Key ID: {result['key_id']}")
    print(f"Stored key: {result['api_key_redacted']}")
    print(f"Old key revoked by server: {old_status.get('key_id') if old_status.get('connected') else 'N/A'}")
    return 0

def predict_command(command: list[str]) -> int:
    """Predict command failure risk without executing it."""
    if not command:
        print("No command was provided. Example: sage predict -- pytest")
        return 2

    import subprocess
    from .ml import FailurePredictor

    command_text = subprocess.list2cmdline(command)
    will_fail, confidence, reason = FailurePredictor().predict(command_text)
    outcome = "likely to fail" if will_fail else "likely to succeed"

    print(f"Prediction: {outcome}")
    print(f"Confidence: {confidence:.0%}")
    print(f"Reason: {reason}")
    return 0

def ml_command(args) -> int:
    """Train and inspect ML models."""
    from .ml import SklearnFailureModel

    if not hasattr(args, "ml_command") or args.ml_command is None:
        print("Usage: sage ml <train|import-history|status>")
        return 1

    model = SklearnFailureModel()

    if args.ml_command == "train":
        from .ml.family_model import FamilyFailureModel

        # Use per-family models by default
        family_model = FamilyFailureModel()
        result = family_model.train_from_history(
            min_samples_per_family=max(20, args.min_samples // 2),
            fallback_min_samples=args.min_samples,
        )
        print("SAGE ML training (per-family models v4)")
        print(f"Trained: {result.trained}")
        print(f"Families trained: {len(result.families)}")
        for family, stats in sorted(result.families.items()):
            print(f"  {family:15} {stats['samples']:4} samples, {stats['failures']:3} failures, threshold={stats['threshold']:.2f}")
        print(f"Fallback model: {result.fallback_samples} samples, accuracy={result.fallback_accuracy:.3f}")
        print(f"Models dir: {result.model_paths.get('fallback', 'N/A')}")
        print(f"Message: {result.message}")
        return 0 if result.trained else 1

    if args.ml_command == "import-history":
        from .ml.history_importer import HistoryImporter

        paths = [Path(item) for item in args.path] if args.path else None
        result = HistoryImporter().import_history(
            source=args.source,
            paths=paths,
            limit=args.limit or None,
            dry_run=args.dry_run,
        )
        print("SAGE ML history import")
        print(f"Source: {result.source}")
        print(f"Dry run: {result.dry_run}")
        print(f"Scanned files: {result.scanned_files}")
        print(f"Scanned bytes: {result.scanned_bytes:,}")
        print(f"Found examples: {result.found_examples}")
        print(f"Inserted examples: {result.inserted_examples}")
        print(f"Skipped examples: {result.skipped_examples}")

        if args.train and not args.dry_run:
            train_result = model.train_from_history(target_samples=args.target_samples or None)
            print()
            print("SAGE ML training")
            print(f"Trained: {train_result.trained}")
            print(f"Model: {train_result.model_path}")
            print(f"Samples: {train_result.samples} ({train_result.positives} failed, {train_result.negatives} succeeded)")
            print(f"Model kind: {train_result.model_kind}")
            print(f"Accuracy: {train_result.accuracy:.3f}")
            print(f"Precision: {train_result.precision:.3f}")
            print(f"Recall: {train_result.recall:.3f}")
            print(f"ROC AUC: {train_result.roc_auc:.3f}" if train_result.roc_auc is not None else "ROC AUC: n/a")
            print(f"Message: {train_result.message}")
            return 0 if train_result.trained else 1

        return 0

    if args.ml_command == "status":
        from .ml.family_model import FamilyFailureModel

        # Check both family models (v4) and global model (v3)
        family_model = FamilyFailureModel()
        family_status = family_model.status()

        print("SAGE ML status")
        print(f"\nPer-family models (v4):")
        print(f"  Trained: {family_status['trained']}")
        print(f"  Models dir: {family_status['models_dir']}")
        if family_status["trained"]:
            print(f"  Families:")
            for family, info in sorted(family_status.get("families", {}).items()):
                print(f"    {family:15} {info['samples']:4} samples, {info['failures']:3} failures, threshold={info['threshold']:.2f}")
            fallback = family_status.get("fallback")
            if fallback:
                print(f"  Fallback model: {fallback['samples']} samples, {fallback['failures']} failures, threshold={fallback['threshold']:.2f}")

        status = model.status()
        print(f"\nGlobal ensemble model (v3 - legacy):")
        print(f"  Trained: {status['trained']}")
        print(f"  Model: {status['model_path']}")
        if status["trained"]:
            metrics = status.get("metrics", {})
            with connect() as conn:
                imported = conn.execute("SELECT COUNT(*) FROM ml_training_examples").fetchone()[0]
            print(f"  Trained at: {status.get('trained_at')}")
            print(f"  History samples: {status.get('history_samples', 0)}")
            print(f"  Imported examples: {imported}")
            print(f"  Training samples: {status.get('training_samples', 0)}")
            print(f"  Model kind: {status.get('model_kind', 'unknown')}")
            print(f"  Accuracy: {metrics.get('accuracy', 0):.3f}")
            print(f"  Precision: {metrics.get('precision', 0):.3f}")
            print(f"  Recall: {metrics.get('recall', 0):.3f}")
            roc_auc = metrics.get("roc_auc")
            print(f"  ROC AUC: {roc_auc:.3f}" if roc_auc is not None else "ROC AUC: n/a")
            print(f"  Features: {len(status.get('features', []))}")
        return 0

    if args.ml_command == "validate":
        # Support both family models (v4) and global model (v3)
        if getattr(args, "family_models", False):
            from .ml.family_validation import validate_family_models, write_family_validation_report

            report = validate_family_models(test_fraction=args.test_fraction)
            path = write_family_validation_report(report, getattr(args, "output", None))

            if args.format == "json":
                print(json.dumps(report, indent=2, ensure_ascii=False))
                return 0 if report.get("validated") else 1

            print("SAGE ML family models temporal validation (v4)")
            print(f"Report: {path}")
            print(f"Validated: {report.get('validated')}")
            print(f"Samples: {report['samples']} real (dropped {report['dropped_duplicates']} duplicates)")
            print(f"Families: {report['families_count']}")
            print(f"Dataset hash: {report['dataset_hash'][:16]}...")

            if report.get("validated"):
                agg = report.get("aggregate_metrics", {})
                print(f"\nAggregate metrics across {len(report['families'])} families:")
                print(f"  Test samples: {agg.get('test_samples', 0)}")
                print(f"  Failures: {agg.get('failures', 0)}")
                print(f"  Accuracy:  {agg.get('accuracy', 0):.3f}")
                print(f"  Precision: {agg.get('precision', 0):.3f}")
                print(f"  Recall:    {agg.get('recall', 0):.3f}")
                print(f"  F1:        {agg.get('f1', 0):.3f}")

                print(f"\nTop 10 families by test samples:")
                families = report.get("families", {})
                sorted_families = sorted(families.items(), key=lambda x: x[1]["test_samples"], reverse=True)[:10]
                for family, metrics in sorted_families:
                    print(f"  {family:15} test={metrics['test_samples']:3}, acc={metrics['accuracy']:.3f}, f1={metrics['f1']:.3f}, auc={metrics['roc_auc']:.3f}")
            else:
                print(f"Message: {report.get('message')}")
            return 0 if report.get("validated") else 1
        else:
            from .ml.validation import validate_temporal, write_validation_report

            report = validate_temporal(test_fraction=args.test_fraction)
            path = write_validation_report(report, getattr(args, "output", None))

            if args.format == "json":
                print(json.dumps(report, indent=2, ensure_ascii=False))
                return 0 if report.get("validated") else 1

            print("SAGE ML temporal validation (global model v3)")
            print(f"Report: {path}")
            print(f"Validated: {report.get('validated')}")
            print(f"Samples: {report['samples']} real (dropped {report['dropped_duplicates']} duplicates, {report['label_conflicts']} label conflicts)")
            print(f"Provenance: {report['provenance']['local_run']} local runs, {report['provenance']['imported']} imported")
            print(f"Synthetic samples: {report['synthetic_samples']}")
            print(f"Dataset hash: {report['dataset_hash'][:16]}...")
            if report.get("validated"):
                train, test, metrics = report["train"], report["test"], report["metrics"]
                print(f"Train: {train['samples']} samples ({train['failures']} failures) {train['from']} -> {train['to']}")
                print(f"Test:  {test['samples']} samples ({test['failures']} failures) {test['from']} -> {test['to']}")
                print(f"Accuracy:  {metrics['accuracy']:.3f}")
                print(f"Precision: {metrics['precision']:.3f}")
                print(f"Recall:    {metrics['recall']:.3f}")
                print(f"ROC AUC:   {metrics['roc_auc']:.3f}")
            else:
                print(f"Message: {report.get('message')}")
            return 0 if report.get("validated") else 1

    return 1

def doctor() -> int:
    from .security import load_policy, policy_path

    print("S.A.G.E doctor")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Database: {db_path()}")
    try:
        with connect() as conn:
            run_count = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"Database runs: {run_count}")
        print(f"Database integrity: {integrity}")
    except Exception as exc:
        print(f"Database integrity: error - {exc}")

    policy = load_policy()
    print(f"Security policy: {policy_path()}")
    print(f"Policy mode: {policy.get('mode')}")
    print(f"Redaction strictness: {policy.get('redaction_strictness')}")
    print(f"Retention days: {policy.get('retain_raw_days')}")
    print(f"Encryption at rest: {policy.get('encryption_at_rest')}")

    for name in ["python", "git", "node", "npm", "claude", "codex", "gh"]:
        found = shutil.which(name)
        print(f"{name}: {found or 'not found'}")

    try:
        import tiktoken  # noqa: F401

        print("tiktoken: available")
    except Exception:
        print("tiktoken: not found")
    return 0

def stats_command() -> int:
    """Show a compact SAGE operating summary."""
    from .ml import SklearnFailureModel

    with connect() as conn:
        runs = conn.execute(
            "SELECT COUNT(*), SUM(CASE WHEN exit_code = 0 THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN exit_code != 0 THEN 1 ELSE 0 END) FROM runs"
        ).fetchone()
        compression = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(original_tokens),0), "
            "COALESCE(SUM(compressed_tokens),0), COALESCE(SUM(saved_tokens),0) "
            "FROM context_compression"
        ).fetchone()
        agents = conn.execute("SELECT COUNT(*) FROM agent_tasks").fetchone()[0]
        redactions = conn.execute(
            "SELECT COALESCE(SUM(stdout_redactions + stderr_redactions + summary_redactions),0) FROM runs"
        ).fetchone()[0]
    original = int(compression[1] or 0)
    saved = int(compression[3] or 0)
    rate = (saved / original * 100) if original else 0.0
    print("SAGE stats")
    print(f"Runs: {runs[0]} ({runs[1] or 0} succeeded, {runs[2] or 0} failed)")
    print(f"Context rows: {compression[0]}")
    print(f"Original tokens: {original:,}")
    print(f"Compressed tokens: {int(compression[2] or 0):,}")
    print(f"Saved tokens: {saved:,} ({rate:.1f}%)")
    print(f"Agent tasks: {agents:,}")
    print(f"Redactions applied: {int(redactions or 0):,}")
    status = SklearnFailureModel().status()
    print(f"ML trained: {status['trained']}")
    if status["trained"]:
        metrics = status.get("metrics", {})
        print(f"ML accuracy: {metrics.get('accuracy', 0):.3f}")
        print(f"ML ROC AUC: {metrics.get('roc_auc', 0):.3f}")
    return 0


def _compression_totals() -> dict[str, int]:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS rows,
                COALESCE(SUM(original_tokens), 0) AS original,
                COALESCE(SUM(compressed_tokens), 0) AS compressed,
                COALESCE(SUM(saved_tokens), 0) AS saved
            FROM context_compression
            """
        ).fetchone()
    return {
        "rows": int(row["rows"] or 0),
        "original": int(row["original"] or 0),
        "compressed": int(row["compressed"] or 0),
        "saved": int(row["saved"] or 0),
    }


def savings_command(args) -> int:
    agent = args.agent
    if agent not in SAVINGS_PROFILES:
        print(f"Unknown agent/provider: {agent}")
        print("Available: " + ", ".join(sorted(SAVINGS_PROFILES)))
        return 1
    totals = _compression_totals()
    profile = SAVINGS_PROFILES[agent]
    input_rate = float(profile.get("input_rate_per_million", 0) or 0)
    dollars_saved = estimate_savings_usd(totals["saved"], agent)
    rate = (totals["saved"] / totals["original"] * 100) if totals["original"] else 0.0
    payload = {
        "agent": agent,
        "label": profile["label"],
        "provider": profile["provider"],
        "input_rate_per_million": input_rate,
        "rows": totals["rows"],
        "original_tokens": totals["original"],
        "compressed_tokens": totals["compressed"],
        "saved_tokens": totals["saved"],
        "compression_rate": round(rate, 2),
        "estimated_savings_usd": dollars_saved,
        "savings_by_agent": build_agent_savings(totals["saved"]),
    }
    if args.format == "json":
        print(json.dumps(payload, indent=2))
        return 0
    print(f"SAGE savings estimate ({profile['label']})")
    print(f"Original tokens: {payload['original_tokens']:,}")
    print(f"Compressed tokens: {payload['compressed_tokens']:,}")
    print(f"Saved tokens: {payload['saved_tokens']:,} ({payload['compression_rate']:.1f}%)")
    print(f"Reference input rate: ${input_rate:.4f}/M tokens")
    print(f"Estimated savings: ${payload['estimated_savings_usd']:.4f}")
    return 0


def firewall_command(args) -> int:
    from .security import load_policy, policy_path, save_policy

    if not hasattr(args, "firewall_command") or args.firewall_command is None:
        print("Usage: sage firewall <status|enable|disable|rules|allow|block|audit>")
        return 1

    policy = load_policy()

    if args.firewall_command == "status":
        print("SAGE firewall status")
        print(f"Policy file: {policy_path()}")
        print(f"Mode: {policy.get('mode')}")
        print(f"Deny rules: {len(policy.get('denylist', []))}")
        print(f"Confirm rules: {len(policy.get('confirm_required', []))}")
        print(f"Allow rules: {len(policy.get('allowlist', []))}")
        return 0

    if args.firewall_command == "enable":
        policy["mode"] = "company"
        save_policy(policy)
        print("SAGE firewall enabled in strict mode.")
        return 0

    if args.firewall_command == "disable":
        policy["mode"] = "personal"
        save_policy(policy)
        print("SAGE firewall set to personal warning mode.")
        return 0

    if args.firewall_command == "rules":
        if getattr(args, "firewall_rules_command", None) != "list":
            print("Usage: sage firewall rules list")
            return 1
        print("SAGE firewall rules")
        for label, key in (("Allow", "allowlist"), ("Block", "denylist"), ("Confirm", "confirm_required")):
            print(f"{label}:")
            values = list(policy.get(key, []) or [])
            if not values:
                print("  - (none)")
            for item in values:
                print(f"  - {item}")
        return 0

    if args.firewall_command == "allow":
        allowlist = list(policy.get("allowlist", []) or [])
        if args.pattern not in allowlist:
            allowlist.append(args.pattern)
        policy["allowlist"] = allowlist
        save_policy(policy)
        print(f"Allowed command pattern: {args.pattern}")
        return 0

    if args.firewall_command == "block":
        denylist = list(policy.get("denylist", []) or [])
        if args.pattern not in denylist:
            denylist.append(args.pattern)
        policy["denylist"] = denylist
        save_policy(policy)
        print(f"Blocked command pattern: {args.pattern}")
        return 0

    if args.firewall_command == "audit":
        with connect() as conn:
            decisions = conn.execute(
                "SELECT policy_decision, COUNT(*) AS count FROM runs GROUP BY policy_decision ORDER BY count DESC"
            ).fetchall()
            redactions = conn.execute(
                "SELECT COALESCE(SUM(stdout_redactions + stderr_redactions + summary_redactions), 0) FROM runs"
            ).fetchone()[0]
            blocked = conn.execute("SELECT COUNT(*) FROM runs WHERE policy_decision = 'blocked'").fetchone()[0]
        print("SAGE firewall audit")
        print(f"Blocked runs: {int(blocked or 0):,}")
        print(f"Redactions applied: {int(redactions or 0):,}")
        print("Policy decisions:")
        if not decisions:
            print("  - (none)")
        for row in decisions:
            print(f"  - {row['policy_decision']}: {row['count']}")
        return 0

    return 1


def github_bot_command(args) -> int:
    if not hasattr(args, "github_bot_command") or args.github_bot_command is None:
        print("Usage: sage github-bot <comment>")
        return 1

    if args.github_bot_command == "comment":
        body = _render_github_bot_comment(kind=args.kind, run_id=args.run_id)
        if args.output:
            Path(args.output).write_text(body, encoding="utf-8")
            print(f"GitHub bot comment written: {args.output}")
        else:
            print(body)
        return 0

    return 1


def _render_github_bot_comment(*, kind: str, run_id: int | None = None) -> str:
    if run_id is None:
        record = latest_run()
        if record is None:
            return "### SAGE Bot\n\nNo local SAGE runs are available yet."
        run_id = record.id

    with connect() as conn:
        row = conn.execute(
            """
            SELECT id, created_at, project, command, exit_code, duration_ms, summary,
                   stdout_redactions, stderr_redactions, summary_redactions,
                   policy_decision, policy_reason
            FROM runs
            WHERE id = ?
            """,
            (run_id,),
        ).fetchone()
        compression = conn.execute(
            """
            SELECT original_tokens, compressed_tokens, saved_tokens, strategy
            FROM context_compression
            WHERE run_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (run_id,),
        ).fetchone()

    if not row:
        return f"### SAGE Bot\n\nRun `{run_id}` was not found in local SAGE history."

    title = "SAGE CI Failure Summary" if kind == "ci-failure" else "SAGE Run Summary"
    status = "passed" if int(row["exit_code"]) == 0 else "failed"
    redactions = int(row["stdout_redactions"] or 0) + int(row["stderr_redactions"] or 0) + int(row["summary_redactions"] or 0)
    lines = [
        f"### {title}",
        "",
        f"- Run: `#{row['id']}`",
        f"- Status: `{status}` (exit `{row['exit_code']}`)",
        f"- Duration: `{row['duration_ms']}ms`",
        f"- Policy: `{row['policy_decision']}`",
        f"- Redactions applied: `{redactions}`",
    ]
    if compression:
        original = int(compression["original_tokens"] or 0)
        saved = int(compression["saved_tokens"] or 0)
        rate = (saved / original * 100) if original else 0.0
        lines.extend(
            [
                f"- Tokens: `{original:,}` -> `{int(compression['compressed_tokens'] or 0):,}`",
                f"- Saved: `{saved:,}` tokens (`{rate:.1f}%`)",
            ]
        )
    lines.extend(
        [
            "",
            "**Command**",
            "",
            f"`{str(row['command'])[:180]}`",
            "",
            "**SAGE summary**",
            "",
            str(row["summary"] or "(no summary)").strip()[:1000],
            "",
            "_Raw logs remain local. This comment contains aggregate proof and redacted summary data only._",
        ]
    )
    if row["policy_reason"]:
        lines.insert(7, f"- Policy reason: `{row['policy_reason']}`")
    return "\n".join(lines)


def fix_command(apply: bool = False, min_confidence: float = 0.8) -> int:
    """Auto-fix the most recent error."""
    record = latest_run(only_failures=True)
    if record is None:
        print("No failed commands in history.")
        return 0

    print(f"Analyzing run #{record.id}: {record.command}")
    print()

    # Get full output from database
    with connect() as conn:
        row = conn.execute(
            "SELECT stdout, stderr FROM runs WHERE id = ?", (record.id,)
        ).fetchone()
        if not row:
            print("Could not retrieve command output.")
            return 1

    engine = AutoFixEngine()
    result = engine.analyze_and_fix(
        stdout=row["stdout"],
        stderr=row["stderr"],
        exit_code=record.exit_code,
        command=record.command,
        apply=apply,
        min_confidence=min_confidence,
    )

    print(f"Confidence: {result.confidence:.0%}")
    if result.fix_applied:
        print(f"Suggested fix: {result.fix_applied}")

    if result.success:
        print("\n[OK] Fix applied successfully!")
    elif result.error_message:
        print(f"\n{result.error_message}")

    if not apply and result.fix_applied:
        print("\nRun 'sage fix --apply' to apply this fix.")

    return 0 if result.success else 1

def agents_command(args) -> int:
    """Manage AI agents."""
    from .agents import list_agents, get_agent_status

    if not hasattr(args, "agents_command") or args.agents_command is None:
        print("Usage: sage agents <list|status>")
        return 1

    if args.agents_command == "list":
        agents = list_agents()
        if not agents:
            print("No agents running.")
            return 0

        for agent in agents:
            print(f"#{agent.id} [{agent.type}] {agent.name} - {agent.status}")
        return 0

    if args.agents_command == "status":
        status = get_agent_status()
        print(f"Total agents: {status['total']}")
        print(f"Active agents: {status['active']}")
        print(f"Idle agents: {status['idle']}")
        print(f"Total tasks: {status['total_tasks']}")
        return 0

    if args.agents_command == "tasks":
        from .agents import get_agent_tasks_for_run

        run_id = args.run_id
        if run_id is None:
            record = latest_run()
            if record is None:
                print("No command history yet.")
                return 0
            run_id = record.id

        tasks = get_agent_tasks_for_run(run_id)
        if not tasks:
            print(f"No agent tasks found for run #{run_id}.")
            return 0

        print(f"Agent tasks for run #{run_id}:")
        for task in tasks:
            result = task["result"]
            finding = result.get("finding", "completed")
            next_step = result.get("next_step", "")
            print(f"- #{task['id']} {task['agent_name']} [{task['agent_type']}] {task['status']}")
            print(f"  Severity: {result.get('severity', 'n/a')} | Confidence: {result.get('confidence', 0):.0%}")
            print(f"  Finding: {finding}")
            if next_step:
                print(f"  Next: {next_step}")
            actions = result.get("actions") or []
            for action in actions[:3]:
                print(f"  Action: {action}")
        return 0

    if args.agents_command == "runs":
        from .agents import get_agent_runs_for_run

        run_id = args.run_id
        if run_id is None:
            record = latest_run()
            if record is None:
                print("No command history yet.")
                return 0
            run_id = record.id
        rows = get_agent_runs_for_run(run_id)
        if not rows:
            print(f"No agent run records found for run #{run_id}.")
            return 0
        print(f"Agent runs for run #{run_id}:")
        for row in rows:
            print(
                f"- #{row['id']} {row.get('agent_name')} [{row.get('agent_type')}] "
                f"status={row['status']} attempts={row['attempts']} confidence={float(row['confidence'] or 0):.0%}"
            )
            if row.get("output_artifact_path"):
                print(f"  Artifact: {row['output_artifact_path']}")
            if row.get("error"):
                print(f"  Error: {row['error']}")
        return 0

    if args.agents_command == "worker":
        from .agents import run_agent_worker_once

        results = run_agent_worker_once(run_id=args.run_id, max_workers=args.max_workers)
        print(f"Processed agent runs: {len(results)}")
        for result in results:
            print(
                f"- {result.get('agent', 'agent')} [{result.get('agent_type', 'unknown')}] "
                f"{result.get('severity', 'info')} {float(result.get('confidence', 0)):.0%}: {result.get('finding')}"
            )
        return 0

    if args.agents_command == "cancel":
        from .agents import cancel_agent_runs

        count = cancel_agent_runs(run_id=args.run_id)
        print(f"Cancelled agent runs: {count}")
        return 0

    if args.agents_command == "report":
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT a.name, a.type, a.status, COUNT(t.id) as task_count, MAX(t.completed_at) as last_done,
                       COALESCE(SUM(CASE WHEN ar.status = 'completed' THEN 1 ELSE 0 END), 0) as completed_runs,
                       COALESCE(SUM(CASE WHEN ar.status = 'failed' THEN 1 ELSE 0 END), 0) as failed_runs
                FROM agents a
                LEFT JOIN agent_tasks t ON t.agent_id = a.id
                LEFT JOIN agent_runs ar ON ar.agent_id = a.id
                GROUP BY a.id
                ORDER BY task_count DESC, a.name ASC
                """
            ).fetchall()
        print("SAGE agent report")
        for row in rows:
            print(
                f"- {row['name']} [{row['type']}] status={row['status']} "
                f"tasks={row['task_count']} completed_runs={row['completed_runs']} failed_runs={row['failed_runs']} "
                f"last={row['last_done'] or 'n/a'}"
            )
        return 0

    if args.agents_command == "eval":
        from .agents.evaluation import evaluate_agents, write_eval_report

        agent_types = {args.agent_type} if getattr(args, "agent_type", None) else None
        report = evaluate_agents(agent_types=agent_types)

        if getattr(args, "output", None):
            path = write_eval_report(report, args.output)
            print(f"Wrote agent eval report: {path}")

        if args.format == "json":
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 0

        print(f"SAGE agent evaluation ({report['harness_version']})")
        print(f"Scenarios: {report['scenario_count']} | Overall score: {report['overall_score']:.0%}")
        print(f"Dimensions: {', '.join(report['dimensions'])}")
        for agent_type, data in report["agents"].items():
            print(f"- {agent_type}: score={data['score']:.0%} scenarios={data['scenarios']}")
            for failed in data["failed_checks"]:
                print(f"  failed: {failed}")
        return 0

    return 1

def privacy_command(args) -> int:
    """Privacy, redaction, retention, and audit commands."""
    from .security import load_policy, policy_path

    if not hasattr(args, "privacy_command") or args.privacy_command is None:
        print("Usage: sage privacy <report|set|export-audit|purge-raw>")
        return 1

    if args.privacy_command == "set":
        from . import telemetry

        names_to_levels = {name: level for level, name in telemetry.LEVEL_NAMES.items()}
        level = int(args.level) if args.level.isdigit() else names_to_levels[args.level]
        effective = telemetry.set_level(level)
        print(f"Telemetry level set to {level} ({telemetry.LEVEL_NAMES[level]}).")
        if effective != level:
            print(f"Effective level is {effective} ({telemetry.LEVEL_NAMES[effective]}) — a stricter account/org policy applies.")
        return 0

    if args.privacy_command == "report":
        policy = load_policy()
        with connect() as conn:
            runs = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
            redactions = conn.execute(
                "SELECT COALESCE(SUM(stdout_redactions + stderr_redactions + summary_redactions),0) FROM runs"
            ).fetchone()[0]
            retained = conn.execute("SELECT COUNT(*) FROM runs WHERE raw_retained = 1").fetchone()[0]
            policy_rows = conn.execute(
                "SELECT policy_decision, COUNT(*) FROM runs GROUP BY policy_decision ORDER BY COUNT(*) DESC"
            ).fetchall()
        print("SAGE privacy report")
        print(f"Policy file: {policy_path()}")
        print(f"Mode: {policy.get('mode')}")
        print(f"Redaction strictness: {policy.get('redaction_strictness')}")
        print(f"Raw retention days: {policy.get('retain_raw_days')}")
        print(f"Encryption at rest: {policy.get('encryption_at_rest')}")
        print(f"Runs stored: {runs}")
        print(f"Runs retaining raw output: {retained}")
        print(f"Redactions applied: {int(redactions or 0)}")
        print("Policy decisions:")
        for row in policy_rows:
            print(f"- {row[0]}: {row[1]}")
        return 0

    if args.privacy_command == "export-audit":
        output = Path(args.output) if args.output else Path.cwd() / "sage-audit-export.json"
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT id, created_at, project, command_sha256, exit_code, duration_ms, summary,
                       stdout_redactions, stderr_redactions, summary_redactions,
                       policy_mode, policy_decision, policy_reason, raw_retained
                FROM runs
                ORDER BY id ASC
                """
            ).fetchall()
        payload = {
            "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": "SAGE local audit export",
            "runs": [dict(row) for row in rows],
        }
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Audit export written: {output}")
        print(f"Runs exported: {len(rows)}")
        return 0

    if args.privacy_command == "purge-raw":
        cutoff_days = max(0, int(args.days))
        sql = """
            SELECT id FROM runs
            WHERE raw_retained = 1
              AND datetime(created_at) <= datetime('now', ?)
        """
        modifier = f"-{cutoff_days} days"
        with connect() as conn:
            ids = [int(row[0]) for row in conn.execute(sql, (modifier,)).fetchall()]
            if args.apply and ids:
                conn.executemany(
                    "UPDATE runs SET stdout = '', stderr = '', raw_retained = 0 WHERE id = ?",
                    [(run_id,) for run_id in ids],
                )
                conn.commit()
        action = "Purged" if args.apply else "Would purge"
        print(f"{action} raw output for {len(ids)} run(s) older than {cutoff_days} day(s).")
        if not args.apply:
            print("Run with --apply to write changes.")
        return 0

    return 1

def redact_command(*, limit: int = 0, apply: bool = False) -> int:
    """Scan stored runs and optionally redact legacy output."""
    from .security import load_policy, redact_text

    strictness = str(load_policy().get("redaction_strictness") or "standard")
    sql = "SELECT id, stdout, stderr, summary FROM runs ORDER BY id DESC"
    params: tuple = ()
    if limit and limit > 0:
        sql += " LIMIT ?"
        params = (limit,)

    changed: list[tuple[str, str, str, int, int, int, int]] = []
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
        for row in rows:
            out = redact_text(row["stdout"], strictness=strictness)
            err = redact_text(row["stderr"], strictness=strictness)
            summary = redact_text(row["summary"], strictness=strictness)
            total = out.count + err.count + summary.count
            if total:
                changed.append((out.text, err.text, summary.text, out.count, err.count, summary.count, int(row["id"])))
        if apply and changed:
            conn.executemany(
                """
                UPDATE runs
                SET stdout = ?, stderr = ?, summary = ?,
                    stdout_redactions = stdout_redactions + ?,
                    stderr_redactions = stderr_redactions + ?,
                    summary_redactions = summary_redactions + ?
                WHERE id = ?
                """,
                changed,
            )
            conn.commit()

    print(f"Scanned runs: {len(rows)}")
    print(f"Runs with redactions: {len(changed)}")
    print(f"Redactions found: {sum(item[3] + item[4] + item[5] for item in changed)}")
    if apply:
        print("Database updated.")
    else:
        print("Dry run only. Run with --apply to write changes.")
    return 0

def workflow_command(args) -> int:
    """Manage workflows."""
    import asyncio
    from .workflows import WorkflowParser, WorkflowExecutor

    if not hasattr(args, "workflow_command") or args.workflow_command is None:
        print("Usage: sage workflow <run|list>")
        return 1

    if args.workflow_command == "run":
        workflow_path = Path(args.name)
        if not workflow_path.exists():
            # Try templates
            template_path = Path(__file__).parent / "workflows" / "templates" / f"{args.name}.yml"
            if template_path.exists():
                workflow_path = template_path
            else:
                print(f"Workflow not found: {args.name}")
                return 1

        parser = WorkflowParser()
        try:
            workflow = parser.parse_file(workflow_path)
            errors = parser.validate(workflow)
            if errors:
                print("Workflow validation errors:")
                for error in errors:
                    print(f"  - {error}")
                return 1

            executor = WorkflowExecutor()
            success = asyncio.run(executor.execute(workflow))
            return 0 if success else 1

        except Exception as e:
            print(f"Error: {e}")
            return 1

    if args.workflow_command == "list":
        template_dir = Path(__file__).parent / "workflows" / "templates"
        if template_dir.exists():
            templates = list(template_dir.glob("*.yml"))
            if templates:
                print("Available workflows:")
                for t in templates:
                    print(f"  - {t.stem}")
            else:
                print("No workflow templates found.")
        return 0

    return 1

def dashboard_command(args) -> int:
    """Manage dashboard."""
    from .dashboard import DashboardServer

    if not hasattr(args, "dashboard_command") or args.dashboard_command is None:
        print("Usage: sage dashboard <start|stop>")
        return 1

    if args.dashboard_command == "start":
        try:
            server = DashboardServer(port=args.port)
            server.start(open_browser=not args.no_browser)
            return 0
        except ImportError as e:
            print(f"Error: {e}")
            print("Install dependencies: pip install fastapi uvicorn[standard]")
            return 1

    if args.dashboard_command == "stop":
        print("Dashboard stop not implemented (use Ctrl+C)")
        return 0

    return 1

def mcp_command(args) -> int:
    """Manage MCP server."""
    import json
    import os

    if not hasattr(args, "mcp_command") or args.mcp_command is None:
        print("Usage: sage mcp <install|start>")
        return 1

    if args.mcp_command == "install":
        # Default to the local MCP client config path. Override with
        # SAGE_MCP_CONFIG_PATH when a different location is needed.
        config_path = Path(os.getenv("SAGE_MCP_CONFIG_PATH", str(Path.home() / ".claude" / "mcp-servers.json")))
        config_path.parent.mkdir(parents=True, exist_ok=True)

        sage_config = {
            "sage": {
                "command": "python",
                "args": ["-m", "sage.mcp.server"],
                "description": (
                    "Smart Agent Guidance Engine. Local command execution is disabled by default; "
                    "set SAGE_MCP_ENABLE_COMMANDS=1 only for trusted local MCP clients."
                )
            }
        }

        if config_path.exists():
            with open(config_path, 'r') as f:
                existing = json.load(f)
            existing.update(sage_config)
            sage_config = existing

        with open(config_path, 'w') as f:
            json.dump(sage_config, f, indent=2)

        print(f"[OK] MCP server config installed to {config_path}")
        print("Restart your MCP-compatible client to use SAGE tools.")
        return 0

    if args.mcp_command == "start":
        from .mcp.server import main
        main()
        return 0

    return 1

def context_command(args) -> int:
    """Manage context and token usage."""
    from .context import ContextManager

    if not hasattr(args, "context_command") or args.context_command is None:
        print("Usage: sage context <stats|optimize|report|snapshot|benchmark>")
        return 1

    context_mgr = ContextManager()

    if args.context_command == "stats":
        stats = context_mgr.get_token_stats()

        print("\n=== Token Usage Statistics ===")
        print(f"Total commands: {stats['total_commands']}")
        print(f"Estimated tokens: {stats['total_estimated']:,}")
        print(f"Compressed tokens: {stats['total_compressed']:,}")
        print(f"Tokens saved: {stats['total_savings']:,}")
        print(f"Compression rate: {stats['savings_percent']:.1f}%")
        print()

        if stats['total_savings'] > 0:
            # Rough cost calculation (at $3/million input tokens)
            dollars_saved = (stats['total_savings'] / 1_000_000) * 3
            print(f"Estimated cost savings: ${dollars_saved:.4f}")

        return 0

    if args.context_command == "optimize":
        # Get last command output
        record = latest_run()
        if not record:
            print("No commands in history.")
            return 0

        with connect() as conn:
            row = conn.execute(
                "SELECT stdout, stderr FROM runs WHERE id = ?", (record.id,)
            ).fetchone()
            if not row:
                return 1

        combined = f"{row['stdout']}\n{row['stderr']}"
        suggestions = context_mgr.suggest_context_optimizations(combined)

        if suggestions:
            print(f"\nOptimization suggestions for run #{record.id}:")
            for i, suggestion in enumerate(suggestions, 1):
                print(f"{i}. {suggestion}")
        else:
            print(f"Run #{record.id} output is already optimized!")

        return 0

    if args.context_command == "report":
        return context_report_command(format_name=args.format, output=args.output)

    if args.context_command == "snapshot":
        return context_snapshot_command(month=args.month)

    if args.context_command == "benchmark":
        sizes = [int(item.strip()) for item in str(args.sizes).split(",") if item.strip()]
        return context_benchmark_command(sizes=sizes, format_name=args.format, output=args.output)

    return 1

def _compression_report_payload() -> dict:
    from statistics import median
    from .context.tokens import is_real_tokenizer

    with connect() as conn:
        totals = conn.execute(
            """
            SELECT COUNT(*) as rows,
                   COALESCE(SUM(original_tokens), 0) as original,
                   COALESCE(SUM(compressed_tokens), 0) as compressed,
                   COALESCE(SUM(saved_tokens), 0) as saved
            FROM context_compression
            """
        ).fetchone()
        ratios = [
            (float(row["saved_tokens"]) / float(row["original_tokens"]) * 100)
            for row in conn.execute(
                "SELECT original_tokens, saved_tokens FROM context_compression WHERE original_tokens > 0"
            ).fetchall()
        ]
        strategies = conn.execute(
            """
            SELECT strategy,
                   COUNT(*) as rows,
                   COALESCE(SUM(original_tokens), 0) as original,
                   COALESCE(SUM(compressed_tokens), 0) as compressed,
                   COALESCE(SUM(saved_tokens), 0) as saved
            FROM context_compression_strategies
            GROUP BY strategy
            ORDER BY saved DESC
            """
        ).fetchall()
        noisy = conn.execute(
            """
            SELECT cc.run_id, r.command, cc.original_tokens, cc.compressed_tokens, cc.saved_tokens, cc.strategy
            FROM context_compression cc
            LEFT JOIN runs r ON r.id = cc.run_id
            ORDER BY cc.saved_tokens DESC
            LIMIT 10
            """
        ).fetchall()

    original = int(totals["original"] or 0)
    saved = int(totals["saved"] or 0)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "verified_tokenizer": "tiktoken" if is_real_tokenizer() else "fallback",
        "rows": int(totals["rows"] or 0),
        "original_tokens": original,
        "compressed_tokens": int(totals["compressed"] or 0),
        "saved_tokens": saved,
        "compression_rate": (saved / original * 100) if original else 0.0,
        "median_compression": median(ratios) if ratios else 0.0,
        "strategies": [dict(row) for row in strategies],
        "top_noisy_commands": [dict(row) for row in noisy],
    }

def context_report_command(*, format_name: str = "text", output: str = "") -> int:
    payload = _compression_report_payload()
    if format_name == "json":
        rendered = json.dumps(payload, indent=2)
    elif format_name == "md":
        rendered = _render_context_report_md(payload)
    else:
        rendered = _render_context_report_text(payload)

    if output:
        Path(output).write_text(rendered, encoding="utf-8")
        print(f"Context report written: {output}")
    else:
        print(rendered)
    return 0

def context_snapshot_command(*, month: str = "") -> int:
    from statistics import median
    from .context.tokens import is_real_tokenizer

    month = month or datetime.now(timezone.utc).strftime("%Y-%m")
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT original_tokens, compressed_tokens, saved_tokens
            FROM context_compression
            WHERE substr(created_at, 1, 7) = ?
            """,
            (month,),
        ).fetchall()
        ratios = [(row["saved_tokens"] / row["original_tokens"] * 100) for row in rows if row["original_tokens"]]
        original = sum(int(row["original_tokens"] or 0) for row in rows)
        compressed = sum(int(row["compressed_tokens"] or 0) for row in rows)
        saved = sum(int(row["saved_tokens"] or 0) for row in rows)
        conn.execute(
            """
            INSERT INTO context_monthly_snapshots
            (month, created_at, total_runs, original_tokens, compressed_tokens, saved_tokens, median_compression, verified_tokenizer)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(month) DO UPDATE SET
                created_at = excluded.created_at,
                total_runs = excluded.total_runs,
                original_tokens = excluded.original_tokens,
                compressed_tokens = excluded.compressed_tokens,
                saved_tokens = excluded.saved_tokens,
                median_compression = excluded.median_compression,
                verified_tokenizer = excluded.verified_tokenizer
            """,
            (
                month,
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                len(rows),
                original,
                compressed,
                saved,
                median(ratios) if ratios else 0.0,
                "tiktoken" if is_real_tokenizer() else "fallback",
            ),
        )
        conn.commit()
    print(f"Snapshot saved for {month}: runs={len(rows)} saved={saved:,} median={median(ratios) if ratios else 0.0:.1f}%")
    return 0

def context_benchmark_command(*, sizes: list[int], format_name: str = "text", output: str = "") -> int:
    from .context.benchmarks import run_benchmarks
    from .context.tokens import is_real_tokenizer

    results = run_benchmarks(sizes)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "verified_tokenizer": "tiktoken" if is_real_tokenizer() else "fallback",
        "benchmarks": [result.__dict__ for result in results],
    }
    if format_name == "json":
        rendered = json.dumps(payload, indent=2)
    elif format_name == "md":
        lines = [
            "# SAGE Context Benchmark",
            "",
            f"- Verified tokenizer: `{payload['verified_tokenizer']}`",
            "",
            "| Target | Original | Compressed | Saved | Rate | Strategy |",
            "|---:|---:|---:|---:|---:|---|",
        ]
        for row in payload["benchmarks"]:
            lines.append(
                f"| {row['target_tokens']:,} | {row['original_tokens']:,} | {row['compressed_tokens']:,} | "
                f"{row['saved_tokens']:,} | {row['compression_rate']:.1f}% | {row['strategy']} |"
            )
        rendered = "\n".join(lines)
    else:
        lines = [f"SAGE context benchmark (verified tokenizer: {payload['verified_tokenizer']})"]
        for row in payload["benchmarks"]:
            lines.append(
                f"- target={row['target_tokens']:,} original={row['original_tokens']:,} "
                f"compressed={row['compressed_tokens']:,} saved={row['saved_tokens']:,} "
                f"rate={row['compression_rate']:.1f}% strategy={row['strategy']}"
            )
        rendered = "\n".join(lines)

    if output:
        Path(output).write_text(rendered, encoding="utf-8")
        print(f"Context benchmark written: {output}")
    else:
        print(rendered)
    return 0

def _render_context_report_text(payload: dict) -> str:
    lines = [
        "SAGE context compression report",
        f"Verified tokenizer: {payload['verified_tokenizer']}",
        f"Rows: {payload['rows']}",
        f"Original tokens: {payload['original_tokens']:,}",
        f"Compressed tokens: {payload['compressed_tokens']:,}",
        f"Saved tokens: {payload['saved_tokens']:,} ({payload['compression_rate']:.1f}%)",
        f"Median compression: {payload['median_compression']:.1f}%",
        "",
        "Strategies:",
    ]
    for row in payload["strategies"]:
        original = int(row["original"] or 0)
        saved = int(row["saved"] or 0)
        rate = (saved / original * 100) if original else 0.0
        lines.append(f"- {row['strategy']}: saved={saved:,} rate={rate:.1f}% rows={row['rows']}")
    lines.append("")
    lines.append("Top noisy commands:")
    for row in payload["top_noisy_commands"]:
        command = str(row.get("command") or "")[:100]
        lines.append(f"- run #{row['run_id']} saved={int(row['saved_tokens'] or 0):,} strategy={row.get('strategy')}: {command}")
    return "\n".join(lines)

def _render_context_report_md(payload: dict) -> str:
    lines = [
        "# SAGE Context Compression Report",
        "",
        f"- Verified tokenizer: `{payload['verified_tokenizer']}`",
        f"- Rows: `{payload['rows']}`",
        f"- Original tokens: `{payload['original_tokens']:,}`",
        f"- Compressed tokens: `{payload['compressed_tokens']:,}`",
        f"- Saved tokens: `{payload['saved_tokens']:,}` (`{payload['compression_rate']:.1f}%`)",
        f"- Median compression: `{payload['median_compression']:.1f}%`",
        "",
        "## Strategies",
        "",
        "| Strategy | Rows | Saved | Rate |",
        "|---|---:|---:|---:|",
    ]
    for row in payload["strategies"]:
        original = int(row["original"] or 0)
        saved = int(row["saved"] or 0)
        rate = (saved / original * 100) if original else 0.0
        lines.append(f"| {row['strategy']} | {row['rows']} | {saved:,} | {rate:.1f}% |")
    lines.extend(["", "## Top Noisy Commands", ""])
    for row in payload["top_noisy_commands"]:
        command = str(row.get("command") or "")[:140].replace("|", "\\|")
        lines.append(f"- Run `#{row['run_id']}` saved `{int(row['saved_tokens'] or 0):,}` tokens with `{row.get('strategy')}`: `{command}`")
    return "\n".join(lines)

def init_project() -> int:
    path = Path.cwd() / "SAGE.md"
    path.write_text(ASSISTANT_INSTRUCTIONS, encoding="utf-8")
    print(f"Created {path}")
    print("Tell local assistant or terminal agent: read SAGE.md before running terminal commands.")
    return 0

def gui_command() -> int:
    """Show GUI availability status."""
    print("SAGE GUI is in development and is not included in the public CLI repo yet.")
    print("It will be released later with AI agents and ML workflows.")
    print("\nFor now use:")
    print("   sage connect")
    print("   sage init")
    print("   sage run -- <command>")
    print("   sage context stats")
    return 0
