from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    kind: str
    line: str


PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("python-traceback", re.compile(r"^Traceback \(most recent call last\):")),
    ("python-error", re.compile(r"\b(?:AssertionError|SyntaxError|ModuleNotFoundError|ImportError|TypeError|ValueError):")),
    ("test-failure", re.compile(r"\b(?:FAILED|FAILURES|FAIL|Error|ERROR)\b")),
    ("typescript-error", re.compile(r"\bTS\d{4}:")),
    ("javascript-error", re.compile(r"\b(?:TypeError|ReferenceError|SyntaxError):")),
    ("rust-error", re.compile(r"\berror(?:\[[A-Z]\d+\])?:")),
    ("npm-error", re.compile(r"\bnpm ERR!")),
    ("generic-error", re.compile(r"\b(?:fatal|error|failed|exception)\b", re.IGNORECASE)),
]


def detect_findings(text: str, limit: int = 30) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[tuple[str, str]] = set()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        for kind, pattern in PATTERNS:
            if pattern.search(line):
                key = (kind, line)
                if key not in seen:
                    findings.append(Finding(kind=kind, line=line))
                    seen.add(key)
                break

        if len(findings) >= limit:
            break

    return findings


def summarize_output(stdout: str, stderr: str, exit_code: int, max_lines: int = 40) -> str:
    combined = "\n".join(part for part in [stdout, stderr] if part)
    findings = detect_findings(combined, limit=max_lines)

    if findings:
        lines = ["Important output:"]
        for finding in findings:
            lines.append(f"- [{finding.kind}] {finding.line}")
        return "\n".join(lines)

    lines = [line.rstrip() for line in combined.splitlines() if line.strip()]
    if not lines:
        return "Command produced no output."

    if exit_code == 0:
        visible = lines[: min(12, len(lines))]
        suffix = "" if len(lines) <= 12 else f"\n... {len(lines) - 12} more line(s) hidden"
        return "\n".join(visible) + suffix

    visible = lines[-min(max_lines, len(lines)) :]
    return "Command failed. Last output lines:\n" + "\n".join(visible)
