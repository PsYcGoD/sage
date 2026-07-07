"""Client-side telemetry: privacy levels, payloads, queue, accounts.

Everything here is local until a server endpoint is explicitly configured.
Default level is 0 (local only) — SAGE never uploads anything unless the
user raises the level AND configures an endpoint. Level 1 payloads contain
counters only: no command text, no output, no paths.

Strictest-policy-wins: the effective level is the minimum of the user's
setting, the active account's org maximum, and the account key maximum.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

from .classify import workspace_hash as _workspace_hash
from .savings import build_agent_savings, build_model_savings, estimate_total_model_savings_usd
from .security import redact_text
from .store import connect, data_dir

SCHEMA_VERSION = "1.0"
DEFAULT_API_BASE_URL = "https://sage.api.marketingstudios.in"
FALLBACK_API_BASE_URL = "https://sage-api.pascoaldsouza28.workers.dev"
KEYRING_SERVICE = "psycgod-sage"

# 🔒 SECURITY: Master key for API key generation
# This is intentionally in the code (not in repo) and used by local CLI clients.
# If compromised, we can rotate it in Cloudflare environment variables
LEVEL_NAMES = {
    0: "local-only",
    1: "anonymous-metrics",
    2: "redacted-summaries",
    3: "team-diagnostics",
    4: "research-full-logs",
}
# Keys that must NEVER appear in a Level 1 payload.
LEVEL1_FORBIDDEN_KEYS = {"command", "stdout", "stderr", "output", "raw", "project", "path", "file"}


def config_path() -> Path:
    return data_dir() / "telemetry.json"


def _keyring_account(config: dict[str, Any]) -> str:
    return str(
        config.get("api_key_account")
        or config.get("api_key_id")
        or config.get("installation_id")
        or "default"
    )


def _keyring_get(account: str) -> str:
    try:
        import keyring

        return str(keyring.get_password(KEYRING_SERVICE, account) or "")
    except Exception:
        return ""


def _keyring_set(account: str, api_key: str) -> bool:
    try:
        import keyring

        keyring.set_password(KEYRING_SERVICE, account, api_key)
        return True
    except Exception:
        return False


def _keyring_delete(account: str) -> None:
    try:
        import keyring

        keyring.delete_password(KEYRING_SERVICE, account)
    except Exception:
        return


def resolve_api_key(config: dict[str, Any] | None = None) -> str:
    """Return the API key from keyring, with legacy config fallback."""
    config = config or load_config()
    if str(config.get("api_key_storage", "")).lower() == "keyring":
        api_key = _keyring_get(_keyring_account(config))
        if api_key:
            return api_key.strip()
    return str(config.get("api_key", "")).strip()


def _store_api_key(config: dict[str, Any], api_key: str, key_id: str) -> str:
    """Store API key in OS keyring when possible.

    If keyring is unavailable, keep a clearly marked file fallback so headless
    test and CI machines can still connect without crashing.
    """
    account = key_id or _keyring_account(config)
    config["api_key_account"] = account
    if _keyring_set(account, api_key):
        config.pop("api_key", None)
        config["api_key_storage"] = "keyring"
        return "keyring"
    config["api_key"] = api_key
    config["api_key_storage"] = "file-fallback"
    return "file-fallback"


def _delete_api_key(config: dict[str, Any]) -> None:
    account = _keyring_account(config)
    if account:
        _keyring_delete(account)
    config["api_key"] = ""
    config["api_key_account"] = ""
    config["api_key_storage"] = ""


def load_config() -> dict[str, Any]:
    path = config_path()
    if path.exists():
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            config = {}
    else:
        config = {}
    changed = False
    if "installation_id" not in config:
        config["installation_id"] = str(uuid.uuid4())
        changed = True
    if "salt" not in config:
        config["salt"] = secrets.token_hex(16)
        changed = True
    config.setdefault("telemetry_level", 0)
    config.setdefault("api_endpoint", "")
    config.setdefault("api_base_url", "")
    config.setdefault("api_key", "")
    config.setdefault("api_key_id", "")
    config.setdefault("api_key_account", "")
    config.setdefault("api_key_storage", "legacy-file" if config.get("api_key") else "")
    config.setdefault("api_profile", {})
    config.setdefault("accounts", {})
    config.setdefault("active_account", "")
    if changed:
        save_config(config)
    return config


def save_config(config: dict[str, Any]) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def effective_level(config: dict[str, Any] | None = None) -> int:
    """Strictest-wins across user setting, org policy, and key scope."""
    config = config or load_config()
    level = int(config.get("telemetry_level", 0))
    account = config.get("accounts", {}).get(config.get("active_account", ""))
    if account:
        level = min(level, int(account.get("org_max_level", 4)), int(account.get("key_max_level", 4)))
    return max(0, min(4, level))


def set_level(level: int) -> int:
    if not 0 <= level <= 4:
        raise ValueError("Telemetry level must be 0-4.")
    config = load_config()
    config["telemetry_level"] = level
    save_config(config)
    return effective_level(config)


# ---------------------------------------------------------------- accounts

def account_link(alias: str, *, user_id: str = "", org_id: str = "", api_key_ref: str = "",
                 org_max_level: int = 4, key_max_level: int = 4) -> None:
    config = load_config()
    config["accounts"][alias] = {
        "user_id": user_id,
        "org_id": org_id,
        # Reference only — the key itself belongs in the OS credential store.
        "api_key_ref": api_key_ref,
        "org_max_level": org_max_level,
        "key_max_level": key_max_level,
        "linked_at": _now(),
    }
    if not config.get("active_account"):
        config["active_account"] = alias
    save_config(config)


def account_list() -> dict[str, Any]:
    config = load_config()
    return {"active": config.get("active_account", ""), "accounts": config.get("accounts", {})}


def account_use(alias: str) -> bool:
    config = load_config()
    if alias == "anonymous":
        config["active_account"] = ""
        save_config(config)
        return True
    if alias not in config.get("accounts", {}):
        return False
    config["active_account"] = alias
    save_config(config)
    return True


def account_unlink(alias: str) -> bool:
    config = load_config()
    if alias not in config.get("accounts", {}):
        return False
    del config["accounts"][alias]
    if config.get("active_account") == alias:
        config["active_account"] = ""
    save_config(config)
    return True


def account_status() -> dict[str, Any]:
    config = load_config()
    active = config.get("active_account", "")
    return {
        "active_account": active or "anonymous",
        "installation_id": config["installation_id"],
        "user_level": int(config.get("telemetry_level", 0)),
        "effective_level": effective_level(config),
        "effective_level_name": LEVEL_NAMES[effective_level(config)],
        "api_endpoint": config.get("api_endpoint", "") or "(not configured)",
        "api_key_id": config.get("api_key_id", "") or "(not connected)",
    }


# ---------------------------------------------------------------- API login

def api_github_login(
    *,
    auth_code: str = "",
    github_access_token: str = "",
    redirect_uri: str = "",
    display_name: str | None = None,
    public_profile: bool = False,
    expiry_days: int = 30,
    base_url: str = "",
) -> dict[str, Any]:
    """
    Create SAGE API key using GitHub OAuth.

    Args:
        auth_code: GitHub OAuth authorization code
        display_name: Optional display name (defaults to GitHub name)
        public_profile: Show name on public proof
        expiry_days: API key expiration (30/60/90 days)
        base_url: Optional API base URL

    Returns:
        Dict with api_key, key_id, username, etc.
    """
    payload = {
        "github_auth_code": auth_code,
        "github_access_token": github_access_token,
        "redirect_uri": redirect_uri,
        "display_name": display_name,
        "public_profile": bool(public_profile),
        "expiry_days": max(1, min(365, int(expiry_days))),
        "scope": "personal",
    }

    last_error = ""
    for candidate in _endpoint_candidates(base_url or DEFAULT_API_BASE_URL):
        try:
            # Send to /v1/github-login endpoint (handles OAuth exchange)
            data = json.dumps(payload).encode("utf-8")
            request = urllib_request.Request(
                f"{candidate}/v1/github-login",
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "SAGE-CLI/0.1",
                },
                method="POST",
            )
            with urllib_request.urlopen(request, timeout=30) as http_response:
                body = http_response.read().decode("utf-8")
            response = json.loads(body or "{}")
        except urllib_error.HTTPError as exc:
            try:
                body = exc.read().decode("utf-8", errors="replace")
                parsed = json.loads(body or "{}")
                detail = parsed.get("detail") or parsed.get("error") or body
            except Exception:
                detail = str(exc)
            raise RuntimeError(f"SAGE API rejected GitHub login: HTTP {exc.code}: {detail}") from exc
        except OSError as exc:
            last_error = str(exc)
            continue

        api_key = str(response.get("api_key") or "")
        key_id = str(response.get("key_id") or "")
        github_username = str(response.get("github_username") or "")
        github_id = int(response.get("github_id") or 0)

        if not api_key or not key_id:
            raise RuntimeError("SAGE API did not return an API key.")

        # Save config
        config = load_config()
        config["api_base_url"] = candidate
        config["api_endpoint"] = f"{candidate}/v1/telemetry"
        config["api_key_id"] = key_id
        storage = _store_api_key(config, api_key, key_id)
        config["api_profile"] = {
            "display_name": response.get("display_name", github_username),
            "username": github_username,
            "github_id": github_id,
            "public_profile": bool(public_profile),
            "scope": "personal",
        }
        config["telemetry_level"] = 1
        save_config(config)

        # Link account
        account_link(
            github_username,
            user_id=str(github_id),
            api_key_ref=key_id,
            key_max_level=1,
        )
        account_use(github_username)

        return {
            "ok": True,
            "base_url": candidate,
            "endpoint": f"{candidate}/v1/telemetry",
            "api_key_redacted": _redact_key(api_key),
            "key_id": key_id,
            "username": github_username,
            "github_id": github_id,
            "display_name": response.get("display_name", github_username),
            "expires_at": response.get("expires_at", ""),
            "public_profile": bool(public_profile),
            "effective_level": 1,
            "effective_level_name": "Level 1 (safe metrics only)",
            "api_key_storage": storage,
        }

    raise RuntimeError(f"SAGE API unreachable. Last error: {last_error}")


def api_login(
    *,
    display_name: str = "",
    username: str = "",
    public_profile: bool = False,
    privacy_max: int = 1,
    scope: str = "personal",
    base_url: str = "",
    expiry_days: int = 30,
) -> dict[str, Any]:
    """Create a SAGE API key and store it locally."""
    raise RuntimeError("Legacy API login is disabled. Use GitHub OAuth with `sage connect`.")
    payload = {
        "display_name": display_name,
        "username": username,
        "public_profile": bool(public_profile),
        "privacy_max": max(0, min(4, int(privacy_max))),
        "scope": scope,
        "expiry_days": max(1, min(365, int(expiry_days))),  # 🔒 SECURITY: Clamp 1-365 days
    }
    last_error = ""
    for candidate in _endpoint_candidates(base_url or DEFAULT_API_BASE_URL):
        try:
            # 🔒 SECURITY: Send master key in header
            data = json.dumps(payload).encode("utf-8")
            request = urllib_request.Request(
                f"{candidate}/v1/keys",
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "SAGE-CLI/0.1",
                    "X-SAGE-Master-Key": "",
                },
                method="POST",
            )
            with urllib_request.urlopen(request, timeout=15) as http_response:
                body = http_response.read().decode("utf-8")
            response = json.loads(body or "{}")
        except OSError as exc:
            last_error = str(exc)
            continue
        api_key = str(response.get("api_key") or "")
        key_id = str(response.get("key_id") or "")
        if not api_key or not key_id:
            raise RuntimeError("SAGE API did not return an API key.")
        config = load_config()
        config["api_base_url"] = candidate
        config["api_endpoint"] = f"{candidate}/v1/telemetry"
        config["api_key_id"] = key_id
        storage = _store_api_key(config, api_key, key_id)
        config["api_profile"] = {
            "display_name": display_name,
            "username": username,
            "public_profile": bool(public_profile),
            "scope": scope,
        }
        config["telemetry_level"] = min(max(1, int(config.get("telemetry_level", 0))), int(privacy_max))
        save_config(config)
        alias = username or display_name or "sage-cloud"
        account_link(
            alias,
            user_id=username or display_name,
            api_key_ref=key_id,
            key_max_level=int(privacy_max),
        )
        account_use(alias)
        return {
            "ok": True,
            "base_url": candidate,
            "endpoint": config["api_endpoint"],
            "key_id": key_id,
            "api_key_redacted": _redact_key(api_key),
            "api_key_storage": storage,
            "public_profile": bool(public_profile),
            "effective_level": effective_level(load_config()),
        }
    raise RuntimeError(f"Could not connect to SAGE API. Last error: {last_error or 'unknown error'}")


def api_logout() -> None:
    config = load_config()
    _delete_api_key(config)
    config["api_key_id"] = ""
    config["api_profile"] = {}
    config["api_endpoint"] = ""
    config["api_base_url"] = ""
    config["telemetry_level"] = 0
    save_config(config)


def api_whoami() -> dict[str, Any]:
    config = load_config()
    profile = config.get("api_profile", {}) or {}
    api_key = resolve_api_key(config)
    return {
        "connected": bool(api_key and config.get("api_endpoint")),
        "base_url": config.get("api_base_url", "") or "(not configured)",
        "endpoint": config.get("api_endpoint", "") or "(not configured)",
        "key_id": config.get("api_key_id", "") or "(not connected)",
        "api_key": _redact_key(api_key) if api_key else "(not stored)",
        "api_key_storage": config.get("api_key_storage", "") or "(not stored)",
        "display_name": profile.get("display_name", ""),
        "username": profile.get("username", ""),
        "public_profile": bool(profile.get("public_profile", False)),
        "effective_level": effective_level(config),
        "effective_level_name": LEVEL_NAMES[effective_level(config)],
    }


# ---------------------------------------------------------------- payloads

def build_payload(run_id: int, *, level: int | None = None) -> dict[str, Any] | None:
    """Build the telemetry event for one run at the given (or effective) level."""
    config = load_config()
    level = effective_level(config) if level is None else level
    if level <= 0:
        return None

    with connect() as conn:
        run = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if run is None:
            return None
        compression = conn.execute(
            """
            SELECT original_tokens, compressed_tokens, saved_tokens
            FROM context_compression WHERE run_id = ? ORDER BY id DESC LIMIT 1
            """,
            (run_id,),
        ).fetchone()
        agent_count = conn.execute(
            "SELECT COUNT(*) FROM agent_tasks WHERE run_id = ?", (run_id,)
        ).fetchone()[0]

    original = int(compression["original_tokens"]) if compression else 0
    compressed = int(compression["compressed_tokens"]) if compression else 0
    if compressed > original:
        compressed = original
    saved = max(0, int(compression["saved_tokens"]) if compression else 0)
    account = config.get("accounts", {}).get(config.get("active_account", ""))

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "event_type": "command_completed",
        "client_id": (account or {}).get("user_id") or f"anon:{config['installation_id'][:8]}",
        "installation_id": config["installation_id"],
        "run_id_local_hash": hashlib.sha256(f"{config['salt']}:{run_id}".encode()).hexdigest(),
        "workspace_hash": str(run["workspace_hash"] or _workspace_hash(str(run["project"]), config["salt"])),
        "timestamp": _now(),
        "client_created_at": str(run["created_at"]),
        "command_kind": str(run["command_kind"] or "unknown"),
        "command_family": str(run["command_family"] or "unknown"),
        "caller": str(run["caller"] or "cli"),
        "duration_ms": int(run["duration_ms"]),
        "exit_code": int(run["exit_code"]),
        "original_tokens": original,
        "compressed_tokens": compressed,
        "saved_tokens": saved,
        "compression_ratio": round(saved / original, 4) if original else 0.0,
        "stdout_bytes": len(str(run["stdout"]).encode("utf-8", errors="replace")),
        "stderr_bytes": len(str(run["stderr"]).encode("utf-8", errors="replace")),
        "error_category": _error_category(run),
        "agent_count": int(agent_count),
        # Model version lets the server filter weak-model rows later.
        "ml_model_version": _ml_model_version(),
    }

    if level >= 2:
        redacted_summary = redact_text(str(run["summary"]))
        payload["compressed_summary"] = redacted_summary.text[:1000]
        payload["redacted_command"] = _redact_command(str(run["command"]))

    return payload


def dedupe_key(payload: dict[str, Any]) -> str:
    raw = f"{payload['installation_id']}:{payload['workspace_hash']}:{payload['run_id_local_hash']}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def queue_event(run_id: int) -> dict[str, Any] | None:
    """Build and enqueue a telemetry event; idempotent per run."""
    payload = build_payload(run_id)
    if payload is None:
        return None
    key = dedupe_key(payload)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO telemetry_queue (created_at, run_id, level, dedupe_key, payload)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(dedupe_key) DO UPDATE SET payload = excluded.payload, level = excluded.level
            """,
            (_now(), run_id, effective_level(), key, json.dumps(payload, ensure_ascii=False)),
        )
        conn.commit()
    return payload


def queue_all_runs(*, limit: int | None = None) -> dict[str, int]:
    """Queue telemetry payloads for existing runs without duplicating sent rows."""
    if effective_level() <= 0:
        return {"scanned": 0, "queued": 0, "skipped": 0}

    query = "SELECT id FROM runs ORDER BY id ASC"
    params: tuple[Any, ...] = ()
    if limit and limit > 0:
        query += " LIMIT ?"
        params = (int(limit),)

    with connect() as conn:
        rows = conn.execute(query, params).fetchall()

    queued = 0
    skipped = 0
    for row in rows:
        payload = queue_event(int(row["id"]))
        if payload is None:
            skipped += 1
        else:
            queued += 1
    return {"scanned": len(rows), "queued": queued, "skipped": skipped}


def queue_status() -> dict[str, int]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) as n FROM telemetry_queue GROUP BY status"
        ).fetchall()
    counts = {str(row["status"]): int(row["n"]) for row in rows}
    counts.setdefault("queued", 0)
    counts.setdefault("failed", 0)
    counts.setdefault("sent", 0)
    return counts


def queue_errors(limit: int = 5) -> list[dict[str, Any]]:
    """Return recent queued-event errors for diagnostics."""
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, attempts, last_error
            FROM telemetry_queue
            WHERE status = 'queued' AND last_error != ''
            ORDER BY attempts DESC, id ASC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
    return [
        {
            "id": int(row["id"]),
            "attempts": int(row["attempts"] or 0),
            "last_error": str(row["last_error"] or ""),
        }
        for row in rows
    ]


def delete_local_queue() -> int:
    with connect() as conn:
        cur = conn.execute("DELETE FROM telemetry_queue WHERE status = 'queued'")
        conn.commit()
        return int(cur.rowcount or 0)


def send_queued(*, dry_run: bool = True, limit: int = 50) -> dict[str, Any]:
    """Send queued events. Without a configured endpoint this is always a no-op."""
    config = load_config()
    endpoint = str(config.get("api_endpoint", "")).strip()
    api_key = resolve_api_key(config)
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, dedupe_key, payload FROM telemetry_queue WHERE status = 'queued' ORDER BY id ASC LIMIT ?",
            (limit,),
        ).fetchall()

    if dry_run or not endpoint or not api_key:
        return {
            "sent": 0,
            "queued": len(rows),
            "dry_run": True,
            "endpoint": endpoint or "(not configured - events stay local)",
            "preview": [json.loads(row["payload"]) for row in rows[:3]],
        }

    sent = 0
    failed = 0
    for row in rows:
        payload = json.loads(row["payload"])
        payload.setdefault("client_created_at", payload.get("timestamp") or _now())
        payload["timestamp"] = _now()
        request = urllib_request.Request(
            endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "X-SAGE-Idempotency-Key": str(row["dedupe_key"]),
                "X-SAGE-Timestamp": payload["timestamp"],
                "User-Agent": "SAGE-CLI/0.1",
            },
            method="POST",
        )
        try:
            with urllib_request.urlopen(request, timeout=15) as response:
                ok = 200 <= response.status < 300
        except urllib_error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""
            last_error = f"HTTP {exc.code}: {body or exc.reason}"
            if exc.code in {400, 409, 413}:
                failed += 1
                with connect() as conn:
                    conn.execute(
                        "UPDATE telemetry_queue SET status = 'failed', attempts = attempts + 1, last_error = ? WHERE id = ?",
                        (last_error, int(row["id"])),
                    )
                    conn.commit()
                continue
            with connect() as conn:
                conn.execute(
                    "UPDATE telemetry_queue SET attempts = attempts + 1, last_error = ? WHERE id = ?",
                    (last_error, int(row["id"])),
                )
                conn.commit()
            continue
        except OSError as exc:
            with connect() as conn:
                conn.execute(
                    "UPDATE telemetry_queue SET attempts = attempts + 1, last_error = ? WHERE id = ?",
                    (str(exc), int(row["id"])),
                )
                conn.commit()
            continue
        if ok:
            sent += 1
            with connect() as conn:
                conn.execute(
                    "UPDATE telemetry_queue SET status = 'sent', sent_at = ? WHERE id = ?",
                    (_now(), int(row["id"])),
                )
                conn.commit()
    return {
        "sent": sent,
        "failed": failed,
        "queued": queue_status().get("queued", 0),
        "dry_run": False,
        "endpoint": endpoint,
    }


def sync_all_runs(*, dry_run: bool = False, batch_size: int = 50) -> dict[str, Any]:
    """Queue all historical runs, then send queued events in batches."""
    queued = queue_all_runs()
    total_sent = 0
    last_result: dict[str, Any] = {
        "sent": 0,
        "queued": 0,
        "dry_run": dry_run,
        "endpoint": api_status()["endpoint"],
    }
    if dry_run:
        last_result = send_queued(dry_run=True, limit=batch_size)
        return {"queued_all": queued, **last_result}

    while True:
        result = send_queued(dry_run=False, limit=batch_size)
        total_sent += int(result.get("sent", 0))
        last_result = result
        remaining = queue_status().get("queued", 0)
        if (int(result.get("sent", 0)) == 0 and int(result.get("failed", 0)) == 0) or remaining == 0:
            break
    final_queue = queue_status()
    try:
        snapshot = send_proof_snapshot()
    except Exception as exc:
        snapshot = {"ok": False, "error": str(exc)}
    return {
        "queued_all": queued,
        "sent": total_sent,
        "queued": final_queue.get("queued", 0),
        "dry_run": False,
        "endpoint": last_result.get("endpoint", ""),
        "snapshot": snapshot,
    }


def build_prediction_stats(limit: int = 250) -> dict[str, Any]:
    """Build public ML proof from trained local models, with a cheap history fallback."""
    try:
        from .ml.model import SklearnFailureModel

        status = SklearnFailureModel().status()
    except Exception:
        status = {"trained": False}

    if status.get("trained"):
        metrics = status.get("metrics") or {}
        accuracy = float(metrics.get("accuracy") or 0)
        roc_auc = float(metrics.get("roc_auc") or 0)
        score = accuracy or roc_auc
        events = max(
            int(status.get("training_samples") or 0),
            int(status.get("history_samples") or 0),
        )
        if events and score:
            return {
                "events_with_prediction": events,
                "avg_prediction_score": round(max(0.0, min(1.0, score)), 4),
            }

    try:
        from .ml.family_model import FamilyFailureModel

        family_status = FamilyFailureModel().status()
    except Exception:
        family_status = {"trained": False}

    if family_status.get("trained"):
        families = family_status.get("families") or {}
        fallback = family_status.get("fallback") or {}
        family_samples = sum(int(item.get("samples") or 0) for item in families.values())
        events = max(family_samples, int(fallback.get("samples") or 0))
        if events:
            return {
                "events_with_prediction": events,
                "avg_prediction_score": 1.0,
            }

    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS events,
                COALESCE(AVG(CASE WHEN exit_code != 0 THEN 1.0 ELSE 0.0 END), 0) AS avg_failure_rate
            FROM (
                SELECT exit_code
                FROM runs
                WHERE command IS NOT NULL AND command != ''
                ORDER BY id DESC
                LIMIT ?
            )
            """,
            (limit,),
        ).fetchone()
    events = int(row["events"] or 0)
    return {
        "events_with_prediction": events,
        "avg_prediction_score": round(float(row["avg_failure_rate"] or 0), 4) if events else 0,
    }


def build_proof_snapshot() -> dict[str, Any]:
    """Build safe public proof totals from the same local counters as `sage context stats`."""
    config = load_config()
    profile = config.get("api_profile", {}) or {}
    with connect() as conn:
        token_stats = conn.execute(
            """
            SELECT
                COUNT(*) AS total_commands,
                COALESCE(SUM(estimated_tokens), 0) AS estimated_tokens,
                COALESCE(SUM(CASE WHEN savings < 0 THEN estimated_tokens ELSE compressed_tokens END), 0) AS compressed_tokens,
                COALESCE(SUM(CASE WHEN savings < 0 THEN 0 ELSE savings END), 0) AS saved_tokens
            FROM token_usage
            """
        ).fetchone()
        runs = conn.execute(
            """
            SELECT
                COUNT(*) AS total_runs,
                COALESCE(SUM(CASE WHEN exit_code = 0 THEN 1 ELSE 0 END), 0) AS successful_runs,
                COALESCE(SUM(CASE WHEN exit_code != 0 THEN 1 ELSE 0 END), 0) AS failed_runs
            FROM runs
            """
        ).fetchone()
    original = int(token_stats["estimated_tokens"] or 0)
    compressed = int(token_stats["compressed_tokens"] or 0)
    saved = int(token_stats["saved_tokens"] or 0)
    total_runs = int(token_stats["total_commands"] or 0)
    successful = min(int(runs["successful_runs"] or 0), total_runs)
    prediction_stats = build_prediction_stats()
    savings_by_model = build_model_savings(saved)
    savings_by_agent = build_agent_savings(saved)
    return {
        "display_name": "PsYc+GoD AI & ML",
        "username": profile.get("username") or "PsYcGoD",
        "totals": {
            "total_runs": total_runs,
            "successful_runs": successful,
            "failed_runs": max(0, total_runs - successful),
            "tokens_processed": original,
            "tokens_compressed": compressed,
            "tokens_saved": saved,
            "estimated_savings_usd": estimate_total_model_savings_usd(saved),
            "savings_by_model": savings_by_model,
            "savings_by_agent": savings_by_agent,
            "compression_percent": round((saved / original) * 100, 2) if original else 0,
            "success_rate": round((successful / total_runs) * 100, 2) if total_runs else 0,
            "failure_prediction_stats": prediction_stats,
        },
    }


def send_proof_snapshot() -> dict[str, Any]:
    """Publish current safe aggregate proof totals to the configured SAGE API."""
    config = load_config()
    base_url = str(config.get("api_base_url") or DEFAULT_API_BASE_URL).strip().rstrip("/")
    api_key = resolve_api_key(config)
    if not base_url or not api_key:
        return {"ok": False, "error": "not-connected"}
    payload = build_proof_snapshot()
    request = urllib_request.Request(
        f"{base_url}/v1/proof-snapshot",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "SAGE-CLI/0.1",
        },
        method="POST",
    )
    with urllib_request.urlopen(request, timeout=15) as response:
        raw = response.read().decode("utf-8")
        if response.status < 200 or response.status >= 300:
            raise OSError(f"SAGE API snapshot failed: HTTP {response.status} {raw}")
        return json.loads(raw)


def get_visitor_stats() -> dict[str, Any]:
    """Fetch private public-dashboard visitor stats using the saved SAGE API key."""
    config = load_config()
    base_url = str(config.get("api_base_url") or DEFAULT_API_BASE_URL).strip().rstrip("/")
    api_key = resolve_api_key(config)
    if not base_url or not api_key:
        raise RuntimeError("SAGE API is not connected.")
    request = urllib_request.Request(
        f"{base_url}/v1/admin/visitors",
        headers={
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "SAGE-CLI/0.1",
        },
        method="GET",
    )
    with urllib_request.urlopen(request, timeout=15) as response:
        raw = response.read().decode("utf-8")
        if response.status < 200 or response.status >= 300:
            raise OSError(f"SAGE API visitor stats failed: HTTP {response.status} {raw}")
        return json.loads(raw)


def api_status() -> dict[str, Any]:
    config = load_config()
    endpoint = str(config.get("api_endpoint", "")).strip()
    api_key = resolve_api_key(config)
    return {
        "endpoint": endpoint or "(not configured)",
        "base_url": config.get("api_base_url", "") or "(not configured)",
        "mode": "cloud-sync-possible" if endpoint and api_key else "local-only",
        "connected": bool(endpoint and api_key),
        "key_id": config.get("api_key_id", "") or "(not connected)",
        "api_key_storage": config.get("api_key_storage", "") or "(not stored)",
        "profile": config.get("api_profile", {}) or {},
        "effective_level": effective_level(config),
        "effective_level_name": LEVEL_NAMES[effective_level(config)],
        "queue": queue_status(),
    }


def _error_category(run) -> str | None:
    if int(run["exit_code"]) == 0:
        return None
    summary = str(run["summary"]).lower()
    for category in ("traceback", "assertion", "import", "dependency", "permission", "timeout", "syntax"):
        if category in summary:
            return category
    return "nonzero-exit"


def _redact_command(command: str) -> str:
    redacted = redact_text(command).text
    parts = redacted.split()
    cleaned = [
        "<path>" if ("/" in part or "\\" in part or ":" in part[1:3]) else part
        for part in parts
    ]
    return " ".join(cleaned)[:300]


def _ml_model_version() -> str:
    try:
        from .ml.model import MODEL_VERSION

        return f"v{MODEL_VERSION}"
    except Exception:
        return "none"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _endpoint_candidates(base_url: str) -> list[str]:
    candidates = [_normal_base_url(base_url)]
    fallback = _normal_base_url(FALLBACK_API_BASE_URL)
    if fallback not in candidates:
        candidates.append(fallback)
    return candidates


def _normal_base_url(value: str) -> str:
    value = (value or DEFAULT_API_BASE_URL).strip().rstrip("/")
    if not value.startswith(("http://", "https://")):
        value = f"https://{value}"
    return value


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib_request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "SAGE-CLI/0.1"},
        method="POST",
    )
    with urllib_request.urlopen(request, timeout=15) as response:
        body = response.read().decode("utf-8")
    return json.loads(body or "{}")


def _redact_key(api_key: str) -> str:
    if not api_key:
        return ""
    if len(api_key) <= 18:
        return "***"
    return f"{api_key[:18]}...{api_key[-6:]}"
