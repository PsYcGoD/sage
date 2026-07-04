"""`sage grep` — search with compressed, navigable output.

Uses ripgrep when available, falls back to a pure-Python walker. Output is
grouped by file with per-file caps so noisy result sets stay readable while
paths and line numbers stay exact. Exit codes follow grep semantics:
0 = matches found, 1 = no matches, 2 = error.
"""

from __future__ import annotations

import fnmatch
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .classify import workspace_hash
from .context.tokens import count_tokens
from .security import command_hash, load_policy, redact_text, retention_expiry
from .store import save_run

MAX_MATCHES_PER_FILE = 8
MAX_FILES_SHOWN = 40
_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", ".idea", ".mypy_cache", ".ruff_cache"}


@dataclass
class GrepResult:
    pattern: str
    paths: list[str]
    engine: str = "python"
    matches: dict[str, list[tuple[int, str]]] = field(default_factory=dict)
    match_count: int = 0
    hidden_matches: int = 0
    error: str = ""
    exit_code: int = 1

    @property
    def matched_files(self) -> int:
        return len(self.matches)


def search(
    pattern: str,
    paths: list[str],
    *,
    glob: str = "",
    ignore_case: bool = False,
    context: int = 0,
    files_with_matches: bool = False,
) -> GrepResult:
    result = GrepResult(pattern=pattern, paths=paths or ["."])
    rg = shutil.which("rg")
    try:
        if rg:
            result.engine = "rg"
            _search_rg(rg, result, glob=glob, ignore_case=ignore_case)
            if result.match_count == 0:
                result.engine = "python"
                _search_python(result, glob=glob, ignore_case=ignore_case)
        else:
            _search_python(result, glob=glob, ignore_case=ignore_case)
    except re.error as exc:
        result.error = f"Invalid pattern: {exc}"
        result.exit_code = 2
        return result
    except OSError as exc:
        result.error = str(exc)
        result.exit_code = 2
        return result

    result.exit_code = 0 if result.match_count else 1
    return result


def render(result: GrepResult, *, files_with_matches: bool = False, count_only: bool = False) -> str:
    if result.error:
        return f"sage grep error: {result.error}"
    if not result.match_count:
        return f"No matches for {result.pattern!r} in {', '.join(result.paths)}."

    lines = [
        f"{result.match_count} matches in {result.matched_files} files "
        f"(engine={result.engine}"
        + (f", {result.hidden_matches} more matches hidden - narrow the pattern or path" if result.hidden_matches else "")
        + ")"
    ]
    if count_only:
        for file, hits in result.matches.items():
            lines.append(f"{file}: {len(hits)}")
        return "\n".join(lines)
    for file, hits in list(result.matches.items())[:MAX_FILES_SHOWN]:
        if files_with_matches:
            lines.append(file)
            continue
        lines.append(f"\n{file}")
        for line_no, text in hits:
            lines.append(f"  {line_no}: {text.strip()[:240]}")
    shown_files = min(result.matched_files, MAX_FILES_SHOWN)
    if result.matched_files > shown_files:
        lines.append(f"... [{result.matched_files - shown_files} more files hidden]")
    return "\n".join(lines)


def save_grep_run(result: GrepResult, rendered: str, raw_output: str, *, caller: str = "cli") -> int:
    import os
    command_text = f"sage grep -- {result.pattern} {' '.join(result.paths)}"
    strictness = str(load_policy().get("redaction_strictness") or "standard")
    shown = redact_text(rendered, strictness=strictness)
    raw_tokens = count_tokens(raw_output)
    shown_tokens = count_tokens(rendered)
    summary = (
        f"grep {result.pattern!r}: {result.match_count} matches, {result.matched_files} files, "
        f"engine={result.engine}; tokens {raw_tokens} -> {shown_tokens}"
    )

    # Inherit session context from environment
    session_id = os.environ.get("SAGE_SESSION_ID", "")
    is_ai_session = 1 if session_id or caller == "mcp" else 0

    return save_run(
        project=str(Path.cwd()),
        command=command_text,
        exit_code=result.exit_code,
        duration_ms=0,
        stdout=shown.text,
        stderr=result.error,
        summary=summary,
        stdout_redactions=shown.count,
        command_sha256=command_hash(command_text),
        retention_expires_at=retention_expiry(),
        command_kind="grep",
        command_family=result.engine,
        caller=caller,
        workspace_hash=workspace_hash(str(Path.cwd())),
        session_id=session_id,
        is_ai_session=is_ai_session,
    )


def _record_match(result: GrepResult, file: str, line_no: int, text: str) -> None:
    result.match_count += 1
    bucket = result.matches.setdefault(file, [])
    if len(bucket) < MAX_MATCHES_PER_FILE:
        bucket.append((line_no, text))
    else:
        result.hidden_matches += 1


def _search_rg(rg: str, result: GrepResult, *, glob: str, ignore_case: bool) -> None:
    args = [rg, "--line-number", "--no-heading", "--color", "never", "--max-columns", "300", "--hidden"]
    for skip_dir in sorted(_SKIP_DIRS):
        args.extend(["--glob", f"!**/{skip_dir}/**"])
    if ignore_case:
        args.append("--ignore-case")
    if glob:
        args.extend(["--glob", glob])
    args.extend(["--regexp", result.pattern])
    args.extend(result.paths)
    completed = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    if completed.returncode == 2:
        raise OSError(completed.stderr.strip() or "ripgrep failed")
    for line in completed.stdout.splitlines():
        parts = line.split(":", 2)
        if len(parts) == 3 and parts[1].isdigit():
            _record_match(result, parts[0], int(parts[1]), parts[2])


def _search_python(result: GrepResult, *, glob: str, ignore_case: bool) -> None:
    regex = re.compile(result.pattern, re.IGNORECASE if ignore_case else 0)
    for base in result.paths:
        base_path = Path(base)
        candidates = [base_path] if base_path.is_file() else [
            p for p in base_path.rglob(glob or "*")
            if p.is_file() and not (_SKIP_DIRS & set(part for part in p.parts))
        ]
        for path in candidates:
            if glob and not fnmatch.fnmatch(path.name, glob):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if "\x00" in text[:1024]:
                continue
            for line_no, line in enumerate(text.splitlines(), 1):
                if regex.search(line):
                    _record_match(result, str(path), line_no, line)
