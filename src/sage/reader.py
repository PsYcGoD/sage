"""`sage read` — measurable, compressible, raw-recoverable file reads.

Small files print exactly. Large files print an outline (imports, symbols,
headings) plus the head of the file under a token budget, with stable line
references so an agent can request exact ranges next. Every read is stored
as a run (kind="read") with token savings recorded like any other command.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from .classify import workspace_hash
from .context.tokens import count_tokens
from .security import command_hash, load_policy, redact_text, retention_expiry
from .store import save_run

DEFAULT_MAX_TOKENS = 1_500

_LANGUAGES = {
    ".py": "python", ".js": "javascript", ".ts": "typescript", ".tsx": "typescript",
    ".jsx": "javascript", ".md": "markdown", ".json": "json", ".yaml": "yaml",
    ".yml": "yaml", ".toml": "toml", ".html": "html", ".css": "css", ".rs": "rust",
    ".go": "go", ".java": "java", ".cs": "csharp", ".ps1": "powershell", ".sh": "shell",
}

_SYMBOL_PATTERNS = {
    "python": re.compile(r"^\s*(?:class|def)\s+\w+|^(?:import|from)\s+\S+"),
    "javascript": re.compile(r"^\s*(?:export\s+)?(?:class|function|const|let)\s+\w+|^import\s"),
    "typescript": re.compile(r"^\s*(?:export\s+)?(?:class|function|interface|type|const)\s+\w+|^import\s"),
    "markdown": re.compile(r"^#{1,6}\s"),
    "yaml": re.compile(r"^\w[\w.-]*:"),
    "json": re.compile(r"^\s{0,4}\"[\w.-]+\":"),
    "toml": re.compile(r"^\[[\w.\"-]+\]|^\w[\w.-]*\s*="),
}


@dataclass
class ReadResult:
    path: str
    exists: bool
    output: str = ""
    error: str = ""
    bytes: int = 0
    lines: int = 0
    language: str = "unknown"
    original_tokens: int = 0
    shown_tokens: int = 0
    mode: str = "exact"
    symbols: list[str] = field(default_factory=list)

    @property
    def saved_tokens(self) -> int:
        return max(0, self.original_tokens - self.shown_tokens)


def read_file(
    path_text: str,
    *,
    lines: str = "",
    max_tokens: int = DEFAULT_MAX_TOKENS,
    raw: bool = False,
    symbols_only: bool = False,
) -> ReadResult:
    path = Path(path_text)
    if not path.exists() or not path.is_file():
        return ReadResult(path=path_text, exists=False, error=f"File not found: {path_text}")

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return ReadResult(path=path_text, exists=False, error=f"Cannot read {path_text}: {exc}")

    all_lines = text.splitlines()
    language = _LANGUAGES.get(path.suffix.lower(), "unknown")
    result = ReadResult(
        path=str(path),
        exists=True,
        bytes=len(text.encode("utf-8", errors="replace")),
        lines=len(all_lines),
        language=language,
        original_tokens=count_tokens(text),
    )
    result.symbols = _extract_symbols(all_lines, language)

    if lines:
        start, end = _parse_range(lines, len(all_lines))
        selected = all_lines[start - 1:end]
        result.output = _numbered(selected, start)
        result.mode = f"lines {start}:{end}"
    elif symbols_only:
        result.output = "\n".join(result.symbols) or "(no symbols detected)"
        result.mode = "symbols"
    elif raw or result.original_tokens <= max_tokens:
        result.output = _numbered(all_lines, 1)
        result.mode = "exact" if not raw else "raw"
    else:
        result.output = _compressed_view(all_lines, result, max_tokens)
        result.mode = "compressed"

    result.shown_tokens = count_tokens(result.output)
    return result


def save_read_run(result: ReadResult, *, caller: str = "cli") -> int:
    """Persist the read as a run so history/telemetry/proof see it."""
    import os
    command_text = f"sage read -- {result.path}"
    strictness = str(load_policy().get("redaction_strictness") or "standard")
    shown = redact_text(result.output, strictness=strictness)
    summary = (
        f"read {result.path} [{result.language}] {result.lines} lines, {result.bytes} bytes; "
        f"mode={result.mode}; tokens {result.original_tokens} -> {result.shown_tokens}"
    )

    # Inherit session context from environment
    session_id = os.environ.get("SAGE_SESSION_ID", "")
    is_ai_session = 1 if session_id or caller == "mcp" else 0

    return save_run(
        project=str(Path.cwd()),
        command=command_text,
        exit_code=0 if result.exists else 1,
        duration_ms=0,
        stdout=shown.text,
        stderr=result.error,
        summary=summary,
        stdout_redactions=shown.count,
        command_sha256=command_hash(command_text),
        retention_expires_at=retention_expiry(),
        command_kind="read",
        command_family=result.language,
        caller=caller,
        workspace_hash=workspace_hash(str(Path.cwd())),
        session_id=session_id,
        is_ai_session=is_ai_session,
    )


def _parse_range(spec: str, total: int) -> tuple[int, int]:
    match = re.match(r"^(\d+):(\d+)$", spec.strip())
    if not match:
        raise ValueError(f"Invalid --lines value '{spec}'. Use START:END, e.g. 120:220.")
    start = max(1, int(match.group(1)))
    end = min(total, int(match.group(2)))
    if end < start:
        raise ValueError(f"--lines end ({end}) is before start ({start}).")
    return start, end


def _numbered(lines: list[str], start: int) -> str:
    return "\n".join(f"{index:>5}\t{line}" for index, line in enumerate(lines, start))


def _extract_symbols(lines: list[str], language: str) -> list[str]:
    pattern = _SYMBOL_PATTERNS.get(language)
    if not pattern:
        return []
    return [
        f"{index:>5}\t{line.strip()[:160]}"
        for index, line in enumerate(lines, 1)
        if pattern.match(line)
    ][:200]


def _compressed_view(all_lines: list[str], result: ReadResult, max_tokens: int) -> str:
    parts = [
        f"# {result.path} [{result.language}] {result.lines} lines, {result.bytes} bytes, "
        f"{result.original_tokens} tokens (compressed view; use --raw or --lines START:END for exact content)",
    ]
    if result.symbols:
        parts.append("## Outline")
        parts.extend(result.symbols[:80])
    parts.append("## Head")
    head: list[str] = []
    used = count_tokens("\n".join(parts))
    for index, line in enumerate(all_lines, 1):
        used += count_tokens(line) + 1
        if used >= max_tokens:
            head.append(f"... [{result.lines - index + 1} more lines; read exact ranges with --lines]")
            break
        head.append(f"{index:>5}\t{line}")
    parts.extend(head)
    return "\n".join(parts)
