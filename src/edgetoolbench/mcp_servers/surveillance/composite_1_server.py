"""Surveillance domain – Composite-1 MCP server (1 unified tool).

Run standalone:  python -m edgetoolbench.mcp_servers.surveillance.composite_1_server
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
from edgetoolbench.mcp_servers.surveillance._store import SurveillanceStore

mcp = FastMCP("surveillance-composite-1")
store = SurveillanceStore()
injector = FaultInjector(FaultConfig.from_env())


@mcp.tool()
async def surveillance(
    action: str,
    location: str | None = None,
    camera_id: str | None = None,
    sensor_id: str | None = None,
    point_id: str | None = None,
    zone_id: str | None = None,
    event_id: str | None = None,
    patrol_id: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    limit: int = 10,
    recording: bool | None = None,
    night_vision: bool | None = None,
    sensitivity: str | None = None,
    access_level: int | None = None,
    acknowledge: bool = False,
    response_actions: list[str] | None = None,
    name: str | None = None,
    route: list[str] | None = None,
    scheduled_time: str | None = None,
    assigned_guard: str | None = None,
) -> dict:
    """Unified surveillance interface. All read and write operations via a single tool.

    **Read actions:**
    - 'security_overview': Full overview. Optional: location.
    - 'cameras': List or get cameras. Optional: camera_id, location.
    - 'motion_sensors': List or get sensors. Optional: sensor_id, location.
    - 'access_points': List or get access points. Optional: point_id, location.
    - 'alarm_zones': List or get zones. Optional: zone_id.
    - 'events': Get security events. Optional: severity, limit.
    - 'patrols': List or get patrols. Optional: patrol_id, status.

    **Write actions:**
    - 'set_camera': Update camera. Requires: camera_id. Optional: status, recording, night_vision.
    - 'set_sensor': Update sensor. Requires: sensor_id. Optional: status, sensitivity.
    - 'lock_access': Lock access point. Requires: point_id. Optional: access_level.
    - 'unlock_access': Unlock access point. Requires: point_id. Optional: access_level.
    - 'arm_zone': Arm alarm zone. Requires: zone_id.
    - 'disarm_zone': Disarm alarm zone. Requires: zone_id.
    - 'handle_event': Handle security event. Requires: event_id. Optional: acknowledge, response_actions.
    - 'schedule_patrol': Schedule new patrol. Requires: name, route, scheduled_time. Optional: assigned_guard.
    - 'update_patrol': Update patrol. Requires: patrol_id. Optional: status, assigned_guard.

    Args:
        action: The action to perform (see above).
        location: Location filter.
        camera_id: Camera ID.
        sensor_id: Motion sensor ID.
        point_id: Access point ID.
        zone_id: Alarm zone ID.
        event_id: Security event ID.
        patrol_id: Patrol ID.
        severity: Event severity filter.
        status: Status value/filter.
        limit: Max event entries (default 10).
        recording: Camera recording flag.
        night_vision: Camera night vision flag.
        sensitivity: Sensor sensitivity level.
        access_level: Access level (1-5).
        acknowledge: Whether to acknowledge event.
        response_actions: Response actions for event handling.
        name: Patrol name.
        route: Patrol route checkpoints.
        scheduled_time: Patrol scheduled time.
        assigned_guard: Guard assignment.
    """
    fault = await injector.maybe_raise(action)

    # ── Read actions ──────────────────────────────────────────────────────
    if action == "security_overview":
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

    elif action == "cameras":
        if camera_id:
            cam = store.get_camera(camera_id)
            if not cam:
                return {"error": f"Camera '{camera_id}' not found."}
            result = {"camera": cam.model_dump()}
            if fault == FaultType.CONTRADICTORY:
                result["camera"]["status"] = "idle" if cam.status == "recording" else "recording"
            return result
        cameras = store.list_cameras(location)
        results = [c.model_dump() for c in cameras]
        if fault == FaultType.PARTIAL_RESPONSE:
            return {"cameras": truncate_response(results)}
        return {"cameras": results}

    elif action == "motion_sensors":
        if sensor_id:
            sensor = store.get_motion_sensor(sensor_id)
            if not sensor:
                return {"error": f"Motion sensor '{sensor_id}' not found."}
            result = {"motion_sensor": sensor.model_dump()}
            if fault == FaultType.CONTRADICTORY:
                result["motion_sensor"] = corrupt_numeric_field(
                    result["motion_sensor"], "battery_level"
                )
            return result
        sensors = store.list_motion_sensors(location)
        results = [s.model_dump() for s in sensors]
        if fault == FaultType.PARTIAL_RESPONSE:
            return {"motion_sensors": truncate_response(results)}
        if fault == FaultType.CONTRADICTORY:
            return {"motion_sensors": [corrupt_numeric_field(r, "battery_level") for r in results]}
        return {"motion_sensors": results}

    elif action == "access_points":
        if point_id:
            point = store.get_access_point(point_id)
            if not point:
                return {"error": f"Access point '{point_id}' not found."}
            result = {"access_point": point.model_dump()}
            if fault == FaultType.CONTRADICTORY:
                result["access_point"]["status"] = (
                    "unlocked" if point.status == "locked" else "locked"
                )
            return result
        points = store.list_access_points(location)
        results = [a.model_dump() for a in points]
        if fault == FaultType.PARTIAL_RESPONSE:
            return {"access_points": truncate_response(results)}
        return {"access_points": results}

    elif action == "alarm_zones":
        if zone_id:
            zone = store.get_alarm_zone(zone_id)
            if not zone:
                return {"error": f"Alarm zone '{zone_id}' not found."}
            result = {"alarm_zone": zone.model_dump()}
            if fault == FaultType.CONTRADICTORY:
                result["alarm_zone"]["status"] = "disarmed" if zone.status == "armed" else "armed"
            return result
        zones = store.list_alarm_zones()
        results = [z.model_dump() for z in zones]
        if fault == FaultType.PARTIAL_RESPONSE:
            return {"alarm_zones": truncate_response(results)}
        return {"alarm_zones": results}

    elif action == "events":
        events = store.get_events(severity=severity, limit=limit)
        results = [e.model_dump() for e in events]
        if fault == FaultType.PARTIAL_RESPONSE:
            return {"events": truncate_response(results)}
        return {"events": results}

    elif action == "patrols":
        if patrol_id:
            patrol = store.get_patrol(patrol_id)
            if not patrol:
                return {"error": f"Patrol '{patrol_id}' not found."}
            return {"patrol": patrol.model_dump()}
        patrols = store.list_patrols(status)
        results = [p.model_dump() for p in patrols]
        if fault == FaultType.PARTIAL_RESPONSE:
            return {"patrols": truncate_response(results)}
        return {"patrols": results}

    # ── Write actions ─────────────────────────────────────────────────────
    elif action == "set_camera":
        if not camera_id:
            return {"error": "set_camera requires 'camera_id'."}
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
            return {"error": f"Motion sensor '{sensor_id}' not found."}
        return {"action": "set_sensor", "sensor": sensor.model_dump()}

    elif action == "lock_access":
        if not point_id:
            return {"error": "lock_access requires 'point_id'."}
        kwargs: dict = {"status": "locked"}
        if access_level is not None:
            kwargs["access_level"] = access_level
        point = store.set_access_point(point_id, **kwargs)
        if not point:
            return {"error": f"Access point '{point_id}' not found."}
        return {"action": "lock_access", "access_point": point.model_dump()}

    elif action == "unlock_access":
        if not point_id:
            return {"error": "unlock_access requires 'point_id'."}
        kwargs = {"status": "unlocked"}
        if access_level is not None:
            kwargs["access_level"] = access_level
        point = store.set_access_point(point_id, **kwargs)
        if not point:
            return {"error": f"Access point '{point_id}' not found."}
        return {"action": "unlock_access", "access_point": point.model_dump()}

    elif action == "arm_zone":
        if not zone_id:
            return {"error": "arm_zone requires 'zone_id'."}
        zone = store.set_alarm_zone(zone_id, status="armed")
        if not zone:
            return {"error": f"Alarm zone '{zone_id}' not found."}
        return {"action": "arm_zone", "alarm_zone": zone.model_dump()}

    elif action == "disarm_zone":
        if not zone_id:
            return {"error": "disarm_zone requires 'zone_id'."}
        zone = store.set_alarm_zone(zone_id, status="disarmed")
        if not zone:
            return {"error": f"Alarm zone '{zone_id}' not found."}
        return {"action": "disarm_zone", "alarm_zone": zone.model_dump()}

    elif action == "handle_event":
        if not event_id:
            return {"error": "handle_event requires 'event_id'."}
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
                    actions_taken.append(
                        {"action": "lockdown", "point": ap.name, "status": "locked"}
                    )
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
            "error": f"Unknown action '{action}'. Supported: security_overview, cameras, "
            "motion_sensors, access_points, alarm_zones, events, patrols, set_camera, "
            "set_sensor, lock_access, unlock_access, arm_zone, disarm_zone, handle_event, "
            "schedule_patrol, update_patrol."
        }


if __name__ == "__main__":
    mcp.run(transport="stdio")
