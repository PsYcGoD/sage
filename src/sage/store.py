from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class RunRecord:
    id: int
    created_at: str
    project: str
    command: str
    exit_code: int
    duration_ms: int
    summary: str


def data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "SAGE"
    return Path.home() / ".sage"


def db_path() -> Path:
    return data_dir() / "sage.db"


def connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            project TEXT NOT NULL,
            command TEXT NOT NULL,
            exit_code INTEGER NOT NULL,
            duration_ms INTEGER NOT NULL,
            stdout TEXT NOT NULL,
            stderr TEXT NOT NULL,
            summary TEXT NOT NULL
        )
        """
    )

    # Auto-fix knowledge base
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS fixes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            error_pattern TEXT NOT NULL,
            fix_template TEXT NOT NULL,
            language TEXT,
            confidence REAL DEFAULT 0.5,
            success_rate REAL DEFAULT 0.0,
            times_applied INTEGER DEFAULT 0,
            times_succeeded INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    # Agent tracking
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            status TEXT DEFAULT 'idle',
            capabilities TEXT,
            created_at TEXT NOT NULL,
            last_active TEXT
        )
        """
    )

    # Agent tasks
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id INTEGER,
            task_description TEXT,
            status TEXT DEFAULT 'pending',
            result TEXT,
            started_at TEXT,
            completed_at TEXT,
            FOREIGN KEY (agent_id) REFERENCES agents(id)
        )
        """
    )

    # Workflow executions
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS workflow_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workflow_name TEXT NOT NULL,
            status TEXT DEFAULT 'running',
            steps_total INTEGER,
            steps_completed INTEGER DEFAULT 0,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            error_message TEXT
        )
        """
    )

    conn.commit()


def save_run(
    *,
    project: str,
    command: str,
    exit_code: int,
    duration_ms: int,
    stdout: str,
    stderr: str,
    summary: str,
) -> int:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO runs
              (created_at, project, command, exit_code, duration_ms, stdout, stderr, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (now, project, command, exit_code, duration_ms, stdout, stderr, summary),
        )
        return int(cursor.lastrowid)


def latest_run(only_failures: bool = False) -> RunRecord | None:
    sql = """
        SELECT id, created_at, project, command, exit_code, duration_ms, summary
        FROM runs
    """
    if only_failures:
        sql += " WHERE exit_code != 0"
    sql += " ORDER BY id DESC LIMIT 1"

    with connect() as conn:
        row = conn.execute(sql).fetchone()
        return _to_record(row) if row else None


def recent_runs(limit: int = 10) -> list[RunRecord]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, project, command, exit_code, duration_ms, summary
            FROM runs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [_to_record(row) for row in rows]


def _to_record(row: sqlite3.Row) -> RunRecord:
    return RunRecord(
        id=int(row["id"]),
        created_at=str(row["created_at"]),
        project=str(row["project"]),
        command=str(row["command"]),
        exit_code=int(row["exit_code"]),
        duration_ms=int(row["duration_ms"]),
        summary=str(row["summary"]),
    )
