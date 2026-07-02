from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from . import __version__
from .runner import run_command
from .store import connect, db_path, latest_run, recent_runs
from .suggestions import suggest_next_steps
from .autofix import AutoFixEngine


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sage",
        description="Smart Agent Guidance Engine for developer automation tools.",
    )
    parser.add_argument("--version", action="version", version=f"sage {__version__}")

    sub = parser.add_subparsers(dest="command_name", required=True)

    run = sub.add_parser("run", help="Run a command and remember the important output.")
    run.add_argument("command", nargs=argparse.REMAINDER, help="Command to run after --")

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

    agents_parser = sub.add_parser("agents", help="Manage AI agents.")
    agents_sub = agents_parser.add_subparsers(dest="agents_command")
    agents_sub.add_parser("list", help="List all agents.")
    agents_sub.add_parser("status", help="Show agent status.")

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

    sub.add_parser("doctor", help="Check local setup.")
    sub.add_parser("init", help="Create S.A.G.E instructions for developer tools.")
    sub.add_parser("gui", help="Launch SAGE Desktop GUI.")

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
        return explain(only_failed=args.failed)

    if args.command_name == "suggest":
        return suggest(only_failed=args.failed)

    if args.command_name == "fix":
        return fix_command(apply=args.apply, min_confidence=args.confidence)

    if args.command_name == "agents":
        return agents_command(args)

    if args.command_name == "workflow":
        return workflow_command(args)

    if args.command_name == "dashboard":
        return dashboard_command(args)

    if args.command_name == "mcp":
        return mcp_command(args)

    if args.command_name == "context":
        return context_command(args)

    if args.command_name == "history":
        return history(args.limit)

    if args.command_name == "doctor":
        return doctor()

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
        print("\nâœ“ Fix applied successfully!")
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
        print(f"Active agents: {status['active']}")
        print(f"Idle agents: {status['idle']}")
        print(f"Total tasks: {status['total_tasks']}")
        return 0

    return 1


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
                "description": "Smart Agent Guidance Engine"
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
        print("Usage: sage context <stats|optimize>")
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

    return 1


def init_project() -> int:
    path = Path.cwd() / "SAGE.md"
    path.write_text(ASSISTANT_INSTRUCTIONS, encoding="utf-8")
    print(f"Created {path}")
    print("Tell local assistant or terminal agent: read SAGE.md before running terminal commands.")
    return 0


def gui_command() -> int:
    """Launch SAGE Desktop GUI."""
    try:
        from .gui.app import main
        main()
        return 0
    except ImportError as e:
        print(f"Error: {e}")
        print("Install GUI dependencies: pip install customtkinter pillow psutil")
        return 1

