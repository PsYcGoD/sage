"""Natural language parser for SAGE commands."""

from __future__ import annotations

import re


class NLParser:
    """Parse simple natural language requests into SAGE commands."""

    def __init__(self):
        self.patterns = self._build_patterns()

    def parse(self, text: str) -> str | None:
        """Return a SAGE command string, or None when no pattern matches."""
        normalized = text.lower().strip()

        for pattern_group in self.patterns:
            for pattern in pattern_group["patterns"]:
                match = re.search(pattern, normalized, re.IGNORECASE)
                if match:
                    command = pattern_group["command"]
                    if match.groups():
                        command = command.format(*match.groups())
                    return command

        return None

    def get_suggestions(self, partial: str) -> list[str]:
        """Get command suggestions for partial natural-language input."""
        partial = partial.lower()
        keywords = {
            "run": "sage run -- <command>",
            "fix": "sage fix --apply",
            "explain": "sage explain --failed",
            "suggest": "sage suggest --failed",
            "test": "sage workflow run test",
            "history": "sage history",
            "agents": "sage agents list",
            "workflow": "sage workflow list",
            "dashboard": "sage dashboard start",
            "predict": "sage predict -- <command>",
        }
        return [command for keyword, command in keywords.items() if keyword.startswith(partial)][:5]

    def _build_patterns(self) -> list[dict]:
        return [
            {
                "intent": "run_command",
                "patterns": [r"run\s+(.+)", r"execute\s+(.+)", r"please run\s+(.+)"],
                "command": "sage run -- {0}",
            },
            {
                "intent": "predict_failure",
                "patterns": [r"predict\s+(.+)", r"will\s+(.+)\s+fail"],
                "command": "sage predict -- {0}",
            },
            {
                "intent": "explain_error",
                "patterns": [
                    r"what went wrong",
                    r"explain.*(error|failure|problem)",
                    r"what (happened|broke)",
                    r"show.*(error|failure)",
                ],
                "command": "sage explain --failed",
            },
            {
                "intent": "suggest_fix",
                "patterns": [
                    r"how (do i|to) fix",
                    r"what should i do",
                    r"suggest.*fix",
                    r"how can i solve",
                ],
                "command": "sage suggest --failed",
            },
            {
                "intent": "auto_fix",
                "patterns": [r"fix (it|this|the error)", r"apply.*fix", r"auto.?fix"],
                "command": "sage fix --apply",
            },
            {
                "intent": "run_tests",
                "patterns": [r"run.*tests?", r"test (everything|all|it)", r"execute.*tests?"],
                "command": "sage workflow run test",
            },
            {
                "intent": "show_history",
                "patterns": [r"show.*history", r"what.*run", r"recent commands", r"command history"],
                "command": "sage history",
            },
            {
                "intent": "list_agents",
                "patterns": [r"list agents", r"show.*agents", r"what agents"],
                "command": "sage agents list",
            },
        ]
