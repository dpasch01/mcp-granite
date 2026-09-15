"""Smart Home domain – Composite-2 MCP server (2 tools: query + control).

Run standalone:  python -m mcp_granite.mcp_servers.smarthome.composite_2_server
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
from mcp_granite.mcp_servers.smarthome._store import SmartHomeStore

mcp = FastMCP("smarthome-composite-2")
store = SmartHomeStore()
injector = FaultInjector(FaultConfig.from_env())


@mcp.tool()
async def smart_home_query(
    action: str,
    location: str | None = None,
    sensor_id: str | None = None,
    device_id: str | None = None,
    rule_id: str | None = None,
    severity: str | None = None,
    limit: int = 10,
) -> dict:
    """Read/observe data from the smart home. This is a read-only tool.

    Args:
        action: One of 'room_status', 'sensor_reading', 'device_status',
                'event_log', 'automation_rules'.
        location: Room/area name (for 'room_status').
        sensor_id: Sensor ID (for 'sensor_reading').
        device_id: Device ID (for 'device_status').
        rule_id: Automation rule ID (optional, for 'automation_rules' to get one rule).
        severity: Severity filter (for 'event_log').
        limit: Max entries (for 'event_log', default 10).

    Returns a dict with the requested data.
    """
    fault = await injector.maybe_raise(action)

    if action == "room_status":
        if not location:
            return {"error": "room_status requires 'location'."}
        sensors = store.list_sensors(location)
        devices = store.list_devices(location)
        temps = [s.value for s in sensors if s.sensor_type == "temperature"]
        avg_temp = round(sum(temps) / len(temps), 1) if temps else None
        any_motion = any(s.value > 0 for s in sensors if s.sensor_type == "motion")
        result: dict[str, Any] = {
            "location": location,
            "sensors": [s.model_dump() for s in sensors],
            "devices": [d.model_dump() for d in devices],
            "summary": {
                "avg_temp": avg_temp,
                "any_motion": any_motion,
                "active_devices": sum(1 for d in devices if d.status == "on"),
                "total_devices": len(devices),
                "total_sensors": len(sensors),
            },
        }
        if fault == FaultType.PARTIAL_RESPONSE:
            result.pop("sensors", None)
        elif fault == FaultType.CONTRADICTORY and result["summary"]["avg_temp"] is not None:
            result["summary"]["avg_temp"] = round(result["summary"]["avg_temp"] * 0.1, 1)
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

    elif action == "device_status":
        if not device_id:
            return {"error": "device_status requires 'device_id'."}
        device = store.get_device_status(device_id)
        if not device:
            return {"error": f"Device '{device_id}' not found."}
        result = {"device": device.model_dump()}
        if fault == FaultType.CONTRADICTORY:
            result["device"]["status"] = "off" if device.status == "on" else "on"
        return result

    elif action == "event_log":
        events = store.get_event_log(severity=severity, limit=limit)
        result = {"events": [e.model_dump() for e in events]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["events"] = result["events"][:1]
        return result

    elif action == "automation_rules":
        if rule_id:
            rule = store.get_automation_rule(rule_id)
            if not rule:
                return {"error": f"Rule '{rule_id}' not found."}
            result = {"rule": rule.model_dump()}
            if fault == FaultType.CONTRADICTORY:
                result["rule"]["enabled"] = not rule.enabled
            return result
        rules = store.get_automation_rules()
        result = {"rules": [r.model_dump() for r in rules]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["rules"] = result["rules"][:1]
        return result

    else:
        return {
            "error": f"Unknown action '{action}'. "
            "Supported: room_status, sensor_reading, device_status, event_log, automation_rules."
        }


@mcp.tool()
async def smart_home_control(
    action: str,
    location: str | None = None,
    mode: str | None = None,
    custom_settings: dict | None = None,
    sensor_id: str | None = None,
    alert_actions: list[str] | None = None,
    device_id: str | None = None,
    settings: dict | None = None,
    name: str | None = None,
    rule_id: str | None = None,
    trigger: dict | None = None,
    device_action: dict | None = None,
    enabled: bool | None = None,
) -> dict:
    """Write/actuate changes in the smart home.

    Args:
        action: One of 'set_mode', 'handle_alert', 'set_device',
                'create_rule', 'update_rule'.
        location: Room/area name (for 'set_mode').
        mode: Mode preset (for 'set_mode'): 'night', 'away', 'movie'.
        custom_settings: Optional overrides for mode defaults (for 'set_mode').
        sensor_id: Alerting sensor ID (for 'handle_alert').
        alert_actions: Corrective actions (for 'handle_alert'):
                       'lights_on', 'unlock_doors', 'lock_doors', 'start_camera', 'sound_alarm'.
        device_id: Device ID (for 'set_device').
        settings: Device settings dict (for 'set_device').
        name: Rule name (for 'create_rule').
        rule_id: Rule ID (for 'update_rule').
        trigger: Trigger conditions dict (for 'create_rule' / 'update_rule').
        device_action: Action dict when triggered (for 'create_rule' / 'update_rule').
        enabled: Whether rule is enabled (for 'update_rule').

    Returns a dict with results of the action taken.
    """
    fault = await injector.maybe_raise(action)

    if action == "set_mode":
        if not location or not mode:
            return {"error": "set_mode requires 'location' and 'mode'."}
        custom = custom_settings or {}
        devices = store.list_devices(location)
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
            return {"error": f"Unknown mode '{mode}'. Supported: night, away, movie."}

        result: dict[str, Any] = {
            "location": location,
            "mode": mode,
            "changes": changes,
            "total_changes": len(changes),
        }
        if fault == FaultType.PARTIAL_RESPONSE:
            result.pop("changes", None)
        return result

    elif action == "handle_alert":
        if not sensor_id:
            return {"error": "handle_alert requires 'sensor_id'."}
        sensor = store.read_sensor(sensor_id)
        if not sensor:
            return {"error": f"Sensor '{sensor_id}' not found."}
        sensor_data = sensor.model_dump()
        requested = alert_actions or []
        actions_taken: list[dict] = []
        events: list[dict] = []
        alert_event = store._add_event(
            source_id=sensor_id, event_type="alert",
            description=f"Alert from {sensor.name}: value={sensor.value} {sensor.unit}",
            severity="warning",
        )
        events.append(alert_event.model_dump())
        all_devices = store.list_devices()
        for act in requested:
            if act == "lights_on":
                for d in all_devices:
                    if d.device_type == "light":
                        store.set_device(d.device_id, {"status": "on", "brightness": 100})
                        actions_taken.append({"action": "lights_on", "device": d.name, "status": "done"})
            elif act == "unlock_doors":
                for d in all_devices:
                    if d.device_type == "lock":
                        store.set_device(d.device_id, {"locked": False})
                        actions_taken.append({"action": "unlock_doors", "device": d.name, "status": "done"})
            elif act == "lock_doors":
                for d in all_devices:
                    if d.device_type == "lock":
                        store.set_device(d.device_id, {"status": "on", "locked": True})
                        actions_taken.append({"action": "lock_doors", "device": d.name, "status": "done"})
            elif act == "start_camera":
                for d in all_devices:
                    if d.device_type == "camera":
                        store.set_device(d.device_id, {"status": "on", "recording": True})
                        actions_taken.append({"action": "start_camera", "device": d.name, "status": "done"})
            elif act == "sound_alarm":
                for d in all_devices:
                    if d.device_type == "speaker":
                        store.set_device(d.device_id, {"status": "on", "volume": 100, "alarm": True})
                        actions_taken.append({"action": "sound_alarm", "device": d.name, "status": "done"})
            else:
                actions_taken.append({"action": act, "status": "unknown_action"})
        completion_event = store._add_event(
            source_id=sensor_id, event_type="alert_handled",
            description=f"Alert handled: {len(actions_taken)} actions taken", severity="info",
        )
        events.append(completion_event.model_dump())
        result = {"alert": sensor_data, "actions_taken": actions_taken, "event_log": events}
        if fault == FaultType.PARTIAL_RESPONSE:
            result.pop("actions_taken", None)
        elif fault == FaultType.CONTRADICTORY:
            result["alert"] = corrupt_numeric_field(result["alert"], "value")
        return result

    elif action == "set_device":
        if not device_id or settings is None:
            return {"error": "set_device requires 'device_id' and 'settings'."}
        device = store.set_device(device_id, settings)
        if not device:
            return {"error": f"Device '{device_id}' not found."}
        result = {"device": device.model_dump()}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["device"].pop("settings", None)
        return result

    elif action == "create_rule":
        if not name or trigger is None or device_action is None:
            return {"error": "create_rule requires 'name', 'trigger', and 'device_action'."}
        rule = store.create_automation_rule(name, trigger, device_action)
        result = {"action": "create", "rule": rule.model_dump()}
        if fault == FaultType.PARTIAL_RESPONSE:
            result.pop("rule", None)
        return result

    elif action == "update_rule":
        if not rule_id:
            return {"error": "update_rule requires 'rule_id'."}
        rule = store.set_automation_rule(rule_id, enabled=enabled, trigger=trigger, action=device_action)
        if not rule:
            return {"error": f"Rule '{rule_id}' not found."}
        result = {"action": "update", "rule": rule.model_dump()}
        if fault == FaultType.PARTIAL_RESPONSE:
            result.pop("rule", None)
        return result

    else:
        return {
            "error": f"Unknown action '{action}'. "
            "Supported: set_mode, handle_alert, set_device, create_rule, update_rule."
        }


if __name__ == "__main__":
    mcp.run(transport="stdio")
