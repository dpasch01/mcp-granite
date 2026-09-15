"""Surveillance domain – Composite-4 MCP server (4 high-level tools).

Run standalone:  python -m edgetoolbench.mcp_servers.surveillance.composite_4_server
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from edgetoolbench.mcp_servers._base import (
    FaultConfig,
    FaultInjector,
    FaultType,
)
from edgetoolbench.mcp_servers.surveillance._store import SurveillanceStore

mcp = FastMCP("surveillance-composite-4")
store = SurveillanceStore()
injector = FaultInjector(FaultConfig.from_env())


@mcp.tool()
async def get_security_overview(location: str | None = None) -> dict:
    """Get a complete security overview including cameras, sensors, access points, and alarm zones.

    Args:
        location: Optional location filter.
    """
    fault = await injector.maybe_raise("get_security_overview")
    cameras = store.list_cameras(location)
    sensors = store.list_motion_sensors(location)
    access = store.list_access_points(location)
    zones = store.list_alarm_zones()
    events = store.get_events(limit=5)
    result = {
        "cameras": [c.model_dump() for c in cameras],
        "motion_sensors": [s.model_dump() for s in sensors],
        "access_points": [a.model_dump() for a in access],
        "alarm_zones": [z.model_dump() for z in zones],
        "recent_events": [e.model_dump() for e in events],
        "summary": {
            "cameras_recording": sum(1 for c in cameras if c.recording),
            "sensors_armed": sum(1 for s in sensors if s.status == "armed"),
            "sensors_triggered": sum(1 for s in sensors if s.status == "triggered"),
            "access_locked": sum(1 for a in access if a.status == "locked"),
            "zones_armed": sum(1 for z in zones if z.status == "armed"),
        },
    }
    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("cameras", None)
        result.pop("access_points", None)
    return result


@mcp.tool()
async def manage_access_control(
    action: str,
    point_id: str | None = None,
    location: str | None = None,
    status: str | None = None,
    access_level: int | None = None,
    zone_id: str | None = None,
) -> dict:
    """Manage access points and alarm zones.

    Args:
        action: One of 'list_access', 'lock', 'unlock', 'set_access_level',
                'arm_zone', 'disarm_zone', 'list_zones'.
        point_id: Access point ID.
        location: Location filter.
        status: Status value.
        access_level: Access level (1-5).
        zone_id: Alarm zone ID.
    """
    fault = await injector.maybe_raise("manage_access_control")

    if action == "list_access":
        points = store.list_access_points(location)
        result = {"access_points": [a.model_dump() for a in points]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["access_points"] = result["access_points"][:1]
        return result
    elif action in ("lock", "unlock"):
        if not point_id:
            return {"error": f"{action} requires 'point_id'."}
        point = store.set_access_point(
            point_id, status="locked" if action == "lock" else "unlocked"
        )
        if not point:
            return {"error": f"Access point '{point_id}' not found."}
        return {"action": action, "access_point": point.model_dump()}
    elif action == "set_access_level":
        if not point_id or access_level is None:
            return {"error": "set_access_level requires 'point_id' and 'access_level'."}
        point = store.set_access_point(point_id, access_level=access_level)
        if not point:
            return {"error": f"Access point '{point_id}' not found."}
        return {"action": "set_access_level", "access_point": point.model_dump()}
    elif action in ("arm_zone", "disarm_zone"):
        if not zone_id:
            return {"error": f"{action} requires 'zone_id'."}
        zone = store.set_alarm_zone(zone_id, status="armed" if action == "arm_zone" else "disarmed")
        if not zone:
            return {"error": f"Alarm zone '{zone_id}' not found."}
        return {"action": action, "alarm_zone": zone.model_dump()}
    elif action == "list_zones":
        zones = store.list_alarm_zones()
        return {"alarm_zones": [z.model_dump() for z in zones]}
    else:
        return {
            "error": f"Unknown action '{action}'. Supported: list_access, lock, unlock, set_access_level, arm_zone, disarm_zone, list_zones."
        }


@mcp.tool()
async def handle_security_alert(
    event_id: str | None = None,
    severity: str | None = None,
    acknowledge: bool = False,
    response_actions: list[str] | None = None,
) -> dict:
    """View, acknowledge, and respond to security events.

    Args:
        event_id: Specific event to handle.
        severity: Filter by severity.
        acknowledge: Whether to acknowledge the event.
        response_actions: Actions to take: 'lockdown', 'enable_cameras',
                         'arm_all_zones', 'dispatch_patrol', 'sound_alarm'.
    """
    fault = await injector.maybe_raise("handle_security_alert")

    if not event_id:
        events = store.get_events(severity=severity)
        result = {"events": [e.model_dump() for e in events]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["events"] = result["events"][:1]
        return result

    event = store.acknowledge_event(event_id) if acknowledge else None
    if not event:
        for e in store.events:
            if e.event_id == event_id:
                event = e
                break
    if not event:
        return {"error": f"Event '{event_id}' not found."}

    actions_taken: list[dict] = []
    for act in response_actions or []:
        if act == "lockdown":
            for ap in store.list_access_points():
                store.set_access_point(ap.point_id, status="locked")
                actions_taken.append({"action": "lockdown", "point": ap.name, "status": "locked"})
        elif act == "enable_cameras":
            for cam in store.list_cameras():
                store.set_camera(cam.camera_id, status="recording", recording=True)
                actions_taken.append(
                    {"action": "enable_cameras", "camera": cam.name, "status": "recording"}
                )
        elif act == "arm_all_zones":
            for zone in store.list_alarm_zones():
                store.set_alarm_zone(zone.zone_id, status="armed")
                actions_taken.append(
                    {"action": "arm_all_zones", "zone": zone.name, "status": "armed"}
                )
        elif act == "dispatch_patrol":
            patrol = store.schedule_patrol(
                "Emergency Response",
                ["main entrance", "parking lot", "north fence"],
                "2025-06-01T09:00:00",
                "Guard C",
            )
            actions_taken.append({"action": "dispatch_patrol", "patrol": patrol.model_dump()})
        elif act == "sound_alarm":
            actions_taken.append({"action": "sound_alarm", "status": "alarm_activated"})
        else:
            actions_taken.append({"action": act, "status": "unknown_action"})

    result = {
        "event": event.model_dump(),
        "acknowledged": event.acknowledged,
        "actions_taken": actions_taken,
    }
    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("actions_taken", None)
    return result


@mcp.tool()
async def manage_surveillance_ops(
    action: str,
    camera_id: str | None = None,
    sensor_id: str | None = None,
    patrol_id: str | None = None,
    status: str | None = None,
    recording: bool | None = None,
    sensitivity: str | None = None,
    name: str | None = None,
    route: list[str] | None = None,
    scheduled_time: str | None = None,
    assigned_guard: str | None = None,
    location: str | None = None,
) -> dict:
    """Manage cameras, sensors, and patrols.

    Args:
        action: One of 'set_camera', 'set_sensor', 'list_patrols',
                'schedule_patrol', 'update_patrol'.
    """
    fault = await injector.maybe_raise("manage_surveillance_ops")

    if action == "set_camera":
        if not camera_id:
            return {"error": "set_camera requires 'camera_id'."}
        kwargs = {}
        if status is not None:
            kwargs["status"] = status
        if recording is not None:
            kwargs["recording"] = recording
        cam = store.set_camera(camera_id, **kwargs)
        if not cam:
            return {"error": f"Camera '{camera_id}' not found."}
        return {"action": "set_camera", "camera": cam.model_dump()}
    elif action == "set_sensor":
        if not sensor_id:
            return {"error": "set_sensor requires 'sensor_id'."}
        kwargs = {}
        if status is not None:
            kwargs["status"] = status
        if sensitivity is not None:
            kwargs["sensitivity"] = sensitivity
        sensor = store.set_motion_sensor(sensor_id, **kwargs)
        if not sensor:
            return {"error": f"Sensor '{sensor_id}' not found."}
        return {"action": "set_sensor", "sensor": sensor.model_dump()}
    elif action == "list_patrols":
        patrols = store.list_patrols(status)
        result = {"patrols": [p.model_dump() for p in patrols]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["patrols"] = result["patrols"][:1]
        return result
    elif action == "schedule_patrol":
        if not name or not route or not scheduled_time:
            return {"error": "schedule_patrol requires 'name', 'route', and 'scheduled_time'."}
        patrol = store.schedule_patrol(name, route, scheduled_time, assigned_guard)
        return {"action": "schedule_patrol", "patrol": patrol.model_dump()}
    elif action == "update_patrol":
        if not patrol_id:
            return {"error": "update_patrol requires 'patrol_id'."}
        kwargs = {}
        if status is not None:
            kwargs["status"] = status
        if assigned_guard is not None:
            kwargs["assigned_guard"] = assigned_guard
        patrol = store.update_patrol(patrol_id, **kwargs)
        if not patrol:
            return {"error": f"Patrol '{patrol_id}' not found."}
        return {"action": "update_patrol", "patrol": patrol.model_dump()}
    else:
        return {
            "error": f"Unknown action '{action}'. Supported: set_camera, set_sensor, list_patrols, schedule_patrol, update_patrol."
        }


if __name__ == "__main__":
    mcp.run(transport="stdio")
