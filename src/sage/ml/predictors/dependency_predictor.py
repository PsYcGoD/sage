"""Dependency Missing Predictor - detects missing packages/modules."""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path
from typing import Optional

from .base import BasePredictor, Prediction

PACKAGE_MANAGERS = {"pip", "pip3", "pipx", "npm", "npx", "yarn", "pnpm", "cargo", "gem", "go"}

IMPORT_COMMANDS = {
    "python": "pip install",
    "python3": "pip install",
    "node": "npm install",
    "ruby": "gem install",
    "cargo": "cargo add",
}


class DependencyPredictor(BasePredictor):
    """Detects commands likely to fail due to missing dependencies."""

    CATEGORY = "dependency_missing"

    def predict(self, command: str, **context) -> Optional[Prediction]:
        parts = command.strip().split()
        if not parts:
            return None

        base_cmd = parts[0].lower()
        reasons = []
        probability = 0.0
        suggestion = None

        # Direct tool invocation - check if tool exists
        if base_cmd not in PACKAGE_MANAGERS and shutil.which(base_cmd) is None:
            # Check common dev tools that need installation
            dev_tools = {
                "pytest": "pip install pytest",
                "black": "pip install black",
                "ruff": "pip install ruff",
                "mypy": "pip install mypy",
                "flask": "pip install flask",
                "django-admin": "pip install django",
                "uvicorn": "pip install uvicorn",
                "gunicorn": "pip install gunicorn",
                "tsc": "npm install -g typescript",
                "eslint": "npm install eslint",
                "jest": "npm install jest",
                "vitest": "npm install vitest",
                "webpack": "npm install webpack",
                "vite": "npm install vite",
            }
            if base_cmd in dev_tools:
                reasons.append(f"'{base_cmd}' not installed")
                suggestion = f"Install: {dev_tools[base_cmd]}"
                probability = max(probability, 0.90)

        # python -m <module> pattern
        if base_cmd in ("python", "python3") and len(parts) >= 3 and parts[1] == "-m":
            module = parts[2]
            # Check if module is importable
            try:
                import importlib.util
                if importlib.util.find_spec(module) is None:
                    reasons.append(f"Module '{module}' not found")
                    suggestion = f"Install: pip install {module}"
                    probability = max(probability, 0.85)
            except (ModuleNotFoundError, ValueError):
                reasons.append(f"Module '{module}' not importable")
                suggestion = f"Install: pip install {module}"
                probability = max(probability, 0.80)

        # npm/yarn run without package.json
        if base_cmd in ("npm", "yarn", "pnpm") and len(parts) >= 2:
            if parts[1] in ("run", "start", "test", "build"):
                if not Path("package.json").exists():
                    reasons.append("No package.json in current directory")
                    suggestion = "Run: npm init or cd to project root"
                    probability = max(probability, 0.85)
                elif parts[1] != "start" and not Path("node_modules").exists():
                    reasons.append("node_modules missing")
                    suggestion = "Run: npm install"
                    probability = max(probability, 0.80)

        # Check past failures for this command from history
        db_path = context.get("db_path")
        if db_path and probability < 0.5:
            prob = self._check_history(command, db_path)
            if prob > probability:
                probability = prob
                reasons.append("Similar commands failed with import/module errors")

        if not reasons:
            return None

        return Prediction(
            category=self.CATEGORY,
            probability=probability,
            will_trigger=probability >= 0.65,
            reason="; ".join(reasons),
            suggestion=suggestion,
        )

    def _check_history(self, command: str, db_path: Path) -> float:
        """Check if similar commands have failed with dependency errors."""
        try:
            with sqlite3.connect(db_path) as conn:
                rows = conn.execute(
                    """
                    SELECT stderr FROM runs
                    WHERE command = ? AND exit_code != 0
                    ORDER BY created_at DESC LIMIT 5
                    """,
                    (command,),
                ).fetchall()

            dep_errors = ("ModuleNotFoundError", "ImportError", "command not found",
                          "Cannot find module", "MODULE_NOT_FOUND")
            for row in rows:
                stderr = row[0] or ""
                if any(err in stderr for err in dep_errors):
                    return 0.85
            return 0.0
        except Exception:
            return 0.0
