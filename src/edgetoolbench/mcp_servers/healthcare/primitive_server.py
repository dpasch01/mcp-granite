"""Healthcare domain -- Primitive MCP server (10 fine-grained tools).

Run standalone:  python -m edgetoolbench.mcp_servers.healthcare.primitive_server
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from edgetoolbench.mcp_servers._base import (
    FaultConfig,
    FaultInjector,
    FaultType,
    corrupt_numeric_field,
    truncate_response,
)
from edgetoolbench.mcp_servers.healthcare._store import HealthcareStore

mcp = FastMCP("healthcare-primitive")
store = HealthcareStore()
injector = FaultInjector(FaultConfig.from_env())


# -- tools -------------------------------------------------------------------


@mcp.tool()
async def list_patients(room: str | None = None, condition: str | None = None) -> list[dict]:
    """List all patients in the ward, optionally filtered by room or condition."""
    fault = await injector.maybe_raise("list_patients")
    patients = store.list_patients(room=room, condition=condition)
    results = [p.model_dump() for p in patients]
    if fault == FaultType.PARTIAL_RESPONSE:
        return truncate_response(results)
    return results


@mcp.tool()
async def get_patient(patient_id: str) -> dict:
    """Get detailed information about a specific patient."""
    fault = await injector.maybe_raise("get_patient")
    patient = store.get_patient(patient_id)
    if not patient:
        return {"error": f"Patient '{patient_id}' not found."}
    result = patient.model_dump()
    if fault == FaultType.CONTRADICTORY:
        result["condition"] = "stable" if result["condition"] == "critical" else "critical"
    return result


@mcp.tool()
async def get_vitals(patient_id: str | None = None) -> list[dict]:
    """Get vital sign readings, optionally filtered by patient ID."""
    fault = await injector.maybe_raise("get_vitals")
    vitals = store.list_vitals(patient_id=patient_id)
    results = [v.model_dump() for v in vitals]
    if fault == FaultType.PARTIAL_RESPONSE:
        return truncate_response(results)
    if fault == FaultType.CONTRADICTORY:
        return [corrupt_numeric_field(r, "value") for r in results]
    return results


@mcp.tool()
async def list_devices(
    room: str | None = None,
    device_type: str | None = None,
    status: str | None = None,
) -> list[dict]:
    """List all medical devices, optionally filtered by room, device type, or status."""
    fault = await injector.maybe_raise("list_devices")
    devices = store.list_devices(room=room, device_type=device_type, status=status)
    results = [d.model_dump() for d in devices]
    if fault == FaultType.PARTIAL_RESPONSE:
        return truncate_response(results)
    return results


@mcp.tool()
async def set_device(device_id: str, settings: dict) -> dict:
    """Update settings for a specific medical device (e.g. mode, rate, thresholds, status)."""
    fault = await injector.maybe_raise("set_device")
    device = store.set_device(device_id, settings)
    if not device:
        return {"error": f"Device '{device_id}' not found."}
    result = device.model_dump()
    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("settings", None)
    return result


@mcp.tool()
async def get_bed_sensor(sensor_id: str | None = None, room: str | None = None) -> list[dict]:
    """Get bed sensor data. Provide sensor_id for one sensor or room for all sensors in a room."""
    fault = await injector.maybe_raise("get_bed_sensor")
    if sensor_id:
        sensor = store.get_bed_sensor(sensor_id)
        if not sensor:
            return [{"error": f"Bed sensor '{sensor_id}' not found."}]
        results = [sensor.model_dump()]
    else:
        sensors = store.list_bed_sensors(room=room)
        results = [s.model_dump() for s in sensors]
    if fault == FaultType.PARTIAL_RESPONSE:
        return truncate_response(results)
    if fault == FaultType.CONTRADICTORY:
        return [corrupt_numeric_field(r, "weight_kg") for r in results]
    return results


@mcp.tool()
async def list_nurse_calls(status: str | None = None, room: str | None = None) -> list[dict]:
    """List nurse calls, optionally filtered by status (active/acknowledged/resolved) or room."""
    fault = await injector.maybe_raise("list_nurse_calls")
    calls = store.list_nurse_calls(status=status, room=room)
    results = [c.model_dump() for c in calls]
    if fault == FaultType.PARTIAL_RESPONSE:
        return truncate_response(results)
    return results


@mcp.tool()
async def create_nurse_call(room: str, bed: str, patient_id: str, call_type: str) -> dict:
    """Create a new nurse call (routine/urgent/emergency/bathroom/pain)."""
    await injector.maybe_raise("create_nurse_call")
    call = store.create_nurse_call(room=room, bed=bed, patient_id=patient_id, call_type=call_type)
    return call.model_dump()


@mcp.tool()
async def acknowledge_nurse_call(call_id: str, nurse: str) -> dict:
    """Acknowledge a nurse call and assign a nurse to respond."""
    await injector.maybe_raise("acknowledge_nurse_call")
    call = store.acknowledge_nurse_call(call_id, nurse)
    if not call:
        return {"error": f"Nurse call '{call_id}' not found."}
    return call.model_dump()


@mcp.tool()
async def list_environment(room: str | None = None) -> list[dict]:
    """List environment readings (temperature, humidity, air pressure, noise level) for rooms."""
    fault = await injector.maybe_raise("list_environment")
    readings = store.list_environment_readings(room=room)
    results = [r.model_dump() for r in readings]
    if fault == FaultType.PARTIAL_RESPONSE:
        return truncate_response(results)
    if fault == FaultType.CONTRADICTORY:
        return [corrupt_numeric_field(r, "value") for r in results]
    return results


if __name__ == "__main__":
    mcp.run(transport="stdio")
