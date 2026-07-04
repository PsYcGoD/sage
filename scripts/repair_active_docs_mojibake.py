"""Repair mojibake in active SAGE markdown docs.

The affected docs contain UTF-8 emoji/box-drawing bytes that were decoded as
Windows-1252 and then saved as UTF-8. This script reverses that transformation
for active docs only, leaving archived backups untouched.
"""

from __future__ import annotations

from pathlib import Path


TARGETS = [
    Path("README.md"),
    Path("SAGE_V2_COMPLETE.md"),
]


MOJIBAKE_MARKERS = ("ð", "â", "Ã", "Â")


def repair_line(line: str) -> str:
    if not any(marker in line for marker in MOJIBAKE_MARKERS):
        return line
    try:
        return line.encode("cp1252").decode("utf-8")
    except UnicodeError:
        return line


def repair_text(text: str) -> str:
    return "".join(repair_line(line) for line in text.splitlines(keepends=True))


def main() -> int:
    changed = 0
    for path in TARGETS:
        original = path.read_text(encoding="utf-8")
        repaired = repair_text(original)
        if repaired != original:
            path.write_text(repaired, encoding="utf-8", newline="\n")
            changed += 1
            print(f"repaired {path}")
    print(f"changed={changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
