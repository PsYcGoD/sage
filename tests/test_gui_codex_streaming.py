import json

from sage.gui.persistent_ai_client import PersistentAIClient
from sage.gui.widgets.powershell_terminal import PowerShellTerminal


def test_codex_filter_shows_output_without_legacy_marker():
    client = PersistentAIClient("codex")

    hidden_header = client._filter_codex_line(
        "OpenAI Codex v0.139.0\n",
        "stdout",
        visible_started=False,
        suppress_rest=False,
    )
    answer = client._filter_codex_line(
        "3 because 1 + 2 equals 3.\n",
        "stdout",
        visible_started=False,
        suppress_rest=False,
    )

    assert hidden_header is None
    assert answer == "3 because 1 + 2 equals 3.\n"


def test_codex_filter_stops_at_token_usage():
    client = PersistentAIClient("codex")

    marker = client._filter_codex_line(
        "tokens used\n",
        "stdout",
        visible_started=True,
        suppress_rest=False,
    )
    trailing = client._filter_codex_line(
        "15,200\n",
        "stdout",
        visible_started=True,
        suppress_rest=True,
    )

    assert marker == "__STOP__"
    assert trailing is None


def test_codex_line_classifier_exposes_reasoning_and_coding():
    client = PersistentAIClient("codex")

    thinking_type, thinking = client._classify_codex_line(
        "Reasoning: inspect the failing test\n",
        "stdout",
        visible_started=False,
        suppress_rest=False,
    )
    coding_type, coding = client._classify_codex_line(
        "```python\n",
        "stdout",
        visible_started=True,
        suppress_rest=False,
    )
    tool_type, tool = client._classify_codex_line(
        "apply_patch: updating runner.py\n",
        "stdout",
        visible_started=True,
        suppress_rest=False,
    )

    assert (thinking_type, thinking) == ("thinking", "Reasoning: inspect the failing test\n")
    assert (coding_type, coding) == ("coding", "```python\n")
    assert (tool_type, tool) == ("tool", "apply_patch: updating runner.py\n")


def test_codex_command_requests_json_stream_and_plain_color(tmp_path):
    client = PersistentAIClient("codex")
    client.codex_command = "codex"

    cmd = client._codex_command(resume=False, output_path=tmp_path / "last.txt")

    assert cmd[:5] == ["codex", "exec", "--json", "--color", "never"]


def test_codex_json_classifier_exposes_reasoning_text_and_in_progress_tool():
    client = PersistentAIClient("codex")

    thinking_type, thinking = client._classify_codex_stream_item(
        '{"type":"item.completed","item":{"type":"reasoning","summary":"Inspecting failing test"}}\n',
        "stdout",
        visible_started=False,
        suppress_rest=False,
    )
    tool_type, tool = client._classify_codex_stream_item(
        '{"type":"item.started","item":{"type":"function_call","name":"shell","status":"in_progress","arguments":"pytest tests/test_gui_codex_streaming.py"}}\n',
        "stdout",
        visible_started=True,
        suppress_rest=False,
    )
    text_type, text = client._classify_codex_stream_item(
        '{"type":"item.completed","item":{"type":"message","content":[{"type":"output_text","text":"Done."}]}}\n',
        "stdout",
        visible_started=True,
        suppress_rest=False,
    )

    assert (thinking_type, thinking) == ("thinking", "Inspecting failing test\n")
    assert (tool_type, tool) == ("tool", "Running pytest tests/test_gui_codex_streaming.py\n")
    assert (text_type, text) == ("text", "Done.")


def test_codex_tool_summary_cleans_powershell_sage_wrapper():
    client = PersistentAIClient("codex")
    payload = {
        "type": "item.completed",
        "item": {
            "type": "function_call",
            "name": "shell",
            "arguments": (
                '"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" '
                "-Command 'sage run -- git status --short'"
            ),
        },
    }

    tool_type, tool = client._classify_codex_stream_item(
        json.dumps(payload) + "\n",
        "stdout",
        visible_started=True,
        suppress_rest=False,
    )

    assert (tool_type, tool) == ("tool", "sage run -- git status --short\n")


def test_codex_tool_summary_includes_failed_command_output():
    client = PersistentAIClient("codex")
    payload = {
        "type": "item.completed",
        "item": {
            "type": "function_call",
            "name": "shell",
            "status": "completed",
            "exit_code": 1,
            "arguments": "sage run -- powershell -NoProfile -Command \"sage agents --help\"",
            "output": "Usage: sage agents <list|status>\n",
        },
    }

    tool_type, tool = client._classify_codex_stream_item(
        json.dumps(payload) + "\n",
        "stdout",
        visible_started=True,
        suppress_rest=False,
    )

    assert tool_type == "tool"
    assert "Failed (1) sage run -- powershell" in tool
    assert "Usage: sage agents <list|status>" in tool


def test_codex_tool_output_event_is_shown_as_output_not_ran_output():
    client = PersistentAIClient("codex")
    payload = {
        "type": "item.completed",
        "item": {
            "type": "function_call_output",
            "output": "command timed out after 62320 milliseconds\nTraceback...\n",
        },
    }

    tool_type, tool = client._classify_codex_stream_item(
        json.dumps(payload) + "\n",
        "stdout",
        visible_started=True,
        suppress_rest=False,
    )

    assert tool_type == "tool"
    assert tool == "command timed out after 62320 milliseconds\nTraceback...\n"


def test_codex_filter_keeps_non_error_stderr_progress():
    client = PersistentAIClient("codex")

    status_type, status = client._classify_codex_stream_item(
        "Thinking about the patch\n",
        "stderr",
        visible_started=False,
        suppress_rest=False,
    )

    assert (status_type, status) == ("thinking", "Thinking about the patch\n")


def test_codex_token_limit_error_is_visible_from_stderr():
    client = PersistentAIClient("codex")

    event_type, message = client._classify_codex_stream_item(
        "OpenAI API error: context_length_exceeded: maximum context length is 128000 tokens\n",
        "stderr",
        visible_started=False,
        suppress_rest=False,
    )

    assert event_type == "error"
    assert "API error" in message
    assert "context/token limit" in message


def test_codex_token_limit_error_is_visible_from_json():
    client = PersistentAIClient("codex")

    event_type, message = client._classify_codex_stream_item(
        '{"type":"turn.error","error":{"message":"maximum context length exceeded"}}\n',
        "stdout",
        visible_started=False,
        suppress_rest=False,
    )

    assert event_type == "error"
    assert "context/token limit" in message


def test_claude_daily_token_limit_retry_is_terminal_error():
    text = "✻ 429 Too many tokens per day, please wait before trying again. · Retrying in 2s · attempt 5/10"

    assert PowerShellTerminal._is_claude_retry_limit_error(text)
    message = PowerShellTerminal._format_claude_retry_limit_error(text)
    assert message == "Claude API limit hit: too many tokens per day. Wait before trying again."


def test_terminal_accepts_structured_sections_without_output_view():
    terminal = PowerShellTerminal.__new__(PowerShellTerminal)
    calls = []
    terminal.append_text = lambda text, tag=None: calls.append((text, tag))

    terminal.append_expandable_section("Tool Activity", "running pytest", "running", collapsed=False)

    assert calls == [("\nTool Activity\n", "info"), ("running pytest\n", "dim")]
