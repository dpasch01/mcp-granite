"""Domain models for the Fleet Management mock."""

from __future__ import annotations

from pydantic import BaseModel


class Vehicle(BaseModel):
    vehicle_id: str
    plate: str
    vehicle_type: str  # van, truck, motorcycle
    status: str  # available, en_route, maintenance, out_of_service
    current_location: dict  # {"lat": float, "lng": float}
    fuel_level: float  # percentage 0-100
    mileage: float  # km


class Driver(BaseModel):
    driver_id: str
    name: str
    license_type: str  # B, C, A
    status: str  # available, on_duty, off_duty
    assigned_vehicle_id: str | None = None
    hours_today: float


class Delivery(BaseModel):
    delivery_id: str
    vehicle_id: str | None = None
    driver_id: str | None = None
    pickup_location: str
    dropoff_location: str
    status: str  # pending, picked_up, in_transit, delivered, failed
    priority: str  # normal, express, urgent
    created_at: str
    eta: str | None = None


class Route(BaseModel):
    route_id: str
    origin: str
    destination: str
    distance_km: float
    estimated_duration_min: float
    conditions: str  # clear, traffic, construction, closed


class VehicleDiagnostic(BaseModel):
    diagnostic_id: str
    vehicle_id: str
    timestamp: str
    engine_temp: float
    tire_pressure: dict  # {"fl": float, "fr": float, "rl": float, "rr": float}
    fuel_efficiency: float  # km/l
    brake_wear: float  # percentage 0-100
    battery_voltage: float
    alerts: list[str]
