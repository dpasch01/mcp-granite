"""Execution trace data models for capturing agent behavior."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    """A single tool invocation by the agent."""

    tool_name: str
    arguments: dict[str, Any]
    timestamp: float  # relative to run start


@dataclass
class ToolResponse:
    """Response from a tool invocation."""

    tool_name: str
    response: Any
    is_error: bool
    timestamp: float  # relative to run start


@dataclass
class ExecutionTrace:
    """Full execution trace of a single scenario run."""

    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_responses: list[ToolResponse] = field(default_factory=list)
    final_answer: str | None = None
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    wall_time_seconds: float = 0.0
    num_llm_turns: int = 0
    timed_out: bool = False
    error: str | None = None
    raw_events: list[dict[str, Any]] = field(default_factory=list)
    started_at: str | None = None  # ISO-8601 UTC wall-clock start
    ended_at: str | None = None    # ISO-8601 UTC wall-clock end

    def tool_call_names(self) -> list[str]:
        """Return ordered list of tool names called."""
        return [tc.tool_name for tc in self.tool_calls]

    def tool_call_set(self) -> set[str]:
        """Return set of unique tool names called."""
        return {tc.tool_name for tc in self.tool_calls}

    def total_tokens(self) -> int:
        return self.total_tokens_in + self.total_tokens_out

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_calls": [
                {"tool_name": tc.tool_name, "arguments": tc.arguments, "timestamp": tc.timestamp}
                for tc in self.tool_calls
            ],
            "tool_responses": [
                {"tool_name": tr.tool_name, "response": tr.response, "is_error": tr.is_error, "timestamp": tr.timestamp}
                for tr in self.tool_responses
            ],
            "final_answer": self.final_answer,
            "total_tokens_in": self.total_tokens_in,
            "total_tokens_out": self.total_tokens_out,
            "wall_time_seconds": self.wall_time_seconds,
            "num_llm_turns": self.num_llm_turns,
            "timed_out": self.timed_out,
            "error": self.error,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
        }
