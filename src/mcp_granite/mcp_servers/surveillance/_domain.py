"""Domain models for the Surveillance (security) edge-computing mock."""

from __future__ import annotations

from pydantic import BaseModel


class Camera(BaseModel):
    camera_id: str
    name: str
    location: str
    camera_type: str  # fixed, ptz, dome, thermal
    status: str  # recording, idle, offline, fault
    resolution: str  # 1080p, 4k, 720p
    night_vision: bool
    recording: bool
    last_updated: str


class MotionSensor(BaseModel):
    sensor_id: str
    name: str
    location: str
    sensitivity: str  # low, medium, high
    status: str  # armed, disarmed, triggered, fault
    last_triggered: str | None = None
    battery_level: float
    last_updated: str


class AccessPoint(BaseModel):
    point_id: str
    name: str
    location: str
    point_type: str  # door, gate, turnstile, barrier
    status: str  # locked, unlocked, open, fault
    access_level: int  # 1=public, 5=restricted
    last_access: str | None = None
    last_updated: str


class AlarmZone(BaseModel):
    zone_id: str
    name: str
    zone_type: str  # perimeter, interior, high_security, parking
    status: str  # armed, disarmed, alarm, testing
    sensors: list[str]  # sensor IDs in this zone
    cameras: list[str]  # camera IDs in this zone
    last_updated: str


class SecurityEvent(BaseModel):
    event_id: str
    timestamp: str
    source_id: str
    event_type: str  # motion_detected, access_granted, access_denied, alarm_triggered, camera_tamper, patrol_complete
    description: str
    severity: str  # info, warning, critical
    acknowledged: bool = False


class Patrol(BaseModel):
    patrol_id: str
    name: str
    route: list[str]  # list of location checkpoints
    status: str  # scheduled, in_progress, completed, cancelled
    assigned_guard: str | None = None
    scheduled_time: str
    last_completed: str | None = None
