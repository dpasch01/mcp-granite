from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GoldToolCallDef(BaseModel):
    """A single expected tool call in the gold-standard sequence."""

    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    required: bool = True
    order_flexible: bool = False


class ExpectedOutput(BaseModel):
    """Expected properties of the agent's final answer."""

    contains: list[str] = Field(default_factory=list)
    values: dict[str, Any] = Field(default_factory=dict)


class ScenarioDef(BaseModel):
    """Complete definition of a benchmark scenario loaded from YAML."""

    id: str
    domain: str
    name: str
    description: str
    difficulty: str  # "easy", "medium", "hard"
    user_prompt: str
    context: dict[str, Any] = Field(default_factory=dict)

    # Separate gold standards per granularity level
    gold_standard: dict[str, list[GoldToolCallDef]]  # keys: "primitive", "composite"

    expected_output: ExpectedOutput
