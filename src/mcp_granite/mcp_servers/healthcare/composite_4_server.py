"""Healthcare domain -- Composite MCP server (4 high-level tools).

Run standalone:  python -m mcp_granite.mcp_servers.healthcare.composite_4_server
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

mcp = FastMCP("healthcare-composite-4")
store = HealthcareStore()
injector = FaultInjector(FaultConfig.from_env())


@mcp.tool()
async def get_ward_overview(room: str | None = None, condition: str | None = None) -> dict:
    """Get a complete ward overview including patients, devices, bed sensors, and environment.

    Args:
        room: Optional room number to filter (e.g. '101'). If omitted, returns all rooms.
        condition: Optional patient condition filter (stable/critical/recovering/observation).

    Returns a dict with patients, devices, bed_sensors, environment, and a ward summary.
    """
    fault = await injector.maybe_raise("get_ward_overview")

    patients = store.list_patients(room=room, condition=condition)
    devices = store.list_devices(room=room)
    bed_sensors = store.list_bed_sensors(room=room)
    env_readings = store.list_environment_readings(room=room)
    nurse_calls = store.list_nurse_calls(room=room)

    critical_patients = [p for p in patients if p.condition == "critical"]
    active_calls = [c for c in nurse_calls if c.status == "active"]
    faulty_devices = [d for d in devices if d.status in ("fault", "alarm")]

    result: dict[str, Any] = {
        "patients": [p.model_dump() for p in patients],
        "devices": [d.model_dump() for d in devices],
        "bed_sensors": [s.model_dump() for s in bed_sensors],
        "environment": [r.model_dump() for r in env_readings],
        "nurse_calls": [c.model_dump() for c in nurse_calls],
        "summary": {
            "total_patients": len(patients),
            "critical_patients": len(critical_patients),
            "active_nurse_calls": len(active_calls),
            "faulty_devices": len(faulty_devices),
            "occupied_beds": sum(1 for s in bed_sensors if s.occupied),
            "total_beds": len(bed_sensors),
        },
    }

    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("devices", None)
        result.pop("bed_sensors", None)
    elif fault == FaultType.CONTRADICTORY:
        result["summary"]["critical_patients"] = 0

    return result


@mcp.tool()
async def manage_devices(
    action: str,
    device_id: str | None = None,
    room: str | None = None,
    device_type: str | None = None,
    status_filter: str | None = None,
    settings: dict | None = None,
) -> dict:
    """List, inspect, or update medical devices.

    Args:
        action: One of 'list', 'get', 'update'.
        device_id: Device ID (required for 'get' and 'update').
        room: Room filter (for 'list').
        device_type: Device type filter (for 'list').
        status_filter: Device status filter (for 'list').
        settings: New settings dict to merge (for 'update'). Can include 'status'.

    Returns device data or a list of devices.
    """
    fault = await injector.maybe_raise("manage_devices")

    if action == "list":
        devices = store.list_devices(room=room, device_type=device_type, status=status_filter)
        results = [d.model_dump() for d in devices]
        if fault == FaultType.PARTIAL_RESPONSE:
            results = results[:1]
        return {"devices": results, "total": len(results)}

    elif action == "get":
        if not device_id:
            return {"error": "get requires 'device_id'."}
        device = store.get_device(device_id)
        if not device:
            return {"error": f"Device '{device_id}' not found."}
        result = device.model_dump()
        if fault == FaultType.CONTRADICTORY:
            result["status"] = "active" if result["status"] != "active" else "fault"
        return {"device": result}

    elif action == "update":
        if not device_id or settings is None:
            return {"error": "update requires 'device_id' and 'settings'."}
        device = store.set_device(device_id, settings)
        if not device:
            return {"error": f"Device '{device_id}' not found."}
        result = device.model_dump()
        if fault == FaultType.PARTIAL_RESPONSE:
            result.pop("settings", None)
        return {"device": result, "action": "updated"}

    else:
        return {"error": f"Unknown action '{action}'. Supported: list, get, update."}


@mcp.tool()
async def handle_nurse_call(
    action: str,
    call_id: str | None = None,
    room: str | None = None,
    bed: str | None = None,
    patient_id: str | None = None,
    call_type: str | None = None,
    nurse: str | None = None,
    status_filter: str | None = None,
) -> dict:
    """Manage nurse calls: list, create, acknowledge, or resolve.

    Args:
        action: One of 'list', 'create', 'acknowledge', 'resolve'.
        call_id: Call ID (for 'acknowledge' and 'resolve').
        room: Room number (for 'list' filter or 'create').
        bed: Bed letter (for 'create').
        patient_id: Patient ID (for 'create').
        call_type: Call type (for 'create'): routine/urgent/emergency/bathroom/pain.
        nurse: Nurse name (for 'acknowledge').
        status_filter: Status filter (for 'list'): active/acknowledged/resolved.

    Returns call data or a list of calls.
    """
    fault = await injector.maybe_raise("handle_nurse_call")

    if action == "list":
        calls = store.list_nurse_calls(status=status_filter, room=room)
        results = [c.model_dump() for c in calls]
        if fault == FaultType.PARTIAL_RESPONSE:
            results = results[:1]
        return {"nurse_calls": results, "total": len(results)}

    elif action == "create":
        if not room or not bed or not patient_id or not call_type:
            return {"error": "create requires 'room', 'bed', 'patient_id', and 'call_type'."}
        call = store.create_nurse_call(
            room=room, bed=bed, patient_id=patient_id, call_type=call_type
        )
        return {"call": call.model_dump(), "action": "created"}

    elif action == "acknowledge":
        if not call_id or not nurse:
            return {"error": "acknowledge requires 'call_id' and 'nurse'."}
        call = store.acknowledge_nurse_call(call_id, nurse)
        if not call:
            return {"error": f"Nurse call '{call_id}' not found."}
        result = call.model_dump()
        return {"call": result, "action": "acknowledged"}

    elif action == "resolve":
        if not call_id:
            return {"error": "resolve requires 'call_id'."}
        call = store.resolve_nurse_call(call_id)
        if not call:
            return {"error": f"Nurse call '{call_id}' not found."}
        return {"call": call.model_dump(), "action": "resolved"}

    else:
        return {
            "error": f"Unknown action '{action}'. Supported: list, create, acknowledge, resolve."
        }


@mcp.tool()
async def monitor_patient(
    patient_id: str,
    include_vitals: bool = True,
    include_bed_sensor: bool = True,
    include_devices: bool = True,
    update_condition: str | None = None,
) -> dict:
    """Get comprehensive monitoring data for a specific patient and optionally update condition.

    Args:
        patient_id: The patient ID to monitor.
        include_vitals: Whether to include vital sign readings (default True).
        include_bed_sensor: Whether to include bed sensor data (default True).
        include_devices: Whether to include assigned device data (default True).
        update_condition: If provided, update the patient's condition
                         (stable/critical/recovering/observation).

    Returns a dict with patient info, vitals, bed sensor, and device data.
    """
    fault = await injector.maybe_raise("monitor_patient")

    patient = store.get_patient(patient_id)
    if not patient:
        return {"error": f"Patient '{patient_id}' not found."}

    if update_condition:
        store.update_patient(patient_id, condition=update_condition)
        patient = store.get_patient(patient_id)

    result: dict[str, Any] = {"patient": patient.model_dump()}

    if include_vitals:
        vitals = store.list_vitals(patient_id=patient_id)
        result["vitals"] = [v.model_dump() for v in vitals]
        critical_vitals = [v for v in vitals if v.status == "critical"]
        result["critical_vitals"] = len(critical_vitals)

    if include_bed_sensor:
        bed_sensors = store.list_bed_sensors(room=patient.room)
        matching = [s for s in bed_sensors if s.patient_id == patient_id]
        result["bed_sensor"] = matching[0].model_dump() if matching else None

    if include_devices:
        devices = store.list_devices(room=patient.room)
        assigned = [d for d in devices if d.patient_id == patient_id]
        result["devices"] = [d.model_dump() for d in assigned]

    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("vitals", None)
        result.pop("bed_sensor", None)
    elif fault == FaultType.CONTRADICTORY:
        if "vitals" in result:
            result["vitals"] = [corrupt_numeric_field(v, "value") for v in result["vitals"]]

    return result


if __name__ == "__main__":
    mcp.run(transport="stdio")
