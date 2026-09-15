"""Healthcare domain -- Composite-2 MCP server (2 tools: query + control).

Run standalone:  python -m mcp_granite.mcp_servers.healthcare.composite_2_server
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_granite.mcp_servers._base import (
    FaultConfig,
    FaultInjector,
    FaultType,
    corrupt_numeric_field,
)
from mcp_granite.mcp_servers.healthcare._store import HealthcareStore

mcp = FastMCP("healthcare-composite-2")
store = HealthcareStore()
injector = FaultInjector(FaultConfig.from_env())


@mcp.tool()
async def healthcare_query(
    action: str,
    patient_id: str | None = None,
    room: str | None = None,
    condition: str | None = None,
    device_id: str | None = None,
    device_type: str | None = None,
    sensor_id: str | None = None,
    call_status: str | None = None,
    device_status: str | None = None,
) -> dict:
    """Read/observe data from the healthcare ward. This is a read-only tool.

    Args:
        action: One of 'list_patients', 'get_patient', 'get_vitals',
                'list_devices', 'get_device', 'get_bed_sensor',
                'list_nurse_calls', 'list_environment', 'ward_overview'.
        patient_id: Patient ID (for 'get_patient', 'get_vitals').
        room: Room number filter (for 'list_patients', 'list_devices',
              'get_bed_sensor', 'list_nurse_calls', 'list_environment', 'ward_overview').
        condition: Condition filter (for 'list_patients', 'ward_overview').
        device_id: Device ID (for 'get_device').
        device_type: Device type filter (for 'list_devices').
        sensor_id: Bed sensor ID (for 'get_bed_sensor').
        call_status: Nurse call status filter (for 'list_nurse_calls').
        device_status: Device status filter (for 'list_devices').

    Returns a dict with the requested data.
    """
    fault = await injector.maybe_raise(action)

    if action == "list_patients":
        patients = store.list_patients(room=room, condition=condition)
        results = [p.model_dump() for p in patients]
        if fault == FaultType.PARTIAL_RESPONSE:
            results = results[:1]
        return {"patients": results}

    elif action == "get_patient":
        if not patient_id:
            return {"error": "get_patient requires 'patient_id'."}
        patient = store.get_patient(patient_id)
        if not patient:
            return {"error": f"Patient '{patient_id}' not found."}
        result = patient.model_dump()
        if fault == FaultType.CONTRADICTORY:
            result["condition"] = "stable" if result["condition"] == "critical" else "critical"
        return {"patient": result}

    elif action == "get_vitals":
        vitals = store.list_vitals(patient_id=patient_id)
        results = [v.model_dump() for v in vitals]
        if fault == FaultType.PARTIAL_RESPONSE:
            results = results[:1]
        if fault == FaultType.CONTRADICTORY:
            results = [corrupt_numeric_field(r, "value") for r in results]
        return {"vitals": results}

    elif action == "list_devices":
        devices = store.list_devices(room=room, device_type=device_type, status=device_status)
        results = [d.model_dump() for d in devices]
        if fault == FaultType.PARTIAL_RESPONSE:
            results = results[:1]
        return {"devices": results}

    elif action == "get_device":
        if not device_id:
            return {"error": "get_device requires 'device_id'."}
        device = store.get_device(device_id)
        if not device:
            return {"error": f"Device '{device_id}' not found."}
        result = device.model_dump()
        if fault == FaultType.CONTRADICTORY:
            result["status"] = "active" if result["status"] != "active" else "fault"
        return {"device": result}

    elif action == "get_bed_sensor":
        if sensor_id:
            sensor = store.get_bed_sensor(sensor_id)
            if not sensor:
                return {"error": f"Bed sensor '{sensor_id}' not found."}
            results = [sensor.model_dump()]
        else:
            sensors = store.list_bed_sensors(room=room)
            results = [s.model_dump() for s in sensors]
        if fault == FaultType.PARTIAL_RESPONSE:
            results = results[:1]
        if fault == FaultType.CONTRADICTORY:
            results = [corrupt_numeric_field(r, "weight_kg") for r in results]
        return {"bed_sensors": results}

    elif action == "list_nurse_calls":
        calls = store.list_nurse_calls(status=call_status, room=room)
        results = [c.model_dump() for c in calls]
        if fault == FaultType.PARTIAL_RESPONSE:
            results = results[:1]
        return {"nurse_calls": results}

    elif action == "list_environment":
        readings = store.list_environment_readings(room=room)
        results = [r.model_dump() for r in readings]
        if fault == FaultType.PARTIAL_RESPONSE:
            results = results[:1]
        if fault == FaultType.CONTRADICTORY:
            results = [corrupt_numeric_field(r, "value") for r in results]
        return {"environment": results}

    elif action == "ward_overview":
        patients = store.list_patients(room=room, condition=condition)
        devices = store.list_devices(room=room)
        bed_sensors = store.list_bed_sensors(room=room)
        env_readings = store.list_environment_readings(room=room)
        nurse_calls = store.list_nurse_calls(room=room)
        critical = [p for p in patients if p.condition == "critical"]
        active_calls = [c for c in nurse_calls if c.status == "active"]
        faulty = [d for d in devices if d.status in ("fault", "alarm")]
        result: dict[str, Any] = {
            "patients": [p.model_dump() for p in patients],
            "devices": [d.model_dump() for d in devices],
            "bed_sensors": [s.model_dump() for s in bed_sensors],
            "environment": [r.model_dump() for r in env_readings],
            "nurse_calls": [c.model_dump() for c in nurse_calls],
            "summary": {
                "total_patients": len(patients),
                "critical_patients": len(critical),
                "active_nurse_calls": len(active_calls),
                "faulty_devices": len(faulty),
                "occupied_beds": sum(1 for s in bed_sensors if s.occupied),
            },
        }
        if fault == FaultType.PARTIAL_RESPONSE:
            result.pop("devices", None)
            result.pop("bed_sensors", None)
        return result

    else:
        return {
            "error": f"Unknown action '{action}'. Supported: list_patients, get_patient, "
            "get_vitals, list_devices, get_device, get_bed_sensor, list_nurse_calls, "
            "list_environment, ward_overview."
        }


@mcp.tool()
async def healthcare_control(
    action: str,
    device_id: str | None = None,
    settings: dict | None = None,
    patient_id: str | None = None,
    update_condition: str | None = None,
    room: str | None = None,
    bed: str | None = None,
    call_type: str | None = None,
    call_id: str | None = None,
    nurse: str | None = None,
) -> dict:
    """Write/actuate changes in the healthcare ward.

    Args:
        action: One of 'set_device', 'update_patient', 'create_nurse_call',
                'acknowledge_nurse_call', 'resolve_nurse_call'.
        device_id: Device ID (for 'set_device').
        settings: Settings dict to merge (for 'set_device'). Can include 'status'.
        patient_id: Patient ID (for 'update_patient', 'create_nurse_call').
        update_condition: New condition (for 'update_patient').
        room: Room number (for 'create_nurse_call').
        bed: Bed letter (for 'create_nurse_call').
        call_type: Call type (for 'create_nurse_call'): routine/urgent/emergency/bathroom/pain.
        call_id: Call ID (for 'acknowledge_nurse_call', 'resolve_nurse_call').
        nurse: Nurse name (for 'acknowledge_nurse_call').

    Returns a dict with results of the action taken.
    """
    fault = await injector.maybe_raise(action)

    if action == "set_device":
        if not device_id or settings is None:
            return {"error": "set_device requires 'device_id' and 'settings'."}
        device = store.set_device(device_id, settings)
        if not device:
            return {"error": f"Device '{device_id}' not found."}
        result = device.model_dump()
        if fault == FaultType.PARTIAL_RESPONSE:
            result.pop("settings", None)
        return {"device": result, "action": "updated"}

    elif action == "update_patient":
        if not patient_id:
            return {"error": "update_patient requires 'patient_id'."}
        kwargs: dict[str, Any] = {}
        if update_condition:
            kwargs["condition"] = update_condition
        patient = store.update_patient(patient_id, **kwargs)
        if not patient:
            return {"error": f"Patient '{patient_id}' not found."}
        return {"patient": patient.model_dump(), "action": "updated"}

    elif action == "create_nurse_call":
        if not room or not bed or not patient_id or not call_type:
            return {"error": "create_nurse_call requires 'room', 'bed', 'patient_id', 'call_type'."}
        call = store.create_nurse_call(
            room=room, bed=bed, patient_id=patient_id, call_type=call_type
        )
        return {"call": call.model_dump(), "action": "created"}

    elif action == "acknowledge_nurse_call":
        if not call_id or not nurse:
            return {"error": "acknowledge_nurse_call requires 'call_id' and 'nurse'."}
        call = store.acknowledge_nurse_call(call_id, nurse)
        if not call:
            return {"error": f"Nurse call '{call_id}' not found."}
        return {"call": call.model_dump(), "action": "acknowledged"}

    elif action == "resolve_nurse_call":
        if not call_id:
            return {"error": "resolve_nurse_call requires 'call_id'."}
        call = store.resolve_nurse_call(call_id)
        if not call:
            return {"error": f"Nurse call '{call_id}' not found."}
        return {"call": call.model_dump(), "action": "resolved"}

    else:
        return {
            "error": f"Unknown action '{action}'. Supported: set_device, update_patient, "
            "create_nurse_call, acknowledge_nurse_call, resolve_nurse_call."
        }


if __name__ == "__main__":
    mcp.run(transport="stdio")
