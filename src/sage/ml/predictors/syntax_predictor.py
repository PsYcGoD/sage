"""Syntax Error Predictor - detects typos, missing quotes, malformed commands."""

from __future__ import annotations

import re
import shutil
from typing import Optional

from .base import BasePredictor, Prediction

COMMON_TYPOS = {
    "pytset": "pytest",
    "pytst": "pytest",
    "pyhton": "python",
    "ptyhon": "python",
    "pyton": "python",
    "gti": "git",
    "gi": "git",
    "giit": "git",
    "npx": "npx",
    "nmp": "npm",
    "nmpm": "npm",
    "dcoker": "docker",
    "dokcer": "docker",
    "kubeclt": "kubectl",
    "kubctl": "kubectl",
}

UNMATCHED_QUOTES = re.compile(r"""^[^'"]*(?:'[^']*$|"[^"]*$)""")
UNMATCHED_PARENS = re.compile(r"^[^()]*\([^)]*$")
DOUBLE_FLAGS = re.compile(r"--\w+--\w+")


class SyntaxPredictor(BasePredictor):
    """Detects syntax errors: typos, unmatched quotes, malformed flags."""

    CATEGORY = "syntax_error"

    def predict(self, command: str, **context) -> Optional[Prediction]:
        parts = command.strip().split()
        if not parts:
            return None

        base_cmd = parts[0].lower()
        reasons = []
        probability = 0.0

        # Check for common typos in command name
        if base_cmd in COMMON_TYPOS:
            correct = COMMON_TYPOS[base_cmd]
            reasons.append(f"Typo: '{base_cmd}' → did you mean '{correct}'?")
            probability = max(probability, 0.90)

        # Check if command exists on PATH
        elif not base_cmd.startswith(("./", "/", "\\")) and shutil.which(base_cmd) is None:
            # Only flag if it looks like a real command (not a path)
            if not any(c in base_cmd for c in "/\\:."):
                reasons.append(f"Command '{base_cmd}' not found on PATH")
                probability = max(probability, 0.75)

        # Unmatched quotes
        if UNMATCHED_QUOTES.search(command):
            reasons.append("Unmatched quote detected")
            probability = max(probability, 0.85)

        # Unmatched parentheses
        if UNMATCHED_PARENS.search(command):
            reasons.append("Unmatched parenthesis")
            probability = max(probability, 0.70)

        # Double-dashed flags merged (--force--verbose)
        if DOUBLE_FLAGS.search(command):
            reasons.append("Malformed flag (merged double-dash flags)")
            probability = max(probability, 0.80)

        if not reasons:
            return None

        suggestion = None
        if base_cmd in COMMON_TYPOS:
            correct = COMMON_TYPOS[base_cmd]
            suggestion = f"Did you mean: {correct} {' '.join(parts[1:])}"

        return Prediction(
            category=self.CATEGORY,
            probability=probability,
            will_trigger=probability >= 0.65,
            reason="; ".join(reasons),
            suggestion=suggestion,
        )
