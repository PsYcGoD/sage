"""Tests for sage write/edit/glob/tree and their snapshots."""

import json

import pytest

import sage.fileops as fileops
from sage.fileops import (
    edit_file,
    glob_files,
    render_glob,
    restore_snapshot,
    tree_view,
    write_file,
)


@pytest.fixture(autouse=True)
def isolated_snapshots(tmp_path, monkeypatch):
    monkeypatch.setattr(fileops, "data_dir", lambda: tmp_path / "sage-data")


# -------------------------------------------------------------------- write

def test_write_creates_and_verifies(tmp_path):
    target = tmp_path / "new" / "mod.py"
    result = write_file(str(target), "def f():\n    return 1\n")
    assert result.ok and result.created
    assert result.lines == 2 and len(result.sha256) == 64
    assert target.read_text(encoding="utf-8") == "def f():\n    return 1\n"


def test_write_refuses_overwrite_without_flag(tmp_path):
    target = tmp_path / "exists.txt"
    target.write_text("original", encoding="utf-8")
    result = write_file(str(target), "replacement")
    assert not result.ok and "--overwrite" in result.error
    assert target.read_text(encoding="utf-8") == "original"  # untouched


def test_write_overwrite_takes_snapshot(tmp_path):
    target = tmp_path / "exists.txt"
    target.write_text("original", encoding="utf-8")
    result = write_file(str(target), "replacement", overwrite=True)
    assert result.ok and result.overwritten and result.snapshot
    ok, _ = restore_snapshot(result.snapshot)
    assert ok
    assert target.read_text(encoding="utf-8") == "original"  # undo works


def test_write_append(tmp_path):
    target = tmp_path / "log.txt"
    target.write_text("line1\n", encoding="utf-8")
    result = write_file(str(target), "line2\n", append=True)
    assert result.ok
    assert target.read_text(encoding="utf-8") == "line1\nline2\n"


def test_write_rejects_directory(tmp_path):
    result = write_file(str(tmp_path), "content", overwrite=True)
    assert not result.ok and "directory" in result.error


# --------------------------------------------------------------------- edit

def test_edit_unique_replacement_with_preview(tmp_path):
    target = tmp_path / "mod.py"
    target.write_text("def f():\n    return 'old_value'\n", encoding="utf-8")
    result = edit_file(str(target), "old_value", "new_value")
    assert result.ok and result.replacements == 1
    assert result.changed_lines == [2]
    assert "new_value" in result.preview
    assert "def f():" in result.preview  # context lines shown
    assert "new_value" in target.read_text(encoding="utf-8")


def test_edit_rejects_ambiguous_old(tmp_path):
    target = tmp_path / "dup.txt"
    target.write_text("same\nsame\n", encoding="utf-8")
    result = edit_file(str(target), "same", "different")
    assert not result.ok and "--all" in result.error
    assert target.read_text(encoding="utf-8") == "same\nsame\n"  # untouched


def test_edit_replace_all(tmp_path):
    target = tmp_path / "dup.txt"
    target.write_text("same\nsame\n", encoding="utf-8")
    result = edit_file(str(target), "same", "different", replace_all=True)
    assert result.ok and result.replacements == 2
    assert target.read_text(encoding="utf-8") == "different\ndifferent\n"


def test_edit_missing_old_string(tmp_path):
    target = tmp_path / "x.txt"
    target.write_text("content", encoding="utf-8")
    result = edit_file(str(target), "not_there", "y")
    assert not result.ok and "not found" in result.error


def test_edit_snapshot_roundtrip(tmp_path):
    target = tmp_path / "undo.txt"
    target.write_text("before edit", encoding="utf-8")
    result = edit_file(str(target), "before", "after")
    assert result.ok
    ok, message = restore_snapshot(result.snapshot)
    assert ok and "Restored" in message
    assert target.read_text(encoding="utf-8") == "before edit"


def test_restore_missing_snapshot():
    ok, message = restore_snapshot("no/such/snapshot.json")
    assert not ok and "not found" in message


# --------------------------------------------------------------------- glob

def test_glob_sorts_newest_first_and_caps(tmp_path):
    import os
    import time

    for index in range(5):
        path = tmp_path / f"file{index}.py"
        path.write_text(f"# {index}", encoding="utf-8")
        os.utime(path, (time.time() - 100 + index, time.time() - 100 + index))
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "junk.py").write_text("x", encoding="utf-8")

    result = glob_files("*.py", str(tmp_path), limit=3)
    assert result.total_found == 5  # junk dir excluded
    assert len(result.files) == 3
    assert result.files[0][0].endswith("file4.py")  # newest first
    rendered = render_glob(result)
    assert "2 more" in rendered


def test_glob_no_matches(tmp_path):
    result = glob_files("*.zig", str(tmp_path))
    assert result.total_found == 0
    assert "No files match" in render_glob(result)


def test_glob_missing_root():
    result = glob_files("*.py", "no/such/root")
    assert result.error


# --------------------------------------------------------------------- tree

def test_tree_depth_and_skip_dirs(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text("x", encoding="utf-8")
    (tmp_path / "pkg" / "deep").mkdir()
    (tmp_path / "pkg" / "deep" / "b.py").write_text("x", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "c.pyc").write_text("x", encoding="utf-8")

    rendered = tree_view(str(tmp_path), depth=2)
    assert "pkg/" in rendered and "a.py" in rendered
    assert "__pycache__" not in rendered
    assert "b.py" not in rendered  # beyond depth 2


def test_tree_missing_root():
    assert "error" in tree_view("no/such/dir")


# ---------------------------------------------------------------- MCP tools

def test_mcp_fileops_tools_registered(monkeypatch):
    from sage.mcp.server import MCPServer
    from sage.mcp.tools import SAGE_TOOLS

    monkeypatch.delenv("SAGE_MCP_ENABLE_COMMANDS", raising=False)
    names = {tool["name"] for tool in SAGE_TOOLS}
    assert {"sage_write_file", "sage_edit_file", "sage_glob", "sage_tree"} <= names
    server = MCPServer()
    assert {tool["name"] for tool in server._tool_specs()} == set(server.tools)


def test_mcp_write_and_edit_roundtrip(tmp_path):
    from sage.mcp.tools import sage_edit_file, sage_write_file

    target = tmp_path / "mcp.py"
    written = sage_write_file(str(target), "value = 'first'\n")
    assert written["success"] and written["content_tokens_not_echoed"] > 0
    edited = sage_edit_file(str(target), "first", "second")
    assert edited["success"] and edited["replacements"] == 1
    assert target.read_text(encoding="utf-8") == "value = 'second'\n"
    blocked = sage_write_file(str(target), "clobber")
    assert not blocked["success"]  # overwrite requires the flag
