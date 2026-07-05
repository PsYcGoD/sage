import sys
import shutil
import types


def test_claude_cli_available_with_provider_api_key(monkeypatch):
    from sage.gui import native_cli_client

    calls = {"auth_status": 0}

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(shutil, "which", lambda name: "claude" if name == "claude" else None)

    def fake_run(*args, **kwargs):
        calls["auth_status"] += 1
        raise AssertionError("auth status should not run when ANTHROPIC_API_KEY is set")

    monkeypatch.setattr(native_cli_client.subprocess, "run", fake_run)

    assert native_cli_client.check_native_cli_available("claude") is True
    assert calls["auth_status"] == 0


def test_direct_claude_client_uses_custom_base_url(monkeypatch):
    from sage.gui.direct_ai_client import DirectClaudeClient

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://provider.example/")

    client = DirectClaudeClient()

    assert client.api_url == "https://provider.example/v1/messages"


def test_persistent_claude_prefers_custom_base_url_over_bedrock(monkeypatch):
    from sage.gui.persistent_ai_client import PersistentAIClient

    created = {}

    class FakeAnthropic:
        def __init__(self, api_key=None, base_url=None):
            created["anthropic"] = {"api_key": api_key, "base_url": base_url}

    class FakeBedrock:
        def __init__(self, **kwargs):
            created["bedrock"] = kwargs

    fake_module = types.SimpleNamespace(Anthropic=FakeAnthropic, AnthropicBedrock=FakeBedrock)

    monkeypatch.setitem(sys.modules, "anthropic", fake_module)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://provider.example/")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "aws-key-that-should-not-force-bedrock")

    client = PersistentAIClient("claude")

    assert client._start_claude_session() is True
    assert created == {
        "anthropic": {
            "api_key": "test-key",
            "base_url": "https://provider.example/",
        }
    }
    assert client.is_bedrock is False


def test_gui_uses_plain_claude_print_for_custom_provider(monkeypatch):
    from sage.gui.app import SAGEApp

    app = SAGEApp.__new__(SAGEApp)

    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    assert app._claude_provider_uses_plain_print() is False

    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://provider.example/")
    assert app._claude_provider_uses_plain_print() is True


def test_cli_stream_always_stops_running_state_after_answer(monkeypatch):
    from sage.gui.app import SAGEApp

    class FakeClient:
        last_run_id = 123

        def stream_response(self, prompt):
            yield "answer text"

    class FakeOutput:
        def __init__(self):
            self.assistant_text = []
            self.errors = []

        def append_assistant_text(self, text):
            self.assistant_text.append(text)

        def append_text(self, text, tag=None):
            self.errors.append((text, tag))

    class FakeOverlay:
        def __init__(self):
            self.hidden = 0

        def show(self):
            pass

        def hide(self):
            self.hidden += 1

    app = SAGEApp.__new__(SAGEApp)
    app.output_tabs = {7: {"ai_running": True}}
    app.active_output_tab_id = 7
    app.ai_running = True
    app.thinking_overlay = FakeOverlay()
    app.current_client = FakeClient()
    output = FakeOutput()
    statuses = []

    monkeypatch.setattr(app, "after", lambda delay, func=None: func() if func else None)
    monkeypatch.setattr(app, "_set_run_status", lambda text, color="gray60": statuses.append(text))
    monkeypatch.setattr(app, "_append_run_status", lambda view, text: None)
    monkeypatch.setattr(app, "_mark_tab_stream_event", lambda tab_id: None)
    monkeypatch.setattr(app, "_save_prompt_for_run", lambda run_id, text: None)
    monkeypatch.setattr(app, "_record_context_compression", lambda run_id, output_view=None: (_ for _ in ()).throw(RuntimeError("late failure")))
    monkeypatch.setattr(app, "_remember_conversation_turn", lambda role, text: None)
    monkeypatch.setattr(app, "_drain_queued_prompt", lambda tab_id: None)

    app._run_cli_stream("prompt", "claude", "prompt", tab_id=7, client=app.current_client, output_view=output)

    assert output.assistant_text == ["answer text"]
    assert app.output_tabs[7]["ai_running"] is False
    assert app.ai_running is False
    assert app.thinking_overlay.hidden >= 1
    assert statuses[-1] == "Idle"
