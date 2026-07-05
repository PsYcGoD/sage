from sage.gui.session_manager import SessionManager


def test_session_manager_persists_provider_resume_state(tmp_path):
    manager = SessionManager(tmp_path / "sessions.json")
    session_id = manager.create_session(str(tmp_path), title="Terminal Chat")

    manager.set_provider_state(
        str(tmp_path),
        session_id,
        "claude",
        {
            "mode": "interactive-terminal",
            "session_id": "00000000-0000-0000-0000-000000000000",
        },
    )

    state = manager.get_provider_state(str(tmp_path), session_id, "claude")

    assert state["mode"] == "interactive-terminal"
    assert state["session_id"] == "00000000-0000-0000-0000-000000000000"
    assert state["updated_at"]
