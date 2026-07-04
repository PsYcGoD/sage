"""Feature extraction for command failure prediction."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Mapping
import re


class FeatureExtractor:
    """Extract numeric command and project features."""

    def extract(
        self,
        command: str,
        context: Mapping[str, float] | None = None,
        project_path: Path | None = None,
    ) -> dict[str, float]:
        """Return feature_name -> feature_value for a command."""
        context = context or {}
        project_path = project_path or Path.cwd()
        command_lower = command.lower()
        args = command.split()
        now = datetime.now()

        return {
            "cmd_length": float(len(command)),
            "arg_count": float(len(args)),
            "has_test_keyword": self._has_any(command_lower, ["test", "pytest", "unittest", "jest"]),
            "has_pytest_keyword": self._has_any(command_lower, ["pytest"]),
            "has_build_keyword": self._has_any(command_lower, ["build", "compile", "make"]),
            "has_install_keyword": self._has_install_intent(command_lower),
            "has_error_keyword": self._has_any(command_lower, ["error", "fail", "missing", "broken"]),
            "has_shell_chain": 1.0 if any(token in command for token in ["&&", "||", ";"]) else 0.0,
            "has_path_argument": 1.0 if re.search(r"[/\\]|\.\w{1,6}\b", command) else 0.0,
            "starts_python": 1.0 if command_lower.startswith(("python", "py ")) else 0.0,
            "starts_node": 1.0 if command_lower.startswith(("node", "npm", "yarn", "pnpm")) else 0.0,
            "starts_git": 1.0 if command_lower.startswith("git") else 0.0,
            "starts_sage": 1.0 if command_lower.startswith("sage") else 0.0,
            "hour_of_day": float(now.hour),
            "is_monday": 1.0 if now.weekday() == 0 else 0.0,
            "is_friday": 1.0 if now.weekday() == 4 else 0.0,
            "minutes_since_last_failure": float(context.get("minutes_since_last_failure", 1440.0)),
            "num_recent_failures": float(context.get("num_recent_failures", 0.0)),
            "num_recent_changes": float(context.get("num_recent_changes", 0.0)),
            "has_requirements_txt": 1.0 if (project_path / "requirements.txt").exists() else 0.0,
            "has_package_json": 1.0 if (project_path / "package.json").exists() else 0.0,
            "has_tests_dir": 1.0 if (project_path / "tests").exists() else 0.0,
        }

    def get_feature_names(self) -> list[str]:
        """Get feature names in stable model order."""
        return [
            "cmd_length",
            "arg_count",
            "has_test_keyword",
            "has_pytest_keyword",
            "has_build_keyword",
            "has_install_keyword",
            "has_error_keyword",
            "has_shell_chain",
            "has_path_argument",
            "starts_python",
            "starts_node",
            "starts_git",
            "starts_sage",
            "hour_of_day",
            "is_monday",
            "is_friday",
            "minutes_since_last_failure",
            "num_recent_failures",
            "num_recent_changes",
            "has_requirements_txt",
            "has_package_json",
            "has_tests_dir",
        ]

    @staticmethod
    def _has_any(text: str, words: list[str]) -> float:
        return 1.0 if any(word in text for word in words) else 0.0

    @staticmethod
    def _has_install_intent(text: str) -> float:
        install_patterns = [
            "install",
            "pip install",
            "python -m pip install",
            "npm install",
            "npm i ",
            "yarn add",
            "yarn install",
        ]
        return 1.0 if any(pattern in text for pattern in install_patterns) else 0.0
