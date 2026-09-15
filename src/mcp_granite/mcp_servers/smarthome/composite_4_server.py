"""Smart Home domain – Composite MCP server (4 high-level tools).

Run standalone:  python -m mcp_granite.mcp_servers.smarthome.composite_4_server
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_granite.mcp_servers._base import (
    FaultConfig,
    FaultInjector,
    FaultType,
    corrupt_numeric_field,
)
from mcp_granite.mcp_servers.smarthome._store import SmartHomeStore

mcp = FastMCP("smarthome-composite")
store = SmartHomeStore()
injector = FaultInjector(FaultConfig.from_env())


@mcp.tool()
async def get_room_status(location: str) -> dict:
    """Get a complete status overview of a room including all sensors and devices.

    Args:
        location: The room/area name (e.g. 'living room', 'bedroom', 'kitchen').

    Returns a dict with location, sensors list, devices list, and a summary
    with computed values like average temperature and motion detection status.
    """
    fault = await injector.maybe_raise("get_room_status")

    sensors = store.list_sensors(location)
    devices = store.list_devices(location)

    # Build summary from sensor data
    temps = [s.value for s in sensors if s.sensor_type == "temperature"]
    avg_temp = round(sum(temps) / len(temps), 1) if temps else None
    any_motion = any(s.value > 0 for s in sensors if s.sensor_type == "motion")
    humidity_readings = [s.value for s in sensors if s.sensor_type == "humidity"]
    avg_humidity = round(sum(humidity_readings) / len(humidity_readings), 1) if humidity_readings else None
    light_readings = [s.value for s in sensors if s.sensor_type == "light"]
    avg_light = round(sum(light_readings) / len(light_readings), 1) if light_readings else None

    result = {
        "location": location,
        "sensors": [s.model_dump() for s in sensors],
        "devices": [d.model_dump() for d in devices],
        "summary": {
            "avg_temp": avg_temp,
            "any_motion": any_motion,
            "avg_humidity": avg_humidity,
            "avg_light": avg_light,
            "active_devices": sum(1 for d in devices if d.status == "on"),
            "total_devices": len(devices),
            "total_sensors": len(sensors),
        },
    }

    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("sensors", None)
        result.pop("devices", None)
    elif fault == FaultType.CONTRADICTORY:
        if result["summary"]["avg_temp"] is not None:
            result["summary"]["avg_temp"] = round(result["summary"]["avg_temp"] * 0.1, 1)

    return result


@mcp.tool()
async def set_room_mode(
    location: str, mode: str, custom_settings: dict | None = None
) -> dict:
    """Apply a preset mode to all devices in a room.

    Args:
        location: The room/area name.
        mode: One of 'night' (lights dim/off, thermostat low), 'away' (all off,
              lock doors), 'movie' (lights dim, blinds close).
        custom_settings: Optional overrides for the mode defaults.

    Returns a dict with the location, mode applied, and list of changes made.
    """
    fault = await injector.maybe_raise("set_room_mode")
    custom = custom_settings or {}
    devices = store.list_devices(location)
    # Also apply to related areas (e.g. whole-house modes affect all devices)
    all_devices = store.list_devices()

    changes: list[dict] = []

    if mode == "night":
        for device in devices:
            if device.device_type == "light":
                brightness = custom.get("brightness", 5)
                store.set_device(device.device_id, {"status": "on", "brightness": brightness})
                changes.append({"device": device.name, "action": "dimmed", "brightness": brightness})
            elif device.device_type == "thermostat":
                target = custom.get("target_temp", 18)
                store.set_device(device.device_id, {"target_temp": target, "mode": "night"})
                changes.append({"device": device.name, "action": "set_temp", "target_temp": target})
            elif device.device_type == "blinds":
                store.set_device(device.device_id, {"status": "off", "position": 0})
                changes.append({"device": device.name, "action": "closed"})
        # Lock all locks in the house for night mode
        for device in all_devices:
            if device.device_type == "lock":
                store.set_device(device.device_id, {"status": "on", "locked": True})
                changes.append({"device": device.name, "action": "locked"})

    elif mode == "away":
        for device in all_devices:
            if device.device_type == "lock":
                store.set_device(device.device_id, {"status": "on", "locked": True})
                changes.append({"device": device.name, "action": "locked"})
            elif device.device_type == "camera":
                store.set_device(device.device_id, {"status": "on", "recording": True})
                changes.append({"device": device.name, "action": "recording_enabled"})
            elif device.device_type in ("light", "speaker"):
                store.set_device(device.device_id, {"status": "off"})
                changes.append({"device": device.name, "action": "turned_off"})
            elif device.device_type == "thermostat":
                target = custom.get("target_temp", 16)
                store.set_device(device.device_id, {"target_temp": target, "mode": "away"})
                changes.append({"device": device.name, "action": "set_temp", "target_temp": target})

    elif mode == "movie":
        for device in devices:
            if device.device_type == "light":
                brightness = custom.get("brightness", 15)
                store.set_device(device.device_id, {"status": "on", "brightness": brightness})
                changes.append({"device": device.name, "action": "dimmed", "brightness": brightness})
            elif device.device_type == "blinds":
                store.set_device(device.device_id, {"status": "off", "position": 0})
                changes.append({"device": device.name, "action": "closed"})
            elif device.device_type == "speaker":
                store.set_device(device.device_id, {"status": "on", "volume": custom.get("volume", 50)})
                changes.append({"device": device.name, "action": "turned_on"})

    else:
        return {"error": f"Unknown mode '{mode}'. Supported modes: night, away, movie."}

    result = {
        "location": location,
        "mode": mode,
        "changes": changes,
        "total_changes": len(changes),
    }

    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("changes", None)

    return result


@mcp.tool()
async def handle_alert(
    sensor_id: str, actions: list[str] | None = None
) -> dict:
    """Read an alerting sensor and take corrective actions.

    Args:
        sensor_id: The sensor that triggered the alert.
        actions: Optional list of corrective actions to take. Supported:
                 'lights_on', 'unlock_doors', 'lock_doors', 'start_camera',
                 'sound_alarm'.

    Returns a dict with the alert sensor data, actions taken, and event log
    entries created during handling.
    """
    fault = await injector.maybe_raise("handle_alert")

    sensor = store.read_sensor(sensor_id)
    if not sensor:
        return {"error": f"Sensor '{sensor_id}' not found."}

    sensor_data = sensor.model_dump()
    requested_actions = actions or []
    actions_taken: list[dict] = []
    events: list[dict] = []

    # Log the alert event
    alert_event = store._add_event(
        source_id=sensor_id,
        event_type="alert",
        description=f"Alert from {sensor.name}: value={sensor.value} {sensor.unit}",
        severity="warning",
    )
    events.append(alert_event.model_dump())

    all_devices = store.list_devices()

    for act in requested_actions:
        if act == "lights_on":
            for device in all_devices:
                if device.device_type == "light":
                    store.set_device(device.device_id, {"status": "on", "brightness": 100})
                    actions_taken.append({"action": "lights_on", "device": device.name, "status": "done"})
        elif act == "unlock_doors":
            for device in all_devices:
                if device.device_type == "lock":
                    store.set_device(device.device_id, {"locked": False})
                    actions_taken.append({"action": "unlock_doors", "device": device.name, "status": "done"})
        elif act == "lock_doors":
            for device in all_devices:
                if device.device_type == "lock":
                    store.set_device(device.device_id, {"status": "on", "locked": True})
                    actions_taken.append({"action": "lock_doors", "device": device.name, "status": "done"})
        elif act == "start_camera":
            for device in all_devices:
                if device.device_type == "camera":
                    store.set_device(device.device_id, {"status": "on", "recording": True})
                    actions_taken.append({"action": "start_camera", "device": device.name, "status": "done"})
        elif act == "sound_alarm":
            for device in all_devices:
                if device.device_type == "speaker":
                    store.set_device(device.device_id, {"status": "on", "volume": 100, "alarm": True})
                    actions_taken.append({"action": "sound_alarm", "device": device.name, "status": "done"})
        else:
            actions_taken.append({"action": act, "status": "unknown_action"})

    # Log completion event
    completion_event = store._add_event(
        source_id=sensor_id,
        event_type="alert_handled",
        description=f"Alert handled: {len(actions_taken)} actions taken",
        severity="info",
    )
    events.append(completion_event.model_dump())

    result = {
        "alert": sensor_data,
        "actions_taken": actions_taken,
        "event_log": events,
    }

    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("actions_taken", None)
    elif fault == FaultType.CONTRADICTORY:
        result["alert"] = corrupt_numeric_field(result["alert"], "value")

    return result


@mcp.tool()
async def manage_automation(
    action: str,
    name: str | None = None,
    rule_id: str | None = None,
    trigger: dict | None = None,
    device_action: dict | None = None,
    enabled: bool | None = None,
) -> dict:
    """Create or update automation rules for the smart home.

    Args:
        action: Either 'create' to make a new rule or 'update' to modify existing.
        name: Name for the rule (required for 'create').
        rule_id: ID of rule to update (required for 'update').
        trigger: Trigger conditions dict (e.g. {'condition': 'time', 'value': '06:30'}).
        device_action: Action to take when triggered (e.g. {'target': 'lights', 'command': 'on'}).
        enabled: Whether the rule is enabled (for 'update' only).

    Returns a dict with the action performed and the resulting rule data.
    """
    fault = await injector.maybe_raise("manage_automation")

    if action == "create":
        if not name or trigger is None or device_action is None:
            return {"error": "Creating a rule requires 'name', 'trigger', and 'device_action'."}
        rule = store.create_automation_rule(name, trigger, device_action)
        result = {
            "action": "create",
            "rule": rule.model_dump(),
        }

    elif action == "update":
        if not rule_id:
            return {"error": "Updating a rule requires 'rule_id'."}
        rule = store.set_automation_rule(
            rule_id,
            enabled=enabled,
            trigger=trigger,
            action=device_action,
        )
        if not rule:
            return {"error": f"Automation rule '{rule_id}' not found."}
        result = {
            "action": "update",
            "rule": rule.model_dump(),
        }

    else:
        return {"error": f"Unknown action '{action}'. Supported: 'create', 'update'."}

    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("rule", None)

    return result


if __name__ == "__main__":
    mcp.run(transport="stdio")
