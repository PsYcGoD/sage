"""Safe file modifier for SAGE codegen - snapshots and rollback."""

from __future__ import annotations

import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class FileSnapshot:
    """A snapshot of a file's state."""

    path: Path
    content: str
    timestamp: float
    backup_path: Path | None = None

    @property
    def age_seconds(self) -> float:
        return time.time() - self.timestamp


@dataclass
class ModificationResult:
    """Result of a file modification."""

    path: Path
    success: bool
    snapshot_id: str
    error: str | None = None
    validation_issues: list[Any] = field(default_factory=list)


class SafeModifier:
    """Safe file modification with snapshots and rollback."""

    def __init__(self, root: Path, backup_dir: Path | None = None):
        self.root = root
        self.backup_dir = backup_dir or root / ".sage_backups"
        self._snapshots: dict[str, FileSnapshot] = {}
        self._snapshot_counter = 0

    def _generate_snapshot_id(self) -> str:
        self._snapshot_counter += 1
        return f"snap_{self._snapshot_counter}_{int(time.time())}"

    def snapshot(self, path: Path) -> str:
        """Create a snapshot of a file. Returns snapshot ID."""
        snapshot_id = self._generate_snapshot_id()

        if path.exists():
            content = path.read_text(encoding="utf-8", errors="replace")
        else:
            content = ""

        # Create backup directory if needed
        if not self.backup_dir.exists():
            self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Create backup file
        backup_path = self.backup_dir / f"{path.name}.{snapshot_id}"
        if path.exists():
            shutil.copy2(path, backup_path)

        self._snapshots[snapshot_id] = FileSnapshot(
            path=path,
            content=content,
            timestamp=time.time(),
            backup_path=backup_path if path.exists() else None,
        )

        return snapshot_id

    def snapshot_multiple(self, paths: list[Path]) -> dict[Path, str]:
        """Create snapshots for multiple files."""
        return {path: self.snapshot(path) for path in paths}

    def rollback(self, snapshot_id: str) -> bool:
        """Rollback a file to a snapshot."""
        snapshot = self._snapshots.get(snapshot_id)
        if not snapshot:
            return False

        if snapshot.backup_path and snapshot.backup_path.exists():
            shutil.copy2(snapshot.backup_path, snapshot.path)
        elif snapshot.content:
            snapshot.path.write_text(snapshot.content, encoding="utf-8")
        elif snapshot.path.exists():
            # Original file didn't exist, remove it
            snapshot.path.unlink()

        return True

    def rollback_all(self, snapshot_ids: list[str] | None = None) -> int:
        """Rollback multiple snapshots. Returns count of successful rollbacks."""
        if snapshot_ids is None:
            snapshot_ids = list(self._snapshots.keys())

        count = 0
        for snap_id in snapshot_ids:
            if self.rollback(snap_id):
                count += 1
        return count

    def write_safe(
        self,
        path: Path,
        content: str,
        validate: bool = True,
        validator: Any | None = None,
    ) -> ModificationResult:
        """Write to a file with automatic snapshot and optional validation."""
        # Create snapshot first
        snapshot_id = self.snapshot(path)

        # Validate if requested
        issues: list[Any] = []
        if validate and validator:
            try:
                result = validator.validate(path, content)
                if hasattr(result, "issues"):
                    issues = result.issues
                elif isinstance(result, list):
                    issues = result

                # Check for blocking issues (errors)
                blocking = [i for i in issues if getattr(i, "severity", "") == "error"]
                if blocking:
                    return ModificationResult(
                        path=path,
                        success=False,
                        snapshot_id=snapshot_id,
                        error="Validation failed with errors",
                        validation_issues=issues,
                    )
            except Exception as e:
                return ModificationResult(
                    path=path,
                    success=False,
                    snapshot_id=snapshot_id,
                    error=f"Validation error: {e}",
                )

        # Write the file
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return ModificationResult(
                path=path,
                success=True,
                snapshot_id=snapshot_id,
                validation_issues=issues,
            )
        except OSError as e:
            # Rollback on write failure
            self.rollback(snapshot_id)
            return ModificationResult(
                path=path,
                success=False,
                snapshot_id=snapshot_id,
                error=f"Write failed: {e}",
            )

    def edit_safe(
        self,
        path: Path,
        old: str,
        new: str,
        validate: bool = True,
        validator: Any | None = None,
    ) -> ModificationResult:
        """Edit a file with automatic snapshot and validation."""
        if not path.exists():
            return ModificationResult(
                path=path,
                success=False,
                snapshot_id="",
                error="File does not exist",
            )

        # Read current content
        content = path.read_text(encoding="utf-8", errors="replace")

        # Check if old string exists
        if old not in content:
            return ModificationResult(
                path=path,
                success=False,
                snapshot_id="",
                error="Old string not found in file",
            )

        # Create new content
        new_content = content.replace(old, new, 1)

        return self.write_safe(path, new_content, validate, validator)

    def delete_safe(self, path: Path) -> ModificationResult:
        """Delete a file with automatic snapshot."""
        if not path.exists():
            return ModificationResult(
                path=path,
                success=False,
                snapshot_id="",
                error="File does not exist",
            )

        # Create snapshot
        snapshot_id = self.snapshot(path)

        try:
            path.unlink()
            return ModificationResult(
                path=path,
                success=True,
                snapshot_id=snapshot_id,
            )
        except OSError as e:
            return ModificationResult(
                path=path,
                success=False,
                snapshot_id=snapshot_id,
                error=f"Delete failed: {e}",
            )

    def get_snapshot(self, snapshot_id: str) -> FileSnapshot | None:
        """Get a snapshot by ID."""
        return self._snapshots.get(snapshot_id)

    def list_snapshots(self, path: Path | None = None) -> list[FileSnapshot]:
        """List all snapshots, optionally filtered by path."""
        snapshots = list(self._snapshots.values())
        if path:
            snapshots = [s for s in snapshots if s.path == path]
        return sorted(snapshots, key=lambda s: s.timestamp, reverse=True)

    def cleanup_old_snapshots(self, max_age_seconds: float = 3600) -> int:
        """Remove snapshots older than max_age. Returns count removed."""
        now = time.time()
        to_remove: list[str] = []

        for snap_id, snapshot in self._snapshots.items():
            if now - snapshot.timestamp > max_age_seconds:
                to_remove.append(snap_id)
                if snapshot.backup_path and snapshot.backup_path.exists():
                    try:
                        snapshot.backup_path.unlink()
                    except OSError:
                        pass

        for snap_id in to_remove:
            del self._snapshots[snap_id]

        return len(to_remove)

    def get_diff(self, snapshot_id: str) -> str | None:
        """Get diff between snapshot and current file state."""
        snapshot = self._snapshots.get(snapshot_id)
        if not snapshot:
            return None

        if not snapshot.path.exists():
            return f"--- {snapshot.path}\n+++ (deleted)\n"

        current = snapshot.path.read_text(encoding="utf-8", errors="replace")

        if current == snapshot.content:
            return "No changes"

        # Simple line-based diff
        old_lines = snapshot.content.splitlines(keepends=True)
        new_lines = current.splitlines(keepends=True)

        import difflib
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{snapshot.path.name}",
            tofile=f"b/{snapshot.path.name}",
        )
        return "".join(diff)
