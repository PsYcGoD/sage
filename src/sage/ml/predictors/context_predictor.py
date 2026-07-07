"""Context Predictor - detects wrong directory or missing virtual environment."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from .base import BasePredictor, Prediction

PROJECT_MARKERS = {
    "python": ["setup.py", "pyproject.toml", "setup.cfg", "requirements.txt"],
    "node": ["package.json", "node_modules"],
    "rust": ["Cargo.toml"],
    "go": ["go.mod"],
    "ruby": ["Gemfile"],
    "java": ["pom.xml", "build.gradle"],
}

VENV_COMMANDS = {"pytest", "python", "python3", "pip", "pip3", "flask", "django-admin", "uvicorn", "gunicorn"}


class ContextPredictor(BasePredictor):
    """Detects commands likely to fail due to wrong directory or missing venv."""

    CATEGORY = "context_error"

    def predict(self, command: str, **context) -> Optional[Prediction]:
        parts = command.strip().split()
        if not parts:
            return None

        base_cmd = parts[0].lower()
        reasons = []
        probability = 0.0
        suggestion = None

        # Python command without active virtualenv
        if base_cmd in VENV_COMMANDS:
            if not os.environ.get("VIRTUAL_ENV") and not os.environ.get("CONDA_DEFAULT_ENV"):
                # Check if a venv exists but isn't activated
                venv_dirs = [".venv", "venv", "env", ".env"]
                for vd in venv_dirs:
                    venv_path = Path(vd)
                    if venv_path.is_dir() and (venv_path / "pyvenv.cfg").exists():
                        reasons.append(f"Virtual environment '{vd}' exists but not activated")
                        probability = max(probability, 0.55)
                        if os.name == "nt":
                            suggestion = f"Activate: {vd}\\Scripts\\activate"
                        else:
                            suggestion = f"Activate: source {vd}/bin/activate"
                        break

        # manage.py commands outside Django project root
        if "manage.py" in command:
            if not Path("manage.py").exists():
                reasons.append("manage.py not found in current directory")
                probability = max(probability, 0.85)
                suggestion = "cd to Django project root (where manage.py lives)"

        # npm/yarn commands without package.json
        if base_cmd in ("npm", "yarn", "pnpm") and len(parts) >= 2:
            if parts[1] not in ("init", "create", "help", "--version", "-v"):
                if not Path("package.json").exists():
                    reasons.append("No package.json in current directory")
                    probability = max(probability, 0.80)
                    suggestion = "cd to project root or run: npm init"

        # cargo commands without Cargo.toml
        if base_cmd == "cargo" and len(parts) >= 2:
            if parts[1] not in ("init", "new", "help", "--version"):
                if not Path("Cargo.toml").exists():
                    reasons.append("No Cargo.toml in current directory")
                    probability = max(probability, 0.85)
                    suggestion = "cd to Rust project root"

        # Makefile commands without Makefile
        if base_cmd == "make":
            if not Path("Makefile").exists() and not Path("makefile").exists():
                reasons.append("No Makefile in current directory")
                probability = max(probability, 0.90)
                suggestion = "cd to directory with Makefile"

        if not reasons:
            return None

        return Prediction(
            category=self.CATEGORY,
            probability=probability,
            will_trigger=probability >= 0.55,
            reason="; ".join(reasons),
            suggestion=suggestion,
        )
