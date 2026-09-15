"""Agriculture domain – Primitive MCP server (10 fine-grained tools).

Run standalone:  python -m mcp_granite.mcp_servers.agriculture.primitive_server
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
from mcp_granite.mcp_servers.agriculture._store import AgricultureStore

mcp = FastMCP("agriculture-primitive")
store = AgricultureStore()
injector = FaultInjector(FaultConfig.from_env())


@mcp.tool()
async def list_sensors(field_zone: str | None = None) -> list[dict]:
    """List all agricultural sensors, optionally filtered by field zone."""
    fault = await injector.maybe_raise("list_sensors")
    sensors = store.list_sensors(field_zone)
    results = [s.model_dump() for s in sensors]
    if fault == FaultType.PARTIAL_RESPONSE:
        return truncate_response(results)
    if fault == FaultType.CONTRADICTORY:
        return [corrupt_numeric_field(r, "value") for r in results]
    return results


@mcp.tool()
async def read_sensor(sensor_id: str) -> dict:
    """Read the current value of a specific agricultural sensor."""
    fault = await injector.maybe_raise("read_sensor")
    sensor = store.read_sensor(sensor_id)
    if not sensor:
        return {"error": f"Sensor '{sensor_id}' not found."}
    result = sensor.model_dump()
    if fault == FaultType.CONTRADICTORY:
        result = corrupt_numeric_field(result, "value")
    return result


@mcp.tool()
async def list_irrigation_zones(field_zone: str | None = None) -> list[dict]:
    """List all irrigation zones, optionally filtered by field zone."""
    fault = await injector.maybe_raise("list_irrigation_zones")
    zones = store.list_irrigation_zones(field_zone)
    results = [z.model_dump() for z in zones]
    if fault == FaultType.PARTIAL_RESPONSE:
        return truncate_response(results)
    return results


@mcp.tool()
async def get_irrigation_zone(zone_id: str) -> dict:
    """Get details of a specific irrigation zone."""
    fault = await injector.maybe_raise("get_irrigation_zone")
    zone = store.get_irrigation_zone(zone_id)
    if not zone:
        return {"error": f"Irrigation zone '{zone_id}' not found."}
    result = zone.model_dump()
    if fault == FaultType.CONTRADICTORY:
        result = corrupt_numeric_field(result, "flow_rate")
    return result


@mcp.tool()
async def set_irrigation_zone(
    zone_id: str,
    status: str | None = None,
    flow_rate: float | None = None,
    schedule: dict | None = None,
) -> dict:
    """Update an irrigation zone's status, flow rate, or schedule."""
    await injector.maybe_raise("set_irrigation_zone")
    kwargs = {}
    if status is not None:
        kwargs["status"] = status
    if flow_rate is not None:
        kwargs["flow_rate"] = flow_rate
    if schedule is not None:
        kwargs["schedule"] = schedule
    zone = store.set_irrigation_zone(zone_id, **kwargs)
    if not zone:
        return {"error": f"Irrigation zone '{zone_id}' not found."}
    return zone.model_dump()


@mcp.tool()
async def list_crops(field_zone: str | None = None) -> list[dict]:
    """List all crops, optionally filtered by field zone."""
    fault = await injector.maybe_raise("list_crops")
    crops = store.list_crops(field_zone)
    results = [c.model_dump() for c in crops]
    if fault == FaultType.PARTIAL_RESPONSE:
        return truncate_response(results)
    return results


@mcp.tool()
async def get_crop(crop_id: str) -> dict:
    """Get details of a specific crop including health and growth stage."""
    fault = await injector.maybe_raise("get_crop")
    crop = store.get_crop(crop_id)
    if not crop:
        return {"error": f"Crop '{crop_id}' not found."}
    result = crop.model_dump()
    if fault == FaultType.CONTRADICTORY:
        result["health_status"] = "healthy" if result["health_status"] != "healthy" else "stressed"
    return result


@mcp.tool()
async def get_weather(station_id: str | None = None) -> dict | list[dict]:
    """Get weather data from a specific station or all stations."""
    fault = await injector.maybe_raise("get_weather")
    if station_id:
        station = store.get_weather_station(station_id)
        if not station:
            return {"error": f"Weather station '{station_id}' not found."}
        result = station.model_dump()
        if fault == FaultType.CONTRADICTORY:
            result = corrupt_numeric_field(result, "temperature")
        return result
    stations = store.list_weather_stations()
    results = [s.model_dump() for s in stations]
    if fault == FaultType.PARTIAL_RESPONSE:
        return truncate_response(results)
    return results


@mcp.tool()
async def schedule_drone_task(
    drone_id: str, task_type: str, field_zone: str, scheduled_time: str
) -> dict:
    """Schedule a new drone task (survey, spray, seed, or monitor)."""
    await injector.maybe_raise("schedule_drone_task")
    task = store.schedule_drone_task(drone_id, task_type, field_zone, scheduled_time)
    return task.model_dump()


@mcp.tool()
async def get_alerts(severity: str | None = None, limit: int = 10) -> list[dict]:
    """Get recent agricultural alerts, optionally filtered by severity."""
    fault = await injector.maybe_raise("get_alerts")
    alerts = store.get_alerts(severity=severity, limit=limit)
    results = [a.model_dump() for a in alerts]
    if fault == FaultType.PARTIAL_RESPONSE:
        return truncate_response(results)
    return results


if __name__ == "__main__":
    mcp.run(transport="stdio")
