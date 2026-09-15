"""Domain models for the Agriculture (smart farming) edge-computing mock."""

from __future__ import annotations

from pydantic import BaseModel


class Sensor(BaseModel):
    sensor_id: str
    name: str
    field_zone: str
    sensor_type: str  # soil_moisture, soil_ph, temperature, humidity, wind_speed, rainfall
    value: float
    unit: str
    last_updated: str
    battery_level: float


class IrrigationZone(BaseModel):
    zone_id: str
    name: str
    field_zone: str
    status: str  # active, idle, scheduled, fault
    flow_rate: float  # liters per minute
    schedule: dict  # e.g. {"start": "06:00", "duration_min": 30}
    last_activated: str


class Crop(BaseModel):
    crop_id: str
    name: str
    field_zone: str
    variety: str
    plant_date: str
    health_status: str  # healthy, stressed, diseased, dormant
    growth_stage: str  # germination, vegetative, flowering, harvest_ready
    expected_harvest: str


class WeatherStation(BaseModel):
    station_id: str
    name: str
    location: str
    temperature: float
    humidity: float
    wind_speed: float
    rainfall_mm: float
    forecast: str  # clear, cloudy, rain, storm
    last_updated: str


class DroneTask(BaseModel):
    task_id: str
    drone_id: str
    task_type: str  # survey, spray, seed, monitor
    field_zone: str
    status: str  # pending, in_progress, completed, failed
    scheduled_time: str
    result: dict | None = None


class AlertLog(BaseModel):
    alert_id: str
    timestamp: str
    source_id: str
    alert_type: str  # pest_detected, frost_warning, low_moisture, equipment_fault, disease_detected
    description: str
    severity: str  # info, warning, critical
    acknowledged: bool = False
