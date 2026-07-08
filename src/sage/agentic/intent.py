"""Intent detection — understands multi-step workflows and what the user is trying to do."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class WorkflowStep:
    """A step in a detected workflow."""
    name: str
    command_patterns: list[str]
    completed: bool = False


@dataclass
class DetectedIntent:
    """A recognized user intent with its workflow steps."""
    name: str
    steps: list[WorkflowStep]
    current_step: int = 0
    confidence: float = 0.0

    @property
    def progress(self) -> str:
        done = sum(1 for s in self.steps if s.completed)
        return f"{done}/{len(self.steps)}"

    @property
    def next_step(self) -> WorkflowStep | None:
        for step in self.steps:
            if not step.completed:
                return step
        return None


# Known multi-step workflow templates
WORKFLOW_TEMPLATES = [
    {
        "name": "deploy",
        "triggers": [r"deploy", r"ship", r"release"],
        "steps": [
            WorkflowStep("build", ["build", "compile", "bundle"]),
            WorkflowStep("test", ["test", "pytest", "jest", "mocha"]),
            WorkflowStep("push", ["git push", "push"]),
            WorkflowStep("deploy", ["deploy", "publish", "release"]),
            WorkflowStep("verify", ["curl", "health", "status"]),
        ],
    },
    {
        "name": "fix_bug",
        "triggers": [r"fix", r"debug", r"bug"],
        "steps": [
            WorkflowStep("reproduce", ["test", "run", "reproduce"]),
            WorkflowStep("debug", ["print", "log", "debug", "breakpoint"]),
            WorkflowStep("fix", ["edit", "sed", "patch"]),
            WorkflowStep("verify", ["test", "pytest", "jest"]),
            WorkflowStep("commit", ["git commit", "git add"]),
        ],
    },
    {
        "name": "setup_project",
        "triggers": [r"setup", r"init", r"bootstrap", r"clone"],
        "steps": [
            WorkflowStep("clone", ["git clone", "clone"]),
            WorkflowStep("install_deps", ["npm install", "pip install", "yarn", "pnpm"]),
            WorkflowStep("configure", ["cp .env", "config", "setup"]),
            WorkflowStep("verify", ["test", "run", "start"]),
        ],
    },
    {
        "name": "refactor",
        "triggers": [r"refactor", r"rename", r"restructure"],
        "steps": [
            WorkflowStep("test_before", ["test", "pytest"]),
            WorkflowStep("change", ["edit", "mv", "rename"]),
            WorkflowStep("test_after", ["test", "pytest"]),
            WorkflowStep("commit", ["git commit"]),
        ],
    },
    {
        "name": "publish_package",
        "triggers": [r"publish", r"pypi", r"npm publish"],
        "steps": [
            WorkflowStep("bump_version", ["bump", "version"]),
            WorkflowStep("build", ["build", "sdist", "wheel"]),
            WorkflowStep("test", ["test", "twine check"]),
            WorkflowStep("publish", ["twine upload", "npm publish", "publish"]),
            WorkflowStep("tag", ["git tag"]),
        ],
    },
]


def detect_intent(command: str, history: list[str] | None = None) -> DetectedIntent | None:
    """Detect the user's workflow intent from command and history."""
    command_lower = command.lower()

    best_match: DetectedIntent | None = None
    best_confidence = 0.0

    for template in WORKFLOW_TEMPLATES:
        confidence = 0.0

        # Check triggers
        for trigger in template["triggers"]:
            if re.search(trigger, command_lower):
                confidence += 0.4
                break

        # Check if command matches any step
        for step in template["steps"]:
            for pattern in step.command_patterns:
                if pattern in command_lower:
                    confidence += 0.2
                    break

        # Check history for workflow progression
        if history:
            steps_matched = 0
            for hist_cmd in history[-10:]:
                for step in template["steps"]:
                    for pattern in step.command_patterns:
                        if pattern in hist_cmd.lower():
                            steps_matched += 1
                            break
            if steps_matched >= 2:
                confidence += 0.3

        if confidence > best_confidence and confidence >= 0.4:
            best_confidence = confidence
            # Build detected intent with step completion from history
            steps = [WorkflowStep(s.name, s.command_patterns) for s in template["steps"]]
            if history:
                for step in steps:
                    for hist_cmd in history:
                        for pattern in step.command_patterns:
                            if pattern in hist_cmd.lower():
                                step.completed = True
                                break
            best_match = DetectedIntent(
                name=template["name"],
                steps=steps,
                confidence=best_confidence,
            )

    return best_match


def suggest_next_command(intent: DetectedIntent) -> str | None:
    """Given a detected intent, suggest the next command to run."""
    next_step = intent.next_step
    if next_step is None:
        return None
    return next_step.command_patterns[0] if next_step.command_patterns else None
