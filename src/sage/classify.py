"""Shared command classification for run/read/grep/call and telemetry.

One pure function so the runner, telemetry payloads, ML features, and the
agent planner never disagree about what a command was. Classification must
never block execution: unknown commands classify as ("run", first-token).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

KINDS = (
    "read",
    "grep",
    "write",
    "edit",
    "glob",
    "tree",
    "test",
    "build",
    "install",
    "lint",
    "git",
    "network",
    "run",
    "call",
    "unknown",
)

_READ_TOOLS = {"cat", "type", "get-content", "gc", "head", "tail", "more", "less", "bat"}
_GREP_TOOLS = {"rg", "grep", "select-string", "findstr", "sls", "ag", "ack"}
_TEST_TOKENS = {"pytest", "unittest", "jest", "vitest", "mocha", "nose2", "tox"}
_BUILD_TOKENS = {"make", "cmake", "cargo", "gradle", "gradlew", "maven", "mvn", "msbuild", "webpack", "vite", "tsc", "dotnet"}
_LINT_TOKENS = {"ruff", "flake8", "pylint", "eslint", "black", "isort", "mypy", "prettier", "clang-format"}
_INSTALL_MANAGERS = {"pip", "pip3", "npm", "pnpm", "yarn", "uv", "poetry", "conda", "choco", "winget", "apt", "apt-get", "brew"}
_NETWORK_TOOLS = {"curl", "wget", "ping", "ssh", "scp", "telnet", "nslookup", "invoke-webrequest", "iwr", "invoke-restmethod", "irm"}


@dataclass(frozen=True)
class CommandClass:
    kind: str
    family: str


def _tokens(command: str) -> list[str]:
    try:
        cleaned = re.sub(r"[\"']", " ", command)
        return [token.lower() for token in cleaned.split() if token.strip()]
    except Exception:
        return []


def classify_command(command: str) -> CommandClass:
    """Classify a shell command into (kind, family). Never raises."""
    tokens = _tokens(command or "")
    if not tokens:
        return CommandClass("unknown", "unknown")

    # Skip wrappers to classify the real work: sage run -- pytest, python -m pytest
    significant = [t for t in tokens if t not in {"sage", "run", "call", "--", "-m", "-q", "-u"}]
    head = significant[0] if significant else tokens[0]
    head_base = head.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].removesuffix(".exe").removesuffix(".cmd")
    token_set = set(tokens)

    if head_base in _READ_TOOLS:
        return CommandClass("read", head_base)
    if head_base in _GREP_TOOLS or token_set & _GREP_TOOLS:
        return CommandClass("grep", head_base if head_base in _GREP_TOOLS else next(iter(token_set & _GREP_TOOLS)))
    if token_set & _TEST_TOKENS:
        return CommandClass("test", next(iter(token_set & _TEST_TOKENS)))
    if head_base == "git" or (head_base in {"gh"} and "pr" not in token_set):
        return CommandClass("git", head_base)
    if head_base in _INSTALL_MANAGERS:
        if any(t in token_set for t in ("install", "add", "sync", "update", "upgrade", "ci")):
            return CommandClass("install", head_base)
        if any(t in token_set for t in ("test", "run")) and head_base in {"npm", "pnpm", "yarn"}:
            return CommandClass("test" if "test" in token_set else "run", head_base)
        return CommandClass("run", head_base)
    if head_base in _LINT_TOKENS or token_set & _LINT_TOKENS:
        return CommandClass("lint", head_base if head_base in _LINT_TOKENS else next(iter(token_set & _LINT_TOKENS)))
    if head_base in _BUILD_TOKENS or ("build" in token_set and head_base not in {"echo"}):
        return CommandClass("build", head_base)
    if head_base in _NETWORK_TOOLS:
        return CommandClass("network", head_base)
    if head_base in {"python", "python3", "py", "node", "deno", "bun"}:
        return CommandClass("run", head_base)
    return CommandClass("run", head_base)


# Tools whose exit code 1 means "no result", not "failure".
# grep/rg/findstr/Select-String: 1 = no matches (2+ = real error).
# diff/cmp: 1 = files differ (2+ = real error).
_EXIT1_IS_NO_MATCH = {"grep", "rg", "findstr", "select-string", "egrep", "fgrep", "diff", "cmp"}


def label_failure(command: str, exit_code: int) -> int:
    """Family-aware failure label: 1 = real failure, 0 = success.

    Plain ``exit_code != 0`` mislabels search tools where exit 1 only means
    "no matches found" — that is a successful search, not a failure. Training
    on those labels buries the real failure signal in noise.
    """
    code = int(exit_code)
    if code == 0:
        return 0
    if code == 1 and classify_command(command).family in _EXIT1_IS_NO_MATCH:
        return 0
    return 1


def workspace_hash(path: str, salt: str = "") -> str:
    """Anonymized repo/project identity: sha256(salt + normalized path)."""
    normalized = str(path or "").strip().lower().replace("\\", "/").rstrip("/")
    return hashlib.sha256(f"{salt}{normalized}".encode("utf-8")).hexdigest()


def command_fingerprint(command: str) -> str:
    """Stable fingerprint that groups trivially-varying commands."""
    normalized = re.sub(r"\s+", " ", (command or "").strip().lower())
    normalized = re.sub(r"\d+", "N", normalized)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
