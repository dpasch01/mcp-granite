"""Fault injection infrastructure shared by all MCP servers."""

from __future__ import annotations

import asyncio
import json
import os
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FaultType(str, Enum):
    TRANSIENT_ERROR = "transient_error"
    TIMEOUT = "timeout"
    PARTIAL_RESPONSE = "partial_response"
    CONTRADICTORY = "contradictory"


@dataclass
class FaultConfig:
    """Configuration for fault injection, typically read from FAULT_CONFIG env var."""

    rate: float = 0.0
    seed: int = 42
    fault_types: list[str] = field(
        default_factory=lambda: [ft.value for ft in FaultType]
    )

    def to_json(self) -> str:
        return json.dumps(
            {"rate": self.rate, "seed": self.seed, "fault_types": self.fault_types}
        )

    @classmethod
    def from_env(cls) -> FaultConfig:
        raw = os.environ.get("FAULT_CONFIG", "{}")
        data = json.loads(raw)
        return cls(**data)


class FaultInjector:
    """Deterministic fault injector using a seeded RNG.

    Usage in an MCP tool:
        fault = injector.check(tool_name)
        if fault == FaultType.PARTIAL_RESPONSE:
            # return truncated data
        elif fault is None:
            # normal execution
    """

    def __init__(self, config: FaultConfig) -> None:
        self.rate = config.rate
        self.rng = random.Random(config.seed)
        self.fault_types = config.fault_types
        self.call_count = 0

    def check(self, tool_name: str) -> FaultType | None:
        """Check whether a fault should be injected on this call.

        Returns the FaultType to inject, or None for normal execution.
        Raises ValueError for transient errors (caller should catch and re-raise as tool error).
        """
        self.call_count += 1
        if self.rate <= 0 or self.rng.random() >= self.rate:
            return None
        chosen = self.rng.choice(self.fault_types)
        return FaultType(chosen)

    async def maybe_raise(self, tool_name: str) -> FaultType | None:
        """Check for fault and raise/sleep for error types. Returns fault type for data faults.

        - TRANSIENT_ERROR: raises ValueError (MCP server should convert to tool error).
        - TIMEOUT: sleeps for 30s (will likely hit caller's timeout).
        - PARTIAL_RESPONSE / CONTRADICTORY: returned for the tool to handle.
        """
        fault = self.check(tool_name)
        if fault is None:
            return None
        if fault == FaultType.TRANSIENT_ERROR:
            raise ValueError(
                f"Service temporarily unavailable for '{tool_name}'. Please retry."
            )
        if fault == FaultType.TIMEOUT:
            await asyncio.sleep(30)
            return fault
        return fault


def truncate_response(data: list[dict[str, Any]], keep: int = 1) -> list[dict[str, Any]]:
    """Truncate a list response to simulate partial data."""
    return data[:keep] if data else data


def corrupt_numeric_field(data: dict[str, Any], field: str, factor: float = 0.1) -> dict[str, Any]:
    """Corrupt a numeric field to simulate contradictory data."""
    if field in data and isinstance(data[field], (int, float)):
        data = {**data, field: round(data[field] * factor, 2)}
    return data
