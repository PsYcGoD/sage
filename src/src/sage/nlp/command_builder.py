"""Command builder from parsed intents."""

from __future__ import annotations

from typing import Dict, Optional


class CommandBuilder:
    """Build SAGE commands from parsed intents."""

    def build(self, intent: str, entities: Dict) -> Optional[str]:
        """
        Build command from intent and entities.
        
        Args:
            intent: Detected intent (e.g., 'run_command', 'fix_error')
            entities: Extracted entities (e.g., {'command': 'pytest'})
            
        Returns:
            SAGE command string
        """
        builders = {
            'run_command': self._build_run,
            'explain_error': self._build_explain,
            'suggest_fix': self._build_suggest,
            'auto_fix': self._build_fix,
            'run_tests': self._build_tests,
            'show_history': self._build_history,
            'list_agents': self._build_agents,
            'run_workflow': self._build_workflow,
        }

        builder = builders.get(intent)
        if builder:
            return builder(entities)

        return None

    def _build_run(self, entities: Dict) -> str:
        """Build 'sage run' command."""
        command = entities.get('command', '')
        return f'sage run -- {command}'

    def _build_explain(self, entities: Dict) -> str:
        """Build 'sage explain' command."""
        failed = entities.get('failed', True)
        return 'sage explain --failed' if failed else 'sage explain'

    def _build_suggest(self, entities: Dict) -> str:
        """Build 'sage suggest' command."""
        failed = entities.get('failed', True)
        return 'sage suggest --failed' if failed else 'sage suggest'

    def _build_fix(self, entities: Dict) -> str:
        """Build 'sage fix' command."""
        apply = entities.get('apply', True)
        return 'sage fix --apply' if apply else 'sage fix'

    def _build_tests(self, entities: Dict) -> str:
        """Build test command."""
        workflow = entities.get('workflow', 'test')
        return f'sage workflow run {workflow}'

    def _build_history(self, entities: Dict) -> str:
        """Build 'sage history' command."""
        limit = entities.get('limit', 10)
        return f'sage history --limit {limit}'

    def _build_agents(self, entities: Dict) -> str:
        """Build 'sage agents' command."""
        return 'sage agents list'

    def _build_workflow(self, entities: Dict) -> str:
        """Build 'sage workflow' command."""
        workflow = entities.get('workflow', 'test')
        return f'sage workflow run {workflow}'
