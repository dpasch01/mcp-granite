"""Domain models for the Warehouse (logistics) edge-computing mock."""

from __future__ import annotations

from pydantic import BaseModel


class ConveyorBelt(BaseModel):
    belt_id: str
    name: str
    zone: str  # inbound, sorting, packing, outbound
    speed_mps: float
    status: str  # running, stopped, fault, maintenance
    items_per_hour: int
    last_updated: str


class Robot(BaseModel):
    robot_id: str
    name: str
    robot_type: str  # picker, packer, transport, scanner
    zone: str
    status: str  # active, idle, charging, fault, maintenance
    battery_level: float
    current_task: str | None = None
    last_updated: str


class InventorySlot(BaseModel):
    slot_id: str
    location: str  # e.g. "A-01-03" (aisle-rack-shelf)
    zone: str
    product_name: str
    sku: str
    quantity: int
    max_capacity: int
    last_updated: str


class DockDoor(BaseModel):
    door_id: str
    name: str
    status: str  # open, closed, loading, unloading, fault
    assigned_truck: str | None = None
    direction: str  # inbound, outbound
    last_updated: str


class EnvironmentSensor(BaseModel):
    sensor_id: str
    name: str
    zone: str
    sensor_type: str  # temperature, humidity, air_quality, noise_level
    value: float
    unit: str
    threshold_min: float
    threshold_max: float
    last_updated: str


class PickOrder(BaseModel):
    order_id: str
    customer_id: str
    items: list[dict]  # [{"sku": "...", "quantity": N, "slot_id": "..."}]
    status: str  # pending, picking, packing, shipped, cancelled
    priority: int  # 1=highest, 5=lowest
    assigned_robot: str | None = None
    created_at: str
