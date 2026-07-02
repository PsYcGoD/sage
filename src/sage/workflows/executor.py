"""Workflow execution engine."""

from __future__ import annotations

import asyncio
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..store import connect
from .conditions import evaluate_condition
from .parser import Workflow, WorkflowStep


class WorkflowExecutor:
    """Execute workflow pipelines."""

    def __init__(self):
        self.run_id: Optional[int] = None

    async def execute(self, workflow: Workflow) -> bool:
        """Execute a complete workflow."""
        # Record workflow start
        self.run_id = self._save_workflow_start(workflow)
        
        print(f"[SAGE] Starting workflow: {workflow.name}")
        
        # Set environment variables
        env = os.environ.copy()
        env.update(workflow.env)
        
        # Execute pipeline steps
        steps_completed = 0
        for step in workflow.pipeline:
            print(f"[SAGE] Step: {step.name}")
            
            success = await self._execute_step(step, env, workflow.variables)
            
            if success:
                steps_completed += 1
                # Handle on_success
                if step.on_success:
                    await self._handle_actions(step.on_success, env)
            else:
                # Handle on_fail
                if step.on_fail:
                    await self._handle_actions(step.on_fail, env)
                
                if not step.continue_on_fail:
                    print(f"[SAGE] Workflow failed at step: {step.name}")
                    self._save_workflow_end(success=False, steps_completed=steps_completed)
                    return False
        
        print(f"[SAGE] Workflow completed successfully")
        self._save_workflow_end(success=True, steps_completed=steps_completed)
        return True

    async def _execute_step(
        self,
        step: WorkflowStep,
        env: dict,
        variables: dict,
    ) -> bool:
        """Execute a single workflow step."""
        # Substitute variables in command
        command = step.run
        for key, value in variables.items():
            command = command.replace(f"${{{key}}}", str(value))
        
        # Execute with retries
        for attempt in range(step.retry + 1):
            if attempt > 0:
                print(f"[SAGE] Retry {attempt}/{step.retry}")
            
            try:
                result = await asyncio.wait_for(
                    self._run_command(command, env),
                    timeout=step.timeout,
                )
                
                if result == 0:
                    return True
                
            except asyncio.TimeoutError:
                print(f"[SAGE] Step timed out after {step.timeout}s")
            except Exception as e:
                print(f"[SAGE] Step error: {e}")
        
        return False

    async def _run_command(self, command: str, env: dict) -> int:
        """Run command asynchronously."""
        process = await asyncio.create_subprocess_shell(
            command,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        stdout, stderr = await process.communicate()
        
        if stdout:
            print(stdout.decode())
        if stderr:
            print(stderr.decode())
        
        return process.returncode or 0

    async def _handle_actions(self, actions: list[str], env: dict) -> None:
        """Handle on_success or on_fail actions."""
        for action in actions:
            if action == "exit":
                break
            else:
                # Execute action as command
                await self._run_command(action, env)

    def _save_workflow_start(self, workflow: Workflow) -> int:
        """Save workflow start to database."""
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        
        with connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO workflow_runs
                (workflow_name, status, steps_total, started_at)
                VALUES (?, ?, ?, ?)
                """,
                (workflow.name, "running", len(workflow.pipeline), now),
            )
            conn.commit()
            return cursor.lastrowid

    def _save_workflow_end(self, success: bool, steps_completed: int) -> None:
        """Save workflow completion to database."""
        if not self.run_id:
            return
        
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        status = "completed" if success else "failed"
        
        with connect() as conn:
            conn.execute(
                """
                UPDATE workflow_runs
                SET status = ?, steps_completed = ?, completed_at = ?
                WHERE id = ?
                """,
                (status, steps_completed, now, self.run_id),
            )
            conn.commit()
