"""Main auto-fix orchestrator."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from ..store import connect
from .analyzers.python_analyzer import PythonAnalyzer
from .analyzers.javascript_analyzer import JavaScriptAnalyzer
from .fixers.import_fixer import ImportFixer
from .fixers.dependency_fixer import DependencyFixer
from .knowledge_base import KnowledgeBase


@dataclass
class FixResult:
    """Result of an auto-fix attempt."""
    success: bool
    fix_applied: Optional[str]
    confidence: float
    error_message: Optional[str] = None


class AutoFixEngine:
    """Main auto-fix orchestrator that analyzes errors and applies fixes."""

    def __init__(self):
        self.analyzers = [
            PythonAnalyzer(),
            JavaScriptAnalyzer(),
        ]
        self.fixers = [
            ImportFixer(),
            DependencyFixer(),
        ]
        self.knowledge_base = KnowledgeBase()

    def analyze_and_fix(
        self,
        stdout: str,
        stderr: str,
        exit_code: int,
        command: str,
        apply: bool = False,
        min_confidence: float = 0.8,
    ) -> FixResult:
        """
        Analyze command output and optionally apply fix.

        Args:
            stdout: Standard output from command
            stderr: Standard error from command
            exit_code: Command exit code
            command: Original command that failed
            apply: Whether to actually apply the fix
            min_confidence: Minimum confidence threshold (0.0-1.0)

        Returns:
            FixResult with success status and details
        """
        if exit_code == 0:
            return FixResult(
                success=False,
                fix_applied=None,
                confidence=0.0,
                error_message="Command succeeded, no fix needed",
            )

        combined_output = f"{stdout}\n{stderr}"

        # Step 1: Analyze error with appropriate analyzer
        error_analysis = None
        for analyzer in self.analyzers:
            if analyzer.can_handle(combined_output, command):
                error_analysis = analyzer.analyze(combined_output, command)
                break

        if not error_analysis:
            return FixResult(
                success=False,
                fix_applied=None,
                confidence=0.0,
                error_message="No analyzer could handle this error",
            )

        # Step 2: Check knowledge base for historical fixes
        historical_fix = self.knowledge_base.find_fix(
            error_pattern=error_analysis.pattern,
            language=error_analysis.language,
        )

        if historical_fix and historical_fix.success_rate > min_confidence:
            confidence = historical_fix.success_rate
            fix_template = historical_fix.template
        else:
            # Step 3: Generate fix from appropriate fixer
            fix_template = None
            confidence = 0.0
            for fixer in self.fixers:
                if fixer.can_fix(error_analysis):
                    fix_template = fixer.generate_fix(error_analysis)
                    confidence = fixer.confidence
                    break

            if not fix_template:
                return FixResult(
                    success=False,
                    fix_applied=None,
                    confidence=0.0,
                    error_message="No fixer available for this error type",
                )

        # Step 4: Check confidence threshold
        if confidence < min_confidence:
            return FixResult(
                success=False,
                fix_applied=fix_template,
                confidence=confidence,
                error_message=f"Confidence {confidence:.0%} below threshold {min_confidence:.0%}",
            )

        # Step 5: Apply fix if requested
        if apply:
            try:
                success = self._apply_fix(fix_template, error_analysis)
                if success:
                    # Record successful fix
                    self.knowledge_base.record_fix_attempt(
                        error_pattern=error_analysis.pattern,
                        fix_template=fix_template,
                        language=error_analysis.language,
                        success=True,
                    )
                    return FixResult(
                        success=True,
                        fix_applied=fix_template,
                        confidence=confidence,
                    )
                else:
                    # Record failed fix
                    self.knowledge_base.record_fix_attempt(
                        error_pattern=error_analysis.pattern,
                        fix_template=fix_template,
                        language=error_analysis.language,
                        success=False,
                    )
                    return FixResult(
                        success=False,
                        fix_applied=fix_template,
                        confidence=confidence,
                        error_message="Fix application failed",
                    )
            except Exception as e:
                return FixResult(
                    success=False,
                    fix_applied=fix_template,
                    confidence=confidence,
                    error_message=f"Error applying fix: {str(e)}",
                )
        else:
            # Just suggest, don't apply
            return FixResult(
                success=False,
                fix_applied=fix_template,
                confidence=confidence,
                error_message="Fix available but not applied (use --apply flag)",
            )

    def _apply_fix(self, fix_template: str, error_analysis) -> bool:
        """Actually apply the fix to the file system."""
        import subprocess
        import sys

        # Extract command from fix template
        # For now, we support pip install and npm install commands
        if fix_template.startswith("pip install "):
            package = fix_template.replace("pip install ", "")
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", package],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                return result.returncode == 0
            except Exception:
                return False

        elif fix_template.startswith("npm install "):
            package = fix_template.replace("npm install ", "")
            try:
                result = subprocess.run(
                    ["npm", "install", package],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                return result.returncode == 0
            except Exception:
                return False

        # Other fix types not yet implemented
        return False
