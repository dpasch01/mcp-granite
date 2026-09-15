"""Energy (microgrid) domain – Primitive MCP server (10 fine-grained tools).

Run standalone:  python -m edgetoolbench.mcp_servers.energy.primitive_server
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from edgetoolbench.mcp_servers._base import (
    FaultConfig,
    FaultInjector,
    FaultType,
    corrupt_numeric_field,
    truncate_response,
)
from edgetoolbench.mcp_servers.energy._store import EnergyStore

mcp = FastMCP("energy-primitive")
store = EnergyStore()
injector = FaultInjector(FaultConfig.from_env())


@mcp.tool()
async def list_power_sources(status: str | None = None) -> list[dict]:
    """List all power sources in the microgrid, optionally filtered by status."""
    fault = await injector.maybe_raise("list_power_sources")
    sources = store.list_power_sources(status)
    results = [s.model_dump() for s in sources]
    if fault == FaultType.PARTIAL_RESPONSE:
        return truncate_response(results)
    if fault == FaultType.CONTRADICTORY:
        return [corrupt_numeric_field(r, "current_output_kw") for r in results]
    return results


@mcp.tool()
async def get_power_source(source_id: str) -> dict:
    """Get details of a specific power source."""
    fault = await injector.maybe_raise("get_power_source")
    source = store.get_power_source(source_id)
    if not source:
        return {"error": f"Power source '{source_id}' not found."}
    result = source.model_dump()
    if fault == FaultType.CONTRADICTORY:
        result = corrupt_numeric_field(result, "current_output_kw")
    return result


@mcp.tool()
async def set_power_source(
    source_id: str, status: str | None = None, current_output_kw: float | None = None
) -> dict:
    """Update a power source's status or output level."""
    await injector.maybe_raise("set_power_source")
    kwargs = {}
    if status is not None:
        kwargs["status"] = status
    if current_output_kw is not None:
        kwargs["current_output_kw"] = current_output_kw
    source = store.set_power_source(source_id, **kwargs)
    if not source:
        return {"error": f"Power source '{source_id}' not found."}
    return source.model_dump()


@mcp.tool()
async def list_load_zones(zone_type: str | None = None) -> list[dict]:
    """List all load zones in the microgrid, optionally filtered by type."""
    fault = await injector.maybe_raise("list_load_zones")
    zones = store.list_load_zones(zone_type)
    results = [z.model_dump() for z in zones]
    if fault == FaultType.PARTIAL_RESPONSE:
        return truncate_response(results)
    return results


@mcp.tool()
async def set_load_zone(
    zone_id: str,
    status: str | None = None,
    current_load_kw: float | None = None,
    priority: int | None = None,
) -> dict:
    """Update a load zone's status, load, or priority."""
    await injector.maybe_raise("set_load_zone")
    kwargs = {}
    if status is not None:
        kwargs["status"] = status
    if current_load_kw is not None:
        kwargs["current_load_kw"] = current_load_kw
    if priority is not None:
        kwargs["priority"] = priority
    zone = store.set_load_zone(zone_id, **kwargs)
    if not zone:
        return {"error": f"Load zone '{zone_id}' not found."}
    return zone.model_dump()


@mcp.tool()
async def get_battery_status(battery_id: str) -> dict:
    """Get the current status of a specific battery."""
    fault = await injector.maybe_raise("get_battery_status")
    battery = store.get_battery(battery_id)
    if not battery:
        return {"error": f"Battery '{battery_id}' not found."}
    result = battery.model_dump()
    if fault == FaultType.CONTRADICTORY:
        result = corrupt_numeric_field(result, "soc_percent")
    return result


@mcp.tool()
async def set_battery(
    battery_id: str,
    status: str | None = None,
    charge_rate_kw: float | None = None,
    discharge_rate_kw: float | None = None,
) -> dict:
    """Update battery status or charge/discharge rates."""
    await injector.maybe_raise("set_battery")
    kwargs = {}
    if status is not None:
        kwargs["status"] = status
    if charge_rate_kw is not None:
        kwargs["charge_rate_kw"] = charge_rate_kw
    if discharge_rate_kw is not None:
        kwargs["discharge_rate_kw"] = discharge_rate_kw
    battery = store.set_battery(battery_id, **kwargs)
    if not battery:
        return {"error": f"Battery '{battery_id}' not found."}
    return battery.model_dump()


@mcp.tool()
async def read_smart_meter(meter_id: str) -> dict:
    """Read the current data from a specific smart meter."""
    fault = await injector.maybe_raise("read_smart_meter")
    meter = store.get_smart_meter(meter_id)
    if not meter:
        return {"error": f"Smart meter '{meter_id}' not found."}
    result = meter.model_dump()
    if fault == FaultType.CONTRADICTORY:
        result = corrupt_numeric_field(result, "current_reading_kwh")
    return result


@mcp.tool()
async def get_energy_alerts(severity: str | None = None, limit: int = 10) -> list[dict]:
    """Get recent energy alerts, optionally filtered by severity."""
    fault = await injector.maybe_raise("get_energy_alerts")
    alerts = store.get_alerts(severity=severity, limit=limit)
    results = [a.model_dump() for a in alerts]
    if fault == FaultType.PARTIAL_RESPONSE:
        return truncate_response(results)
    return results


@mcp.tool()
async def create_schedule_entry(
    name: str, target_id: str, action: str, scheduled_time: str, parameters: dict
) -> dict:
    """Create a new scheduled operation for the microgrid."""
    await injector.maybe_raise("create_schedule_entry")
    entry = store.create_schedule_entry(name, target_id, action, scheduled_time, parameters)
    return entry.model_dump()


if __name__ == "__main__":
    mcp.run(transport="stdio")
