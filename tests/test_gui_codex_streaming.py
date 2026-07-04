from sage.gui.persistent_ai_client import PersistentAIClient


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


def test_codex_json_classifier_exposes_reasoning_tool_and_text():
    client = PersistentAIClient("codex")

    thinking_type, thinking = client._classify_codex_stream_item(
        '{"type":"item.completed","item":{"type":"reasoning","summary":"Inspecting failing test"}}\n',
        "stdout",
        visible_started=False,
        suppress_rest=False,
    )
    tool_type, tool = client._classify_codex_stream_item(
        '{"type":"item.started","item":{"type":"function_call","name":"shell","arguments":"pytest tests/test_gui_codex_streaming.py"}}\n',
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
    assert (tool_type, tool) == ("tool", "shell: pytest tests/test_gui_codex_streaming.py\n")
    assert (text_type, text) == ("text", "Done.")


def test_codex_filter_keeps_non_error_stderr_progress():
    client = PersistentAIClient("codex")

    status_type, status = client._classify_codex_stream_item(
        "Thinking about the patch\n",
        "stderr",
        visible_started=False,
        suppress_rest=False,
    )

    assert (status_type, status) == ("thinking", "Thinking about the patch\n")
