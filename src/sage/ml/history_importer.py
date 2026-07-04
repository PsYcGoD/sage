"""Import command examples from local Claude/Codex history for ML training."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from ..store import connect


COMMAND_KEYS = {"command", "cmd", "shell_command"}
COMMAND_TOOL_NAMES = {
    "bash",
    "shell",
    "terminal",
    "powershell",
    "shell_command",
    "run_command",
    "execute_command",
}
TEXT_KEYS = {"content", "text", "output", "stdout", "stderr", "message", "summary"}
EXIT_CODE_KEYS = {"exit_code", "exitCode", "returncode", "return_code", "code"}
FAILURE_RE = re.compile(r"\b(error|failed|failure|exception|traceback|not recognized|no such file)\b", re.I)
EXIT_RE = re.compile(r"\b(?:exit|return)(?:\s+code)?\s*[:=]?\s*(-?\d+)\b", re.I)


@dataclass(frozen=True)
class ImportResult:
    source: str
    scanned_files: int
    scanned_bytes: int
    found_examples: int
    inserted_examples: int
    skipped_examples: int
    dry_run: bool


@dataclass(frozen=True)
class CommandExample:
    source: str
    source_path: str
    command: str
    exit_code: int
    summary: str
    fingerprint: str


class HistoryImporter:
    """Stream local Claude/Codex histories into compact ML command examples."""

    def default_paths(self, source: str) -> list[Path]:
        home = Path.home()
        source = source.lower()
        paths: list[Path] = []

        if source in {"claude", "all"}:
            claude_home = Path(os.getenv("CLAUDE_CONFIG_DIR", str(home / ".claude")))
            paths.extend([claude_home / "projects", claude_home])

        if source in {"codex", "all"}:
            codex_home = Path(os.getenv("CODEX_HOME", str(home / ".codex")))
            paths.extend([codex_home / "sessions", codex_home])

        unique: list[Path] = []
        seen: set[Path] = set()
        for path in paths:
            try:
                resolved = path.expanduser().resolve()
            except OSError:
                resolved = path.expanduser()
            if resolved not in seen:
                seen.add(resolved)
                unique.append(resolved)
        return unique

    def import_history(
        self,
        *,
        source: str = "all",
        paths: Iterable[Path] | None = None,
        limit: int | None = None,
        dry_run: bool = False,
    ) -> ImportResult:
        source = source.lower()
        roots = list(paths or self.default_paths(source))
        scanned_files = 0
        scanned_bytes = 0
        found = 0
        inserted = 0
        skipped = 0
        batch: list[CommandExample] = []

        for path in self._iter_history_files(roots):
            if limit is not None and found >= limit:
                break
            scanned_files += 1
            try:
                scanned_bytes += path.stat().st_size
            except OSError:
                pass

            inferred_source = self._infer_source(path, source)
            for example in self._examples_from_file(path, inferred_source):
                found += 1
                batch.append(example)
                if len(batch) >= 500:
                    inserted_now = self._insert_examples(batch, dry_run=dry_run)
                    inserted += inserted_now
                    skipped += len(batch) if dry_run else len(batch) - inserted_now
                    batch = []
                if limit is not None and found >= limit:
                    break

        if batch:
            before = inserted
            inserted += self._insert_examples(batch, dry_run=dry_run)
            skipped += len(batch) if dry_run else len(batch) - (inserted - before)

        return ImportResult(
            source=source,
            scanned_files=scanned_files,
            scanned_bytes=scanned_bytes,
            found_examples=found,
            inserted_examples=0 if dry_run else inserted,
            skipped_examples=skipped,
            dry_run=dry_run,
        )

    def _iter_history_files(self, roots: Iterable[Path]) -> Iterable[Path]:
        suffixes = {".jsonl", ".json", ".log", ".txt", ".md"}
        for root in roots:
            if not root.exists():
                continue
            if root.is_file():
                if root.suffix.lower() in suffixes:
                    yield root
                continue
            for path in root.rglob("*"):
                if path.is_file() and path.suffix.lower() in suffixes:
                    yield path

    def _examples_from_file(self, path: Path, source: str) -> Iterable[CommandExample]:
        pending_command: str | None = None
        pending_summary = ""

        for obj in self._iter_json_objects(path):
            commands = list(self._extract_commands(obj))
            exit_code = self._extract_exit_code(obj)
            text = self._extract_text(obj)
            if exit_code is None and text:
                exit_code = self._exit_code_from_text(text)

            if pending_command and exit_code is not None:
                yield self._example(source, path, pending_command, exit_code, text or pending_summary)
                pending_command = None
                pending_summary = ""

            for command in commands:
                if exit_code is not None:
                    yield self._example(source, path, command, exit_code, text)
                else:
                    pending_command = command
                    pending_summary = text

    def _iter_json_objects(self, path: Path) -> Iterable[Any]:
        try:
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    try:
                        yield json.loads(stripped)
                    except json.JSONDecodeError:
                        yield {"text": stripped}
        except OSError:
            return

    def _extract_commands(self, obj: Any) -> Iterable[str]:
        if isinstance(obj, dict):
            name = str(obj.get("name") or obj.get("tool_name") or obj.get("tool") or "").lower()
            input_obj = obj.get("input") if isinstance(obj.get("input"), dict) else {}
            if name in COMMAND_TOOL_NAMES:
                for key in COMMAND_KEYS:
                    value = input_obj.get(key) if isinstance(input_obj, dict) else None
                    if isinstance(value, str) and self._looks_like_command(value):
                        yield value.strip()

            for key, value in obj.items():
                if key in COMMAND_KEYS and isinstance(value, str) and self._looks_like_command(value):
                    yield value.strip()
                elif key == "arguments" and isinstance(value, str):
                    try:
                        decoded = json.loads(value)
                    except json.JSONDecodeError:
                        decoded = None
                    if isinstance(decoded, dict):
                        yield from self._extract_commands(decoded)
                else:
                    yield from self._extract_commands(value)
        elif isinstance(obj, list):
            for item in obj:
                yield from self._extract_commands(item)

    def _extract_exit_code(self, obj: Any) -> int | None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in EXIT_CODE_KEYS and isinstance(value, int):
                    return int(value)
                if key in {"is_error", "error"} and isinstance(value, bool) and value:
                    return 1
                found = self._extract_exit_code(value)
                if found is not None:
                    return found
        elif isinstance(obj, list):
            for item in obj:
                found = self._extract_exit_code(item)
                if found is not None:
                    return found
        return None

    def _extract_text(self, obj: Any, *, max_chars: int = 2000) -> str:
        parts: list[str] = []

        def walk(value: Any) -> None:
            if len(" ".join(parts)) >= max_chars:
                return
            if isinstance(value, dict):
                for key, nested in value.items():
                    if key in TEXT_KEYS and isinstance(nested, str):
                        parts.append(nested[:max_chars])
                    else:
                        walk(nested)
            elif isinstance(value, list):
                for item in value:
                    walk(item)

        walk(obj)
        return "\n".join(parts)[:max_chars]

    def _exit_code_from_text(self, text: str) -> int | None:
        match = EXIT_RE.search(text)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        if FAILURE_RE.search(text):
            return 1
        if text.strip():
            return 0
        return None

    def _looks_like_command(self, value: str) -> bool:
        text = value.strip()
        if len(text) < 2 or len(text) > 4000:
            return False
        first = text.split(maxsplit=1)[0].lower()
        known = {
            "python", "py", "pytest", "git", "npm", "npx", "node", "pnpm", "yarn",
            "pip", "uv", "cargo", "go", "dart", "flutter", "sage", "codex", "claude",
            "rg", "type", "dir", "powershell", "cmd", "curl", "docker", "make",
        }
        return first in known or any(token in text for token in (" --", " -", "\\", "/", ".py", ".js"))

    def _example(self, source: str, path: Path, command: str, exit_code: int, summary: str) -> CommandExample:
        normalized_exit = 0 if int(exit_code) == 0 else 1
        source_path = str(path)
        digest = hashlib.sha256(f"{source}\0{source_path}\0{command}\0{normalized_exit}".encode("utf-8", "replace")).hexdigest()
        return CommandExample(
            source=source,
            source_path=source_path,
            command=command.strip(),
            exit_code=normalized_exit,
            summary=(summary or "")[:500],
            fingerprint=digest,
        )

    def _insert_examples(self, examples: list[CommandExample], *, dry_run: bool) -> int:
        if dry_run or not examples:
            return 0
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with connect() as conn:
            before = conn.total_changes
            conn.executemany(
                """
                INSERT OR IGNORE INTO ml_training_examples
                  (created_at, source, source_path, command, exit_code, summary, fingerprint)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (now, item.source, item.source_path, item.command, item.exit_code, item.summary, item.fingerprint)
                    for item in examples
                ],
            )
            conn.commit()
            return conn.total_changes - before

    def _infer_source(self, path: Path, requested_source: str) -> str:
        if requested_source != "all":
            return requested_source
        lowered = str(path).lower()
        if ".claude" in lowered:
            return "claude"
        if ".codex" in lowered:
            return "codex"
        return "unknown"
