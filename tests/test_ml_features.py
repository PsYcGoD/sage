"""Tests for SAGE ML/NLP feature wiring."""

from pathlib import Path
from unittest.mock import patch

from sage import cli
from sage.agents import DEFAULT_AGENT_SPECS, select_agents_for_command
from sage.global_store import GlobalDatabase
from sage.ml import FailurePredictor, FeatureExtractor
from sage.mcp.tools import sage_run_command
from sage.nlp import CommandBuilder, NLParser


def test_ml_and_nlp_packages_are_importable():
    assert FailurePredictor is not None
    assert FeatureExtractor is not None
    assert NLParser is not None
    assert CommandBuilder is not None
    assert GlobalDatabase is not None


def test_feature_extractor_returns_stable_feature_set(tmp_path: Path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")

    extractor = FeatureExtractor()
    features = extractor.extract(
        "npm test",
        context={"num_recent_failures": 2, "minutes_since_last_failure": 3},
        project_path=tmp_path,
    )

    assert list(features) == extractor.get_feature_names()
    assert features["has_test_keyword"] == 1.0
    assert features["has_install_keyword"] == 0.0
    assert features["has_package_json"] == 1.0
    assert features["has_tests_dir"] == 1.0
    assert features["num_recent_failures"] == 2.0


def test_failure_predictor_scores_recent_failures_high():
    predictor = FailurePredictor()

    with patch.object(
        predictor,
        "_get_context",
        return_value={"num_recent_failures": 4.0, "minutes_since_last_failure": 2.0},
    ), patch.object(predictor.sklearn_model, "predict", return_value=None):
        will_fail, confidence, reason = predictor.predict("pytest")

    assert will_fail is True
    assert confidence >= 0.65
    assert "failure" in reason


def test_cli_predict_command_prints_prediction(capsys):
    class StubPredictor:
        def predict(self, command):
            return False, 0.42, "Low risk"

    with patch("sage.ml.FailurePredictor", return_value=StubPredictor()):
        code = cli.predict_command(["python", "--version"])

    output = capsys.readouterr().out
    assert code == 0
    assert "Prediction: likely to succeed" in output
    assert "Confidence: 42%" in output


def test_nlp_parser_maps_prediction_request():
    parser = NLParser()

    assert parser.parse("predict pytest tests") == "sage predict -- pytest tests"
    assert "sage predict -- <command>" in parser.get_suggestions("pre")


def test_mcp_run_command_includes_prediction():
    class StubPredictor:
        def predict(self, command):
            return True, 0.9, "test risk"

    with patch("sage.ml.FailurePredictor", return_value=StubPredictor()):
        with patch("sage.runner.run_command", return_value=1) as run:
            result = sage_run_command("pytest -q", predict=True)

    run.assert_called_once_with(["pytest", "-q"], predict=True)
    assert result["success"] is False
    assert result["prediction"] == {
        "will_fail": True,
        "confidence": 0.9,
        "reason": "test risk",
    }


def test_default_agent_catalog_has_24_roles():
    assert len(DEFAULT_AGENT_SPECS) == 24

    selected = select_agents_for_command("pytest failed with sqlite migration error")
    selected_types = {agent.type for agent in selected}

    assert len(selected) == 24
    assert "test" in selected_types
    assert "database" in selected_types or "debug" in selected_types


def test_expanded_agent_catalog_routes_memory_and_security_triads():
    memory_selected = {agent.type for agent in select_agents_for_command("persistent session memory wastes context tokens")}
    security_selected = {agent.type for agent in select_agents_for_command("red-team attack needs blue-team mitigation and auditor evidence")}

    assert "memory" in memory_selected
    assert {"redteam", "blueteam", "auditor"} & security_selected
