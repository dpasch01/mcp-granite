"""Domain models for the Robotics (multi-robot coordination) edge-computing mock."""

from __future__ import annotations

from pydantic import BaseModel


class Robot(BaseModel):
    robot_id: str
    name: str
    robot_type: str  # arm, mobile, agv, cobot, drone, inspection
    workspace: str  # assembly_line, warehouse_floor, clean_room, outdoor, maintenance_bay
    status: str  # active, idle, fault, e_stop, maintenance, charging
    battery_level: float
    current_task: str | None = None
    position: dict  # {"x": float, "y": float, "z": float}
    last_updated: str


class Waypoint(BaseModel):
    waypoint_id: str
    name: str
    workspace: str
    position: dict  # {"x": float, "y": float, "z": float}
    waypoint_type: str  # pickup, dropoff, charging, inspection, home, transit
    accessible: bool
    last_updated: str


class TaskQueue(BaseModel):
    task_id: str
    name: str
    task_type: str  # pick_and_place, transport, inspect, weld, assemble, calibrate
    assigned_robot: str | None = None
    workspace: str
    priority: int  # 1=highest, 5=lowest
    status: str  # queued, assigned, in_progress, completed, failed, cancelled
    parameters: dict
    created_at: str


class SensorReading(BaseModel):
    reading_id: str
    robot_id: str
    sensor_type: str  # force_torque, proximity, vision, lidar, temperature, vibration
    value: float
    unit: str
    status: str  # normal, warning, critical
    timestamp: str


class SafetyInterlock(BaseModel):
    interlock_id: str
    name: str
    workspace: str
    interlock_type: str  # light_curtain, e_stop, door_switch, pressure_mat, fence_gate
    status: str  # active, triggered, bypassed, fault
    last_triggered: str | None = None
    last_updated: str


class OperationLog(BaseModel):
    log_id: str
    timestamp: str
    robot_id: str
    event_type: str  # task_started, task_completed, fault_detected, e_stop, maintenance_due, collision_avoided
    description: str
    severity: str  # info, warning, critical
