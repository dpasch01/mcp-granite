"""Healthcare domain -- Composite-1 MCP server (1 unified tool).

Run standalone:  python -m edgetoolbench.mcp_servers.healthcare.composite_1_server
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from edgetoolbench.mcp_servers._base import (
    FaultConfig,
    FaultInjector,
    FaultType,
    corrupt_numeric_field,
)
from edgetoolbench.mcp_servers.healthcare._store import HealthcareStore

mcp = FastMCP("healthcare-composite-1")
store = HealthcareStore()
injector = FaultInjector(FaultConfig.from_env())


@mcp.tool()
async def healthcare(
    action: str,
    patient_id: str | None = None,
    room: str | None = None,
    condition: str | None = None,
    device_id: str | None = None,
    device_type: str | None = None,
    device_status: str | None = None,
    sensor_id: str | None = None,
    call_status: str | None = None,
    settings: dict | None = None,
    update_condition: str | None = None,
    bed: str | None = None,
    call_type: str | None = None,
    call_id: str | None = None,
    nurse: str | None = None,
) -> dict:
    """Unified healthcare ward interface. All read and write operations via a single tool.

    **Read actions:**
    - 'list_patients': List patients. Optional: room, condition.
    - 'get_patient': Get patient details. Requires: patient_id.
    - 'get_vitals': Get vital sign readings. Optional: patient_id.
    - 'list_devices': List medical devices. Optional: room, device_type, device_status.
    - 'get_device': Get device details. Requires: device_id.
    - 'get_bed_sensor': Get bed sensor data. Optional: sensor_id, room.
    - 'list_nurse_calls': List nurse calls. Optional: call_status, room.
    - 'list_environment': List room environment readings. Optional: room.
    - 'ward_overview': Full ward summary. Optional: room, condition.

    **Write actions:**
    - 'set_device': Update device settings. Requires: device_id, settings.
    - 'update_patient': Update patient condition. Requires: patient_id, update_condition.
    - 'create_nurse_call': Create nurse call. Requires: room, bed, patient_id, call_type.
    - 'acknowledge_nurse_call': Acknowledge a call. Requires: call_id, nurse.
    - 'resolve_nurse_call': Resolve a call. Requires: call_id.

    Args:
        action: The action to perform (see above).
        patient_id: Patient ID.
        room: Room number.
        condition: Patient condition filter.
        device_id: Medical device ID.
        device_type: Device type filter.
        device_status: Device status filter.
        sensor_id: Bed sensor ID.
        call_status: Nurse call status filter.
        settings: Device settings dict for set_device.
        update_condition: New patient condition for update_patient.
        bed: Bed letter for create_nurse_call.
        call_type: Call type for create_nurse_call (routine/urgent/emergency/bathroom/pain).
        call_id: Nurse call ID for acknowledge/resolve.
        nurse: Nurse name for acknowledge_nurse_call.
    """
    fault = await injector.maybe_raise(action)

    # -- Read actions --------------------------------------------------------
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
        result_dict: dict[str, Any] = {
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
            result_dict.pop("devices", None)
            result_dict.pop("bed_sensors", None)
        return result_dict

    # -- Write actions -------------------------------------------------------
    elif action == "set_device":
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
            "error": f"Unknown action '{action}'. Supported: list_patients, get_patient, "
            "get_vitals, list_devices, get_device, get_bed_sensor, list_nurse_calls, "
            "list_environment, ward_overview, set_device, update_patient, "
            "create_nurse_call, acknowledge_nurse_call, resolve_nurse_call."
        }


if __name__ == "__main__":
    mcp.run(transport="stdio")
