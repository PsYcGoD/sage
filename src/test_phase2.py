"""Test SAGE v2.0 Phase 2 features: Workflows, Dashboard, MCP."""

import asyncio
import json
from pathlib import Path


def test_workflow_system():
    """Test workflow pipeline engine."""
    print("\n=== Testing Workflow System ===")
    
    from sage.workflows import WorkflowParser, WorkflowExecutor
    
    # Test parsing
    parser = WorkflowParser()
    
    test_workflow = {
        "name": "Test Workflow",
        "version": "1.0",
        "env": {"TEST": "true"},
        "variables": {"name": "test"},
        "pipeline": [
            {
                "name": "Step 1",
                "run": "echo Hello ${name}",
            },
            {
                "name": "Step 2",
                "run": "echo Step 2 complete",
            }
        ]
    }
    
    workflow = parser.parse_dict(test_workflow)
    print(f"Workflow: {workflow.name}")
    print(f"Steps: {len(workflow.pipeline)}")
    
    # Validate
    errors = parser.validate(workflow)
    if errors:
        print(f"Validation errors: {errors}")
    else:
        print("[OK] Validation passed")
    
    # Test templates
    template_dir = Path("src/sage/workflows/templates")
    if template_dir.exists():
        templates = list(template_dir.glob("*.yml"))
        print(f"Templates found: {len(templates)}")
        for t in templates:
            print(f"  - {t.stem}")


def test_dashboard_api():
    """Test dashboard API endpoints."""
    print("\n=== Testing Dashboard API ===")
    
    try:
        from sage.dashboard.api.commands import router as commands_router
        from sage.dashboard.api.metrics import router as metrics_router
        
        print("[OK] Dashboard modules imported")
        print("[OK] Commands router available")
        print("[OK] Metrics router available")
        
    except ImportError as e:
        print(f"[SKIP] Dashboard requires: pip install fastapi uvicorn[standard]")
        print(f"Error: {e}")


def test_mcp_tools():
    """Test MCP server tools."""
    print("\n=== Testing MCP Tools ===")
    
    from sage.mcp.tools import (
        SAGE_TOOLS,
        sage_run_command,
        sage_explain_error,
        sage_suggest_fix,
        sage_get_history,
    )
    
    print(f"MCP Tools defined: {len(SAGE_TOOLS)}")
    for tool in SAGE_TOOLS:
        print(f"  - {tool['name']}: {tool['description'][:50]}...")
    
    # Test history function
    print("\nTesting sage_get_history:")
    result = sage_get_history(limit=5)
    print(f"  Commands in history: {result['count']}")
    
    # Test MCP config
    config_path = Path(__file__).parent.parent / "sage-mcp.json"
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
        print(f"\n[OK] MCP config file exists")
        print(f"  Server name: {config['name']}")
        print(f"  Tools: {len(config['tools'])}")


def test_database_schema():
    """Test new database tables."""
    print("\n=== Testing Database Schema ===")
    
    from sage.store import connect
    
    with connect() as conn:
        # Check workflow_runs table
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='workflow_runs'"
        )
        if cursor.fetchone():
            print("[OK] workflow_runs table exists")
        else:
            print("[FAIL] workflow_runs table missing")
        
        # Check agents table
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='agents'"
        )
        if cursor.fetchone():
            print("[OK] agents table exists")
        else:
            print("[FAIL] agents table missing")
        
        # Check fixes table
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='fixes'"
        )
        if cursor.fetchone():
            print("[OK] fixes table exists")
        else:
            print("[FAIL] fixes table missing")


def test_cli_commands():
    """Test new CLI commands exist."""
    print("\n=== Testing CLI Commands ===")
    
    from sage.cli import build_parser
    
    parser = build_parser()
    
    # List all subcommands
    subparsers_actions = [
        action for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    ]
    
    expected_commands = ["workflow", "dashboard", "mcp", "agents", "fix"]
    
    for subparsers_action in subparsers_actions:
        for choice in subparsers_action.choices:
            if choice in expected_commands:
                print(f"[OK] Command '{choice}' available")


if __name__ == "__main__":
    import argparse
    
    print("SAGE V2.0 - Phase 2 Testing")
    print("=" * 50)
    
    test_workflow_system()
    test_dashboard_api()
    test_mcp_tools()
    test_database_schema()
    test_cli_commands()
    
    print("\n" + "=" * 50)
    print("[OK] All Phase 2 tests completed!")

