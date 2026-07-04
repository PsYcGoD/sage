"""`sage write`, `sage edit`, `sage glob`, `sage tree` — token-cheap file operations.

The token savings come from what these commands DON'T print:

- write: confirms with path + bytes + lines + sha256 instead of echoing content
- edit:  prints a compact change summary instead of the whole file, and
         snapshots the pre-edit content so any edit is reversible
- glob:  returns capped, mtime-sorted paths instead of a recursive dir dump
- tree:  returns a depth-limited outline instead of `ls -R` noise

Every operation is stored as a run so history, telemetry counters, and
proof metrics see it like any other command.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .classify import workspace_hash
from .context.tokens import count_tokens
from .security import command_hash, load_policy, redact_text, retention_expiry
from .store import data_dir, save_run

_SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build",
    ".idea", ".vscode", ".mypy_cache", ".ruff_cache", ".pytest_cache", ".tox",
}


# ------------------------------------------------------------------- write

@dataclass
class WriteResult:
    path: str
    ok: bool
    created: bool = False
    overwritten: bool = False
    bytes: int = 0
    lines: int = 0
    sha256: str = ""
    content_tokens: int = 0
    error: str = ""
    snapshot: str = ""


def write_file(
    path_text: str,
    content: str,
    *,
    overwrite: bool = False,
    mkdir: bool = True,
    append: bool = False,
) -> WriteResult:
    path = Path(path_text)
    existed = path.exists()

    if existed and not (overwrite or append):
        return WriteResult(
            path=str(path), ok=False,
            error=f"{path} already exists. Use --overwrite to replace it or --append to add to it.",
        )
    if existed and path.is_dir():
        return WriteResult(path=str(path), ok=False, error=f"{path} is a directory.")

    result = WriteResult(path=str(path), ok=False)
    try:
        if existed and (overwrite or append):
            # Snapshot the previous content so the write is reversible.
            result.snapshot = _snapshot_file(path)
        if mkdir:
            path.parent.mkdir(parents=True, exist_ok=True)
        if append and existed:
            previous = path.read_text(encoding="utf-8", errors="replace")
            content = previous + content
        path.write_text(content, encoding="utf-8", newline="\n")
    except OSError as exc:
        result.error = str(exc)
        return result

    # Verify by reading back.
    written = path.read_text(encoding="utf-8", errors="replace")
    if written != content:
        result.error = "Verification failed: written content does not match."
        return result

    result.ok = True
    result.created = not existed
    result.overwritten = existed and not append
    result.bytes = len(written.encode("utf-8", errors="replace"))
    result.lines = len(written.splitlines())
    result.sha256 = hashlib.sha256(written.encode("utf-8", errors="replace")).hexdigest()
    result.content_tokens = count_tokens(written)
    return result


# -------------------------------------------------------------------- edit

@dataclass
class EditResult:
    path: str
    ok: bool
    replacements: int = 0
    changed_lines: list[int] = field(default_factory=list)
    preview: str = ""
    error: str = ""
    snapshot: str = ""
    file_tokens: int = 0
    shown_tokens: int = 0


def edit_file(
    path_text: str,
    old: str,
    new: str,
    *,
    replace_all: bool = False,
) -> EditResult:
    path = Path(path_text)
    result = EditResult(path=str(path), ok=False)

    if not path.exists() or not path.is_file():
        result.error = f"File not found: {path}"
        return result
    if old == new:
        result.error = "old and new are identical - nothing to do."
        return result
    if not old:
        result.error = "old must not be empty."
        return result

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        result.error = str(exc)
        return result

    occurrences = text.count(old)
    if occurrences == 0:
        result.error = "old string not found in file (must match exactly, including whitespace)."
        return result
    if occurrences > 1 and not replace_all:
        result.error = f"old string appears {occurrences} times. Make it unique or pass --all."
        return result

    result.snapshot = _snapshot_file(path)
    updated = text.replace(old, new) if replace_all else text.replace(old, new, 1)
    try:
        path.write_text(updated, encoding="utf-8", newline="\n")
    except OSError as exc:
        result.error = str(exc)
        return result

    result.ok = True
    result.replacements = occurrences if replace_all else 1
    result.changed_lines = _changed_lines(text, updated)
    result.preview = _change_preview(updated.splitlines(), result.changed_lines)
    result.file_tokens = count_tokens(updated)
    result.shown_tokens = count_tokens(result.preview)
    return result


def _changed_lines(before: str, after: str) -> list[int]:
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    changed = [
        index
        for index, (a, b) in enumerate(zip(before_lines, after_lines), 1)
        if a != b
    ]
    longest = max(len(before_lines), len(after_lines))
    shortest = min(len(before_lines), len(after_lines))
    changed.extend(range(shortest + 1, longest + 1))
    return changed[:50]


def _change_preview(lines: list[str], changed: list[int], context: int = 2) -> str:
    if not changed:
        return "(no line-level change detected)"
    shown: dict[int, str] = {}
    for line_no in changed[:10]:
        for index in range(max(1, line_no - context), min(len(lines), line_no + context) + 1):
            shown[index] = lines[index - 1]
    parts = []
    previous = 0
    for index in sorted(shown):
        if previous and index > previous + 1:
            parts.append("  ...")
        marker = ">" if index in changed else " "
        parts.append(f"{marker}{index:>5}\t{shown[index]}")
        previous = index
    return "\n".join(parts)


# ---------------------------------------------------------------- snapshots

def _snapshot_file(path: Path) -> str:
    """Save the current file content so the operation is reversible."""
    folder = data_dir() / "file-snapshots"
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    safe_name = path.name[:80]
    snapshot = folder / f"{stamp}-{safe_name}.json"
    snapshot.write_text(
        json.dumps(
            {
                "path": str(path.resolve()),
                "saved_at": stamp,
                "content": path.read_text(encoding="utf-8", errors="replace"),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return str(snapshot)


def restore_snapshot(snapshot_path: str) -> tuple[bool, str]:
    """Write a snapshot's content back to its original file."""
    snapshot = Path(snapshot_path)
    if not snapshot.exists():
        return False, f"Snapshot not found: {snapshot_path}"
    try:
        data = json.loads(snapshot.read_text(encoding="utf-8"))
        target = Path(data["path"])
        target.write_text(data["content"], encoding="utf-8", newline="\n")
        return True, f"Restored {target} from {snapshot.name}"
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        return False, str(exc)


# -------------------------------------------------------------------- glob

@dataclass
class GlobResult:
    pattern: str
    root: str
    files: list[tuple[str, int, float]] = field(default_factory=list)  # path, bytes, mtime
    total_found: int = 0
    error: str = ""


def glob_files(pattern: str, root: str = ".", *, limit: int = 50) -> GlobResult:
    result = GlobResult(pattern=pattern, root=root)
    base = Path(root)
    if not base.exists():
        result.error = f"Root not found: {root}"
        return result

    matched: list[tuple[str, int, float]] = []
    if "**" in pattern or "/" in pattern or "\\" in pattern:
        candidates = base.glob(pattern)
    else:
        candidates = base.rglob(pattern)
    for path in candidates:
        if not path.is_file() or _SKIP_DIRS & set(path.parts):
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        matched.append((str(path), stat.st_size, stat.st_mtime))

    matched.sort(key=lambda item: -item[2])  # newest first
    result.total_found = len(matched)
    result.files = matched[:limit]
    return result


def render_glob(result: GlobResult) -> str:
    if result.error:
        return f"sage glob error: {result.error}"
    if not result.total_found:
        return f"No files match {result.pattern!r} under {result.root}."
    lines = [f"{result.total_found} files match {result.pattern!r} (newest first)"]
    for path, size, mtime in result.files:
        stamp = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        lines.append(f"  {path}  ({size:,} B, {stamp})")
    hidden = result.total_found - len(result.files)
    if hidden > 0:
        lines.append(f"... [{hidden} more; raise --limit or narrow the pattern]")
    return "\n".join(lines)


# -------------------------------------------------------------------- tree

def tree_view(root: str = ".", *, depth: int = 3, limit: int = 200) -> str:
    base = Path(root)
    if not base.exists():
        return f"sage tree error: root not found: {root}"

    lines: list[str] = [str(base.resolve())]
    count = 0
    truncated = False

    def walk(folder: Path, level: int) -> None:
        nonlocal count, truncated
        if level > depth or truncated:
            return
        try:
            entries = sorted(folder.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except OSError:
            return
        dirs = [e for e in entries if e.is_dir() and e.name not in _SKIP_DIRS and not e.name.startswith(".")]
        files = [e for e in entries if e.is_file()]
        for entry in dirs:
            if count >= limit:
                truncated = True
                return
            child_files = sum(1 for _ in entry.glob("*") if _.is_file())
            lines.append(f"{'  ' * level}{entry.name}/ ({child_files} files)")
            count += 1
            walk(entry, level + 1)
        shown_files = files[:12] if level > 1 else files
        for entry in shown_files:
            if count >= limit:
                truncated = True
                return
            lines.append(f"{'  ' * level}{entry.name}")
            count += 1
        if len(files) > len(shown_files):
            lines.append(f"{'  ' * level}... [{len(files) - len(shown_files)} more files]")

    walk(base, 1)
    if truncated:
        lines.append(f"... [output capped at {limit} entries; use --depth/--limit to adjust]")
    return "\n".join(lines)


# ------------------------------------------------------------ run recording

def save_fileop_run(
    *,
    kind: str,
    command_text: str,
    output: str,
    exit_code: int,
    summary: str,
    family: str = "sage",
    caller: str = "cli",
) -> int:
    import os
    strictness = str(load_policy().get("redaction_strictness") or "standard")
    shown = redact_text(output, strictness=strictness)

    # Inherit session context from environment
    session_id = os.environ.get("SAGE_SESSION_ID", "")
    is_ai_session = 1 if session_id or caller == "mcp" else 0

    return save_run(
        project=str(Path.cwd()),
        command=command_text,
        exit_code=exit_code,
        duration_ms=0,
        stdout=shown.text,
        stderr="",
        summary=summary,
        stdout_redactions=shown.count,
        command_sha256=command_hash(command_text),
        retention_expires_at=retention_expiry(),
        command_kind=kind,
        command_family=family,
        caller=caller,
        workspace_hash=workspace_hash(str(Path.cwd())),
        session_id=session_id,
        is_ai_session=is_ai_session,
    )
