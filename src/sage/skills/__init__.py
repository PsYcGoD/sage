"""SAGE bundled Agent Skill reference files.

These SKILL.md files travel with SAGE in git as optional references. They are
not installed into Claude Code or Codex by default because personal skills are
loaded into those tools' prompts and can make requests too large.

Agent binding (which SAGE specialist "owns" which skill):

    code      -> coding-master-pro
    research  -> research-master-pro
    frontend  -> design-master-pro   (the UI/UX / design agent)

Add more skills by dropping ``<name>/SKILL.md`` in this folder and extending
``AGENT_SKILL_FILES``. Set ``SAGE_INSTALL_BUNDLED_SKILLS=1`` to copy these
references into the local Claude/Codex personal skill folders.
"""

from __future__ import annotations

import logging
import os
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

# Where each CLI discovers personal skills. Copying into these folders is
# opt-in only; normal SAGE agents run from deterministic local metadata.
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
    """Copy bundled skills into Claude Code and Codex personal skill folders.

    This is disabled by default. Personal skill folders are prompt context for
    those tools, so installing large bundled files globally can increase token
    use and trigger model input limits. Returns the number of files written.
    """
    enabled = os.environ.get("SAGE_INSTALL_BUNDLED_SKILLS", "").strip().lower()
    if enabled not in {"1", "true", "yes", "on"}:
        log.debug("bundled skill install skipped; set SAGE_INSTALL_BUNDLED_SKILLS=1 to enable")
        return 0

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
