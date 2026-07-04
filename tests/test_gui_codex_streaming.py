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
