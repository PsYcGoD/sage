# Real Active Agent Layer Implementation Plan

## Executive Summary

This document provides a detailed implementation plan for transforming SAGE's current synchronous agent system into a **production-grade asynchronous multi-agent orchestration platform** with **Claude-level coding and reasoning capabilities**.

**Current State:**
- Agents are synchronous analysis tools that run post-execution
- No persistent worker processes or task queues
- Limited to pattern-matching heuristics
- No real AI integration for code generation/reasoning

**Target State:**
- Persistent async agent workers with task queues
- Real AI integration (Claude/local LLMs) for coding tasks
- Multi-agent orchestration with planning and decomposition
- Production-ready error handling, monitoring, and scaling

---

## Section 1: Database Schema

### 1.1 Enhanced Agent Runs Table

**New table: `agent_runs`** - tracks actual async agent executions with full lifecycle.

```sql
-- Drop existing limited schema
DROP TABLE IF EXISTS agent_tasks;

-- New comprehensive agent_runs table
CREATE TABLE agent_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL,
    run_id INTEGER,  -- Optional: links to command run if agent was triggered by a run
    parent_agent_run_id INTEGER,  -- For sub-agents spawned by orchestrator
    
    -- Task definition
    task_type TEXT NOT NULL,  -- 'code_generation', 'debug_analysis', 'test_execution', 'security_audit', etc.
    task_description TEXT NOT NULL,
    task_context TEXT,  -- JSON: input files, error messages, requirements
    
    -- Execution state
    state TEXT NOT NULL DEFAULT 'pending',  -- 'pending', 'assigned', 'running', 'completed', 'failed', 'cancelled'
    priority INTEGER DEFAULT 5,  -- 1 (highest) to 10 (lowest)
    
    -- Timing
    created_at TEXT NOT NULL,
    assigned_at TEXT,
    started_at TEXT,
    completed_at TEXT,
    duration_ms INTEGER,
    
    -- Results
    result TEXT,  -- JSON: generated code, analysis, suggestions
    output_files TEXT,  -- JSON: list of file paths created/modified
    exit_code INTEGER DEFAULT 0,
    error_message TEXT,
    
    -- AI metrics
    model_used TEXT,  -- 'claude-sonnet-4', 'codex-gpt-4', 'ollama-qwen2.5-coder', etc.
    tokens_used INTEGER DEFAULT 0,
    api_cost_usd REAL DEFAULT 0.0,
    
    -- Quality tracking
    confidence_score REAL,  -- 0.0-1.0: agent's confidence in result
    human_feedback TEXT,  -- 'approved', 'rejected', 'modified'
    actual_success INTEGER,  -- 0 or 1: did the generated code actually work?
    
    FOREIGN KEY (agent_id) REFERENCES agents(id),
    FOREIGN KEY (run_id) REFERENCES runs(id),
    FOREIGN KEY (parent_agent_run_id) REFERENCES agent_runs(id)
);

CREATE INDEX idx_agent_runs_state ON agent_runs(state);
CREATE INDEX idx_agent_runs_agent_id ON agent_runs(agent_id);
CREATE INDEX idx_agent_runs_run_id ON agent_runs(run_id);
CREATE INDEX idx_agent_runs_created_at ON agent_runs(created_at);
```

### 1.2 Enhanced Agents Table

```sql
-- Modify existing agents table to support persistent workers
ALTER TABLE agents ADD COLUMN worker_status TEXT DEFAULT 'stopped';  
-- 'stopped', 'starting', 'idle', 'busy', 'error', 'shutting_down'

ALTER TABLE agents ADD COLUMN worker_pid INTEGER;
ALTER TABLE agents ADD COLUMN worker_started_at TEXT;
ALTER TABLE agents ADD COLUMN tasks_completed INTEGER DEFAULT 0;
ALTER TABLE agents ADD COLUMN tasks_failed INTEGER DEFAULT 0;
ALTER TABLE agents ADD COLUMN avg_duration_ms INTEGER DEFAULT 0;
ALTER TABLE agents ADD COLUMN model_preference TEXT;  -- JSON: preferred AI models for this agent
ALTER TABLE agents ADD COLUMN resource_limits TEXT;  -- JSON: max_memory_mb, max_duration_ms, etc.
```

### 1.3 Agent Task Queue Table

```sql
-- Persistent task queue for crash recovery
CREATE TABLE agent_task_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_run_id INTEGER NOT NULL,
    queue_name TEXT NOT NULL,  -- 'high_priority', 'default', 'background'
    position INTEGER NOT NULL,
    enqueued_at TEXT NOT NULL,
    dequeued_at TEXT,
    
    FOREIGN KEY (agent_run_id) REFERENCES agent_runs(id),
    UNIQUE(queue_name, position)
);

CREATE INDEX idx_task_queue_queue ON agent_task_queue(queue_name, position);
```

### 1.4 Agent Communication Table

```sql
-- Inter-agent messages for orchestration
CREATE TABLE agent_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_agent_id INTEGER,
    to_agent_id INTEGER NOT NULL,
    message_type TEXT NOT NULL,  -- 'request', 'response', 'broadcast', 'error'
    content TEXT NOT NULL,  -- JSON
    created_at TEXT NOT NULL,
    read_at TEXT,
    
    FOREIGN KEY (from_agent_id) REFERENCES agents(id),
    FOREIGN KEY (to_agent_id) REFERENCES agents(id)
);

CREATE INDEX idx_messages_to_agent ON agent_messages(to_agent_id, read_at);
```

---

## Section 2: Worker Loop Architecture

### 2.1 Async Agent Worker Design

**Pattern: Producer-Consumer with asyncio.Queue**

```python
# src/sage/agents/worker.py

import asyncio
import signal
from datetime import datetime, timezone
from typing import Optional
from contextlib import asynccontextmanager

from .base_agent import BaseAgent, AgentRunRecord
from ..store import connect


class AgentWorker:
    """Persistent async worker for a single agent."""
    
    def __init__(self, agent: BaseAgent, queue_name: str = "default"):
        self.agent = agent
        self.queue_name = queue_name
        self.task_queue: asyncio.Queue[AgentRunRecord] = asyncio.Queue(maxsize=100)
        self.running = False
        self.worker_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
    async def start(self) -> None:
        """Start the worker loop."""
        if self.running:
            return
            
        self.running = True
        await self._update_worker_status("starting")
        
        # Register signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))
        
        # Start worker loop in background
        self.worker_task = asyncio.create_task(self._worker_loop())
        await self._update_worker_status("idle")
        print(f"[SAGE Worker] {self.agent.name} started (queue={self.queue_name})")
        
    async def _worker_loop(self) -> None:
        """Main worker loop - process tasks from queue."""
        while self.running:
            try:
                # Wait for task or shutdown signal
                task = await asyncio.wait_for(
                    self.task_queue.get(), 
                    timeout=1.0
                )
                
                await self._process_task(task)
                self.task_queue.task_done()
                
            except asyncio.TimeoutError:
                # No tasks, check if shutdown requested
                if self._shutdown_event.is_set():
                    break
            except Exception as e:
                print(f"[SAGE Worker] {self.agent.name} error: {e}")
                await self._update_worker_status("error")
                await asyncio.sleep(5)  # Backoff before retry
                await self._update_worker_status("idle")
    
    async def _process_task(self, task: AgentRunRecord) -> None:
        """Execute a single agent task."""
        await self._update_worker_status("busy")
        await self._update_agent_run_state(task.id, "running")
        
        started_at = datetime.now(timezone.utc)
        
        try:
            result = await self.agent.execute_task(task)
            
            # Calculate duration
            completed_at = datetime.now(timezone.utc)
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)
            
            # Save result
            await self._save_agent_run_result(
                task.id, 
                result, 
                state="completed",
                duration_ms=duration_ms,
                completed_at=completed_at.isoformat(timespec="seconds")
            )
            
            # Update agent stats
            await self._increment_agent_stats(success=True, duration_ms=duration_ms)
            
        except Exception as e:
            completed_at = datetime.now(timezone.utc)
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)
            
            await self._save_agent_run_result(
                task.id,
                None,
                state="failed",
                error_message=str(e),
                duration_ms=duration_ms,
                completed_at=completed_at.isoformat(timespec="seconds")
            )
            
            await self._increment_agent_stats(success=False, duration_ms=duration_ms)
            
        finally:
            await self._update_worker_status("idle")
    
    async def enqueue_task(self, task: AgentRunRecord) -> None:
        """Add a task to this worker's queue."""
        await self.task_queue.put(task)
        
        # Persist to DB for crash recovery
        await self._persist_queue_entry(task)
    
    async def shutdown(self) -> None:
        """Graceful shutdown - finish current task, drop pending."""
        print(f"[SAGE Worker] {self.agent.name} shutting down...")
        self._shutdown_event.set()
        self.running = False
        
        if self.worker_task:
            await self.worker_task
        
        await self._update_worker_status("stopped")
        print(f"[SAGE Worker] {self.agent.name} stopped")
    
    async def _update_worker_status(self, status: str) -> None:
        """Update agent worker status in DB."""
        with connect() as conn:
            conn.execute(
                """
                UPDATE agents 
                SET worker_status = ?, last_active = ?
                WHERE id = ?
                """,
                (status, datetime.now(timezone.utc).isoformat(timespec="seconds"), self.agent.db_id)
            )
            conn.commit()
    
    async def _update_agent_run_state(self, agent_run_id: int, state: str) -> None:
        """Update agent_run state."""
        with connect() as conn:
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            
            if state == "running":
                conn.execute(
                    "UPDATE agent_runs SET state = ?, started_at = ? WHERE id = ?",
                    (state, now, agent_run_id)
                )
            else:
                conn.execute(
                    "UPDATE agent_runs SET state = ? WHERE id = ?",
                    (state, agent_run_id)
                )
            conn.commit()
    
    async def _save_agent_run_result(
        self, 
        agent_run_id: int,
        result: Optional[dict],
        state: str,
        duration_ms: int,
        completed_at: str,
        error_message: Optional[str] = None
    ) -> None:
        """Save agent run result to DB."""
        import json
        
        with connect() as conn:
            conn.execute(
                """
                UPDATE agent_runs 
                SET state = ?, result = ?, duration_ms = ?, completed_at = ?, error_message = ?
                WHERE id = ?
                """,
                (
                    state,
                    json.dumps(result) if result else None,
                    duration_ms,
                    completed_at,
                    error_message,
                    agent_run_id
                )
            )
            conn.commit()
    
    async def _increment_agent_stats(self, success: bool, duration_ms: int) -> None:
        """Update agent success rate and avg duration."""
        with connect() as conn:
            if success:
                conn.execute(
                    """
                    UPDATE agents 
                    SET tasks_completed = tasks_completed + 1,
                        avg_duration_ms = (avg_duration_ms * tasks_completed + ?) / (tasks_completed + 1)
                    WHERE id = ?
                    """,
                    (duration_ms, self.agent.db_id)
                )
            else:
                conn.execute(
                    "UPDATE agents SET tasks_failed = tasks_failed + 1 WHERE id = ?",
                    (self.agent.db_id,)
                )
            conn.commit()
    
    async def _persist_queue_entry(self, task: AgentRunRecord) -> None:
        """Persist task to queue table for crash recovery."""
        with connect() as conn:
            # Get current max position
            row = conn.execute(
                "SELECT COALESCE(MAX(position), 0) as max_pos FROM agent_task_queue WHERE queue_name = ?",
                (self.queue_name,)
            ).fetchone()
            next_position = row["max_pos"] + 1
            
            conn.execute(
                """
                INSERT INTO agent_task_queue (agent_run_id, queue_name, position, enqueued_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    task.id,
                    self.queue_name,
                    next_position,
                    datetime.now(timezone.utc).isoformat(timespec="seconds")
                )
            )
            conn.commit()
```

### 2.2 Worker Pool Manager

```python
# src/sage/agents/pool.py

import asyncio
from typing import Dict, List, Optional
from .worker import AgentWorker
from .base_agent import BaseAgent


class WorkerPool:
    """Manages multiple agent workers with load balancing."""
    
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.workers: Dict[str, AgentWorker] = {}
        self.agent_workers: Dict[int, AgentWorker] = {}  # agent_id -> worker
        
    async def start(self) -> None:
        """Start the worker pool."""
        print(f"[SAGE Pool] Starting worker pool (max_workers={self.max_workers})")
    
    async def spawn_worker(self, agent: BaseAgent, queue_name: str = "default") -> AgentWorker:
        """Spawn a new worker for an agent."""
        if agent.db_id in self.agent_workers:
            return self.agent_workers[agent.db_id]
        
        if len(self.workers) >= self.max_workers:
            raise RuntimeError(f"Worker pool at capacity ({self.max_workers})")
        
        worker = AgentWorker(agent, queue_name)
        await worker.start()
        
        worker_key = f"{agent.name}-{agent.db_id}"
        self.workers[worker_key] = worker
        self.agent_workers[agent.db_id] = worker
        
        return worker
    
    async def assign_task(self, agent_id: int, task: 'AgentRunRecord') -> None:
        """Assign a task to a specific agent worker."""
        if agent_id not in self.agent_workers:
            raise ValueError(f"No worker found for agent_id={agent_id}")
        
        worker = self.agent_workers[agent_id]
        await worker.enqueue_task(task)
    
    async def shutdown_all(self) -> None:
        """Shutdown all workers gracefully."""
        print("[SAGE Pool] Shutting down all workers...")
        tasks = [worker.shutdown() for worker in self.workers.values()]
        await asyncio.gather(*tasks, return_exceptions=True)
        self.workers.clear()
        self.agent_workers.clear()
        print("[SAGE Pool] Worker pool stopped")
```

---

## Section 3: Agent Tool Contracts (JSON Schemas)

### 3.1 Base Agent Contract

```python
# src/sage/agents/contracts.py

from typing import TypedDict, Literal, Optional, List
from dataclasses import dataclass


class AgentTaskInput(TypedDict):
    """Standard input format for all agents."""
    task_type: str
    description: str
    context: dict  # Varies by agent type
    priority: int
    deadline_seconds: Optional[int]


class AgentTaskOutput(TypedDict):
    """Standard output format for all agents."""
    status: Literal["success", "partial", "failed"]
    result: dict  # Varies by agent type
    confidence: float  # 0.0-1.0
    metadata: dict  # tokens_used, model, duration_ms, etc.
    next_steps: List[str]
    errors: List[str]


@dataclass
class AgentCapability:
    """Describes what an agent can do."""
    name: str
    input_schema: dict
    output_schema: dict
    cost_estimate: str  # "low", "medium", "high"
    avg_duration_ms: int
```

### 3.2 Code Agent Contract

```python
class CodeAgentInput(TypedDict):
    task_type: Literal["implement", "refactor", "review", "explain"]
    description: str
    context: 'CodeContext'


class CodeContext(TypedDict):
    language: str  # "python", "javascript", "rust", etc.
    files_to_read: List[str]  # Paths to context files
    requirements: str  # Detailed requirements
    constraints: List[str]  # "use asyncio", "no external deps", etc.
    target_file: Optional[str]  # Where to write output
    test_file: Optional[str]  # Associated test file


class CodeAgentOutput(TypedDict):
    status: Literal["success", "partial", "failed"]
    result: 'CodeResult'
    confidence: float
    metadata: dict
    next_steps: List[str]
    errors: List[str]


class CodeResult(TypedDict):
    generated_code: str
    explanation: str
    files_modified: List[str]
    test_suggestions: List[str]
    lint_errors: List[str]
```

### 3.3 Debug Agent Contract

```python
class DebugAgentInput(TypedDict):
    task_type: Literal["analyze_error", "find_root_cause", "suggest_fix"]
    description: str
    context: 'DebugContext'


class DebugContext(TypedDict):
    command: str
    exit_code: int
    stdout: str
    stderr: str
    traceback: Optional[str]
    files_involved: List[str]
    recent_changes: List[str]  # git diff output


class DebugAgentOutput(TypedDict):
    status: Literal["success", "partial", "failed"]
    result: 'DebugResult'
    confidence: float
    metadata: dict
    next_steps: List[str]
    errors: List[str]


class DebugResult(TypedDict):
    root_cause: str
    error_category: str  # "import_error", "syntax_error", "runtime_error", etc.
    fix_suggestions: List['FixSuggestion']
    relevant_lines: List[tuple[str, int]]  # (file_path, line_number)
    similar_errors: List[int]  # run_ids of similar past errors


class FixSuggestion(TypedDict):
    description: str
    confidence: float
    code_patch: Optional[str]  # unified diff format
    commands_to_run: List[str]
    auto_fixable: bool
```

### 3.4 Test Agent Contract

```python
class TestAgentInput(TypedDict):
    task_type: Literal["run_tests", "generate_tests", "improve_coverage"]
    description: str
    context: 'TestContext'


class TestContext(TypedDict):
    test_framework: str  # "pytest", "unittest", "jest", etc.
    target_files: List[str]
    test_pattern: str  # "tests/test_*.py"
    coverage_target: Optional[float]
    max_duration_seconds: int


class TestAgentOutput(TypedDict):
    status: Literal["success", "partial", "failed"]
    result: 'TestResult'
    confidence: float
    metadata: dict
    next_steps: List[str]
    errors: List[str]


class TestResult(TypedDict):
    tests_run: int
    tests_passed: int
    tests_failed: int
    tests_skipped: int
    coverage_percentage: Optional[float]
    failing_tests: List['FailingTest']
    generated_tests: List[str]  # File paths of new tests


class FailingTest(TypedDict):
    test_name: str
    file_path: str
    line_number: int
    error_message: str
    assertion: str
```

### 3.5 Security Agent Contract

```python
class SecurityAgentInput(TypedDict):
    task_type: Literal["audit_code", "check_dependencies", "scan_secrets"]
    description: str
    context: 'SecurityContext'


class SecurityContext(TypedDict):
    files_to_audit: List[str]
    scan_type: str  # "full", "quick", "pre-commit"
    ignore_patterns: List[str]


class SecurityAgentOutput(TypedDict):
    status: Literal["success", "partial", "failed"]
    result: 'SecurityResult'
    confidence: float
    metadata: dict
    next_steps: List[str]
    errors: List[str]


class SecurityResult(TypedDict):
    findings: List['SecurityFinding']
    risk_score: int  # 0-100
    passed: bool


class SecurityFinding(TypedDict):
    severity: Literal["critical", "high", "medium", "low", "info"]
    category: str  # "hardcoded_secret", "sql_injection", "xss", etc.
    file_path: str
    line_number: int
    description: str
    recommendation: str
    cwe_id: Optional[str]
```

### 3.6 Dependency Agent Contract

```python
class DependencyAgentInput(TypedDict):
    task_type: Literal["install", "update", "resolve_conflict", "audit"]
    description: str
    context: 'DependencyContext'


class DependencyContext(TypedDict):
    package_manager: str  # "pip", "npm", "yarn", "cargo", etc.
    manifest_file: str  # "requirements.txt", "package.json", etc.
    packages: List[str]  # Packages to install/update
    constraints: List[str]


class DependencyAgentOutput(TypedDict):
    status: Literal["success", "partial", "failed"]
    result: 'DependencyResult'
    confidence: float
    metadata: dict
    next_steps: List[str]
    errors: List[str]


class DependencyResult(TypedDict):
    installed: List[str]
    updated: List[str]
    failed: List[str]
    conflicts: List['DependencyConflict']
    vulnerabilities: List['VulnerabilityInfo']


class DependencyConflict(TypedDict):
    package_a: str
    package_b: str
    description: str
    resolution: Optional[str]


class VulnerabilityInfo(TypedDict):
    package: str
    version: str
    severity: str
    cve_id: str
    fixed_in: Optional[str]
```

---

## Section 4: Multi-Agent Orchestration

### 4.1 Enhanced Orchestrator with Planning

```python
# src/sage/agents/orchestrator_v2.py

import asyncio
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from .base_agent import BaseAgent
from .pool import WorkerPool
from .contracts import AgentTaskInput, AgentTaskOutput
from .planner import TaskPlanner, ExecutionPlan
from ..store import connect


@dataclass
class OrchestrationResult:
    """Result of multi-agent orchestration."""
    success: bool
    agent_results: List[AgentTaskOutput]
    total_duration_ms: int
    plan: ExecutionPlan


class EnhancedOrchestrator:
    """
    Coordinates multiple agents with:
    - Task decomposition and planning
    - Parallel execution where possible
    - Dependency resolution
    - Error recovery and retry
    """
    
    def __init__(self, max_workers: int = 5):
        self.pool = WorkerPool(max_workers)
        self.planner = TaskPlanner()
        self.agents: Dict[int, BaseAgent] = {}
        
    async def start(self) -> None:
        """Start the orchestrator and worker pool."""
        await self.pool.start()
        print("[SAGE Orchestrator] Started")
    
    async def execute_complex_task(
        self, 
        description: str, 
        context: Dict[str, Any],
        run_id: Optional[int] = None
    ) -> OrchestrationResult:
        """
        Execute a complex task by decomposing into sub-tasks and coordinating agents.
        
        Example:
          description = "Fix all failing tests"
          context = {"run_id": 42, "test_output": "..."}
        
        The orchestrator will:
        1. Analyze the task and create an execution plan
        2. Identify required agents (test, debug, code, etc.)
        3. Execute sub-tasks in optimal order (parallel where possible)
        4. Aggregate results and provide final report
        """
        import time
        start_time = time.time()
        
        # Step 1: Create execution plan
        plan = await self.planner.create_plan(description, context)
        print(f"[SAGE Orchestrator] Plan created: {len(plan.steps)} steps, {len(plan.agents_needed)} agents")
        
        # Step 2: Spawn required agents
        for agent_spec in plan.agents_needed:
            agent = await self._get_or_spawn_agent(agent_spec)
        
        # Step 3: Execute plan steps
        results = []
        for step in plan.steps:
            if step.parallel:
                # Execute parallel steps concurrently
                step_results = await self._execute_parallel_steps(step.sub_tasks)
            else:
                # Execute sequential steps
                step_results = []
                for sub_task in step.sub_tasks:
                    result = await self._execute_single_task(sub_task)
                    step_results.append(result)
                    
                    # Stop if critical step failed
                    if result["status"] == "failed" and step.critical:
                        results.extend(step_results)
                        break
            
            results.extend(step_results)
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        success = all(r["status"] == "success" for r in results)
        
        return OrchestrationResult(
            success=success,
            agent_results=results,
            total_duration_ms=duration_ms,
            plan=plan
        )
    
    async def _execute_single_task(self, task: AgentTaskInput) -> AgentTaskOutput:
        """Execute a single task on the appropriate agent."""
        # Create agent_run record
        agent_run_id = await self._create_agent_run(task)
        
        # Find agent capable of handling this task
        agent = await self._find_agent_for_task(task)
        
        # Assign to worker
        await self.pool.assign_task(agent.db_id, agent_run_id)
        
        # Wait for completion
        result = await self._wait_for_completion(agent_run_id)
        
        return result
    
    async def _execute_parallel_steps(self, tasks: List[AgentTaskInput]) -> List[AgentTaskOutput]:
        """Execute multiple tasks in parallel."""
        task_futures = [self._execute_single_task(task) for task in tasks]
        results = await asyncio.gather(*task_futures, return_exceptions=True)
        
        # Handle exceptions
        final_results = []
        for result in results:
            if isinstance(result, Exception):
                final_results.append({
                    "status": "failed",
                    "result": {},
                    "confidence": 0.0,
                    "metadata": {},
                    "next_steps": [],
                    "errors": [str(result)]
                })
            else:
                final_results.append(result)
        
        return final_results
    
    async def _get_or_spawn_agent(self, agent_spec: dict) -> BaseAgent:
        """Get existing agent or spawn new one."""
        # Implementation depends on agent registry
        pass
    
    async def _find_agent_for_task(self, task: AgentTaskInput) -> BaseAgent:
        """Find the best agent for a task type."""
        # Query agents table for capable agent
        pass
    
    async def _create_agent_run(self, task: AgentTaskInput) -> int:
        """Create agent_run record in DB."""
        import json
        from datetime import datetime, timezone
        
        with connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO agent_runs 
                (agent_id, task_type, task_description, task_context, state, priority, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    0,  # Will be updated when assigned
                    task["task_type"],
                    task["description"],
                    json.dumps(task["context"]),
                    "pending",
                    task.get("priority", 5),
                    datetime.now(timezone.utc).isoformat(timespec="seconds")
                )
            )
            conn.commit()
            return cursor.lastrowid
    
    async def _wait_for_completion(self, agent_run_id: int, timeout_seconds: int = 300) -> AgentTaskOutput:
        """Wait for agent_run to complete."""
        import time
        import json
        
        start = time.time()
        while time.time() - start < timeout_seconds:
            with connect() as conn:
                row = conn.execute(
                    "SELECT state, result, error_message FROM agent_runs WHERE id = ?",
                    (agent_run_id,)
                ).fetchone()
            
            if row["state"] in ["completed", "failed"]:
                result = json.loads(row["result"]) if row["result"] else {}
                return result
            
            await asyncio.sleep(0.5)
        
        raise TimeoutError(f"Agent run {agent_run_id} timed out after {timeout_seconds}s")
    
    async def shutdown(self) -> None:
        """Shutdown orchestrator and all workers."""
        await self.pool.shutdown_all()
        print("[SAGE Orchestrator] Stopped")
```

### 4.2 Task Planner

```python
# src/sage/agents/planner.py

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from .contracts import AgentTaskInput


@dataclass
class PlanStep:
    """A step in an execution plan."""
    step_number: int
    description: str
    sub_tasks: List[AgentTaskInput]
    parallel: bool
    critical: bool  # If this step fails, should we stop?
    depends_on: List[int]  # Step numbers this depends on


@dataclass
class ExecutionPlan:
    """Complete execution plan for a complex task."""
    description: str
    steps: List[PlanStep]
    agents_needed: List[dict]
    estimated_duration_seconds: int
    strategy: str  # "sequential", "parallel", "mixed"


class TaskPlanner:
    """Decomposes complex tasks into executable plans."""
    
    async def create_plan(self, description: str, context: Dict[str, Any]) -> ExecutionPlan:
        """
        Analyze task and create execution plan.
        
        This is where the "intelligence" lives - breaking down complex requests
        into actionable sub-tasks with proper dependencies.
        
        For now, we'll use heuristic pattern matching. Later, this can be
        enhanced with an LLM planner (Claude/GPT-4) for more sophisticated decomposition.
        """
        description_lower = description.lower()
        
        # Pattern: "Fix all failing tests"
        if "fix" in description_lower and "test" in description_lower:
            return self._plan_fix_tests(context)
        
        # Pattern: "Implement feature X"
        elif "implement" in description_lower or "add feature" in description_lower:
            return self._plan_feature_implementation(description, context)
        
        # Pattern: "Debug error in run #X"
        elif "debug" in description_lower or "investigate" in description_lower:
            return self._plan_debug_investigation(context)
        
        # Pattern: "Refactor module X"
        elif "refactor" in description_lower:
            return self._plan_refactor(description, context)
        
        # Default: simple sequential plan
        else:
            return self._plan_generic_task(description, context)
    
    def _plan_fix_tests(self, context: Dict[str, Any]) -> ExecutionPlan:
        """Plan for fixing failing tests."""
        steps = [
            PlanStep(
                step_number=1,
                description="Run tests and identify failures",
                sub_tasks=[{
                    "task_type": "run_tests",
                    "description": "Execute test suite and capture failures",
                    "context": context,
                    "priority": 5
                }],
                parallel=False,
                critical=True,
                depends_on=[]
            ),
            PlanStep(
                step_number=2,
                description="Analyze each failing test",
                sub_tasks=[],  # Will be populated based on step 1 results
                parallel=True,
                critical=False,
                depends_on=[1]
            ),
            PlanStep(
                step_number=3,
                description="Generate fixes for errors",
                sub_tasks=[],
                parallel=True,
                critical=False,
                depends_on=[2]
            ),
            PlanStep(
                step_number=4,
                description="Apply fixes and re-run tests",
                sub_tasks=[],
                parallel=False,
                critical=True,
                depends_on=[3]
            )
        ]
        
        return ExecutionPlan(
            description="Fix all failing tests",
            steps=steps,
            agents_needed=[
                {"type": "test", "name": "Test Agent"},
                {"type": "debug", "name": "Debug Agent"},
                {"type": "code", "name": "Code Agent"}
            ],
            estimated_duration_seconds=120,
            strategy="mixed"
        )
    
    def _plan_feature_implementation(self, description: str, context: Dict[str, Any]) -> ExecutionPlan:
        """Plan for implementing a new feature."""
        steps = [
            PlanStep(
                step_number=1,
                description="Analyze requirements and design approach",
                sub_tasks=[{
                    "task_type": "research",
                    "description": f"Research and design: {description}",
                    "context": context,
                    "priority": 5
                }],
                parallel=False,
                critical=True,
                depends_on=[]
            ),
            PlanStep(
                step_number=2,
                description="Implement core functionality",
                sub_tasks=[{
                    "task_type": "implement",
                    "description": "Write main implementation code",
                    "context": context,
                    "priority": 5
                }],
                parallel=False,
                critical=True,
                depends_on=[1]
            ),
            PlanStep(
                step_number=3,
                description="Generate tests",
                sub_tasks=[{
                    "task_type": "generate_tests",
                    "description": "Create comprehensive test coverage",
                    "context": context,
                    "priority": 6
                }],
                parallel=False,
                critical=False,
                depends_on=[2]
            ),
            PlanStep(
                step_number=4,
                description="Security audit",
                sub_tasks=[{
                    "task_type": "audit_code",
                    "description": "Security review of new code",
                    "context": context,
                    "priority": 7
                }],
                parallel=False,
                critical=False,
                depends_on=[2]
            )
        ]
        
        return ExecutionPlan(
            description=description,
            steps=steps,
            agents_needed=[
                {"type": "research", "name": "Research Agent"},
                {"type": "code", "name": "Code Agent"},
                {"type": "test", "name": "Test Agent"},
                {"type": "security", "name": "Security Agent"}
            ],
            estimated_duration_seconds=300,
            strategy="sequential"
        )
    
    def _plan_debug_investigation(self, context: Dict[str, Any]) -> ExecutionPlan:
        """Plan for debugging an error."""
        steps = [
            PlanStep(
                step_number=1,
                description="Analyze error and identify root cause",
                sub_tasks=[{
                    "task_type": "analyze_error",
                    "description": "Root cause analysis",
                    "context": context,
                    "priority": 3
                }],
                parallel=False,
                critical=True,
                depends_on=[]
            ),
            PlanStep(
                step_number=2,
                description="Generate fix suggestions",
                sub_tasks=[{
                    "task_type": "suggest_fix",
                    "description": "Propose solutions",
                    "context": context,
                    "priority": 4
                }],
                parallel=False,
                critical=True,
                depends_on=[1]
            )
        ]
        
        return ExecutionPlan(
            description="Debug investigation",
            steps=steps,
            agents_needed=[
                {"type": "debug", "name": "Debug Agent"}
            ],
            estimated_duration_seconds=30,
            strategy="sequential"
        )
    
    def _plan_refactor(self, description: str, context: Dict[str, Any]) -> ExecutionPlan:
        """Plan for code refactoring."""
        steps = [
            PlanStep(
                step_number=1,
                description="Analyze current code structure",
                sub_tasks=[{
                    "task_type": "review",
                    "description": "Code analysis",
                    "context": context,
                    "priority": 5
                }],
                parallel=False,
                critical=True,
                depends_on=[]
            ),
            PlanStep(
                step_number=2,
                description="Refactor code",
                sub_tasks=[{
                    "task_type": "refactor",
                    "description": description,
                    "context": context,
                    "priority": 5
                }],
                parallel=False,
                critical=True,
                depends_on=[1]
            ),
            PlanStep(
                step_number=3,
                description="Verify tests still pass",
                sub_tasks=[{
                    "task_type": "run_tests",
                    "description": "Regression testing",
                    "context": context,
                    "priority": 4
                }],
                parallel=False,
                critical=True,
                depends_on=[2]
            )
        ]
        
        return ExecutionPlan(
            description=description,
            steps=steps,
            agents_needed=[
                {"type": "code", "name": "Code Agent"},
                {"type": "test", "name": "Test Agent"}
            ],
            estimated_duration_seconds=180,
            strategy="sequential"
        )
    
    def _plan_generic_task(self, description: str, context: Dict[str, Any]) -> ExecutionPlan:
        """Generic single-agent task plan."""
        steps = [
            PlanStep(
                step_number=1,
                description=description,
                sub_tasks=[{
                    "task_type": "generic",
                    "description": description,
                    "context": context,
                    "priority": 5
                }],
                parallel=False,
                critical=True,
                depends_on=[]
            )
        ]
        
        return ExecutionPlan(
            description=description,
            steps=steps,
            agents_needed=[{"type": "code", "name": "Code Agent"}],
            estimated_duration_seconds=60,
            strategy="sequential"
        )
```

---

## Section 5: Making Agents Claude-Level Effective

### 5.1 AI Integration Architecture

```python
# src/sage/agents/ai_backend.py

from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod


class AIBackend(ABC):
    """Abstract base for AI model backends."""
    
    @abstractmethod
    async def generate_code(
        self, 
        prompt: str, 
        context_files: List[str],
        language: str
    ) -> Dict[str, Any]:
        """Generate code based on prompt."""
        pass
    
    @abstractmethod
    async def analyze_error(
        self,
        error_message: str,
        traceback: str,
        context_files: List[str]
    ) -> Dict[str, Any]:
        """Analyze error and suggest fixes."""
        pass
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str
    ) -> str:
        """General chat completion."""
        pass


class ClaudeBackend(AIBackend):
    """Claude API integration."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
    
    async def generate_code(
        self, 
        prompt: str, 
        context_files: List[str],
        language: str
    ) -> Dict[str, Any]:
        """Generate code using Claude."""
        
        # Read context files
        context_content = []
        for file_path in context_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    context_content.append(f"File: {file_path}\n```{language}\n{content}\n```")
            except Exception as e:
                context_content.append(f"Error reading {file_path}: {e}")
        
        # Build prompt
        full_prompt = f"""You are a senior software engineer. Generate production-ready code based on the following requirements.

Context files:
{chr(10).join(context_content)}

Requirements:
{prompt}

Provide:
1. Complete, working code (no placeholders)
2. Brief explanation of approach
3. Any dependencies needed
4. Test suggestions

Format your response as:
```{language}
[code here]
```

Explanation:
[explanation here]
"""
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            messages=[{"role": "user", "content": full_prompt}]
        )
        
        # Parse response
        content = response.content[0].text
        
        # Extract code from markdown
        import re
        code_match = re.search(rf"```{language}(.*?)```", content, re.DOTALL)
        code = code_match.group(1).strip() if code_match else content
        
        return {
            "code": code,
            "explanation": content,
            "model": self.model,
            "tokens_used": response.usage.input_tokens + response.usage.output_tokens
        }
    
    async def analyze_error(
        self,
        error_message: str,
        traceback: str,
        context_files: List[str]
    ) -> Dict[str, Any]:
        """Analyze error using Claude."""
        
        # Read context files
        context_content = []
        for file_path in context_files[:3]:  # Limit to 3 files
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    context_content.append(f"File: {file_path}\n```python\n{content}\n```")
            except:
                pass
        
        prompt = f"""Analyze this error and provide a fix.

Error:
{error_message}

Traceback:
{traceback}

Context files:
{chr(10).join(context_content)}

Provide:
1. Root cause analysis
2. Step-by-step fix
3. Code patches if applicable
4. Prevention tips
"""
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        content = response.content[0].text
        
        return {
            "analysis": content,
            "model": self.model,
            "tokens_used": response.usage.input_tokens + response.usage.output_tokens
        }
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str
    ) -> str:
        """General chat with Claude."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            system=system_prompt,
            messages=messages
        )
        
        return response.content[0].text


class LocalLLMBackend(AIBackend):
    """Local LLM integration (Ollama, vLLM, etc.)."""
    
    def __init__(self, model: str = "qwen2.5-coder:7b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
    
    async def generate_code(
        self, 
        prompt: str, 
        context_files: List[str],
        language: str
    ) -> Dict[str, Any]:
        """Generate code using local LLM."""
        import aiohttp
        
        # Similar to Claude but calling Ollama API
        context_content = []
        for file_path in context_files[:2]:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    context_content.append(f"{file_path}:\n{content[:1000]}")  # Truncate for context length
            except:
                pass
        
        full_prompt = f"""Generate {language} code for: {prompt}\n\nContext:\n{chr(10).join(context_content)}"""
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": False
                }
            ) as response:
                result = await response.json()
                code = result.get("response", "")
        
        return {
            "code": code,
            "explanation": "Generated by local LLM",
            "model": self.model,
            "tokens_used": 0  # Local models don't report tokens
        }
    
    async def analyze_error(
        self,
        error_message: str,
        traceback: str,
        context_files: List[str]
    ) -> Dict[str, Any]:
        """Analyze error using local LLM."""
        import aiohttp
        
        prompt = f"""Analyze this error:\n{error_message}\n\nTraceback:\n{traceback}\n\nProvide root cause and fix."""
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                }
            ) as response:
                result = await response.json()
                analysis = result.get("response", "")
        
        return {
            "analysis": analysis,
            "model": self.model,
            "tokens_used": 0
        }
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str
    ) -> str:
        """Chat with local LLM."""
        import aiohttp
        
        # Convert messages to single prompt
        prompt = f"{system_prompt}\n\n"
        for msg in messages:
            prompt += f"{msg['role']}: {msg['content']}\n"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                }
            ) as response:
                result = await response.json()
                return result.get("response", "")
```

### 5.2 Enhanced Code Agent with Real AI

```python
# src/sage/agents/specialized/code_agent_v2.py

from typing import Any, Dict
import os

from ..base_agent import BaseAgent, AgentRunRecord
from ..ai_backend import AIBackend, ClaudeBackend, LocalLLMBackend
from ..contracts import CodeAgentInput, CodeAgentOutput


class AICodeAgent(BaseAgent):
    """Code agent with real AI integration."""
    
    def __init__(self, name: str, ai_backend: AIBackend = None):
        super().__init__(
            name=name,
            agent_type="code",
            capabilities=["implement", "refactor", "optimize", "review", "explain"],
        )
        
        # Use Claude if API key available, otherwise local LLM
        if ai_backend:
            self.ai = ai_backend
        elif os.environ.get("ANTHROPIC_API_KEY"):
            self.ai = ClaudeBackend()
        else:
            self.ai = LocalLLMBackend()
    
    async def execute_task(self, task: AgentRunRecord) -> CodeAgentOutput:
        """Execute a code implementation task using AI."""
        import json
        
        context: CodeAgentInput = json.loads(task.task_context)
        
        if context["task_type"] == "implement":
            return await self._implement(context)
        elif context["task_type"] == "refactor":
            return await self._refactor(context)
        elif context["task_type"] == "review":
            return await self._review(context)
        elif context["task_type"] == "explain":
            return await self._explain(context)
        else:
            raise ValueError(f"Unknown task type: {context['task_type']}")
    
    async def _implement(self, context: CodeAgentInput) -> CodeAgentOutput:
        """Implement new code using AI."""
        code_context = context["context"]
        
        # Generate code using AI
        result = await self.ai.generate_code(
            prompt=context["description"],
            context_files=code_context.get("files_to_read", []),
            language=code_context.get("language", "python")
        )
        
        generated_code = result["code"]
        
        # Write to target file if specified
        files_modified = []
        if code_context.get("target_file"):
            target = code_context["target_file"]
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'w', encoding='utf-8') as f:
                f.write(generated_code)
            files_modified.append(target)
        
        # Run basic validation
        lint_errors = await self._lint_code(generated_code, code_context["language"])
        
        confidence = 0.9 if len(lint_errors) == 0 else 0.7
        
        return {
            "status": "success" if len(lint_errors) == 0 else "partial",
            "result": {
                "generated_code": generated_code,
                "explanation": result.get("explanation", ""),
                "files_modified": files_modified,
                "test_suggestions": [
                    f"Test {context['description']} with valid inputs",
                    f"Test edge cases",
                    f"Test error handling"
                ],
                "lint_errors": lint_errors
            },
            "confidence": confidence,
            "metadata": {
                "model": result.get("model", "unknown"),
                "tokens_used": result.get("tokens_used", 0),
                "language": code_context["language"]
            },
            "next_steps": [
                "Review generated code for correctness",
                "Run tests to verify functionality",
                "Commit changes if tests pass"
            ],
            "errors": lint_errors
        }
    
    async def _refactor(self, context: CodeAgentInput) -> CodeAgentOutput:
        """Refactor existing code."""
        # Similar to implement but read existing code first
        pass
    
    async def _review(self, context: CodeAgentInput) -> CodeAgentOutput:
        """Review code for quality, bugs, and improvements."""
        pass
    
    async def _explain(self, context: CodeAgentInput) -> CodeAgentOutput:
        """Explain existing code."""
        pass
    
    async def _lint_code(self, code: str, language: str) -> list[str]:
        """Run linter on generated code."""
        errors = []
        
        if language == "python":
            # Quick syntax check
            try:
                compile(code, "<string>", "exec")
            except SyntaxError as e:
                errors.append(f"Syntax error at line {e.lineno}: {e.msg}")
        
        return errors
```

---

## Section 6: Dependencies and Installation

### 6.1 Updated pyproject.toml

```toml
[project]
name = "sage"
version = "0.2.0"
description = "Smart Agent Guidance Engine with Multi-Agent Orchestration"
requires-python = ">=3.10"
dependencies = [
  # Existing
  "joblib>=1.3",
  "pandas>=2.0",
  "pywinpty>=2.0; platform_system == 'Windows'",
  "scikit-learn>=1.3",
  "tiktoken>=0.7",
  
  # New for agents
  "anthropic>=0.30.0",  # Claude API
  "aiohttp>=3.9.0",  # Async HTTP
  "aiosqlite>=0.19.0",  # Async SQLite
  "redis>=5.0.0; extra == 'redis'",  # Optional: Redis queue backend
]

[project.optional-dependencies]
dev = [
  "pytest>=7.0",
  "pytest-asyncio>=0.21.0",
  "black>=23.0",
  "mypy>=1.0",
]
redis = [
  "redis>=5.0.0",
  "rq>=1.15.0",
]
```

### 6.2 Installation Steps

```bash
# Core installation
sage run -- pip install -e .

# With Redis (for production scale)
sage run -- pip install -e ".[redis]"

# Development
sage run -- pip install -e ".[dev]"
```

---

## Section 7: Step-by-Step Implementation Guide

### Phase 1: Database Migration (Week 1)

**Day 1-2: Schema Updates**

```bash
# 1. Create migration script
sage run -- python scripts/migrate_agent_schema.py

# 2. Backup existing DB
cp ~/.sage/sage.db ~/.sage/sage.db.backup

# 3. Run migration
sage run -- python src/sage/migrations/001_agent_runs.py
```

**Implementation:**

```python
# src/sage/migrations/001_agent_runs.py

def migrate():
    """Migrate to new agent schema."""
    from sage.store import connect
    
    with connect() as conn:
        # Create agent_runs table
        conn.execute("""
            CREATE TABLE agent_runs (
                -- [schema from Section 1.1]
            )
        """)
        
        # Migrate existing agent_tasks
        conn.execute("""
            INSERT INTO agent_runs (agent_id, run_id, task_description, state, result, created_at)
            SELECT agent_id, run_id, task_description, 
                   CASE WHEN status = 'completed' THEN 'completed' 
                        WHEN status = 'error' THEN 'failed' 
                        ELSE 'pending' END,
                   result, started_at
            FROM agent_tasks
        """)
        
        # Alter agents table
        conn.execute("ALTER TABLE agents ADD COLUMN worker_status TEXT DEFAULT 'stopped'")
        # ... more ALTER statements
        
        conn.commit()

if __name__ == "__main__":
    migrate()
    print("Migration complete")
```

**Day 3: Testing**

```bash
# Verify schema
sage run -- python -c "from sage.store import connect; conn = connect(); print(conn.execute('SELECT * FROM agent_runs LIMIT 1').fetchone())"
```

### Phase 2: Worker Infrastructure (Week 2)

**Day 1-2: Base Worker Implementation**

```bash
# 1. Create worker module
touch src/sage/agents/worker.py
touch src/sage/agents/pool.py

# 2. Implement worker loop (from Section 2.1)
# Copy code to worker.py

# 3. Add tests
sage run -- pytest tests/test_agent_worker.py -v
```

**Day 3-4: Worker Pool**

```bash
# Implement pool manager
# Test spawning multiple workers
sage run -- python examples/test_worker_pool.py
```

**Day 5: Integration**

```bash
# Wire up to CLI
sage agents start  # Should spawn worker pool

# Test task assignment
sage agents assign code "Implement hello world"
```

### Phase 3: AI Integration (Week 3)

**Day 1-2: Claude Backend**

```bash
# Set up API key
export ANTHROPIC_API_KEY=sk-...

# Test Claude integration
sage run -- python tests/test_claude_backend.py

# Generate first AI code
sage agents run code "Implement fibonacci function"
```

**Day 3: Local LLM Fallback**

```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull coding model
ollama pull qwen2.5-coder:7b

# Test local backend
sage agents run code "Implement binary search" --backend local
```

**Day 4-5: Enhanced Code Agent**

```bash
# Implement AICodeAgent (Section 5.2)
# Test end-to-end code generation
sage run -- python examples/test_ai_code_agent.py
```

### Phase 4: Orchestration (Week 4)

**Day 1-2: Task Planner**

```bash
# Implement planner (Section 4.2)
# Test plan generation
sage plan "Fix all failing tests"
```

**Day 3-4: Orchestrator**

```bash
# Implement orchestrator (Section 4.1)
# Test multi-agent coordination
sage orchestrate "Implement user authentication feature"
```

**Day 5: End-to-End Testing**

```bash
# Complex task test
sage orchestrate "Add REST API endpoint for user management with tests and docs"

# Verify all agents worked together
sage agents history
```

### Phase 5: Contracts & Specialized Agents (Week 5-6)

**Week 5: Implement remaining agents**

```bash
# Debug Agent
touch src/sage/agents/specialized/debug_agent_v2.py

# Test Agent  
touch src/sage/agents/specialized/test_agent_v2.py

# Security Agent
touch src/sage/agents/specialized/security_agent.py

# Each with real AI integration
```

**Week 6: Polish & Integration**

```bash
# Add all agent types to orchestrator
# Test complex multi-agent workflows
# Performance tuning
```

---

## Section 8: Success Metrics

### Agent Performance Targets

1. **Code Generation Quality**
   - Generated code compiles: >95%
   - Tests pass after generation: >80%
   - Human approval rate: >70%

2. **Debug Effectiveness**
   - Root cause identified: >85%
   - Fix suggestion accuracy: >75%
   - Auto-fix success rate: >60%

3. **Orchestration Efficiency**
   - Task decomposition accuracy: >80%
   - Parallel execution speedup: 2-5x
   - Overall task success rate: >75%

4. **System Performance**
   - Agent response time: <30s (simple tasks)
   - Worker pool utilization: 60-80%
   - Zero message loss (persistent queues)

### Monitoring Queries

```sql
-- Agent success rate
SELECT 
    a.name,
    COUNT(*) as total_runs,
    SUM(CASE WHEN ar.state = 'completed' THEN 1 ELSE 0 END) as successes,
    ROUND(100.0 * SUM(CASE WHEN ar.state = 'completed' THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate
FROM agent_runs ar
JOIN agents a ON ar.agent_id = a.id
WHERE ar.created_at > datetime('now', '-7 days')
GROUP BY a.name;

-- Average agent run duration
SELECT 
    task_type,
    COUNT(*) as runs,
    ROUND(AVG(duration_ms), 0) as avg_duration_ms,
    ROUND(AVG(tokens_used), 0) as avg_tokens
FROM agent_runs
WHERE state = 'completed'
GROUP BY task_type;

-- Worker pool status
SELECT 
    name,
    worker_status,
    tasks_completed,
    tasks_failed,
    ROUND(100.0 * tasks_completed / NULLIF(tasks_completed + tasks_failed, 0), 2) as success_rate
FROM agents
WHERE worker_status != 'stopped';
```

---

## Conclusion

This plan transforms SAGE from a **synchronous analysis tool** into a **production-grade multi-agent orchestration platform** with:

✅ Persistent async workers with real task queues  
✅ Full database schema for agent lifecycle tracking  
✅ Real AI integration (Claude + local LLMs)  
✅ Multi-agent orchestration with planning  
✅ Claude-level coding capabilities  
✅ Production monitoring and scaling

**Total implementation time: 6-8 weeks** with one developer.

**Next steps:**
1. Review and approve this plan
2. Set up development environment
3. Begin Phase 1 (database migration)
4. Iterate based on real-world testing

Sensei, this gives you a **complete roadmap** to turn SAGE agents into a real, production-ready multi-agent system that rivals Claude's capabilities. The architecture is designed to scale from local development (single worker, local LLM) to production (worker pool, Claude API, Redis queues).
