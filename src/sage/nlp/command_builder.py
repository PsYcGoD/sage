"""Command builder from parsed intents."""

from __future__ import annotations

from typing import Mapping


class CommandBuilder:
    """Build SAGE commands from intents and extracted entities."""

    def build(self, intent: str, entities: Mapping) -> str | None:
        builders = {
            "run_command": self._build_run,
            "predict_failure": self._build_predict,
            "explain_error": self._build_explain,
            "suggest_fix": self._build_suggest,
            "auto_fix": self._build_fix,
            "run_tests": self._build_tests,
            "show_history": self._build_history,
            "list_agents": self._build_agents,
            "run_workflow": self._build_workflow,
        }
        builder = builders.get(intent)
        return builder(entities) if builder else None

    def _build_run(self, entities: Mapping) -> str:
        return f"sage run -- {entities.get('command', '')}"

    def _build_predict(self, entities: Mapping) -> str:
        return f"sage predict -- {entities.get('command', '')}"

    def _build_explain(self, entities: Mapping) -> str:
        return "sage explain --failed" if entities.get("failed", True) else "sage explain"

    def _build_suggest(self, entities: Mapping) -> str:
        return "sage suggest --failed" if entities.get("failed", True) else "sage suggest"

    def _build_fix(self, entities: Mapping) -> str:
        return "sage fix --apply" if entities.get("apply", True) else "sage fix"

    def _build_tests(self, entities: Mapping) -> str:
        return f"sage workflow run {entities.get('workflow', 'test')}"

    def _build_history(self, entities: Mapping) -> str:
        return f"sage history --limit {entities.get('limit', 10)}"

    def _build_agents(self, entities: Mapping) -> str:
        return "sage agents list"

    def _build_workflow(self, entities: Mapping) -> str:
        return f"sage workflow run {entities.get('workflow', 'test')}"
