"""Run a single scenario against an ADK agent and capture the execution trace."""

from __future__ import annotations

import time
import asyncio
from datetime import datetime, timezone
from typing import Any

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from edgetoolbench.harness.trace import ExecutionTrace, ToolCall, ToolResponse
from edgetoolbench.scenarios.schema import ScenarioDef


async def run_scenario(
    runner: Runner,
    scenario: ScenarioDef,
    user_id: str = "bench_user",
    session_id: str | None = None,
    timeout_seconds: float = 120.0,
    max_turns: int = 20,
) -> ExecutionTrace:
    """Execute a scenario and return the full execution trace.

    Args:
        runner: ADK Runner instance (already configured with agent + session service).
        scenario: The scenario definition containing the user prompt.
        user_id: User ID for the session.
        session_id: Optional session ID (auto-generated if None).
        timeout_seconds: Wall-time limit for the run.
        max_turns: Maximum number of LLM turns before aborting.

    Returns:
        ExecutionTrace with all tool calls, responses, and metrics.
    """
    session_service: InMemorySessionService = runner.session_service  # type: ignore
    session = await session_service.create_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id,
    )

    trace = ExecutionTrace()
    trace.started_at = datetime.now(timezone.utc).isoformat()
    start_time = time.monotonic()
    turn_count = 0

    user_message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=scenario.user_prompt.strip())],
    )

    try:
        async with asyncio.timeout(timeout_seconds):
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session.id,
                new_message=user_message,
            ):
                elapsed = time.monotonic() - start_time

                # Capture function calls
                for fc in event.get_function_calls():
                    trace.tool_calls.append(ToolCall(
                        tool_name=fc.name or "",
                        arguments=fc.args or {},
                        timestamp=elapsed,
                    ))

                # Capture function responses
                for fr in event.get_function_responses():
                    is_err = _is_error_response(fr)
                    trace.tool_responses.append(ToolResponse(
                        tool_name=fr.name or "",
                        response=fr.response if hasattr(fr, "response") else str(fr),
                        is_error=is_err,
                        timestamp=elapsed,
                    ))

                # Track LLM turns (events authored by agent with content)
                if event.content and event.author != "user":
                    turn_count += 1

                # Capture final response text
                if event.is_final_response() and event.content:
                    text_parts = []
                    for part in (event.content.parts or []):
                        if hasattr(part, "text") and part.text:
                            text_parts.append(part.text)
                    if text_parts:
                        trace.final_answer = "\n".join(text_parts)

                # Safety: abort if too many turns
                if turn_count >= max_turns:
                    trace.timed_out = True
                    trace.error = f"Exceeded max turns ({max_turns})"
                    break

    except TimeoutError:
        trace.timed_out = True
        trace.error = f"Wall-time timeout ({timeout_seconds}s)"

    except Exception as exc:
        trace.error = f"{type(exc).__name__}: {exc}"

    trace.wall_time_seconds = time.monotonic() - start_time
    trace.ended_at = datetime.now(timezone.utc).isoformat()
    trace.num_llm_turns = turn_count

    return trace


def _is_error_response(fr: Any) -> bool:
    """Heuristic: detect if a function response represents an error."""
    resp = fr.response if hasattr(fr, "response") else str(fr)
    if isinstance(resp, dict):
        return "error" in resp
    if isinstance(resp, str):
        return "error" in resp.lower() or "unavailable" in resp.lower()
    return False


def build_runner(
    agent: Any,
    app_name: str = "edgetoolbench",
) -> Runner:
    """Create an ADK Runner for the given agent."""
    session_service = InMemorySessionService()
    return Runner(
        app_name=app_name,
        agent=agent,
        session_service=session_service,
    )
