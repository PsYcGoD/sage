"""Leak-free historical features for failure prediction.

The strongest failure signal is history: did this exact command, this
command family, or this command kind fail before? These features are built
with an expanding window — each sample only ever sees runs that happened
BEFORE it — so temporal validation stays honest and training cannot leak
future outcomes into the past.

Failure rates are Laplace-smoothed toward the running global rate so a
single old failure does not pin a command at 100% risk forever.
"""

from __future__ import annotations

from ..classify import classify_command, command_fingerprint

HISTORY_FEATURE_NAMES = [
    "hist_cmd_runs",
    "hist_cmd_fail_rate",
    "hist_cmd_last_failed",
    "hist_cmd_fail_streak",
    "hist_family_runs",
    "hist_family_fail_rate",
    "hist_kind_fail_rate",
    "hist_global_fail_rate",
    "hist_prev_run_failed",
]

_SMOOTHING = 4.0


class _Stats:
    __slots__ = ("runs", "failures", "last_failed", "streak")

    def __init__(self) -> None:
        self.runs = 0
        self.failures = 0
        self.last_failed = 0
        self.streak = 0

    def update(self, label: int) -> None:
        self.runs += 1
        self.failures += label
        self.last_failed = label
        self.streak = self.streak + 1 if label else 0


class HistoryFeatureBuilder:
    """Expanding-window failure statistics keyed by fingerprint/family/kind."""

    def __init__(self) -> None:
        self._cmd: dict[str, _Stats] = {}
        self._family: dict[str, _Stats] = {}
        self._kind: dict[str, _Stats] = {}
        self._global = _Stats()
        self._prev_failed = 0

    def features_for(self, command: str) -> dict[str, float]:
        """Features from history strictly BEFORE this command runs."""
        fingerprint = command_fingerprint(command)
        klass = classify_command(command)
        cmd = self._cmd.get(fingerprint)
        family = self._family.get(klass.family)
        kind = self._kind.get(klass.kind)
        global_rate = self._global_rate()
        return {
            "hist_cmd_runs": float(min(cmd.runs, 50)) if cmd else 0.0,
            "hist_cmd_fail_rate": self._rate(cmd, global_rate),
            "hist_cmd_last_failed": float(cmd.last_failed) if cmd else 0.0,
            "hist_cmd_fail_streak": float(min(cmd.streak, 10)) if cmd else 0.0,
            "hist_family_runs": float(min(family.runs, 200)) if family else 0.0,
            "hist_family_fail_rate": self._rate(family, global_rate),
            "hist_kind_fail_rate": self._rate(kind, global_rate),
            "hist_global_fail_rate": global_rate,
            "hist_prev_run_failed": float(self._prev_failed),
        }

    def update(self, command: str, label: int) -> None:
        """Record an outcome AFTER its features were emitted."""
        label = 1 if label else 0
        fingerprint = command_fingerprint(command)
        klass = classify_command(command)
        self._cmd.setdefault(fingerprint, _Stats()).update(label)
        self._family.setdefault(klass.family, _Stats()).update(label)
        self._kind.setdefault(klass.kind, _Stats()).update(label)
        self._global.update(label)
        self._prev_failed = label

    def _global_rate(self) -> float:
        if self._global.runs == 0:
            return 0.15
        return (self._global.failures + _SMOOTHING * 0.15) / (self._global.runs + _SMOOTHING)

    @staticmethod
    def _rate(stats: _Stats | None, prior: float) -> float:
        if stats is None or stats.runs == 0:
            return prior
        return (stats.failures + _SMOOTHING * prior) / (stats.runs + _SMOOTHING)

    @classmethod
    def from_samples(cls, samples: list[tuple[str, int]]) -> "HistoryFeatureBuilder":
        """Build a fully-updated builder (for live prediction on new commands)."""
        builder = cls()
        for command, label in samples:
            builder.update(command, label)
        return builder


def build_expanding_rows(
    samples: list[tuple[str, int]],
    base_extract,
) -> tuple[list[dict[str, float]], HistoryFeatureBuilder]:
    """Emit feature rows chronologically with strictly-past history.

    Returns the rows and the final builder state (ready for live prediction).
    """
    builder = HistoryFeatureBuilder()
    rows: list[dict[str, float]] = []
    for command, label in samples:
        row = base_extract(command)
        row.update(builder.features_for(command))
        rows.append(row)
        builder.update(command, label)
    return rows, builder
