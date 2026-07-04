"""Local raw artifact store.

Keeps exact original command output on disk so compression is always
recoverable, while large logs stay out of SQLite. Raw artifacts never
leave the machine; telemetry reads only counters, never these files.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .store import connect, data_dir

# Outputs above this many bytes get a file artifact next to the DB row.
ARTIFACT_THRESHOLD_BYTES = 64_000


def artifacts_dir() -> Path:
    path = data_dir() / "artifacts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def store_raw_output(run_id: int, stdout: str, stderr: str) -> tuple[str, str]:
    """Write raw output to a per-run artifact file; return (path, sha256).

    Small outputs return ("", "") — the DB row already holds them exactly.
    """
    payload = json.dumps(
        {"run_id": run_id, "stdout": stdout, "stderr": stderr},
        ensure_ascii=False,
    )
    if len(payload.encode("utf-8", errors="replace")) < ARTIFACT_THRESHOLD_BYTES:
        return "", ""
    digest = hashlib.sha256(payload.encode("utf-8", errors="replace")).hexdigest()
    path = artifacts_dir() / f"run-{run_id}-raw.json"
    path.write_text(payload, encoding="utf-8")
    return str(path), digest


def load_raw_output(run_id: int) -> dict[str, str] | None:
    """Recover exact raw stdout/stderr for a run, artifact-first."""
    with connect() as conn:
        row = conn.execute(
            "SELECT stdout, stderr, artifact_path, artifact_sha256 FROM runs WHERE id = ?",
            (run_id,),
        ).fetchone()
    if row is None:
        return None
    artifact_path = str(row["artifact_path"] or "")
    if artifact_path and Path(artifact_path).exists():
        try:
            data = json.loads(Path(artifact_path).read_text(encoding="utf-8"))
            return {
                "stdout": str(data.get("stdout", "")),
                "stderr": str(data.get("stderr", "")),
                "source": "artifact",
                "verified": _verify_artifact(artifact_path, str(row["artifact_sha256"] or "")),
            }
        except (OSError, json.JSONDecodeError):
            pass
    return {"stdout": str(row["stdout"]), "stderr": str(row["stderr"]), "source": "db", "verified": "n/a"}


def _verify_artifact(path: str, expected_sha256: str) -> str:
    if not expected_sha256:
        return "no-hash"
    actual = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return "ok" if actual == expected_sha256 else "MISMATCH"


def prune_artifacts(*, days: int | None = None, max_bytes: int | None = None, apply: bool = False) -> dict[str, int]:
    """Prune old/oversized artifacts. Preview by default; delete only with apply=True."""
    files = sorted(artifacts_dir().glob("run-*-raw.json"), key=lambda p: p.stat().st_mtime)
    to_remove: list[Path] = []

    if days is not None:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).timestamp()
        to_remove.extend(p for p in files if p.stat().st_mtime < cutoff)

    if max_bytes is not None:
        remaining = [p for p in files if p not in set(to_remove)]
        total = sum(p.stat().st_size for p in remaining)
        for path in remaining:  # oldest first
            if total <= max_bytes:
                break
            to_remove.append(path)
            total -= path.stat().st_size

    removed_bytes = sum(p.stat().st_size for p in to_remove)
    if apply:
        with connect() as conn:
            for path in to_remove:
                path.unlink(missing_ok=True)
                conn.execute(
                    "UPDATE runs SET artifact_path = '', artifact_sha256 = '' WHERE artifact_path = ?",
                    (str(path),),
                )
            conn.commit()
    return {
        "total_artifacts": len(files),
        "pruned": len(to_remove),
        "pruned_bytes": removed_bytes,
        "applied": int(apply),
    }
