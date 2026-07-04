"""Repair mojibake in active GUI source strings."""

from __future__ import annotations

from pathlib import Path


TARGETS = [
    Path("src/sage/gui/app.py"),
    Path("src/sage/gui/widgets/floating_sidebar.py"),
    Path("src/sage/gui/widgets/output_view.py"),
]
MARKERS = ("ð", "â", "Ã", "Â")


def repair_line(line: str) -> str:
    if not any(marker in line for marker in MARKERS):
        return line
    try:
        return line.encode("cp1252").decode("utf-8")
    except UnicodeError:
        return line


def main() -> int:
    changed = 0
    for path in TARGETS:
        original = path.read_text(encoding="utf-8")
        repaired = "".join(repair_line(line) for line in original.splitlines(keepends=True))
        if repaired != original:
            path.write_text(repaired, encoding="utf-8", newline="\n")
            print(f"repaired {path}")
            changed += 1
    print(f"changed={changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
