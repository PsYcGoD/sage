import io
import json
import os

from sage.cli import main
from sage.ml.soak import SoakConfig, run_ml_soak


def test_ml_soak_one_cycle_writes_proof_files(tmp_path):
    stream = io.StringIO()

    state = run_ml_soak(
        SoakConfig(output_dir=tmp_path, interval_seconds=0, cycles=1),
        stream=stream,
    )

    assert state.status == "completed"
    assert state.total_cycles == 1
    assert state.total_failed == 0
    assert "Cycle 1: ALL" in stream.getvalue()

    json_report = tmp_path / "sage_ml_soak.json"
    txt_report = tmp_path / "sage_ml_soak.txt"
    jsonl_report = tmp_path / "sage_ml_soak.jsonl"
    log_report = tmp_path / "sage_ml_soak.log"

    assert json_report.exists()
    assert txt_report.exists()
    assert jsonl_report.exists()
    assert log_report.exists()

    data = json.loads(json_report.read_text(encoding="utf-8"))
    assert data["status"] == "completed"
    assert data["total_failed"] == 0
    assert data["total_tests"] >= 1
    assert "RESULT: ALL PASS" in txt_report.read_text(encoding="utf-8")
    assert "database_integrity" in jsonl_report.read_text(encoding="utf-8")


def test_ml_soak_restores_localappdata(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", "original-localappdata")

    run_ml_soak(SoakConfig(output_dir=tmp_path, interval_seconds=0, cycles=1), stream=io.StringIO())

    assert os.environ["LOCALAPPDATA"] == "original-localappdata"


def test_cli_ml_soak_quick_cycle(tmp_path, capsys):
    code = main([
        "ml",
        "soak",
        "--cycles",
        "1",
        "--interval-seconds",
        "0",
        "--output-dir",
        str(tmp_path),
    ])

    assert code == 0
    assert "SAGE ML SOAK COMPLETE" in capsys.readouterr().out
    assert (tmp_path / "sage_ml_soak.json").exists()
