"""Neural Command Center - orchestrates all specialized predictors."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .predictors.base import Prediction
from .predictors.syntax_predictor import SyntaxPredictor
from .predictors.dependency_predictor import DependencyPredictor
from .predictors.auth_predictor import AuthPredictor
from .predictors.timeout_predictor import TimeoutPredictor
from .predictors.permission_predictor import PermissionPredictor
from .predictors.context_predictor import ContextPredictor
from .predictors.compression_selector import CompressionSelector
from .predictors.agent_ranker import AgentRanker

logger = logging.getLogger(__name__)


@dataclass
class NeuralResult:
    """Unified result from the Neural Command Center."""

    command: str
    will_fail: bool
    confidence: float
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    compression_strategy: str = "generic"
    agents_to_run: List[str] = field(default_factory=list)
    predictions: Dict[str, Prediction] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "command": self.command,
            "will_fail": self.will_fail,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "compression_strategy": self.compression_strategy,
            "agents_to_run": self.agents_to_run,
        }


class NeuralCommandCenter:
    """Master orchestrator coordinating all 8 specialized predictors.

    Routes commands through relevant predictors, combines predictions,
    and returns a unified result with all warnings and recommendations.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path
        self.syntax = SyntaxPredictor()
        self.dependency = DependencyPredictor()
        self.auth = AuthPredictor()
        self.timeout = TimeoutPredictor()
        self.permission = PermissionPredictor()
        self.context = ContextPredictor()
        self.compression = CompressionSelector()
        self.agent_ranker = AgentRanker()

        self._failure_predictors = [
            self.syntax,
            self.dependency,
            self.auth,
            self.timeout,
            self.permission,
            self.context,
        ]

    def analyze(self, command: str) -> NeuralResult:
        """Run command through all predictors and return unified result."""
        context = {"db_path": self.db_path}
        predictions: Dict[str, Prediction] = {}
        warnings: List[str] = []
        suggestions: List[str] = []
        max_confidence = 0.0
        will_fail = False

        # Run failure predictors
        for predictor in self._failure_predictors:
            try:
                pred = predictor.predict(command, **context)
                if pred is not None:
                    predictions[pred.category] = pred
                    if pred.will_trigger:
                        warnings.append(
                            f"{pred.category}: {pred.reason} ({pred.probability*100:.0f}%)"
                        )
                        if pred.suggestion:
                            suggestions.append(pred.suggestion)
                        max_confidence = max(max_confidence, pred.probability)
                        will_fail = True
            except Exception as e:
                logger.debug(f"Predictor {predictor.CATEGORY} error: {e}")

        # Compression strategy (always runs)
        comp_pred = self.compression.predict(command, **context)
        compression_strategy = "generic"
        if comp_pred and comp_pred.suggestion:
            compression_strategy = comp_pred.suggestion
            predictions[comp_pred.category] = comp_pred

        # Agent ranking (always runs)
        agents_to_run = self.agent_ranker.rank_agents(command)
        agent_pred = self.agent_ranker.predict(command, **context)
        if agent_pred:
            predictions[agent_pred.category] = agent_pred

        # Calculate overall confidence
        if not will_fail:
            max_confidence = 0.2  # Low confidence = likely safe

        return NeuralResult(
            command=command,
            will_fail=will_fail,
            confidence=min(max_confidence, 0.95),
            warnings=warnings,
            suggestions=suggestions,
            compression_strategy=compression_strategy,
            agents_to_run=agents_to_run,
            predictions=predictions,
        )
