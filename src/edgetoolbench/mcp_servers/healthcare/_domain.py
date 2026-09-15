"""Domain models for the Healthcare patient monitoring edge-computing mock."""

from __future__ import annotations

from pydantic import BaseModel


class Patient(BaseModel):
    patient_id: str
    name: str
    room: str
    bed: str
    age: int
    condition: str  # stable, critical, recovering, observation
    admission_date: str
    attending_physician: str


class VitalSign(BaseModel):
    reading_id: str
    patient_id: str
    vital_type: (
        str  # heart_rate, blood_pressure, spo2, temperature, respiratory_rate, blood_glucose
    )
    value: float
    unit: str
    timestamp: str
    status: str  # normal, elevated, low, critical


class MedicalDevice(BaseModel):
    device_id: str
    name: str
    room: str
    device_type: str  # monitor, ventilator, infusion_pump, defibrillator, oximeter, bp_cuff
    status: str  # active, standby, alarm, fault, maintenance
    patient_id: str | None = None
    settings: dict
    last_updated: str


class BedSensor(BaseModel):
    sensor_id: str
    room: str
    bed: str
    patient_id: str | None = None
    occupied: bool
    weight_kg: float
    position: str  # flat, elevated, sitting
    movement_detected: bool
    last_updated: str


class NurseCall(BaseModel):
    call_id: str
    room: str
    bed: str
    patient_id: str
    call_type: str  # routine, urgent, emergency, bathroom, pain
    status: str  # active, acknowledged, resolved
    timestamp: str
    assigned_nurse: str | None = None


class EnvironmentReading(BaseModel):
    reading_id: str
    room: str
    reading_type: str  # temperature, humidity, air_pressure, noise_level
    value: float
    unit: str
    threshold_min: float
    threshold_max: float
    last_updated: str
