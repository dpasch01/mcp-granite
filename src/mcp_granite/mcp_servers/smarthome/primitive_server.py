"""Smart Home domain – Primitive MCP server (9 fine-grained tools).

Run standalone:  python -m mcp_granite.mcp_servers.smarthome.primitive_server
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_granite.mcp_servers._base import (
    FaultConfig,
    FaultInjector,
    FaultType,
    corrupt_numeric_field,
    truncate_response,
)
from mcp_granite.mcp_servers.smarthome._store import SmartHomeStore

mcp = FastMCP("smarthome-primitive")
store = SmartHomeStore()
injector = FaultInjector(FaultConfig.from_env())


# ── tools ────────────────────────────────────────────────────────────────────


@mcp.tool()
async def list_sensors(location: str | None = None) -> list[dict]:
    """List all sensors in the smart home, optionally filtered by location."""
    fault = await injector.maybe_raise("list_sensors")
    sensors = store.list_sensors(location)
    results = [s.model_dump() for s in sensors]
    if fault == FaultType.PARTIAL_RESPONSE:
        return truncate_response(results)
    if fault == FaultType.CONTRADICTORY:
        return [corrupt_numeric_field(r, "value") for r in results]
    return results


@mcp.tool()
async def read_sensor(sensor_id: str) -> dict:
    """Read the current value of a specific sensor."""
    fault = await injector.maybe_raise("read_sensor")
    sensor = store.read_sensor(sensor_id)
    if not sensor:
        return {"error": f"Sensor '{sensor_id}' not found."}
    result = sensor.model_dump()
    if fault == FaultType.CONTRADICTORY:
        result = corrupt_numeric_field(result, "value")
    return result


@mcp.tool()
async def list_devices(location: str | None = None) -> list[dict]:
    """List all controllable devices in the smart home, optionally filtered by location."""
    fault = await injector.maybe_raise("list_devices")
    devices = store.list_devices(location)
    results = [d.model_dump() for d in devices]
    if fault == FaultType.PARTIAL_RESPONSE:
        return truncate_response(results)
    return results


@mcp.tool()
async def get_device_status(device_id: str) -> dict:
    """Get the current status and settings of a specific device."""
    fault = await injector.maybe_raise("get_device_status")
    device = store.get_device_status(device_id)
    if not device:
        return {"error": f"Device '{device_id}' not found."}
    result = device.model_dump()
    if fault == FaultType.CONTRADICTORY:
        result["status"] = "off" if result["status"] == "on" else "on"
    return result


@mcp.tool()
async def set_device(device_id: str, settings: dict) -> dict:
    """Update settings for a specific device (e.g. brightness, target_temp, status)."""
    fault = await injector.maybe_raise("set_device")
    device = store.set_device(device_id, settings)
    if not device:
        return {"error": f"Device '{device_id}' not found."}
    result = device.model_dump()
    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("settings", None)
    return result


@mcp.tool()
async def get_automation_rule(rule_id: str) -> dict:
    """Get details of a specific automation rule."""
    fault = await injector.maybe_raise("get_automation_rule")
    rule = store.get_automation_rule(rule_id)
    if not rule:
        return {"error": f"Automation rule '{rule_id}' not found."}
    result = rule.model_dump()
    if fault == FaultType.CONTRADICTORY:
        result["enabled"] = not result["enabled"]
    return result


@mcp.tool()
async def set_automation_rule(
    rule_id: str,
    enabled: bool | None = None,
    trigger: dict | None = None,
    action: dict | None = None,
) -> dict:
    """Update an existing automation rule's enabled state, trigger, or action."""
    await injector.maybe_raise("set_automation_rule")
    rule = store.set_automation_rule(rule_id, enabled=enabled, trigger=trigger, action=action)
    if not rule:
        return {"error": f"Automation rule '{rule_id}' not found."}
    return rule.model_dump()


@mcp.tool()
async def create_automation_rule(name: str, trigger: dict, action: dict) -> dict:
    """Create a new automation rule with the given trigger and action."""
    await injector.maybe_raise("create_automation_rule")
    rule = store.create_automation_rule(name, trigger, action)
    return rule.model_dump()


@mcp.tool()
async def get_event_log(severity: str | None = None, limit: int = 10) -> list[dict]:
    """Get recent event log entries, optionally filtered by severity (info/warning/critical)."""
    fault = await injector.maybe_raise("get_event_log")
    events = store.get_event_log(severity=severity, limit=limit)
    results = [e.model_dump() for e in events]
    if fault == FaultType.PARTIAL_RESPONSE:
        return truncate_response(results)
    return results


if __name__ == "__main__":
    mcp.run(transport="stdio")
