"""In-memory data store for the Healthcare domain with deterministic seed data."""

from __future__ import annotations

from mcp_granite.mcp_servers._data import generate_id
from mcp_granite.mcp_servers.healthcare._domain import (
    BedSensor,
    EnvironmentReading,
    MedicalDevice,
    NurseCall,
    Patient,
    VitalSign,
)


class HealthcareStore:
    def __init__(self) -> None:
        self.patients: dict[str, Patient] = {}
        self.vitals: dict[str, VitalSign] = {}
        self.devices: dict[str, MedicalDevice] = {}
        self.bed_sensors: dict[str, BedSensor] = {}
        self.nurse_calls: dict[str, NurseCall] = {}
        self.environment_readings: dict[str, EnvironmentReading] = {}
        self._next_call = 4  # NC001-NC003 seeded
        self._seed_data()

    def _seed_data(self) -> None:
        # -- Patients (6 patients in rooms 101-106) --------------------------
        patient_data = [
            ("Alice Johnson", "101", "A", 72, "stable", "2025-05-20", "Dr. Smith"),
            ("Bob Martinez", "102", "A", 58, "critical", "2025-05-28", "Dr. Chen"),
            ("Carol White", "103", "A", 45, "recovering", "2025-05-25", "Dr. Patel"),
            ("David Lee", "104", "B", 81, "observation", "2025-06-01", "Dr. Smith"),
            ("Emma Davis", "105", "A", 34, "stable", "2025-05-30", "Dr. Chen"),
            ("Frank Wilson", "106", "B", 67, "critical", "2025-05-22", "Dr. Patel"),
        ]
        for i, (name, room, bed, age, condition, admission, physician) in enumerate(
            patient_data, 1
        ):
            pid = generate_id("PA", i)
            self.patients[pid] = Patient(
                patient_id=pid,
                name=name,
                room=room,
                bed=bed,
                age=age,
                condition=condition,
                admission_date=admission,
                attending_physician=physician,
            )

        # -- Vital Signs (6 readings, one per patient) ----------------------
        vital_data = [
            ("PA001", "heart_rate", 78.0, "bpm", "2025-06-01T08:00:00", "normal"),
            ("PA002", "blood_pressure", 185.0, "mmHg", "2025-06-01T08:05:00", "critical"),
            ("PA003", "spo2", 97.0, "%", "2025-06-01T08:10:00", "normal"),
            ("PA004", "temperature", 38.9, "C", "2025-06-01T08:15:00", "elevated"),
            ("PA005", "respiratory_rate", 16.0, "breaths/min", "2025-06-01T08:20:00", "normal"),
            ("PA006", "blood_glucose", 42.0, "mg/dL", "2025-06-01T08:25:00", "low"),
        ]
        for i, (patient_id, vital_type, value, unit, timestamp, status) in enumerate(vital_data, 1):
            vid = generate_id("VS", i)
            self.vitals[vid] = VitalSign(
                reading_id=vid,
                patient_id=patient_id,
                vital_type=vital_type,
                value=value,
                unit=unit,
                timestamp=timestamp,
                status=status,
            )

        # -- Medical Devices (6 devices) ------------------------------------
        device_data = [
            (
                "Bedside Monitor 101",
                "101",
                "monitor",
                "active",
                "PA001",
                {"alarm_threshold_hr": 120, "alarm_threshold_spo2": 90},
                "2025-06-01T07:00:00",
            ),
            (
                "Ventilator 102",
                "102",
                "ventilator",
                "active",
                "PA002",
                {"mode": "assist_control", "tidal_volume": 500, "rate": 14, "fio2": 0.6},
                "2025-06-01T07:30:00",
            ),
            (
                "Infusion Pump 103",
                "103",
                "infusion_pump",
                "active",
                "PA003",
                {"rate_ml_hr": 125, "drug": "saline", "total_volume": 1000},
                "2025-06-01T07:15:00",
            ),
            (
                "Defibrillator Ward",
                "104",
                "defibrillator",
                "standby",
                None,
                {"energy_j": 200, "mode": "manual"},
                "2025-06-01T06:00:00",
            ),
            (
                "Pulse Oximeter 105",
                "105",
                "oximeter",
                "active",
                "PA005",
                {"alarm_low_spo2": 92, "continuous": True},
                "2025-06-01T08:00:00",
            ),
            (
                "BP Cuff 106",
                "106",
                "bp_cuff",
                "fault",
                "PA006",
                {"interval_min": 15, "auto_inflate": True},
                "2025-06-01T05:30:00",
            ),
        ]
        for i, (name, room, dtype, status, patient_id, settings, updated) in enumerate(
            device_data, 1
        ):
            did = generate_id("MD", i)
            self.devices[did] = MedicalDevice(
                device_id=did,
                name=name,
                room=room,
                device_type=dtype,
                status=status,
                patient_id=patient_id,
                settings=settings,
                last_updated=updated,
            )

        # -- Bed Sensors (6 sensors, one per room) --------------------------
        bed_sensor_data = [
            ("101", "A", "PA001", True, 65.0, "elevated", False, "2025-06-01T08:00:00"),
            ("102", "A", "PA002", True, 82.5, "flat", True, "2025-06-01T08:05:00"),
            ("103", "A", "PA003", True, 58.0, "sitting", False, "2025-06-01T08:10:00"),
            ("104", "B", "PA004", True, 70.2, "elevated", False, "2025-06-01T08:15:00"),
            ("105", "A", "PA005", True, 55.0, "flat", False, "2025-06-01T08:20:00"),
            ("106", "B", "PA006", True, 78.0, "flat", True, "2025-06-01T08:25:00"),
        ]
        for i, (room, bed, patient_id, occupied, weight, position, movement, updated) in enumerate(
            bed_sensor_data, 1
        ):
            sid = generate_id("BS", i)
            self.bed_sensors[sid] = BedSensor(
                sensor_id=sid,
                room=room,
                bed=bed,
                patient_id=patient_id,
                occupied=occupied,
                weight_kg=weight,
                position=position,
                movement_detected=movement,
                last_updated=updated,
            )

        # -- Nurse Calls (3 active/acknowledged calls) ----------------------
        call_data = [
            ("102", "A", "PA002", "emergency", "active", "2025-06-01T08:30:00", None),
            ("104", "B", "PA004", "routine", "acknowledged", "2025-06-01T08:20:00", "Nurse Rivera"),
            ("106", "B", "PA006", "pain", "active", "2025-06-01T08:35:00", None),
        ]
        for i, (room, bed, patient_id, call_type, status, timestamp, nurse) in enumerate(
            call_data, 1
        ):
            cid = generate_id("NC", i)
            self.nurse_calls[cid] = NurseCall(
                call_id=cid,
                room=room,
                bed=bed,
                patient_id=patient_id,
                call_type=call_type,
                status=status,
                timestamp=timestamp,
                assigned_nurse=nurse,
            )

        # -- Environment Readings (4 readings) ------------------------------
        env_data = [
            ("101", "temperature", 22.0, "C", 18.0, 26.0, "2025-06-01T08:00:00"),
            ("102", "humidity", 45.0, "%", 30.0, 60.0, "2025-06-01T08:05:00"),
            ("103", "air_pressure", 1013.0, "hPa", 980.0, 1050.0, "2025-06-01T08:10:00"),
            ("104", "noise_level", 55.0, "dB", 20.0, 45.0, "2025-06-01T08:15:00"),
        ]
        for i, (room, rtype, value, unit, tmin, tmax, updated) in enumerate(env_data, 1):
            eid = generate_id("ER", i)
            self.environment_readings[eid] = EnvironmentReading(
                reading_id=eid,
                room=room,
                reading_type=rtype,
                value=value,
                unit=unit,
                threshold_min=tmin,
                threshold_max=tmax,
                last_updated=updated,
            )

    # -- Patient methods ----------------------------------------------------

    def list_patients(self, room: str | None = None, condition: str | None = None) -> list[Patient]:
        """List all patients, optionally filtered by room or condition."""
        patients = list(self.patients.values())
        if room:
            patients = [p for p in patients if p.room == room]
        if condition:
            patients = [p for p in patients if p.condition.lower() == condition.lower()]
        return patients

    def get_patient(self, patient_id: str) -> Patient | None:
        """Get a single patient by ID."""
        return self.patients.get(patient_id)

    def update_patient(self, patient_id: str, **kwargs: object) -> Patient | None:
        """Update patient fields (condition, attending_physician, etc.)."""
        patient = self.patients.get(patient_id)
        if not patient:
            return None
        for key, value in kwargs.items():
            if hasattr(patient, key) and key != "patient_id":
                setattr(patient, key, value)
        return patient

    # -- Vital Sign methods -------------------------------------------------

    def list_vitals(self, patient_id: str | None = None) -> list[VitalSign]:
        """List vital sign readings, optionally filtered by patient."""
        vitals = list(self.vitals.values())
        if patient_id:
            vitals = [v for v in vitals if v.patient_id == patient_id]
        return vitals

    def get_vital(self, reading_id: str) -> VitalSign | None:
        """Get a single vital sign reading by ID."""
        return self.vitals.get(reading_id)

    # -- Medical Device methods ---------------------------------------------

    def list_devices(
        self,
        room: str | None = None,
        device_type: str | None = None,
        status: str | None = None,
    ) -> list[MedicalDevice]:
        """List medical devices, optionally filtered by room, type, or status."""
        devices = list(self.devices.values())
        if room:
            devices = [d for d in devices if d.room == room]
        if device_type:
            devices = [d for d in devices if d.device_type.lower() == device_type.lower()]
        if status:
            devices = [d for d in devices if d.status.lower() == status.lower()]
        return devices

    def get_device(self, device_id: str) -> MedicalDevice | None:
        """Get a single device by ID."""
        return self.devices.get(device_id)

    def set_device(self, device_id: str, settings: dict) -> MedicalDevice | None:
        """Update device settings. Merges new settings into existing ones."""
        device = self.devices.get(device_id)
        if not device:
            return None
        if "status" in settings:
            device.status = settings.pop("status")
        if "patient_id" in settings:
            device.patient_id = settings.pop("patient_id")
        device.settings.update(settings)
        return device

    # -- Bed Sensor methods -------------------------------------------------

    def list_bed_sensors(self, room: str | None = None) -> list[BedSensor]:
        """List bed sensors, optionally filtered by room."""
        sensors = list(self.bed_sensors.values())
        if room:
            sensors = [s for s in sensors if s.room == room]
        return sensors

    def get_bed_sensor(self, sensor_id: str) -> BedSensor | None:
        """Get a single bed sensor by ID."""
        return self.bed_sensors.get(sensor_id)

    def update_bed_sensor(self, sensor_id: str, **kwargs: object) -> BedSensor | None:
        """Update bed sensor fields."""
        sensor = self.bed_sensors.get(sensor_id)
        if not sensor:
            return None
        for key, value in kwargs.items():
            if hasattr(sensor, key) and key != "sensor_id":
                setattr(sensor, key, value)
        return sensor

    # -- Nurse Call methods --------------------------------------------------

    def list_nurse_calls(
        self, status: str | None = None, room: str | None = None
    ) -> list[NurseCall]:
        """List nurse calls, optionally filtered by status or room."""
        calls = list(self.nurse_calls.values())
        if status:
            calls = [c for c in calls if c.status.lower() == status.lower()]
        if room:
            calls = [c for c in calls if c.room == room]
        return calls

    def get_nurse_call(self, call_id: str) -> NurseCall | None:
        """Get a single nurse call by ID."""
        return self.nurse_calls.get(call_id)

    def create_nurse_call(
        self,
        room: str,
        bed: str,
        patient_id: str,
        call_type: str,
    ) -> NurseCall:
        """Create a new nurse call with an auto-generated ID."""
        cid = generate_id("NC", self._next_call)
        self._next_call += 1
        call = NurseCall(
            call_id=cid,
            room=room,
            bed=bed,
            patient_id=patient_id,
            call_type=call_type,
            status="active",
            timestamp="2025-06-01T09:00:00",
            assigned_nurse=None,
        )
        self.nurse_calls[cid] = call
        return call

    def acknowledge_nurse_call(self, call_id: str, nurse: str) -> NurseCall | None:
        """Acknowledge a nurse call and assign a nurse."""
        call = self.nurse_calls.get(call_id)
        if not call:
            return None
        call.status = "acknowledged"
        call.assigned_nurse = nurse
        return call

    def resolve_nurse_call(self, call_id: str) -> NurseCall | None:
        """Resolve a nurse call."""
        call = self.nurse_calls.get(call_id)
        if not call:
            return None
        call.status = "resolved"
        return call

    # -- Environment Reading methods ----------------------------------------

    def list_environment_readings(self, room: str | None = None) -> list[EnvironmentReading]:
        """List environment readings, optionally filtered by room."""
        readings = list(self.environment_readings.values())
        if room:
            readings = [r for r in readings if r.room == room]
        return readings

    def get_environment_reading(self, reading_id: str) -> EnvironmentReading | None:
        """Get a single environment reading by ID."""
        return self.environment_readings.get(reading_id)
