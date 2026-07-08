"""Auto-fix pipeline — matches error patterns to known fix strategies."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class FixSuggestion:
    """A suggested fix for a failed command."""
    strategy: str
    fix_command: str
    explanation: str
    confidence: float
    destructive: bool = False


# Pattern → fix strategy mappings
_FIX_PATTERNS: list[tuple[re.Pattern, callable]] = []


def _pattern(regex: str, flags=re.IGNORECASE):
    """Decorator to register a fix pattern."""
    def decorator(fn):
        _FIX_PATTERNS.append((re.compile(regex, flags), fn))
        return fn
    return decorator


@_pattern(r"ModuleNotFoundError: No module named ['\"]([^'\"]+)['\"]")
def _fix_missing_module(match, command: str, stderr: str) -> FixSuggestion:
    module = match.group(1).split(".")[0]
    return FixSuggestion(
        strategy="install_module",
        fix_command=f"pip install {module}",
        explanation=f"Module '{module}' is not installed",
        confidence=0.85,
    )


@_pattern(r"ImportError: cannot import name ['\"]([^'\"]+)['\"]")
def _fix_import_error(match, command: str, stderr: str) -> FixSuggestion:
    name = match.group(1)
    return FixSuggestion(
        strategy="check_import",
        fix_command=f"pip install --upgrade {name}",
        explanation=f"Cannot import '{name}' — may need package upgrade",
        confidence=0.6,
    )


@_pattern(r"Permission denied|EACCES")
def _fix_permission(match, command: str, stderr: str) -> FixSuggestion:
    return FixSuggestion(
        strategy="permission",
        fix_command=f"sudo {command}" if not command.startswith("sudo") else command,
        explanation="Permission denied — may need elevated privileges",
        confidence=0.7,
        destructive=True,
    )


@_pattern(r"(?:address already in use|EADDRINUSE|port\s+\d+\s+.*(?:in use|busy))", flags=re.IGNORECASE)
def _fix_port_in_use(match, command: str, stderr: str) -> FixSuggestion:
    port_match = re.search(r"port\s+(\d+)", stderr, re.IGNORECASE)
    port = port_match.group(1) if port_match else "?"
    return FixSuggestion(
        strategy="port_in_use",
        fix_command=f"npx kill-port {port}" if port != "?" else "netstat -tlnp | grep LISTEN",
        explanation=f"Port {port} is already in use by another process",
        confidence=0.8,
    )


@_pattern(r"CONFLICT.*Merge conflict|merge conflict", flags=re.IGNORECASE)
def _fix_git_conflict(match, command: str, stderr: str) -> FixSuggestion:
    return FixSuggestion(
        strategy="git_conflict",
        fix_command="git status",
        explanation="Git merge conflict detected — resolve conflicts then continue",
        confidence=0.9,
    )


@_pattern(r"FAILED.*test|tests?\s+failed|AssertionError", flags=re.IGNORECASE)
def _fix_test_failure(match, command: str, stderr: str) -> FixSuggestion:
    # Re-run with verbose to see which tests failed
    if "pytest" in command:
        fix = command.replace("pytest", "pytest -v --tb=short", 1)
    else:
        fix = f"{command} --verbose"
    return FixSuggestion(
        strategy="test_failure",
        fix_command=fix,
        explanation="Test failure — re-running with verbose output for details",
        confidence=0.65,
    )


@_pattern(r"command not found|is not recognized|not found in PATH", flags=re.IGNORECASE)
def _fix_command_not_found(match, command: str, stderr: str) -> FixSuggestion:
    cmd_parts = command.split()
    cmd_name = cmd_parts[0] if cmd_parts else command
    return FixSuggestion(
        strategy="command_not_found",
        fix_command=f"which {cmd_name} || echo '{cmd_name} not installed'",
        explanation=f"Command '{cmd_name}' not found — may need to install it",
        confidence=0.8,
    )


@_pattern(r"No space left on device|ENOSPC")
def _fix_disk_space(match, command: str, stderr: str) -> FixSuggestion:
    return FixSuggestion(
        strategy="disk_space",
        fix_command="df -h && du -sh /tmp/* 2>/dev/null | sort -rh | head -10",
        explanation="Disk full — check which directories are using space",
        confidence=0.9,
    )


@_pattern(r"Connection refused|ECONNREFUSED")
def _fix_connection_refused(match, command: str, stderr: str) -> FixSuggestion:
    return FixSuggestion(
        strategy="connection_refused",
        fix_command="echo 'Check if the target service is running'",
        explanation="Connection refused — the target service may not be running",
        confidence=0.7,
    )


@_pattern(r"timeout|ETIMEDOUT|timed out", flags=re.IGNORECASE)
def _fix_timeout(match, command: str, stderr: str) -> FixSuggestion:
    return FixSuggestion(
        strategy="timeout",
        fix_command=command,
        explanation="Command timed out — retrying (network may have been slow)",
        confidence=0.5,
    )


def suggest_fix(command: str, stderr: str) -> FixSuggestion | None:
    """Match stderr against known patterns and return best fix suggestion."""
    best: FixSuggestion | None = None
    for pattern, handler in _FIX_PATTERNS:
        match = pattern.search(stderr)
        if match:
            suggestion = handler(match, command, stderr)
            if best is None or suggestion.confidence > best.confidence:
                best = suggestion
    return best


def suggest_fixes(command: str, stderr: str) -> list[FixSuggestion]:
    """Return all matching fix suggestions, sorted by confidence."""
    results = []
    for pattern, handler in _FIX_PATTERNS:
        match = pattern.search(stderr)
        if match:
            results.append(handler(match, command, stderr))
    results.sort(key=lambda s: s.confidence, reverse=True)
    return results
