"""Agriculture domain – Composite-2 MCP server (2 tools: query + control).

Run standalone:  python -m mcp_granite.mcp_servers.agriculture.composite_2_server
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_granite.mcp_servers._base import (
    FaultConfig,
    FaultInjector,
    FaultType,
    corrupt_numeric_field,
)
from mcp_granite.mcp_servers.agriculture._store import AgricultureStore

mcp = FastMCP("agriculture-composite-2")
store = AgricultureStore()
injector = FaultInjector(FaultConfig.from_env())


@mcp.tool()
async def agriculture_query(
    action: str,
    field_zone: str | None = None,
    sensor_id: str | None = None,
    zone_id: str | None = None,
    crop_id: str | None = None,
    station_id: str | None = None,
    task_id: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    limit: int = 10,
) -> dict:
    """Read-only queries for the agriculture domain.

    Args:
        action: One of 'field_overview', 'sensor_reading', 'irrigation_status',
                'crop_status', 'weather', 'drone_tasks', 'alerts'.
        field_zone: Field zone filter.
        sensor_id: Sensor ID (for 'sensor_reading').
        zone_id: Irrigation zone ID (for 'irrigation_status').
        crop_id: Crop ID (for 'crop_status').
        station_id: Weather station ID (for 'weather').
        task_id: Drone task ID (for 'drone_tasks').
        severity: Alert severity filter (for 'alerts').
        status: Drone task status filter (for 'drone_tasks').
        limit: Max alert entries (default 10).
    """
    fault = await injector.maybe_raise(action)

    if action == "field_overview":
        if not field_zone:
            return {"error": "field_overview requires 'field_zone'."}
        sensors = store.list_sensors(field_zone)
        irrigation = store.list_irrigation_zones(field_zone)
        crops = store.list_crops(field_zone)
        weather = store.list_weather_stations()
        moisture = [s.value for s in sensors if s.sensor_type == "soil_moisture"]
        avg_moisture = round(sum(moisture) / len(moisture), 1) if moisture else None
        result: dict[str, Any] = {
            "field_zone": field_zone,
            "sensors": [s.model_dump() for s in sensors],
            "irrigation_zones": [z.model_dump() for z in irrigation],
            "crops": [c.model_dump() for c in crops],
            "weather": [w.model_dump() for w in weather],
            "summary": {
                "avg_soil_moisture": avg_moisture,
                "active_irrigation": sum(1 for z in irrigation if z.status == "active"),
                "crop_health": {c.name: c.health_status for c in crops},
            },
        }
        if fault == FaultType.PARTIAL_RESPONSE:
            result.pop("sensors", None)
        elif fault == FaultType.CONTRADICTORY and avg_moisture is not None:
            result["summary"]["avg_soil_moisture"] = round(avg_moisture * 0.1, 1)
        return result

    elif action == "sensor_reading":
        if not sensor_id:
            return {"error": "sensor_reading requires 'sensor_id'."}
        sensor = store.read_sensor(sensor_id)
        if not sensor:
            return {"error": f"Sensor '{sensor_id}' not found."}
        result = {"sensor": sensor.model_dump()}
        if fault == FaultType.CONTRADICTORY:
            result["sensor"] = corrupt_numeric_field(result["sensor"], "value")
        return result

    elif action == "irrigation_status":
        if zone_id:
            zone = store.get_irrigation_zone(zone_id)
            if not zone:
                return {"error": f"Irrigation zone '{zone_id}' not found."}
            result = {"zone": zone.model_dump()}
            if fault == FaultType.CONTRADICTORY:
                result["zone"] = corrupt_numeric_field(result["zone"], "flow_rate")
            return result
        zones = store.list_irrigation_zones(field_zone)
        result = {"zones": [z.model_dump() for z in zones]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["zones"] = result["zones"][:1]
        return result

    elif action == "crop_status":
        if crop_id:
            crop = store.get_crop(crop_id)
            if not crop:
                return {"error": f"Crop '{crop_id}' not found."}
            return {"crop": crop.model_dump()}
        crops = store.list_crops(field_zone)
        result = {"crops": [c.model_dump() for c in crops]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["crops"] = result["crops"][:1]
        return result

    elif action == "weather":
        if station_id:
            station = store.get_weather_station(station_id)
            if not station:
                return {"error": f"Weather station '{station_id}' not found."}
            result = {"station": station.model_dump()}
            if fault == FaultType.CONTRADICTORY:
                result["station"] = corrupt_numeric_field(result["station"], "temperature")
            return result
        stations = store.list_weather_stations()
        result = {"stations": [s.model_dump() for s in stations]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["stations"] = result["stations"][:1]
        return result

    elif action == "drone_tasks":
        if task_id:
            task = store.get_drone_task(task_id)
            if not task:
                return {"error": f"Drone task '{task_id}' not found."}
            return {"task": task.model_dump()}
        tasks = store.list_drone_tasks(status)
        result = {"tasks": [t.model_dump() for t in tasks]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["tasks"] = result["tasks"][:1]
        return result

    elif action == "alerts":
        alerts = store.get_alerts(severity=severity, limit=limit)
        result = {"alerts": [a.model_dump() for a in alerts]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["alerts"] = result["alerts"][:1]
        return result

    else:
        return {
            "error": f"Unknown action '{action}'. Supported: field_overview, sensor_reading, "
            "irrigation_status, crop_status, weather, drone_tasks, alerts."
        }


@mcp.tool()
async def agriculture_control(
    action: str,
    zone_id: str | None = None,
    status: str | None = None,
    flow_rate: float | None = None,
    schedule: dict | None = None,
    alert_id: str | None = None,
    acknowledge: bool = False,
    corrective_actions: list[str] | None = None,
    drone_id: str | None = None,
    task_type: str | None = None,
    field_zone: str | None = None,
    scheduled_time: str | None = None,
    crop_id: str | None = None,
    health_status: str | None = None,
    growth_stage: str | None = None,
) -> dict:
    """Write/actuate changes in the agriculture domain.

    Args:
        action: One of 'set_irrigation', 'handle_alert', 'schedule_drone', 'update_crop'.
        zone_id: Irrigation zone ID (for 'set_irrigation').
        status: New status (for 'set_irrigation').
        flow_rate: New flow rate (for 'set_irrigation').
        schedule: New schedule dict (for 'set_irrigation').
        alert_id: Alert ID (for 'handle_alert').
        acknowledge: Whether to acknowledge alert (for 'handle_alert').
        corrective_actions: Actions to take (for 'handle_alert').
        drone_id: Drone ID (for 'schedule_drone').
        task_type: Task type (for 'schedule_drone').
        field_zone: Target field zone (for 'schedule_drone').
        scheduled_time: ISO datetime (for 'schedule_drone').
        crop_id: Crop ID (for 'update_crop').
        health_status: New health status (for 'update_crop').
        growth_stage: New growth stage (for 'update_crop').
    """
    fault = await injector.maybe_raise(action)

    if action == "set_irrigation":
        if not zone_id:
            return {"error": "set_irrigation requires 'zone_id'."}
        kwargs: dict[str, Any] = {}
        if status is not None:
            kwargs["status"] = status
        if flow_rate is not None:
            kwargs["flow_rate"] = flow_rate
        if schedule is not None:
            kwargs["schedule"] = schedule
        zone = store.set_irrigation_zone(zone_id, **kwargs)
        if not zone:
            return {"error": f"Irrigation zone '{zone_id}' not found."}
        result = {"action": "set_irrigation", "zone": zone.model_dump()}
        if fault == FaultType.PARTIAL_RESPONSE:
            result.pop("zone", None)
        return result

    elif action == "handle_alert":
        if not alert_id:
            return {"error": "handle_alert requires 'alert_id'."}
        alert = store.acknowledge_alert(alert_id) if acknowledge else None
        if not alert:
            for a in store.alert_log:
                if a.alert_id == alert_id:
                    alert = a
                    break
        if not alert:
            return {"error": f"Alert '{alert_id}' not found."}

        actions_taken: list[dict] = []
        for act in corrective_actions or []:
            if act == "increase_irrigation":
                zones = store.list_irrigation_zones()
                for z in zones:
                    if z.status == "idle":
                        store.set_irrigation_zone(z.zone_id, status="active")
                        actions_taken.append(
                            {"action": "increase_irrigation", "zone": z.name, "status": "activated"}
                        )
            elif act == "schedule_spray":
                task = store.schedule_drone_task(
                    "DRONE-B", "spray", "west field", "2025-06-01T10:00:00"
                )
                actions_taken.append({"action": "schedule_spray", "task": task.model_dump()})
            elif act == "disable_zone":
                if alert.source_id.startswith("IZ"):
                    store.set_irrigation_zone(alert.source_id, status="idle")
                    actions_taken.append(
                        {"action": "disable_zone", "zone_id": alert.source_id, "status": "disabled"}
                    )
            elif act == "notify_operator":
                actions_taken.append({"action": "notify_operator", "status": "notification_sent"})
            else:
                actions_taken.append({"action": act, "status": "unknown_action"})

        result = {
            "alert": alert.model_dump(),
            "acknowledged": alert.acknowledged,
            "actions_taken": actions_taken,
        }
        if fault == FaultType.PARTIAL_RESPONSE:
            result.pop("actions_taken", None)
        return result

    elif action == "schedule_drone":
        if not all([drone_id, task_type, field_zone, scheduled_time]):
            return {
                "error": "schedule_drone requires drone_id, task_type, field_zone, scheduled_time."
            }
        task = store.schedule_drone_task(drone_id, task_type, field_zone, scheduled_time)
        result = {"action": "schedule_drone", "task": task.model_dump()}
        if fault == FaultType.PARTIAL_RESPONSE:
            result.pop("task", None)
        return result

    elif action == "update_crop":
        if not crop_id:
            return {"error": "update_crop requires 'crop_id'."}
        kwargs = {}
        if health_status is not None:
            kwargs["health_status"] = health_status
        if growth_stage is not None:
            kwargs["growth_stage"] = growth_stage
        crop = store.update_crop(crop_id, **kwargs)
        if not crop:
            return {"error": f"Crop '{crop_id}' not found."}
        return {"action": "update_crop", "crop": crop.model_dump()}

    else:
        return {
            "error": f"Unknown action '{action}'. Supported: set_irrigation, handle_alert, "
            "schedule_drone, update_crop."
        }


if __name__ == "__main__":
    mcp.run(transport="stdio")
