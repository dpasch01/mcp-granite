"""Agriculture domain – Composite-4 MCP server (4 high-level tools).

Run standalone:  python -m mcp_granite.mcp_servers.agriculture.composite_4_server
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_granite.mcp_servers._base import (
    FaultConfig,
    FaultInjector,
    FaultType,
    corrupt_numeric_field,
)
from mcp_granite.mcp_servers.agriculture._store import AgricultureStore

mcp = FastMCP("agriculture-composite-4")
store = AgricultureStore()
injector = FaultInjector(FaultConfig.from_env())


@mcp.tool()
async def get_field_overview(field_zone: str) -> dict:
    """Get a complete overview of a field zone including sensors, irrigation, crops, and weather.

    Args:
        field_zone: The field zone name (e.g. 'north field', 'south field', 'greenhouse').

    Returns a dict with sensors, irrigation zones, crops, weather data, and a summary.
    """
    fault = await injector.maybe_raise("get_field_overview")

    sensors = store.list_sensors(field_zone)
    irrigation = store.list_irrigation_zones(field_zone)
    crops = store.list_crops(field_zone)
    weather = store.list_weather_stations()

    moisture_readings = [s.value for s in sensors if s.sensor_type == "soil_moisture"]
    avg_moisture = (
        round(sum(moisture_readings) / len(moisture_readings), 1) if moisture_readings else None
    )
    temp_readings = [s.value for s in sensors if s.sensor_type == "temperature"]
    avg_temp = round(sum(temp_readings) / len(temp_readings), 1) if temp_readings else None

    result = {
        "field_zone": field_zone,
        "sensors": [s.model_dump() for s in sensors],
        "irrigation_zones": [z.model_dump() for z in irrigation],
        "crops": [c.model_dump() for c in crops],
        "weather": [w.model_dump() for w in weather],
        "summary": {
            "avg_soil_moisture": avg_moisture,
            "avg_temperature": avg_temp,
            "active_irrigation": sum(1 for z in irrigation if z.status == "active"),
            "total_irrigation_zones": len(irrigation),
            "crop_health": {c.name: c.health_status for c in crops},
            "total_sensors": len(sensors),
        },
    }

    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("sensors", None)
        result.pop("irrigation_zones", None)
    elif fault == FaultType.CONTRADICTORY:
        if result["summary"]["avg_soil_moisture"] is not None:
            result["summary"]["avg_soil_moisture"] = round(
                result["summary"]["avg_soil_moisture"] * 0.1, 1
            )

    return result


@mcp.tool()
async def manage_irrigation(
    action: str,
    zone_id: str | None = None,
    status: str | None = None,
    flow_rate: float | None = None,
    schedule: dict | None = None,
    field_zone: str | None = None,
) -> dict:
    """Manage irrigation zones — view, activate, deactivate, or adjust settings.

    Args:
        action: One of 'status', 'activate', 'deactivate', 'adjust'.
        zone_id: Irrigation zone ID (required for activate/deactivate/adjust, optional for status).
        status: New status value (for 'adjust').
        flow_rate: New flow rate (for 'adjust').
        schedule: New schedule dict (for 'adjust').
        field_zone: Filter by field zone (for 'status' without zone_id).
    """
    fault = await injector.maybe_raise("manage_irrigation")

    if action == "status":
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

    elif action == "activate":
        if not zone_id:
            return {"error": "activate requires 'zone_id'."}
        zone = store.set_irrigation_zone(zone_id, status="active")
        if not zone:
            return {"error": f"Irrigation zone '{zone_id}' not found."}
        return {"action": "activate", "zone": zone.model_dump()}

    elif action == "deactivate":
        if not zone_id:
            return {"error": "deactivate requires 'zone_id'."}
        zone = store.set_irrigation_zone(zone_id, status="idle")
        if not zone:
            return {"error": f"Irrigation zone '{zone_id}' not found."}
        return {"action": "deactivate", "zone": zone.model_dump()}

    elif action == "adjust":
        if not zone_id:
            return {"error": "adjust requires 'zone_id'."}
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
        result = {"action": "adjust", "zone": zone.model_dump()}
        if fault == FaultType.PARTIAL_RESPONSE:
            result.pop("zone", None)
        return result

    else:
        return {
            "error": f"Unknown action '{action}'. Supported: status, activate, deactivate, adjust."
        }


@mcp.tool()
async def handle_farm_alert(
    alert_id: str | None = None,
    severity: str | None = None,
    acknowledge: bool = False,
    corrective_actions: list[str] | None = None,
) -> dict:
    """View, acknowledge, and respond to farm alerts.

    Args:
        alert_id: Specific alert to handle (optional).
        severity: Filter alerts by severity (optional).
        acknowledge: Whether to acknowledge the alert.
        corrective_actions: List of corrective actions: 'increase_irrigation',
                           'schedule_spray', 'disable_zone', 'notify_operator'.
    """
    fault = await injector.maybe_raise("handle_farm_alert")

    if not alert_id:
        alerts = store.get_alerts(severity=severity)
        result = {"alerts": [a.model_dump() for a in alerts]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["alerts"] = result["alerts"][:1]
        return result

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


@mcp.tool()
async def schedule_farm_operation(
    operation: str,
    drone_id: str | None = None,
    task_type: str | None = None,
    field_zone: str | None = None,
    scheduled_time: str | None = None,
    crop_id: str | None = None,
    health_status: str | None = None,
    growth_stage: str | None = None,
) -> dict:
    """Schedule drone tasks or update crop status.

    Args:
        operation: One of 'schedule_drone', 'update_crop', 'list_drone_tasks'.
        drone_id: Drone ID (for 'schedule_drone').
        task_type: Task type: survey, spray, seed, monitor (for 'schedule_drone').
        field_zone: Target field zone (for 'schedule_drone').
        scheduled_time: ISO datetime string (for 'schedule_drone').
        crop_id: Crop ID (for 'update_crop').
        health_status: New health status (for 'update_crop').
        growth_stage: New growth stage (for 'update_crop').
    """
    fault = await injector.maybe_raise("schedule_farm_operation")

    if operation == "schedule_drone":
        if not all([drone_id, task_type, field_zone, scheduled_time]):
            return {
                "error": "schedule_drone requires drone_id, task_type, field_zone, scheduled_time."
            }
        task = store.schedule_drone_task(drone_id, task_type, field_zone, scheduled_time)
        result = {"operation": "schedule_drone", "task": task.model_dump()}
        if fault == FaultType.PARTIAL_RESPONSE:
            result.pop("task", None)
        return result

    elif operation == "update_crop":
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
        return {"operation": "update_crop", "crop": crop.model_dump()}

    elif operation == "list_drone_tasks":
        tasks = store.list_drone_tasks()
        result = {"tasks": [t.model_dump() for t in tasks]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["tasks"] = result["tasks"][:1]
        return result

    else:
        return {
            "error": f"Unknown operation '{operation}'. Supported: schedule_drone, update_crop, list_drone_tasks."
        }


if __name__ == "__main__":
    mcp.run(transport="stdio")
