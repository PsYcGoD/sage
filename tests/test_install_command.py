from __future__ import annotations

from sage import cli


def test_install_command_runs_activation_without_wait(monkeypatch):
    calls: list[tuple[bool, bool]] = []

    def fake_activate_command(*, force: bool = False, project: bool = True) -> int:
        calls.append((force, project))
        return 0

    monkeypatch.setattr(cli, "activate_command", fake_activate_command)

    assert cli.install_command(force=True, project=False, wait=False) == 0
    assert calls == [(True, False)]


def test_install_parser_supports_script_safe_flags():
    parser = cli.build_parser()

    args = parser.parse_args(["install", "--force", "--no-project", "--no-wait"])

    assert args.command_name == "install"
    assert args.force is True
    assert args.no_project is True
    assert args.no_wait is True


def test_unknown_first_token_runs_as_wrapped_command(monkeypatch):
    seen = {}

    monkeypatch.setattr(cli, "_ensure_first_run_setup", lambda command_name: 0)
    monkeypatch.setattr(cli, "_ensure_system_enforcement", lambda command_name: True)

    def fake_run_command(command, **kwargs):
        seen["command"] = command
        seen["kwargs"] = kwargs
        return 0

    monkeypatch.setattr(cli, "run_command", fake_run_command)

    assert cli.main(["pytest", "-q"]) == 0
    assert seen["command"] == ["pytest", "-q"]


def test_known_command_still_parses_normally(monkeypatch):
    monkeypatch.setattr(cli, "activate_command", lambda *, force=False, project=True: 0)

    assert cli.main(["activate"]) == 0
