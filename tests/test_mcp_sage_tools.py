"""Tests for the new compressed MCP tools."""

from sage.mcp.server import MCPServer
from sage.mcp.client import connect_and_list
from sage.mcp.tools import SAGE_TOOLS, sage_grep, sage_read_file, sage_run_workflow, sage_spawn_agent


def test_new_tools_are_registered():
    names = {tool["name"] for tool in SAGE_TOOLS}
    assert {"sage_read_file", "sage_grep", "sage_call", "sage_show_raw"} <= names
    server = MCPServer()
    for name in ("sage_read_file", "sage_grep", "sage_call", "sage_show_raw"):
        assert name in server.tools


def test_tools_list_matches_handlers(monkeypatch):
    monkeypatch.delenv("SAGE_MCP_ENABLE_COMMANDS", raising=False)
    server = MCPServer()
    listed = {tool["name"] for tool in server._tool_specs()}
    assert listed == set(server.tools)
    assert "sage_run_command" not in listed
    blocked = server._call_tool({"name": "sage_run_command", "arguments": {"command": "echo no"}})
    assert blocked["isError"] is True
    assert "disabled by default" in blocked["content"][0]["text"]


def test_mcp_run_command_is_opt_in(monkeypatch):
    monkeypatch.setenv("SAGE_MCP_ENABLE_COMMANDS", "1")
    server = MCPServer()
    listed = {tool["name"] for tool in server._tool_specs()}
    assert "sage_run_command" in listed
    assert "sage_run_command" in server.tools


def test_external_mcp_missing_command_fails_fast():
    result = connect_and_list("definitely-not-a-real-mcp-server-command-xyz", timeout=1)
    assert result.ok is False
    assert result.transport == "stdio"
    assert "Command not found" in result.error


def test_sage_read_file_tool(tmp_path):
    path = tmp_path / "tool.py"
    path.write_text("def tool():\n    return 42\n", encoding="utf-8")
    result = sage_read_file(str(path))
    assert result["success"] and result["run_id"] > 0
    assert "def tool():" in result["content"]
    assert result["mode"] == "exact"


def test_sage_read_file_missing():
    result = sage_read_file("missing/nope.py")
    assert not result["success"]


def test_sage_grep_tool(tmp_path):
    (tmp_path / "x.py").write_text("needle_token = 1\n", encoding="utf-8")
    result = sage_grep("needle_token", [str(tmp_path)])
    assert result["success"]
    assert result["match_count"] == 1
    assert "x.py" in result["content"]


def test_sage_spawn_agent_tool_runs_worker():
    result = sage_spawn_agent("debug", "Inspect a passing smoke command")
    assert result["success"]
    assert result["agent_type"] == "debug"
    assert result["run_id"] > 0
    assert result["results"]


def test_sage_run_workflow_tool_runs_yaml(tmp_path):
    workflow = tmp_path / "smoke.yml"
    workflow.write_text(
        "name: mcp-smoke\n"
        "pipeline:\n"
        "  - name: echo\n"
        "    run: python -c \"print('mcp workflow ok')\"\n",
        encoding="utf-8",
    )
    result = sage_run_workflow(workflow_path=str(workflow))
    assert result["success"]
    assert result["workflow"] == "mcp-smoke"
    assert result["workflow_run_id"] > 0
