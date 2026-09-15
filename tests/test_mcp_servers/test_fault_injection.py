"""Tests for fault injection."""

import asyncio

import pytest

from mcp_granite.mcp_servers._base import (
    FaultConfig,
    FaultInjector,
    FaultType,
    truncate_response,
    corrupt_numeric_field,
)


def test_no_fault_when_rate_zero():
    injector = FaultInjector(FaultConfig(rate=0.0))
    for _ in range(100):
        result = injector.check("test_tool")
        assert result is None


def test_always_fault_when_rate_one():
    injector = FaultInjector(FaultConfig(rate=1.0, seed=42))
    faults = [injector.check("test_tool") for _ in range(10)]
    assert all(f is not None for f in faults)


def test_deterministic_with_same_seed():
    inj1 = FaultInjector(FaultConfig(rate=0.5, seed=123))
    inj2 = FaultInjector(FaultConfig(rate=0.5, seed=123))
    results1 = [inj1.check("tool") for _ in range(20)]
    results2 = [inj2.check("tool") for _ in range(20)]
    assert results1 == results2


def test_different_seeds_give_different_results():
    inj1 = FaultInjector(FaultConfig(rate=0.5, seed=1))
    inj2 = FaultInjector(FaultConfig(rate=0.5, seed=2))
    results1 = [inj1.check("tool") for _ in range(20)]
    results2 = [inj2.check("tool") for _ in range(20)]
    assert results1 != results2


@pytest.mark.asyncio
async def test_maybe_raise_transient_error():
    injector = FaultInjector(FaultConfig(
        rate=1.0, seed=42,
        fault_types=["transient_error"],
    ))
    with pytest.raises(ValueError, match="temporarily unavailable"):
        await injector.maybe_raise("test_tool")


def test_truncate_response():
    data = [{"id": 1}, {"id": 2}, {"id": 3}]
    assert truncate_response(data) == [{"id": 1}]
    assert truncate_response([]) == []


def test_corrupt_numeric_field():
    data = {"price": 100.0, "name": "test"}
    corrupted = corrupt_numeric_field(data, "price")
    assert corrupted["price"] == 10.0
    assert corrupted["name"] == "test"


def test_fault_config_from_json():
    config = FaultConfig(rate=0.3, seed=99)
    json_str = config.to_json()
    import json
    data = json.loads(json_str)
    restored = FaultConfig(**data)
    assert restored.rate == 0.3
    assert restored.seed == 99
