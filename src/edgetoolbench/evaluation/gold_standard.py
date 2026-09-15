"""Gold-standard loader for evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from edgetoolbench.scenarios.schema import GoldToolCallDef, ScenarioDef


@dataclass
class GoldToolCall:
    """A single expected tool call."""

    tool_name: str
    arguments: dict[str, Any]
    required: bool = True
    order_flexible: bool = False


@dataclass
class GoldStandard:
    """Gold-standard tool-call sequence for a scenario at a specific granularity."""

    calls: list[GoldToolCall]
    expected_contains: list[str] = field(default_factory=list)
    expected_values: dict[str, Any] = field(default_factory=dict)

    @property
    def required_calls(self) -> list[GoldToolCall]:
        return [c for c in self.calls if c.required]

    @property
    def tool_names(self) -> list[str]:
        return [c.tool_name for c in self.calls]

    @property
    def required_tool_names(self) -> list[str]:
        return [c.tool_name for c in self.required_calls]


def load_gold_standard(scenario: ScenarioDef, granularity: str) -> GoldStandard:
    """Extract the gold standard for a given granularity from a scenario definition."""
    raw_calls: list[GoldToolCallDef] = scenario.gold_standard[granularity]
    calls = [
        GoldToolCall(
            tool_name=c.tool,
            arguments=c.arguments,
            required=c.required,
            order_flexible=c.order_flexible,
        )
        for c in raw_calls
    ]
    return GoldStandard(
        calls=calls,
        expected_contains=scenario.expected_output.contains,
        expected_values=scenario.expected_output.values,
    )
