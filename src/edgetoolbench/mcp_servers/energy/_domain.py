"""Domain models for the Energy (microgrid) edge-computing mock."""

from __future__ import annotations

from pydantic import BaseModel


class PowerSource(BaseModel):
    source_id: str
    name: str
    source_type: str  # solar, wind, diesel, grid_tie, hydro, fuel_cell
    capacity_kw: float
    current_output_kw: float
    status: str  # online, offline, standby, fault
    location: str
    last_updated: str


class LoadZone(BaseModel):
    zone_id: str
    name: str
    zone_type: str  # residential, commercial, industrial, critical, ev_charging, storage
    current_load_kw: float
    max_capacity_kw: float
    priority: int  # 1=highest, 5=lowest
    status: str  # normal, overloaded, shed, offline
    last_updated: str


class Battery(BaseModel):
    battery_id: str
    name: str
    capacity_kwh: float
    current_charge_kwh: float
    charge_rate_kw: float
    discharge_rate_kw: float
    status: str  # charging, discharging, idle, fault
    soc_percent: float  # state of charge percentage
    last_updated: str


class SmartMeter(BaseModel):
    meter_id: str
    name: str
    location: str
    meter_type: str  # generation, consumption, bidirectional, grid_interconnect
    current_reading_kwh: float
    power_factor: float
    voltage: float
    last_updated: str


class EnergyAlert(BaseModel):
    alert_id: str
    timestamp: str
    source_id: str
    alert_type: (
        str  # overload, low_battery, grid_fault, islanding, frequency_deviation, voltage_sag
    )
    description: str
    severity: str  # info, warning, critical
    acknowledged: bool = False


class ScheduleEntry(BaseModel):
    entry_id: str
    name: str
    target_id: str
    action: str  # start, stop, charge, discharge, shed_load, restore_load
    scheduled_time: str
    status: str  # pending, executed, cancelled
    parameters: dict
