from __future__ import annotations

import os
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


_SCHEMA_LOCK = threading.RLock()
_SCHEMA_READY: set[str] = set()


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
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    key = str(path.resolve())
    if key not in _SCHEMA_READY:
        with _SCHEMA_LOCK:
            if key not in _SCHEMA_READY:
                try:
                    conn.execute("PRAGMA journal_mode = WAL")
                except sqlite3.OperationalError:
                    pass
                ensure_schema(conn)
                _SCHEMA_READY.add(key)
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    _ensure_migration_table(conn)
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
    _ensure_column(conn, "runs", "stdout_redactions", "INTEGER DEFAULT 0")
    _ensure_column(conn, "runs", "stderr_redactions", "INTEGER DEFAULT 0")
    _ensure_column(conn, "runs", "summary_redactions", "INTEGER DEFAULT 0")
    _ensure_column(conn, "runs", "command_sha256", "TEXT DEFAULT ''")
    _ensure_column(conn, "runs", "policy_mode", "TEXT DEFAULT 'personal'")
    _ensure_column(conn, "runs", "policy_decision", "TEXT DEFAULT 'allowed'")
    _ensure_column(conn, "runs", "policy_reason", "TEXT DEFAULT ''")
    _ensure_column(conn, "runs", "retention_expires_at", "TEXT DEFAULT ''")
    _ensure_column(conn, "runs", "raw_retained", "INTEGER DEFAULT 1")
    _ensure_column(conn, "runs", "command_kind", "TEXT DEFAULT 'unknown'")
    _ensure_column(conn, "runs", "command_family", "TEXT DEFAULT 'unknown'")
    _ensure_column(conn, "runs", "caller", "TEXT DEFAULT 'cli'")
    _ensure_column(conn, "runs", "workspace_hash", "TEXT DEFAULT ''")
    _ensure_column(conn, "runs", "artifact_path", "TEXT DEFAULT ''")
    _ensure_column(conn, "runs", "artifact_sha256", "TEXT DEFAULT ''")
    _ensure_column(conn, "runs", "session_id", "TEXT DEFAULT ''")
    _ensure_column(conn, "runs", "is_ai_session", "INTEGER DEFAULT 0")

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
            run_id INTEGER,
            agent_id INTEGER,
            task_description TEXT,
            status TEXT DEFAULT 'pending',
            result TEXT,
            started_at TEXT,
            completed_at TEXT,
            FOREIGN KEY (run_id) REFERENCES runs(id),
            FOREIGN KEY (agent_id) REFERENCES agents(id)
        )
        """
    )
    _ensure_column(conn, "agent_tasks", "run_id", "INTEGER")
    _ensure_column(conn, "agent_tasks", "agent_run_id", "INTEGER")
    _ensure_column(conn, "agent_tasks", "rank_score", "REAL DEFAULT 0.0")
    _ensure_column(conn, "agent_tasks", "accepted", "INTEGER DEFAULT 0")
    _ensure_column(conn, "agent_tasks", "false_positive", "INTEGER DEFAULT 0")
    _ensure_column(conn, "agent_tasks", "fix_success", "INTEGER DEFAULT 0")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            agent_id INTEGER,
            task_id INTEGER,
            status TEXT NOT NULL DEFAULT 'queued',
            task_description TEXT,
            payload TEXT,
            result TEXT,
            started_at TEXT,
            finished_at TEXT,
            duration_ms INTEGER DEFAULT 0,
            confidence REAL DEFAULT 0.0,
            output_artifact_path TEXT DEFAULT '',
            lease_owner TEXT DEFAULT '',
            lease_expires_at TEXT DEFAULT '',
            attempts INTEGER DEFAULT 0,
            max_attempts INTEGER DEFAULT 2,
            next_attempt_at TEXT DEFAULT '',
            error TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            cancelled_at TEXT DEFAULT '',
            FOREIGN KEY (run_id) REFERENCES runs(id),
            FOREIGN KEY (agent_id) REFERENCES agents(id),
            FOREIGN KEY (task_id) REFERENCES agent_tasks(id)
        )
        """
    )
    for column, definition in {
        "task_id": "INTEGER",
        "task_description": "TEXT",
        "payload": "TEXT",
        "result": "TEXT",
        "started_at": "TEXT",
        "finished_at": "TEXT",
        "duration_ms": "INTEGER DEFAULT 0",
        "confidence": "REAL DEFAULT 0.0",
        "output_artifact_path": "TEXT DEFAULT ''",
        "lease_owner": "TEXT DEFAULT ''",
        "lease_expires_at": "TEXT DEFAULT ''",
        "attempts": "INTEGER DEFAULT 0",
        "max_attempts": "INTEGER DEFAULT 2",
        "next_attempt_at": "TEXT DEFAULT ''",
        "error": "TEXT DEFAULT ''",
        "created_at": "TEXT",
        "updated_at": "TEXT",
        "cancelled_at": "TEXT DEFAULT ''",
    }.items():
        _ensure_column(conn, "agent_runs", column, definition)

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_quality_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id INTEGER,
            agent_type TEXT NOT NULL,
            metric TEXT NOT NULL,
            value INTEGER DEFAULT 0,
            updated_at TEXT NOT NULL,
            UNIQUE(agent_id, metric)
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

    # Context compression metrics
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS context_compression (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            created_at TEXT NOT NULL,
            original_tokens INTEGER NOT NULL,
            compressed_tokens INTEGER NOT NULL,
            saved_tokens INTEGER NOT NULL,
            FOREIGN KEY (run_id) REFERENCES runs(id)
        )
        """
    )
    _ensure_column(conn, "context_compression", "strategy", "TEXT DEFAULT 'auto'")
    _ensure_column(conn, "context_compression", "verified_tokenizer", "TEXT DEFAULT 'tiktoken'")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS context_compression_strategies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            created_at TEXT NOT NULL,
            strategy TEXT NOT NULL,
            original_tokens INTEGER NOT NULL,
            compressed_tokens INTEGER NOT NULL,
            saved_tokens INTEGER NOT NULL,
            notes TEXT DEFAULT '',
            FOREIGN KEY (run_id) REFERENCES runs(id)
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS context_monthly_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            total_runs INTEGER NOT NULL,
            original_tokens INTEGER NOT NULL,
            compressed_tokens INTEGER NOT NULL,
            saved_tokens INTEGER NOT NULL,
            median_compression REAL NOT NULL,
            verified_tokenizer TEXT NOT NULL
        )
        """
    )

    conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs(created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_command_sha256 ON runs(command_sha256)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_tasks_run_id ON agent_tasks(run_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_tasks_status ON agent_tasks(status)")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS telemetry_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            run_id INTEGER,
            level INTEGER NOT NULL,
            dedupe_key TEXT NOT NULL UNIQUE,
            payload TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            attempts INTEGER DEFAULT 0,
            last_error TEXT DEFAULT '',
            sent_at TEXT DEFAULT ''
        )
        """
    )

    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_runs_status ON agent_runs(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_runs_run_id ON agent_runs(run_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_context_compression_run_id ON context_compression(run_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_context_strategy_run_id ON context_compression_strategies(run_id)")

    # External examples imported from Claude/Codex local histories for ML training.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ml_training_examples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            source TEXT NOT NULL,
            source_path TEXT NOT NULL,
            command TEXT NOT NULL,
            exit_code INTEGER NOT NULL,
            summary TEXT NOT NULL,
            fingerprint TEXT NOT NULL UNIQUE
        )
        """
    )

    conn.commit()
    _record_migration(conn, "0001_current_schema", "Current additive SQLite schema")


def _ensure_migration_table(conn: sqlite3.Connection) -> None:
    """Create the migration ledger before any additive schema work."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )


def _record_migration(conn: sqlite3.Connection, version: str, description: str) -> None:
    """Record that a schema migration/version has been applied."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.execute(
        """
        INSERT OR IGNORE INTO schema_migrations (version, description, applied_at)
        VALUES (?, ?, ?)
        """,
        (version, description, now),
    )
    conn.commit()


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    """Add a column to an existing SQLite table when missing."""
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def save_run(
    *,
    project: str,
    command: str,
    exit_code: int,
    duration_ms: int,
    stdout: str,
    stderr: str,
    summary: str,
    stdout_redactions: int = 0,
    stderr_redactions: int = 0,
    summary_redactions: int = 0,
    command_sha256: str = "",
    policy_mode: str = "personal",
    policy_decision: str = "allowed",
    policy_reason: str = "",
    retention_expires_at: str = "",
    raw_retained: int = 1,
    command_kind: str = "unknown",
    command_family: str = "unknown",
    caller: str = "cli",
    workspace_hash: str = "",
    artifact_path: str = "",
    artifact_sha256: str = "",
    session_id: str = "",
    is_ai_session: int = 0,
) -> int:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO runs
              (
                created_at, project, command, exit_code, duration_ms, stdout, stderr, summary,
                stdout_redactions, stderr_redactions, summary_redactions, command_sha256,
                policy_mode, policy_decision, policy_reason, retention_expires_at, raw_retained,
                command_kind, command_family, caller, workspace_hash, artifact_path, artifact_sha256,
                session_id, is_ai_session
              )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now,
                project,
                command,
                exit_code,
                duration_ms,
                stdout,
                stderr,
                summary,
                stdout_redactions,
                stderr_redactions,
                summary_redactions,
                command_sha256,
                policy_mode,
                policy_decision,
                policy_reason,
                retention_expires_at,
                raw_retained,
                command_kind,
                command_family,
                caller,
                workspace_hash,
                artifact_path,
                artifact_sha256,
                session_id,
                is_ai_session,
            ),
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
