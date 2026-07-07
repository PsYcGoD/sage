"""Tests for ML V2 Neural Command Center."""

import pytest
from sage.ml.predictors.syntax_predictor import SyntaxPredictor
from sage.ml.predictors.dependency_predictor import DependencyPredictor
from sage.ml.predictors.timeout_predictor import TimeoutPredictor
from sage.ml.predictors.permission_predictor import PermissionPredictor
from sage.ml.predictors.context_predictor import ContextPredictor
from sage.ml.predictors.compression_selector import CompressionSelector
from sage.ml.predictors.agent_ranker import AgentRanker
from sage.ml.neural_center import NeuralCommandCenter, NeuralResult


class TestSyntaxPredictor:
    def setup_method(self):
        self.predictor = SyntaxPredictor()

    def test_detects_common_typo(self):
        r = self.predictor.predict("pytst tests/")
        assert r is not None
        assert r.probability >= 0.85
        assert "pytest" in r.suggestion

    def test_detects_unmatched_quote(self):
        r = self.predictor.predict("echo 'hello")
        assert r is not None
        assert r.probability >= 0.80

    def test_no_false_positive_on_valid_command(self):
        r = self.predictor.predict("git status")
        assert r is None

    def test_detects_gti_typo(self):
        r = self.predictor.predict("gti status")
        assert r is not None
        assert "git" in r.suggestion


class TestDependencyPredictor:
    def setup_method(self):
        self.predictor = DependencyPredictor()

    def test_detects_missing_python_module(self):
        r = self.predictor.predict("python -m nonexistent_xyz_module_42")
        assert r is not None
        assert r.probability >= 0.80

    def test_no_false_positive_on_installed_module(self):
        r = self.predictor.predict("python -m pytest")
        assert r is None


class TestTimeoutPredictor:
    def setup_method(self):
        self.predictor = TimeoutPredictor()

    def test_detects_tail_f(self):
        r = self.predictor.predict("tail -f app.log")
        assert r is not None
        assert r.probability >= 0.85

    def test_detects_vim(self):
        r = self.predictor.predict("vim file.txt")
        assert r is not None
        assert r.probability >= 0.85

    def test_no_false_positive_on_quick_command(self):
        r = self.predictor.predict("echo hello")
        assert r is None


class TestPermissionPredictor:
    def setup_method(self):
        self.predictor = PermissionPredictor()

    def test_detects_npm_global(self):
        r = self.predictor.predict("npm install -g typescript")
        assert r is not None
        assert r.probability >= 0.65

    def test_ignores_sudo_prefix(self):
        r = self.predictor.predict("sudo npm install -g typescript")
        assert r is None

    def test_no_false_positive_on_local_install(self):
        r = self.predictor.predict("npm install express")
        assert r is None


class TestContextPredictor:
    def setup_method(self):
        self.predictor = ContextPredictor()

    def test_detects_missing_cargo_toml(self):
        r = self.predictor.predict("cargo build")
        assert r is not None
        assert r.probability >= 0.80

    def test_detects_missing_manage_py(self):
        r = self.predictor.predict("python manage.py runserver")
        assert r is not None
        assert "manage.py" in r.reason


class TestCompressionSelector:
    def setup_method(self):
        self.predictor = CompressionSelector()

    def test_selects_diff_strategy(self):
        r = self.predictor.predict("git diff HEAD~1")
        assert r.suggestion == "diff"

    def test_selects_test_output_strategy(self):
        r = self.predictor.predict("pytest tests/ -v")
        assert r.suggestion == "test_output"

    def test_selects_progress_strategy(self):
        r = self.predictor.predict("pip install requests")
        assert r.suggestion == "progress"

    def test_fallback_to_generic(self):
        r = self.predictor.predict("echo hello world")
        assert r.suggestion == "generic"


class TestAgentRanker:
    def setup_method(self):
        self.ranker = AgentRanker()

    def test_test_command_gets_test_agent(self):
        agents = self.ranker.rank_agents("pytest tests/")
        assert "Test Agent" in agents

    def test_git_push_gets_security_agent(self):
        agents = self.ranker.rank_agents("git push origin main")
        assert "Security Agent" in agents

    def test_always_includes_code_agent(self):
        agents = self.ranker.rank_agents("echo hello")
        assert "Code Agent" in agents

    def test_max_agents_cap(self):
        agents = self.ranker.rank_agents("python -m pytest tests/")
        assert len(agents) <= 4


class TestNeuralCommandCenter:
    def setup_method(self):
        self.center = NeuralCommandCenter()

    def test_detects_typo_and_suggests_fix(self):
        result = self.center.analyze("pytst tests/")
        assert result.will_fail is True
        assert len(result.warnings) > 0
        assert len(result.suggestions) > 0

    def test_safe_command_no_warnings(self):
        result = self.center.analyze("git status")
        assert result.will_fail is False
        assert len(result.warnings) == 0

    def test_always_returns_compression_strategy(self):
        result = self.center.analyze("git diff")
        assert result.compression_strategy == "diff"

    def test_always_returns_agents(self):
        result = self.center.analyze("pytest tests/")
        assert len(result.agents_to_run) > 0

    def test_to_dict_structure(self):
        result = self.center.analyze("echo hello")
        d = result.to_dict()
        assert "command" in d
        assert "will_fail" in d
        assert "confidence" in d
        assert "warnings" in d
        assert "compression_strategy" in d
        assert "agents_to_run" in d

    def test_blocking_command_detected(self):
        result = self.center.analyze("tail -f /var/log/syslog")
        assert result.will_fail is True
        assert any("timeout" in w for w in result.warnings)
