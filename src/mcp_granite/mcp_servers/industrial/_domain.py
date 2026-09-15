"""Domain models for the Industrial IoT edge-computing mock."""

from __future__ import annotations

from pydantic import BaseModel


class Machine(BaseModel):
    machine_id: str
    name: str
    machine_type: str  # cnc, press, conveyor, robot
    location: str
    status: str  # running, idle, warning, fault, maintenance
    uptime_hours: float
    last_maintenance: str


class TelemetryReading(BaseModel):
    reading_id: str
    machine_id: str
    timestamp: str
    metrics: dict  # vibration (mm/s), temperature (C), pressure (bar), rpm, power_draw (kW)


class AlertThreshold(BaseModel):
    threshold_id: str
    machine_id: str
    metric: str
    min_value: float | None = None
    max_value: float | None = None
    severity: str  # info, warning, critical


class MaintenanceLog(BaseModel):
    log_id: str
    machine_id: str
    date: str
    maintenance_type: str  # scheduled, emergency, predictive
    description: str
    parts_replaced: list[str]
    downtime_hours: float


class WorkOrder(BaseModel):
    order_id: str
    machine_id: str
    priority: str  # low, medium, high, critical
    description: str
    status: str  # open, in_progress, completed, cancelled
    created_at: str
    assigned_to: str | None = None


class Alert(BaseModel):
    alert_id: str
    machine_id: str
    metric: str
    value: float
    threshold_id: str
    severity: str
    timestamp: str
    acknowledged: bool = False
