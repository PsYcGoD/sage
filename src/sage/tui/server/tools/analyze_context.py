"""Analyze context tool - pattern detection, style, file structure."""
from __future__ import annotations

from pathlib import Path

from .base import BaseTool


class AnalyzeContextTool(BaseTool):
    """Analyze codebase patterns, style, and structure."""

    @property
    def name(self) -> str:
        return "sage_analyze_context"

    @property
    def description(self) -> str:
        return "Analyze codebase patterns (naming, error handling, testing), style (indent, quotes), file structure"

    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self._parameters(),
            },
        }

    def _parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File or directory to analyze"},
                "sample_size": {"type": "integer", "description": "Number of files to sample (default 15)"},
            },
        }

    async def execute(self, input_data: dict) -> dict:
        target = Path(input_data.get("path", "."))
        sample_size = input_data.get("sample_size", 15)

        if not target.exists():
            return {"error": f"Path not found: {target}"}

        root = target if target.is_dir() else target.parent

        try:
            from sage.codegen import PatternDetector, StyleEnforcer, ContextBuilder

            # Pattern detection
            detector = PatternDetector(root)
            patterns = detector.detect_all(sample_size=sample_size)
            pattern_summary = detector.summarize_patterns(patterns)

            # Style detection
            enforcer = StyleEnforcer(root)
            style = enforcer.get_profile()
            style_summary = enforcer.summarize_style()

            # File context if specific file
            file_summary = None
            related_files = []
            if target.is_file():
                builder = ContextBuilder(root)
                file_summary = builder.summarize_file(target)
                related = builder.find_related_files(target)
                related_files = [str(p.relative_to(root)) for p in related[:5]]

            return {
                "success": True,
                "patterns": [
                    {
                        "category": p.category,
                        "pattern": p.pattern,
                        "confidence": p.confidence,
                    }
                    for p in patterns
                ],
                "style": {
                    "indent_type": style.indent_type,
                    "indent_size": style.indent_size,
                    "quote_style": style.quote_style,
                    "max_line_length": style.max_line_length,
                },
                "pattern_summary": pattern_summary,
                "style_summary": style_summary,
                "file_summary": file_summary,
                "related_files": related_files,
            }
        except Exception as e:
            return {"error": f"Analysis failed: {e}"}
