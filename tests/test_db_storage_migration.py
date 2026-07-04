from sage.cli import main
from sage.store import connect, save_run


def test_schema_migration_ledger_created(tmp_path, monkeypatch):
    import sage.store as store

    monkeypatch.setattr(store, "data_dir", lambda: tmp_path)
    store._SCHEMA_READY.clear()

    with connect() as conn:
        rows = conn.execute("SELECT version, description FROM schema_migrations").fetchall()

    assert rows
    assert rows[0]["version"] == "0001_current_schema"


def test_db_status_reports_integrity_and_migrations(tmp_path, monkeypatch, capsys):
    import sage.store as store

    monkeypatch.setattr(store, "data_dir", lambda: tmp_path)
    store._SCHEMA_READY.clear()

    save_run(
        project=str(tmp_path),
        command="echo ok",
        exit_code=0,
        duration_ms=1,
        stdout="ok",
        stderr="",
        summary="ok",
    )

    assert main(["db", "status"]) == 0
    output = capsys.readouterr().out
    assert "Integrity: ok" in output
    assert "- runs: 1 rows" in output
    assert "- schema_migrations: 1 rows" in output


def test_db_backup_and_restore_roundtrip(tmp_path, monkeypatch):
    import sage.store as store

    monkeypatch.setattr(store, "data_dir", lambda: tmp_path)
    store._SCHEMA_READY.clear()

    save_run(
        project=str(tmp_path),
        command="first",
        exit_code=0,
        duration_ms=1,
        stdout="first",
        stderr="",
        summary="first",
    )
    backup = tmp_path / "backup.db"
    assert main(["db", "backup", "--output", str(backup)]) == 0
    assert backup.exists()

    save_run(
        project=str(tmp_path),
        command="second",
        exit_code=0,
        duration_ms=1,
        stdout="second",
        stderr="",
        summary="second",
    )
    with connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 2

    store._SCHEMA_READY.clear()
    assert main(["db", "restore", str(backup), "--yes"]) == 0
    store._SCHEMA_READY.clear()
    with connect() as conn:
        commands = [row["command"] for row in conn.execute("SELECT command FROM runs ORDER BY id")]

    assert commands == ["first"]
