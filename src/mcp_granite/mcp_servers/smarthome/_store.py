"""In-memory data store for the Smart Home domain with deterministic seed data."""

from __future__ import annotations

from mcp_granite.mcp_servers._data import generate_id
from mcp_granite.mcp_servers.smarthome._domain import (
    AutomationRule,
    Device,
    EventLog,
    Sensor,
)


class SmartHomeStore:
    def __init__(self) -> None:
        self.sensors: dict[str, Sensor] = {}
        self.devices: dict[str, Device] = {}
        self.automation_rules: dict[str, AutomationRule] = {}
        self.event_log: list[EventLog] = []
        self._next_rule = 4  # AR001-AR003 seeded
        self._next_event = 5  # EV001-EV004 seeded
        self._seed_data()

    def _seed_data(self) -> None:
        # ── Sensors ──────────────────────────────────────────────────────
        sensor_data = [
            ("Living Room Temperature", "living room", "temperature", 22.5, "°C", "2025-06-01T08:30:00", 95.0),
            ("Bedroom Humidity", "bedroom", "humidity", 45.0, "%", "2025-06-01T08:28:00", 88.0),
            ("Hallway Motion", "hallway", "motion", 0.0, "boolean", "2025-06-01T08:25:00", 72.0),
            ("Kitchen Light Level", "kitchen", "light", 350.0, "lux", "2025-06-01T08:32:00", 91.0),
            ("Front Door Contact", "front door", "door", 1.0, "closed", "2025-06-01T08:20:00", 65.0),
            ("Basement Smoke Detector", "basement", "smoke", 0.0, "ppm", "2025-06-01T08:15:00", 80.0),
        ]
        for i, (name, location, stype, value, unit, updated, battery) in enumerate(sensor_data, 1):
            sid = generate_id("SN", i)
            self.sensors[sid] = Sensor(
                sensor_id=sid, name=name, location=location, sensor_type=stype,
                value=value, unit=unit, last_updated=updated, battery_level=battery,
            )

        # ── Devices ──────────────────────────────────────────────────────
        device_data = [
            ("Living Room Light", "living room", "light", "on", {"brightness": 80}, "2025-06-01T08:00:00"),
            ("Thermostat", "living room", "thermostat", "on", {"target_temp": 21, "mode": "auto"}, "2025-06-01T07:55:00"),
            ("Front Door Lock", "front door", "lock", "on", {"locked": True}, "2025-06-01T08:10:00"),
            ("Backyard Camera", "backyard", "camera", "on", {"recording": True, "night_vision": True}, "2025-06-01T08:05:00"),
            ("Bedroom Blinds", "bedroom", "blinds", "off", {"position": 100}, "2025-06-01T07:50:00"),
            ("Kitchen Speaker", "kitchen", "speaker", "off", {"volume": 30}, "2025-06-01T07:45:00"),
        ]
        for i, (name, location, dtype, status, settings, updated) in enumerate(device_data, 1):
            did = generate_id("DV", i)
            self.devices[did] = Device(
                device_id=did, name=name, location=location, device_type=dtype,
                status=status, settings=settings, last_updated=updated,
            )

        # ── Automation Rules ─────────────────────────────────────────────
        rule_data = [
            (
                "Night lights off",
                {"condition": "motion", "value": 0, "after": "23:00"},
                {"target": "lights", "command": "off"},
                True,
                "2025-05-31T23:05:00",
            ),
            (
                "Morning warmup",
                {"condition": "time", "value": "06:30"},
                {"target": "thermostat", "command": "set_temp", "value": 22},
                True,
                "2025-06-01T06:30:00",
            ),
            (
                "Security alert",
                {"condition": "door_open", "after": "23:00"},
                {"target": "camera", "command": "record", "also": "lock_check"},
                True,
                None,
            ),
        ]
        for i, (name, trigger, action, enabled, last_triggered) in enumerate(rule_data, 1):
            rid = generate_id("AR", i)
            self.automation_rules[rid] = AutomationRule(
                rule_id=rid, name=name, trigger=trigger,
                action=action, enabled=enabled, last_triggered=last_triggered,
            )

        # ── Event Log ────────────────────────────────────────────────────
        event_data = [
            ("2025-06-01T08:30:00", "SN001", "reading", "Temperature reading: 22.5°C", "info"),
            ("2025-06-01T08:20:00", "SN005", "state_change", "Front door opened", "info"),
            ("2025-06-01T07:55:00", "DV002", "setting_change", "Thermostat target changed to 21°C", "info"),
            ("2025-06-01T06:30:00", "AR002", "automation_triggered", "Morning warmup rule executed", "warning"),
        ]
        for i, (timestamp, source_id, etype, desc, severity) in enumerate(event_data, 1):
            eid = generate_id("EV", i)
            self.event_log.append(EventLog(
                event_id=eid, timestamp=timestamp, source_id=source_id,
                event_type=etype, description=desc, severity=severity,
            ))

    # ── Sensor methods ───────────────────────────────────────────────────

    def list_sensors(self, location: str | None = None) -> list[Sensor]:
        """List all sensors, optionally filtered by location."""
        if location:
            return [s for s in self.sensors.values() if s.location.lower() == location.lower()]
        return list(self.sensors.values())

    def read_sensor(self, sensor_id: str) -> Sensor | None:
        """Read a single sensor by ID."""
        return self.sensors.get(sensor_id)

    # ── Device methods ───────────────────────────────────────────────────

    def list_devices(self, location: str | None = None) -> list[Device]:
        """List all devices, optionally filtered by location."""
        if location:
            return [d for d in self.devices.values() if d.location.lower() == location.lower()]
        return list(self.devices.values())

    def get_device_status(self, device_id: str) -> Device | None:
        """Get a single device by ID."""
        return self.devices.get(device_id)

    def set_device(self, device_id: str, settings: dict) -> Device | None:
        """Update device settings. Merges new settings into existing ones."""
        device = self.devices.get(device_id)
        if not device:
            return None
        # Allow updating top-level fields like status
        if "status" in settings:
            device.status = settings.pop("status")
        device.settings.update(settings)
        return device

    # ── Automation rule methods ──────────────────────────────────────────

    def get_automation_rules(self) -> list[AutomationRule]:
        """Return all automation rules."""
        return list(self.automation_rules.values())

    def get_automation_rule(self, rule_id: str) -> AutomationRule | None:
        """Get a single automation rule by ID."""
        return self.automation_rules.get(rule_id)

    def set_automation_rule(
        self,
        rule_id: str,
        enabled: bool | None = None,
        trigger: dict | None = None,
        action: dict | None = None,
    ) -> AutomationRule | None:
        """Update an existing automation rule."""
        rule = self.automation_rules.get(rule_id)
        if not rule:
            return None
        if enabled is not None:
            rule.enabled = enabled
        if trigger is not None:
            rule.trigger = trigger
        if action is not None:
            rule.action = action
        return rule

    def create_automation_rule(self, name: str, trigger: dict, action: dict) -> AutomationRule:
        """Create a new automation rule with an auto-generated ID."""
        rid = generate_id("AR", self._next_rule)
        self._next_rule += 1
        rule = AutomationRule(
            rule_id=rid, name=name, trigger=trigger,
            action=action, enabled=True, last_triggered=None,
        )
        self.automation_rules[rid] = rule
        return rule

    # ── Event log methods ────────────────────────────────────────────────

    def get_event_log(self, severity: str | None = None, limit: int = 10) -> list[EventLog]:
        """Return event log entries, newest first, optionally filtered by severity."""
        events = self.event_log
        if severity:
            events = [e for e in events if e.severity.lower() == severity.lower()]
        # Sort newest first by timestamp
        events = sorted(events, key=lambda e: e.timestamp, reverse=True)
        return events[:limit]

    def _add_event(self, source_id: str, event_type: str, description: str, severity: str) -> EventLog:
        """Internal helper to add an event log entry."""
        eid = generate_id("EV", self._next_event)
        self._next_event += 1
        event = EventLog(
            event_id=eid, timestamp="2025-06-01T09:00:00", source_id=source_id,
            event_type=event_type, description=description, severity=severity,
        )
        self.event_log.append(event)
        return event
