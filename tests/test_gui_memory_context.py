from sage.gui.app import SAGEApp
from sage.gui.persistent_ai_client import PersistentAIClient
from sage.gui.session_manager import SessionManager
from sage.gui.widgets.floating_sidebar import FloatingSidebar


def _app_without_tk() -> SAGEApp:
    app = SAGEApp.__new__(SAGEApp)
    app.pending_context_compression = None
    app.output_tabs = {1: {"ai_name": "claude"}}
    app.project_memory_turns = []
    return app


def test_context_prompt_includes_one_prior_exchange():
    app = _app_without_tk()
    app.conversation_turns = [
        {"role": "user", "text": "test"},
        {"role": "claude", "text": "Sensei, system operational and ready."},
    ]

    prompt = app._build_contextual_prompt("What did i say before this")

    assert "SAGE memory" in prompt
    assert "User: test" in prompt
    assert "Current user request:" in prompt
    assert "What did i say before this" in prompt


def test_context_prompt_first_turn_stays_plain():
    app = _app_without_tk()
    app.conversation_turns = []

    assert app._build_contextual_prompt("test") == "test"


def test_context_prompt_uses_live_session_not_older_project_memory_by_default():
    app = _app_without_tk()
    app.project_memory_turns = [
        {"role": "user", "text": "older project question"},
        {"role": "claude", "text": "older project answer"},
    ]
    app.conversation_turns = [
        {"role": "user", "text": "1+2="},
        {"role": "claude", "text": "Sensei, 1 + 2 = 3"},
    ]

    prompt = app._build_contextual_prompt("what was my question")

    assert "User: 1+2=" in prompt
    assert "older project question" not in prompt
    assert "latest live-session user message only" in prompt


def test_context_prompt_includes_older_memory_when_explicitly_requested():
    app = _app_without_tk()
    app.project_memory_turns = [
        {"role": "user", "text": "older project question"},
        {"role": "claude", "text": "older project answer"},
    ]
    app.conversation_turns = [
        {"role": "user", "text": "1+2="},
        {"role": "claude", "text": "Sensei, 1 + 2 = 3"},
    ]

    prompt = app._build_contextual_prompt("show older history")

    assert "User: 1+2=" in prompt
    assert "older project question" in prompt
    assert "Older saved project memory" in prompt


def test_persistent_client_hydrates_from_saved_session():
    client = PersistentAIClient("codex")
    client.load_history([
        {"role": "user", "text": "first question"},
        {"role": "codex", "text": "first answer"},
    ])

    assert client.conversation_history == [
        {"role": "user", "content": "first question"},
        {"role": "assistant", "content": "first answer"},
    ]


def test_load_chat_restores_live_and_provider_memory(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    session_manager = SessionManager(tmp_path / "sessions.json")
    session_id = session_manager.create_session(str(project), "Saved Chat")
    session_manager.add_message(str(project), session_id, "user", "remember me")
    session_manager.add_message(str(project), session_id, "codex", "remembered")

    class Output:
        def __init__(self):
            self.events = []

        def clear(self):
            self.events.append(("clear", ""))

        def append_user_message(self, text):
            self.events.append(("user", text))

        def append_assistant_start(self, text):
            self.events.append(("assistant_start", text))

        def append_assistant_text(self, text):
            self.events.append(("assistant_text", text))

        def append_text(self, text, tag=None):
            self.events.append((tag, text))

    app = _app_without_tk()
    app.session_manager = session_manager
    app.output_view = Output()
    app.persistent_client = PersistentAIClient("codex")
    app.load_sidebar_data = lambda: None

    app.load_chat(session_id)

    assert app.current_session_id == session_id
    assert app.conversation_turns[-2:] == [
        {"role": "user", "text": "remember me"},
        {"role": "codex", "text": "remembered"},
    ]
    assert app.persistent_client.conversation_history[-2:] == [
        {"role": "user", "content": "remember me"},
        {"role": "assistant", "content": "remembered"},
    ]


def test_sidebar_scheduled_and_plugins_buttons_dispatch_actions():
    sidebar = FloatingSidebar.__new__(FloatingSidebar)
    actions = []
    sidebar.on_chat_action = lambda action, payload: actions.append((action, payload))

    sidebar._on_scheduled_clicked()
    sidebar._on_plugins_clicked()

    assert actions == [
        ("show_scheduled", {"id": ""}),
        ("show_plugins", {"id": ""}),
    ]
