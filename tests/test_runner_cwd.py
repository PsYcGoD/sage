from __future__ import annotations

import sys

from sage.runner import _build_popen_cmd, run_command


def _quiet_runner(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local-data"))
    monkeypatch.setenv("SAGE_DISABLE_PREDICT", "1")
    monkeypatch.setenv("SAGE_AUTO_SEND_TELEMETRY", "0")
    monkeypatch.setenv("SAGE_DISABLE_AGENTS", "1")


def test_explicit_cwd_supports_desktop_hosts(monkeypatch, tmp_path):
    _quiet_runner(monkeypatch, tmp_path)
    workspace = tmp_path / "host workspace"
    workspace.mkdir()

    exit_code = run_command(
        [
            sys.executable,
            "-c",
            "from pathlib import Path; Path('cwd-proof.txt').write_text(str(Path.cwd()))",
        ],
        cwd=workspace,
    )

    assert exit_code == 0
    assert (workspace / "cwd-proof.txt").read_text(encoding="utf-8") == str(
        workspace.resolve()
    )


def test_desktop_cwd_environment_is_supported(monkeypatch, tmp_path):
    _quiet_runner(monkeypatch, tmp_path)
    workspace = tmp_path / "desktop-env"
    workspace.mkdir()
    monkeypatch.setenv("SAGE_WORKSPACE_CWD", str(workspace))

    exit_code = run_command(
        [sys.executable, "-c", "from pathlib import Path; Path('env-proof.txt').touch()"]
    )

    assert exit_code == 0
    assert (workspace / "env-proof.txt").exists()


def test_invalid_explicit_cwd_fails_before_start(monkeypatch, tmp_path):
    _quiet_runner(monkeypatch, tmp_path)
    assert run_command([sys.executable, "-c", "pass"], cwd=tmp_path / "missing") == 2


def test_windows_native_executable_avoids_shell_reparse(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr("sage.runner.shutil.which", lambda _command: r"C:\\pwsh\\pwsh.exe")
    parts = ["pwsh", "-Command", "Write-Output 'a|b'"]

    args, use_shell = _build_popen_cmd("unused", parts)

    assert args == parts
    assert use_shell is False


def test_powershell_arguments_with_metacharacters_survive_on_windows(
    monkeypatch, tmp_path
):
    if not sys.platform.startswith("win"):
        return
    _quiet_runner(monkeypatch, tmp_path)
    workspace = tmp_path / "quoted-command"
    workspace.mkdir()

    exit_code = run_command(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "[IO.File]::WriteAllText('quoted.txt', 'a|b')",
        ],
        cwd=workspace,
    )

    assert exit_code == 0
    assert (workspace / "quoted.txt").read_text(encoding="utf-8") == "a|b"
