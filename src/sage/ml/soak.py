from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, TextIO


@dataclass
class SoakConfig:
    output_dir: Path
    interval_seconds: float = 30.0
    cycles: int | None = None
    hours: float | None = None
    isolated_data_dir: Path | None = None


@dataclass
class CheckResult:
    name: str
    passed: bool
    duration_s: float
    message: str = ""


@dataclass
class CycleResult:
    cycle: int
    started_at: str
    duration_s: float = 0.0
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    failures: list[str] = field(default_factory=list)
    checks: list[CheckResult] = field(default_factory=list)


@dataclass
class SoakState:
    started: str
    last_update: str
    status: str = "running"
    total_cycles: int = 0
    total_tests: int = 0
    total_passed: int = 0
    total_failed: int = 0
    elapsed_hours: float = 0.0
    output_dir: str = ""
    isolated_data_dir: str = ""
    cycles: list[CycleResult] = field(default_factory=list)


CheckFn = Callable[[], None]


def run_ml_soak(config: SoakConfig, stream: TextIO | None = None) -> SoakState:
    """Run the ML soak proof loop and write JSON/TXT/JSONL/log proof files."""
    config.output_dir = Path(config.output_dir)
    config.output_dir.mkdir(parents=True, exist_ok=True)
    isolated_data_dir = (
        Path(config.isolated_data_dir)
        if config.isolated_data_dir is not None
        else config.output_dir / "localappdata"
    )

    state = SoakState(
        started=_now(),
        last_update=_now(),
        output_dir=str(config.output_dir),
        isolated_data_dir=str(isolated_data_dir),
    )

    log_path = config.output_dir / "sage_ml_soak.log"
    jsonl_path = config.output_dir / "sage_ml_soak.jsonl"
    start_mono = time.monotonic()
    deadline = time.monotonic() + (config.hours * 3600) if config.hours else None
    cycle = 0

    with _isolated_sage_env(isolated_data_dir), log_path.open("a", encoding="utf-8") as log_file:
        _emit(stream, log_file, "")
        _emit(stream, log_file, "=" * 60)
        _emit(stream, log_file, "SAGE ML SOAK PROOF")
        _emit(stream, log_file, f"Started: {state.started}")
        _emit(stream, log_file, "Stop: Ctrl+C")
        _emit(stream, log_file, f"Output: {config.output_dir}")
        _emit(stream, log_file, f"Data dir: {isolated_data_dir}")
        _emit(stream, log_file, "=" * 60)

        try:
            while True:
                if config.cycles is not None and cycle >= config.cycles:
                    state.status = "completed"
                    break
                if deadline is not None and time.monotonic() >= deadline:
                    state.status = "completed"
                    break

                cycle += 1
                elapsed_h = (time.monotonic() - start_mono) / 3600
                state.elapsed_hours = round(max(0.0, elapsed_h), 3)
                _emit(stream, log_file, "")
                _emit(stream, log_file, f"--- Cycle {cycle} ---")

                result = _run_cycle(cycle, stream, log_file, jsonl_path)
                state.total_cycles = cycle
                state.total_tests += result.tests_run
                state.total_passed += result.tests_passed
                state.total_failed += result.tests_failed
                state.cycles.append(result)
                state.last_update = _now()
                _write_reports(config.output_dir, state)

                if result.tests_failed:
                    _emit(stream, log_file, f"Cycle {cycle}: {result.tests_failed} FAILED / {result.tests_run} ({result.duration_s:.1f}s)")
                    for failure in result.failures:
                        _emit(stream, log_file, f"  X {failure}")
                else:
                    _emit(stream, log_file, f"Cycle {cycle}: ALL {result.tests_run} PASS ({result.duration_s:.1f}s)")

                if config.cycles is not None and cycle >= config.cycles:
                    state.status = "completed"
                    break
                if deadline is not None and time.monotonic() >= deadline:
                    state.status = "completed"
                    break

                _sleep_with_interrupt(config.interval_seconds, stream, log_file)
        except KeyboardInterrupt:
            state.status = "stopped_by_user"
            _emit(stream, log_file, "")
            _emit(stream, log_file, "Ctrl+C received. Writing final proof report...")
        finally:
            if state.status == "running":
                state.status = "stopped"
            state.last_update = _now()
            _write_reports(config.output_dir, state)
            _emit(stream, log_file, "")
            _emit(stream, log_file, "SAGE ML SOAK COMPLETE")
            _emit(stream, log_file, f"Status: {state.status}")
            _emit(stream, log_file, f"Cycles: {state.total_cycles}")
            _emit(stream, log_file, f"Tests: {state.total_tests}")
            _emit(stream, log_file, f"Passed: {state.total_passed}")
            _emit(stream, log_file, f"Failed: {state.total_failed}")
            _emit(stream, log_file, f"JSON: {config.output_dir / 'sage_ml_soak.json'}")
            _emit(stream, log_file, f"TXT:  {config.output_dir / 'sage_ml_soak.txt'}")
            _emit(stream, log_file, f"JSONL:{jsonl_path}")

    return state


def default_checks() -> list[tuple[str, CheckFn]]:
    return [
        ("database_integrity", _check_database_integrity),
        ("predictor_imports", _check_predictor_imports),
        ("heuristic_predictions", _check_heuristic_predictions),
        ("feature_extraction", _check_feature_extraction),
        ("model_status", _check_model_status),
        ("fix_patterns", _check_fix_patterns),
    ]


def _run_cycle(
    cycle: int,
    stream: TextIO | None,
    log_file: TextIO,
    jsonl_path: Path,
) -> CycleResult:
    result = CycleResult(cycle=cycle, started_at=_now())
    start = time.monotonic()
    for name, fn in default_checks():
        check_start = time.monotonic()
        try:
            fn()
            passed = True
            message = "ok"
        except Exception as exc:
            passed = False
            message = f"{type(exc).__name__}: {exc}"

        duration_s = round(time.monotonic() - check_start, 3)
        check = CheckResult(name=name, passed=passed, duration_s=duration_s, message=message)
        result.checks.append(check)
        result.tests_run += 1
        if passed:
            result.tests_passed += 1
            _emit(stream, log_file, f"  PASS {name} ({duration_s:.3f}s)")
        else:
            result.tests_failed += 1
            result.failures.append(f"{name}: {message}")
            _emit(stream, log_file, f"  FAIL {name}: {message}")
        _append_jsonl(jsonl_path, {"type": "check", "cycle": cycle, **asdict(check), "at": _now()})

    result.duration_s = round(time.monotonic() - start, 1)
    return result


def _check_database_integrity() -> None:
    from ..store import connect

    with connect() as conn:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise RuntimeError(f"isolated database integrity failed: {integrity}")


def _check_predictor_imports() -> None:
    from .predictor import FailurePredictor

    FailurePredictor()


def _check_heuristic_predictions() -> None:
    from .predictor import FailurePredictor

    predictor = FailurePredictor()
    predictor._v2_failed = True
    commands = [
        "echo hello",
        "python -m pytest",
        "pip install requests",
        "git status --short",
        "npm run build",
        "ollama run llama3.2",
    ]
    for command in commands:
        will_fail, confidence, reason = predictor.predict(command)
        if not isinstance(will_fail, bool):
            raise TypeError(f"{command!r} returned non-bool will_fail")
        if not 0.0 <= float(confidence) <= 1.0:
            raise ValueError(f"{command!r} confidence out of range: {confidence}")
        if not isinstance(reason, str) or not reason:
            raise ValueError(f"{command!r} returned empty reason")


def _check_feature_extraction() -> None:
    from .features import FeatureExtractor

    features = FeatureExtractor().extract(
        "ollama run llama3.2",
        {"num_recent_failures": 0.0, "minutes_since_last_failure": 1440.0},
    )
    if not features:
        raise RuntimeError("feature extractor returned no features")


def _check_model_status() -> None:
    from .family_model import FamilyFailureModel
    from .model import SklearnFailureModel

    family_status = FamilyFailureModel().status()
    global_status = SklearnFailureModel().status()
    if "trained" not in family_status:
        raise RuntimeError("family model status missing trained")
    if "trained" not in global_status:
        raise RuntimeError("global model status missing trained")


def _check_fix_patterns() -> None:
    from ..agentic.fixer import suggest_fix

    cases = [
        ("python app.py", "ModuleNotFoundError: No module named 'requests'", "install_module"),
        ("node server.js", "EADDRINUSE: address already in use port 3000", "port_in_use"),
        ("curl localhost:8080", "Connection refused", "connection_refused"),
    ]
    for command, stderr, expected in cases:
        fix = suggest_fix(command, stderr)
        if fix is None or fix.strategy != expected:
            actual = fix.strategy if fix else "none"
            raise RuntimeError(f"{command!r} expected {expected}, got {actual}")


def _write_reports(output_dir: Path, state: SoakState) -> None:
    data = asdict(state)
    (output_dir / "sage_ml_soak.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    lines = [
        "SAGE ML SOAK PROOF",
        "=" * 60,
        f"Started:      {state.started}",
        f"Last update:  {state.last_update}",
        f"Status:       {state.status}",
        f"Cycles:       {state.total_cycles}",
        f"Total tests:  {state.total_tests}",
        f"Passed:       {state.total_passed}",
        f"Failed:       {state.total_failed}",
        f"Data dir:     {state.isolated_data_dir}",
        "=" * 60,
        "",
    ]
    for cycle in state.cycles:
        status = "ALL PASS" if cycle.tests_failed == 0 else f"{cycle.tests_failed} FAILED"
        lines.append(f"Cycle {cycle.cycle}: {status} ({cycle.duration_s:.1f}s)")
        for failure in cycle.failures:
            lines.append(f"  X {failure}")
    lines.extend(["", "=" * 60, "RESULT: ALL PASS" if state.total_failed == 0 else f"RESULT: {state.total_failed} FAILURES"])
    (output_dir / "sage_ml_soak.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _append_jsonl(path: Path, event: dict) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def _sleep_with_interrupt(seconds: float, stream: TextIO | None, log_file: TextIO) -> None:
    if seconds <= 0:
        return
    _emit(stream, log_file, f"Next cycle in {seconds:.0f}s...")
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        time.sleep(min(1.0, end - time.monotonic()))


@contextmanager
def _isolated_sage_env(localappdata: Path):
    previous = {
        "LOCALAPPDATA": os.environ.get("LOCALAPPDATA"),
        "SAGE_DISABLE_AGENTS": os.environ.get("SAGE_DISABLE_AGENTS"),
        "SAGE_DISABLE_PREDICT": os.environ.get("SAGE_DISABLE_PREDICT"),
        "SAGE_SOAK_PROOF": os.environ.get("SAGE_SOAK_PROOF"),
    }
    localappdata.mkdir(parents=True, exist_ok=True)
    os.environ["LOCALAPPDATA"] = str(localappdata)
    os.environ["SAGE_DISABLE_AGENTS"] = "1"
    os.environ["SAGE_DISABLE_PREDICT"] = "1"
    os.environ["SAGE_SOAK_PROOF"] = "1"
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _emit(stream: TextIO | None, log_file: TextIO, message: str) -> None:
    print(message, file=stream, flush=True) if stream is not None else print(message, flush=True)
    print(message, file=log_file, flush=True)


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")
