"""Tool orchestrator for SAGE codegen - plan and execute tool sequences."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable


class ToolType(Enum):
    """Types of tools available."""

    READ = "read"
    WRITE = "write"
    SEARCH = "search"
    EXECUTE = "execute"
    VALIDATE = "validate"
    ANALYZE = "analyze"


@dataclass
class ToolCall:
    """A planned tool call."""

    tool: str
    args: dict[str, Any]
    tool_type: ToolType
    priority: int = 0  # Higher = more urgent
    depends_on: list[str] = field(default_factory=list)  # IDs of dependent calls
    id: str = ""

    def __post_init__(self):
        if not self.id:
            import uuid
            self.id = str(uuid.uuid4())[:8]


@dataclass
class ToolPlan:
    """A plan of tool calls to execute."""

    calls: list[ToolCall]
    parallelizable: list[list[str]]  # Groups of IDs that can run in parallel
    estimated_tokens: int = 0

    def get_call(self, call_id: str) -> ToolCall | None:
        for call in self.calls:
            if call.id == call_id:
                return call
        return None


@dataclass
class ToolResult:
    """Result of a tool execution."""

    call_id: str
    success: bool
    result: Any
    error: str | None = None
    tokens_used: int = 0


class ToolOrchestrator:
    """Plan and coordinate tool execution."""

    def __init__(self, root: Path):
        self.root = root
        self._handlers: dict[str, Callable] = {}

    def register_handler(self, tool_name: str, handler: Callable) -> None:
        """Register a handler for a tool."""
        self._handlers[tool_name] = handler

    def plan_task(self, task: str, context: dict[str, Any] | None = None) -> ToolPlan:
        """Plan tool calls for a task."""
        calls: list[ToolCall] = []
        task_lower = task.lower()

        # Analyze task to determine needed tools
        if any(w in task_lower for w in ["read", "show", "display", "view", "see"]):
            calls.extend(self._plan_read_task(task, context))

        elif any(w in task_lower for w in ["find", "search", "locate", "where"]):
            calls.extend(self._plan_search_task(task, context))

        elif any(w in task_lower for w in ["write", "create", "add", "implement"]):
            calls.extend(self._plan_write_task(task, context))

        elif any(w in task_lower for w in ["fix", "repair", "correct", "debug"]):
            calls.extend(self._plan_fix_task(task, context))

        elif any(w in task_lower for w in ["refactor", "improve", "optimize"]):
            calls.extend(self._plan_refactor_task(task, context))

        elif any(w in task_lower for w in ["test", "verify", "check"]):
            calls.extend(self._plan_test_task(task, context))

        else:
            # Generic task: analyze first
            calls.append(
                ToolCall(
                    tool="analyze",
                    args={"task": task},
                    tool_type=ToolType.ANALYZE,
                )
            )

        # Build parallel groups
        parallelizable = self._find_parallel_groups(calls)

        return ToolPlan(
            calls=calls,
            parallelizable=parallelizable,
            estimated_tokens=self._estimate_tokens(calls),
        )

    def _plan_read_task(
        self, task: str, context: dict[str, Any] | None
    ) -> list[ToolCall]:
        """Plan tools for a read task."""
        calls: list[ToolCall] = []

        # Extract file path from task if present
        file_path = self._extract_file_path(task)

        if file_path:
            calls.append(
                ToolCall(
                    tool="read_file",
                    args={"path": file_path},
                    tool_type=ToolType.READ,
                    priority=10,
                )
            )
        else:
            # Need to search first
            calls.append(
                ToolCall(
                    tool="glob",
                    args={"pattern": "**/*.py"},
                    tool_type=ToolType.SEARCH,
                    priority=10,
                    id="search_files",
                )
            )
            calls.append(
                ToolCall(
                    tool="read_file",
                    args={"path": "{{search_files.result[0]}}"},
                    tool_type=ToolType.READ,
                    priority=5,
                    depends_on=["search_files"],
                )
            )

        return calls

    def _plan_search_task(
        self, task: str, context: dict[str, Any] | None
    ) -> list[ToolCall]:
        """Plan tools for a search task."""
        calls: list[ToolCall] = []

        # Extract search term
        search_term = self._extract_search_term(task)

        if search_term:
            # Parallel search: grep content and glob files
            calls.append(
                ToolCall(
                    tool="grep",
                    args={"pattern": search_term, "path": str(self.root)},
                    tool_type=ToolType.SEARCH,
                    priority=10,
                    id="grep_search",
                )
            )
            calls.append(
                ToolCall(
                    tool="glob",
                    args={"pattern": f"**/*{search_term}*"},
                    tool_type=ToolType.SEARCH,
                    priority=10,
                    id="glob_search",
                )
            )

        return calls

    def _plan_write_task(
        self, task: str, context: dict[str, Any] | None
    ) -> list[ToolCall]:
        """Plan tools for a write task."""
        calls: list[ToolCall] = []

        # First read related files for context
        calls.append(
            ToolCall(
                tool="analyze_context",
                args={"task": task},
                tool_type=ToolType.ANALYZE,
                priority=10,
                id="analyze",
            )
        )

        # Then generate code
        calls.append(
            ToolCall(
                tool="generate_code",
                args={"task": task},
                tool_type=ToolType.ANALYZE,
                priority=5,
                depends_on=["analyze"],
                id="generate",
            )
        )

        # Validate generated code
        calls.append(
            ToolCall(
                tool="validate",
                args={"code": "{{generate.result}}"},
                tool_type=ToolType.VALIDATE,
                priority=4,
                depends_on=["generate"],
                id="validate",
            )
        )

        # Write if validation passes
        calls.append(
            ToolCall(
                tool="write_file",
                args={"content": "{{generate.result}}"},
                tool_type=ToolType.WRITE,
                priority=3,
                depends_on=["validate"],
            )
        )

        return calls

    def _plan_fix_task(
        self, task: str, context: dict[str, Any] | None
    ) -> list[ToolCall]:
        """Plan tools for a fix task."""
        calls: list[ToolCall] = []

        file_path = self._extract_file_path(task)

        if file_path:
            # Read the file first
            calls.append(
                ToolCall(
                    tool="read_file",
                    args={"path": file_path},
                    tool_type=ToolType.READ,
                    priority=10,
                    id="read",
                )
            )

            # Analyze for issues
            calls.append(
                ToolCall(
                    tool="validate",
                    args={"path": file_path},
                    tool_type=ToolType.VALIDATE,
                    priority=9,
                    depends_on=["read"],
                    id="validate",
                )
            )

            # Generate fix
            calls.append(
                ToolCall(
                    tool="generate_fix",
                    args={"path": file_path, "issues": "{{validate.result}}"},
                    tool_type=ToolType.ANALYZE,
                    priority=5,
                    depends_on=["validate"],
                    id="fix",
                )
            )

            # Apply fix
            calls.append(
                ToolCall(
                    tool="write_file",
                    args={"path": file_path, "content": "{{fix.result}}"},
                    tool_type=ToolType.WRITE,
                    priority=3,
                    depends_on=["fix"],
                )
            )

        return calls

    def _plan_refactor_task(
        self, task: str, context: dict[str, Any] | None
    ) -> list[ToolCall]:
        """Plan tools for a refactor task."""
        calls: list[ToolCall] = []

        file_path = self._extract_file_path(task)

        if file_path:
            # Read and analyze
            calls.append(
                ToolCall(
                    tool="read_file",
                    args={"path": file_path, "strategy": "smart"},
                    tool_type=ToolType.READ,
                    priority=10,
                    id="read",
                )
            )

            # Detect patterns
            calls.append(
                ToolCall(
                    tool="detect_patterns",
                    args={"path": file_path},
                    tool_type=ToolType.ANALYZE,
                    priority=9,
                    depends_on=["read"],
                    id="patterns",
                )
            )

            # Generate refactored code
            calls.append(
                ToolCall(
                    tool="refactor",
                    args={"path": file_path, "patterns": "{{patterns.result}}"},
                    tool_type=ToolType.ANALYZE,
                    priority=5,
                    depends_on=["patterns"],
                    id="refactor",
                )
            )

            # Validate
            calls.append(
                ToolCall(
                    tool="validate",
                    args={"code": "{{refactor.result}}"},
                    tool_type=ToolType.VALIDATE,
                    priority=4,
                    depends_on=["refactor"],
                    id="validate",
                )
            )

            # Write
            calls.append(
                ToolCall(
                    tool="write_file",
                    args={"path": file_path, "content": "{{refactor.result}}"},
                    tool_type=ToolType.WRITE,
                    priority=3,
                    depends_on=["validate"],
                )
            )

        return calls

    def _plan_test_task(
        self, task: str, context: dict[str, Any] | None
    ) -> list[ToolCall]:
        """Plan tools for a test task."""
        calls: list[ToolCall] = []

        file_path = self._extract_file_path(task)

        if file_path:
            # Validate first
            calls.append(
                ToolCall(
                    tool="validate",
                    args={"path": file_path},
                    tool_type=ToolType.VALIDATE,
                    priority=10,
                    id="validate",
                )
            )

            # Run tests
            calls.append(
                ToolCall(
                    tool="execute",
                    args={"command": f"python -m pytest {file_path} -v"},
                    tool_type=ToolType.EXECUTE,
                    priority=5,
                    depends_on=["validate"],
                )
            )
        else:
            # Run all tests
            calls.append(
                ToolCall(
                    tool="execute",
                    args={"command": "python -m pytest -v"},
                    tool_type=ToolType.EXECUTE,
                    priority=10,
                )
            )

        return calls

    def _find_parallel_groups(self, calls: list[ToolCall]) -> list[list[str]]:
        """Find groups of calls that can run in parallel."""
        groups: list[list[str]] = []
        remaining = {call.id for call in calls}
        completed: set[str] = set()

        while remaining:
            # Find all calls whose dependencies are satisfied
            parallel = [
                call.id
                for call in calls
                if call.id in remaining
                and all(dep in completed for dep in call.depends_on)
            ]

            if not parallel:
                break

            groups.append(parallel)
            completed.update(parallel)
            remaining -= set(parallel)

        return groups

    def _estimate_tokens(self, calls: list[ToolCall]) -> int:
        """Estimate tokens for a set of calls."""
        estimates = {
            ToolType.READ: 500,
            ToolType.WRITE: 200,
            ToolType.SEARCH: 300,
            ToolType.EXECUTE: 400,
            ToolType.VALIDATE: 100,
            ToolType.ANALYZE: 800,
        }
        return sum(estimates.get(call.tool_type, 200) for call in calls)

    def _extract_file_path(self, task: str) -> str | None:
        """Extract file path from task description."""
        import re

        # Look for path-like patterns
        patterns = [
            r"['\"]([^'\"]+\.py)['\"]",  # Quoted paths
            r"(\S+\.py)\b",  # Unquoted .py files
            r"(\S+/\S+)",  # Path with slash
            r"(\S+\\\S+)",  # Path with backslash
        ]

        for pattern in patterns:
            match = re.search(pattern, task)
            if match:
                return match.group(1)

        return None

    def _extract_search_term(self, task: str) -> str | None:
        """Extract search term from task description."""
        import re

        # Look for quoted strings
        match = re.search(r"['\"]([^'\"]+)['\"]", task)
        if match:
            return match.group(1)

        # Look for words after "find", "search", "locate"
        match = re.search(r"\b(?:find|search|locate)\s+(\w+)", task, re.IGNORECASE)
        if match:
            return match.group(1)

        return None

    async def execute_plan(
        self, plan: ToolPlan, handlers: dict[str, Callable] | None = None
    ) -> list[ToolResult]:
        """Execute a tool plan."""
        if handlers:
            self._handlers.update(handlers)

        results: list[ToolResult] = []
        completed_results: dict[str, Any] = {}

        for group in plan.parallelizable:
            # Execute group in parallel (or sequentially if no async)
            group_results = []
            for call_id in group:
                call = plan.get_call(call_id)
                if not call:
                    continue

                # Resolve dependencies
                args = self._resolve_args(call.args, completed_results)

                # Execute
                handler = self._handlers.get(call.tool)
                if handler:
                    try:
                        result = handler(**args)
                        group_results.append(
                            ToolResult(call_id=call_id, success=True, result=result)
                        )
                        completed_results[call_id] = result
                    except Exception as e:
                        group_results.append(
                            ToolResult(
                                call_id=call_id,
                                success=False,
                                result=None,
                                error=str(e),
                            )
                        )
                else:
                    group_results.append(
                        ToolResult(
                            call_id=call_id,
                            success=False,
                            result=None,
                            error=f"No handler for tool: {call.tool}",
                        )
                    )

            results.extend(group_results)

        return results

    def _resolve_args(
        self, args: dict[str, Any], completed: dict[str, Any]
    ) -> dict[str, Any]:
        """Resolve template references in arguments."""
        import re

        resolved: dict[str, Any] = {}

        for key, value in args.items():
            if isinstance(value, str) and "{{" in value:
                # Resolve template
                for match in re.finditer(r"\{\{(\w+)\.(\w+)(?:\[(\d+)\])?\}\}", value):
                    call_id = match.group(1)
                    attr = match.group(2)
                    index = match.group(3)

                    if call_id in completed:
                        result = completed[call_id]
                        if hasattr(result, attr):
                            result = getattr(result, attr)
                        elif isinstance(result, dict) and attr in result:
                            result = result[attr]

                        if index is not None and isinstance(result, list):
                            result = result[int(index)]

                        value = value.replace(match.group(0), str(result))

            resolved[key] = value

        return resolved
