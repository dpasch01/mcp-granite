"""Domain models for the Smart Home edge-computing mock."""

from __future__ import annotations

from pydantic import BaseModel


class Sensor(BaseModel):
    sensor_id: str
    name: str
    location: str
    sensor_type: str  # temperature, humidity, motion, light, door, smoke
    value: float
    unit: str
    last_updated: str
    battery_level: float


class Device(BaseModel):
    device_id: str
    name: str
    location: str
    device_type: str  # light, thermostat, lock, camera, blinds, speaker
    status: str  # on, off
    settings: dict
    last_updated: str


class AutomationRule(BaseModel):
    rule_id: str
    name: str
    trigger: dict
    action: dict
    enabled: bool
    last_triggered: str | None = None


class EventLog(BaseModel):
    event_id: str
    timestamp: str
    source_id: str
    event_type: str
    description: str
    severity: str  # info, warning, critical
