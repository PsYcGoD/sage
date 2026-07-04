"""Tests for temporal ML validation and data-quality helpers."""

import json

from sage.ml.validation import (
    REPORT_VERSION,
    command_fingerprint,
    dataset_hash,
    deduplicate,
    label_run,
    validate_temporal,
    write_validation_report,
)


def test_fingerprint_normalizes_case_whitespace_and_numbers():
    assert command_fingerprint("pytest tests/test_a.py -q") == command_fingerprint(
        "  PYTEST   tests/test_a.py   -q "
    )
    assert command_fingerprint("echo run-1") == command_fingerprint("echo run-2")
    assert command_fingerprint("pytest") != command_fingerprint("npm test")


def test_label_run_is_consistent():
    assert label_run(0) == 0
    assert label_run(1) == 1
    assert label_run(-9) == 1
    assert label_run("2") == 1


def test_deduplicate_keeps_first_and_counts_conflicts():
    samples = [
        {"command": "pytest -q", "label": 1, "created_at": "2026-01-01", "provenance": "local_run"},
        {"command": "PYTEST -q", "label": 0, "created_at": "2026-01-02", "provenance": "local_run"},
        {"command": "git status", "label": 0, "created_at": "2026-01-03", "provenance": "imported"},
        {"command": "git status", "label": 0, "created_at": "2026-01-04", "provenance": "local_run"},
    ]
    kept, dropped, conflicts = deduplicate(samples)
    assert [item["command"] for item in kept] == ["pytest -q", "git status"]
    assert dropped == 2
    assert conflicts == 1
    assert all("fingerprint" in item for item in kept)


def test_dataset_hash_is_deterministic_and_label_sensitive():
    kept, _, _ = deduplicate(
        [{"command": "pytest", "label": 1, "created_at": "", "provenance": "local_run"}]
    )
    flipped, _, _ = deduplicate(
        [{"command": "pytest", "label": 0, "created_at": "", "provenance": "local_run"}]
    )
    assert dataset_hash(kept) == dataset_hash(kept)
    assert dataset_hash(kept) != dataset_hash(flipped)


def test_validate_temporal_report_contract():
    """Runs against the real local DB; must produce an honest report either way."""
    report = validate_temporal()
    assert report["report_version"] == REPORT_VERSION
    assert report["synthetic_samples"] == 0
    assert report["split"] == "temporal"
    assert report["samples"] <= report["raw_samples"]
    assert set(report["provenance"]) == {"local_run", "imported"}
    assert len(report["dataset_hash"]) == 64
    if report["validated"]:
        assert report["train"]["to"] <= report["test"]["from"]
        for key in ("accuracy", "precision", "recall", "roc_auc"):
            assert 0.0 <= report["metrics"][key] <= 1.0
    else:
        assert "message" in report


def test_validate_temporal_rejects_bad_fraction():
    import pytest

    with pytest.raises(ValueError):
        validate_temporal(test_fraction=0.9)


def test_write_validation_report(tmp_path):
    report = {"report_version": REPORT_VERSION, "generated_at": "2026-07-04T00:00:00+00:00"}
    path = write_validation_report(report, tmp_path / "report.json")
    assert json.loads(path.read_text(encoding="utf-8"))["report_version"] == REPORT_VERSION
