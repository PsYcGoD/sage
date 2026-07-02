"""YAML workflow parser with validation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

try:
    import yaml
except ImportError:
    yaml = None


@dataclass
class WorkflowStep:
    """Single step in a workflow pipeline."""
    name: str
    run: str
    on_fail: Optional[list[str]] = None
    on_success: Optional[list[str]] = None
    continue_on_fail: bool = False
    parallel: bool = False
    timeout: int = 300
    retry: int = 0


@dataclass
class Workflow:
    """Complete workflow definition."""
    name: str
    version: str
    env: dict[str, str]
    variables: dict[str, Any]
    pipeline: list[WorkflowStep]


class WorkflowParser:
    """Parse and validate YAML workflow files."""

    def __init__(self):
        if yaml is None:
            raise ImportError("PyYAML not installed. Run: pip install pyyaml")

    def parse_file(self, file_path: Path) -> Workflow:
        """Parse workflow from YAML file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        return self.parse_dict(data)

    def parse_dict(self, data: dict) -> Workflow:
        """Parse workflow from dictionary."""
        # Extract basic info
        name = data.get('name', 'unnamed-workflow')
        version = data.get('version', '1.0')
        env = data.get('env', {})
        variables = data.get('variables', {})

        # Parse pipeline steps
        pipeline = []
        for step_data in data.get('pipeline', []):
            step = WorkflowStep(
                name=step_data['name'],
                run=step_data['run'],
                on_fail=step_data.get('on_fail'),
                on_success=step_data.get('on_success'),
                continue_on_fail=step_data.get('continue_on_fail', False),
                parallel=step_data.get('parallel', False),
                timeout=step_data.get('timeout', 300),
                retry=step_data.get('retry', 0),
            )
            pipeline.append(step)

        return Workflow(
            name=name,
            version=version,
            env=env,
            variables=variables,
            pipeline=pipeline,
        )

    def validate(self, workflow: Workflow) -> list[str]:
        """Validate workflow and return list of errors."""
        errors = []

        if not workflow.name:
            errors.append("Workflow name is required")

        if not workflow.pipeline:
            errors.append("Pipeline must have at least one step")

        for i, step in enumerate(workflow.pipeline):
            if not step.name:
                errors.append(f"Step {i} missing name")
            if not step.run:
                errors.append(f"Step {i} missing run command")

        return errors
