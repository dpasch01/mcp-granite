"""Surveillance domain – Primitive MCP server (10 fine-grained tools).

Run standalone:  python -m mcp_granite.mcp_servers.surveillance.primitive_server
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
from mcp_granite.mcp_servers.surveillance._store import SurveillanceStore

mcp = FastMCP("surveillance-primitive")
store = SurveillanceStore()
injector = FaultInjector(FaultConfig.from_env())


@mcp.tool()
async def list_cameras(location: str | None = None) -> list[dict]:
    """List all security cameras, optionally filtered by location."""
    fault = await injector.maybe_raise("list_cameras")
    results = [c.model_dump() for c in store.list_cameras(location)]
    if fault == FaultType.PARTIAL_RESPONSE:
        return truncate_response(results)
    return results


@mcp.tool()
async def set_camera(
    camera_id: str,
    status: str | None = None,
    recording: bool | None = None,
    night_vision: bool | None = None,
) -> dict:
    """Update a camera's status, recording, or night vision settings."""
    await injector.maybe_raise("set_camera")
    kwargs = {}
    if status is not None:
        kwargs["status"] = status
    if recording is not None:
        kwargs["recording"] = recording
    if night_vision is not None:
        kwargs["night_vision"] = night_vision
    cam = store.set_camera(camera_id, **kwargs)
    if not cam:
        return {"error": f"Camera '{camera_id}' not found."}
    return cam.model_dump()


@mcp.tool()
async def list_motion_sensors(location: str | None = None) -> list[dict]:
    """List all motion sensors, optionally filtered by location."""
    fault = await injector.maybe_raise("list_motion_sensors")
    results = [s.model_dump() for s in store.list_motion_sensors(location)]
    if fault == FaultType.PARTIAL_RESPONSE:
        return truncate_response(results)
    if fault == FaultType.CONTRADICTORY:
        return [corrupt_numeric_field(r, "battery_level") for r in results]
    return results


@mcp.tool()
async def set_motion_sensor(
    sensor_id: str, status: str | None = None, sensitivity: str | None = None
) -> dict:
    """Update a motion sensor's status or sensitivity level."""
    await injector.maybe_raise("set_motion_sensor")
    kwargs = {}
    if status is not None:
        kwargs["status"] = status
    if sensitivity is not None:
        kwargs["sensitivity"] = sensitivity
    sensor = store.set_motion_sensor(sensor_id, **kwargs)
    if not sensor:
        return {"error": f"Motion sensor '{sensor_id}' not found."}
    return sensor.model_dump()


@mcp.tool()
async def get_access_point(point_id: str) -> dict:
    """Get the status of a specific access point."""
    fault = await injector.maybe_raise("get_access_point")
    point = store.get_access_point(point_id)
    if not point:
        return {"error": f"Access point '{point_id}' not found."}
    result = point.model_dump()
    if fault == FaultType.CONTRADICTORY:
        result["status"] = "unlocked" if result["status"] == "locked" else "locked"
    return result


@mcp.tool()
async def set_access_point(
    point_id: str, status: str | None = None, access_level: int | None = None
) -> dict:
    """Update an access point's lock status or access level."""
    await injector.maybe_raise("set_access_point")
    kwargs = {}
    if status is not None:
        kwargs["status"] = status
    if access_level is not None:
        kwargs["access_level"] = access_level
    point = store.set_access_point(point_id, **kwargs)
    if not point:
        return {"error": f"Access point '{point_id}' not found."}
    return point.model_dump()


@mcp.tool()
async def get_alarm_zone(zone_id: str) -> dict:
    """Get the status of a specific alarm zone."""
    fault = await injector.maybe_raise("get_alarm_zone")
    zone = store.get_alarm_zone(zone_id)
    if not zone:
        return {"error": f"Alarm zone '{zone_id}' not found."}
    result = zone.model_dump()
    if fault == FaultType.CONTRADICTORY:
        result["status"] = "disarmed" if result["status"] == "armed" else "armed"
    return result


@mcp.tool()
async def set_alarm_zone(zone_id: str, status: str) -> dict:
    """Set an alarm zone's status (armed/disarmed/testing)."""
    await injector.maybe_raise("set_alarm_zone")
    zone = store.set_alarm_zone(zone_id, status=status)
    if not zone:
        return {"error": f"Alarm zone '{zone_id}' not found."}
    return zone.model_dump()


@mcp.tool()
async def get_security_events(severity: str | None = None, limit: int = 10) -> list[dict]:
    """Get recent security events, optionally filtered by severity."""
    fault = await injector.maybe_raise("get_security_events")
    events = store.get_events(severity=severity, limit=limit)
    results = [e.model_dump() for e in events]
    if fault == FaultType.PARTIAL_RESPONSE:
        return truncate_response(results)
    return results


@mcp.tool()
async def manage_patrol(
    action: str,
    patrol_id: str | None = None,
    name: str | None = None,
    route: list[str] | None = None,
    scheduled_time: str | None = None,
    assigned_guard: str | None = None,
    status: str | None = None,
) -> dict:
    """Manage security patrols: list, schedule, or update."""
    fault = await injector.maybe_raise("manage_patrol")
    if action == "list":
        patrols = store.list_patrols(status)
        results = [p.model_dump() for p in patrols]
        if fault == FaultType.PARTIAL_RESPONSE:
            return {"patrols": truncate_response(results)}
        return {"patrols": results}
    elif action == "schedule":
        if not name or not route or not scheduled_time:
            return {"error": "schedule requires 'name', 'route', and 'scheduled_time'."}
        patrol = store.schedule_patrol(name, route, scheduled_time, assigned_guard)
        return patrol.model_dump()
    elif action == "update":
        if not patrol_id:
            return {"error": "update requires 'patrol_id'."}
        kwargs = {}
        if status is not None:
            kwargs["status"] = status
        if assigned_guard is not None:
            kwargs["assigned_guard"] = assigned_guard
        patrol = store.update_patrol(patrol_id, **kwargs)
        if not patrol:
            return {"error": f"Patrol '{patrol_id}' not found."}
        return patrol.model_dump()
    else:
        return {"error": f"Unknown action '{action}'. Supported: list, schedule, update."}


if __name__ == "__main__":
    mcp.run(transport="stdio")
