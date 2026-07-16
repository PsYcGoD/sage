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
