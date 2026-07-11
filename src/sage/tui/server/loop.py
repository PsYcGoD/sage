"""Core agentic loop for SAGE chat server."""
from __future__ import annotations
import asyncio
import json
import time
from typing import AsyncIterator, Any

from .models import Message, ToolCall
from .providers.base import StreamEvent, BaseProvider
from .tools import ToolRegistry


class AgenticLoop:
    """Agentic loop that streams LLM responses and executes tools."""

    def __init__(
        self,
        provider: BaseProvider,
        tools: ToolRegistry,
        max_iterations: int = 25,
    ):
        self.provider = provider
        self.tools = tools
        self.max_iterations = max_iterations
        self._cancelled = False

    def cancel(self):
        """Cancel the current loop."""
        self._cancelled = True

    async def run(
        self, messages: list[dict], model: str
    ) -> AsyncIterator[StreamEvent]:
        """Run the agentic loop. Yields StreamEvents as they happen."""
        iterations = 0

        while iterations < self.max_iterations and not self._cancelled:
            iterations += 1

            # Collect events from this turn
            assistant_text = ""
            tool_calls_this_turn: list[dict] = []
            current_tool_call: dict[str, Any] | None = None
            tokens_in = 0
            tokens_out = 0

            # Stream from the LLM
            async for event in self.provider.stream(
                messages, self.tools.schemas(), model
            ):
                if self._cancelled:
                    return

                yield event

                # Accumulate assistant response
                if event.type == "token":
                    assistant_text += event.content

                elif event.type == "tool_call_start":
                    current_tool_call = {
                        "id": event.tool_id,
                        "name": event.tool_name,
                        "input": "",
                    }

                elif event.type == "tool_call_delta":
                    if current_tool_call:
                        current_tool_call["input"] += event.tool_input

                elif event.type == "tool_call_end":
                    if current_tool_call:
                        current_tool_call["input"] = event.tool_input
                        tool_calls_this_turn.append(current_tool_call)
                        current_tool_call = None

                elif event.type == "done":
                    tokens_in = event.tokens_in
                    tokens_out = event.tokens_out

                elif event.type == "error":
                    yield event
                    return

            # If no tool calls, we're done
            if not tool_calls_this_turn:
                return

            # Build assistant message with tool calls
            assistant_msg = {
                "role": "assistant",
                "content": assistant_text if assistant_text else [],
            }

            # Add tool_use content blocks (Anthropic format)
            content_blocks = []
            if assistant_text:
                content_blocks.append({"type": "text", "text": assistant_text})

            for tc in tool_calls_this_turn:
                try:
                    input_dict = json.loads(tc["input"]) if isinstance(tc["input"], str) else tc["input"]
                except json.JSONDecodeError:
                    input_dict = {}

                content_blocks.append({
                    "type": "tool_use",
                    "id": tc["id"],
                    "name": tc["name"],
                    "input": input_dict,
                })

            assistant_msg["content"] = content_blocks
            messages.append(assistant_msg)

            # Execute each tool call
            tool_results = []
            for tc in tool_calls_this_turn:
                tool_name = tc["name"]
                tool_id = tc["id"]

                # Parse input
                try:
                    if isinstance(tc["input"], str):
                        tool_input = json.loads(tc["input"])
                    else:
                        tool_input = tc["input"]
                except json.JSONDecodeError:
                    tool_input = {}

                # Notify execution start
                yield StreamEvent(
                    type="tool_execution_start",
                    tool_id=tool_id,
                    tool_name=tool_name,
                )

                # Execute tool
                started = time.perf_counter()
                try:
                    result = await self.tools.execute(tool_name, tool_input)
                    duration_ms = int((time.perf_counter() - started) * 1000)

                    # Format result as string
                    result_str = json.dumps(result, indent=2)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": result_str,
                    })

                    # Notify execution complete
                    yield StreamEvent(
                        type="tool_execution_end",
                        tool_id=tool_id,
                        tool_name=tool_name,
                        content=result_str,
                    )

                except Exception as e:
                    duration_ms = int((time.perf_counter() - started) * 1000)
                    error_str = f"Tool execution error: {str(e)}"
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": error_str,
                        "is_error": True,
                    })

                    yield StreamEvent(
                        type="tool_execution_error",
                        tool_id=tool_id,
                        tool_name=tool_name,
                        error=error_str,
                    )

            # Add tool results as a user message (Anthropic format)
            messages.append({
                "role": "user",
                "content": tool_results,
            })

            # Continue the loop - LLM will see tool results and respond
