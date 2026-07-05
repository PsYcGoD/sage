"""SAGE bundled Agent Skills.

These SKILL.md files travel with SAGE in git and are auto-installed into the
Claude Code and Codex skill folders at startup, so the CLIs that SAGE spawns
(claude, codex) auto-load them and route by each skill's ``description``.

Agent binding (which SAGE specialist "owns" which skill):

    code      -> coding-master-pro
    research  -> research-master-pro
    frontend  -> design-master-pro   (the UI/UX / design agent)

Add more skills by dropping ``<name>/SKILL.md`` in this folder and extending
``AGENT_SKILL_FILES``.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

log = logging.getLogger(__name__)

# Directory that holds the bundled <skill-name>/SKILL.md folders.
SKILLS_DIR = Path(__file__).resolve().parent

# SAGE agent type -> bundled skill folder name.
AGENT_SKILL_FILES: dict[str, str] = {
    "code": "coding-master-pro",
    "research": "research-master-pro",
    "frontend": "design-master-pro",
}

# Where each CLI discovers personal skills. Both get a copy so whichever agent
# (claude or codex) drives a run, the matching skill is available to it.
#   Claude Code: ~/.claude/skills/<name>/SKILL.md
#   Codex:       ~/.agents/skills/<name>/SKILL.md
_INSTALL_ROOTS = (
    Path.home() / ".claude" / "skills",
    Path.home() / ".agents" / "skills",
)


def list_bundled_skills() -> list[str]:
    """Return the folder names of every bundled skill that has a SKILL.md."""
    if not SKILLS_DIR.exists():
        return []
    return sorted(
        p.parent.name
        for p in SKILLS_DIR.glob("*/SKILL.md")
    )


def skill_dir(name: str) -> Path | None:
    """Return the bundled folder for a skill name, or None if missing."""
    candidate = SKILLS_DIR / name
    return candidate if (candidate / "SKILL.md").exists() else None


def agent_skill_file(agent_type: str) -> str | None:
    """Return the bundled skill folder bound to an agent type, if any."""
    return AGENT_SKILL_FILES.get(agent_type)


def load_skill_text(name: str) -> str:
    """Return the full SKILL.md text for a bundled skill, or ''."""
    folder = skill_dir(name)
    if not folder:
        return ""
    try:
        return (folder / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _needs_copy(src: Path, dst: Path) -> bool:
    """True when dst is missing or older/different-sized than src."""
    if not dst.exists():
        return True
    try:
        s, d = src.stat(), dst.stat()
    except OSError:
        return True
    return s.st_size != d.st_size or s.st_mtime > d.st_mtime


def install_skills() -> int:
    """Copy every bundled skill into the Claude Code and Codex skill folders.

    Idempotent: only writes when a target file is missing or out of date, so it
    is safe to call on every startup. Returns the number of files written.
    """
    written = 0
    for src_md in SKILLS_DIR.glob("*/SKILL.md"):
        name = src_md.parent.name
        for root in _INSTALL_ROOTS:
            dst_md = root / name / "SKILL.md"
            if not _needs_copy(src_md, dst_md):
                continue
            try:
                dst_md.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_md, dst_md)
                written += 1
                log.debug("installed skill %s -> %s", name, dst_md)
            except OSError as exc:
                log.debug("skill install skipped for %s: %s", dst_md, exc)
    return written
