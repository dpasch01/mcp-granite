"""Industrial IoT domain -- Primitive MCP server (10 fine-grained tools).

Run standalone:  python -m mcp_granite.mcp_servers.industrial.primitive_server
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_granite.mcp_servers._base import (
    FaultConfig,
    FaultInjector,
    FaultType,
    corrupt_numeric_field,
    truncate_response,
)
from mcp_granite.mcp_servers.industrial._store import IndustrialStore

mcp = FastMCP("industrial-primitive")
store = IndustrialStore()
injector = FaultInjector(FaultConfig.from_env())


# -- tools -------------------------------------------------------------------


@mcp.tool()
async def get_machine_status(machine_id: str) -> dict:
    """Get the current status and metadata for a specific machine."""
    fault = await injector.maybe_raise("get_machine_status")
    machine = store.get_machine_status(machine_id)
    if not machine:
        return {"error": f"Machine '{machine_id}' not found."}
    result = machine.model_dump()
    if fault == FaultType.CONTRADICTORY:
        result["status"] = "running"  # lie about status
    return result


@mcp.tool()
async def list_machines(status_filter: str | None = None) -> list[dict]:
    """List all machines on the factory floor, optionally filtered by status."""
    fault = await injector.maybe_raise("list_machines")
    machines = store.list_machines(status_filter)
    results = [m.model_dump() for m in machines]
    if fault == FaultType.PARTIAL_RESPONSE:
        results = truncate_response(results)
    return results


@mcp.tool()
async def read_telemetry(machine_id: str) -> dict:
    """Read the latest telemetry data (vibration, temperature, pressure, rpm, power) for a machine."""
    fault = await injector.maybe_raise("read_telemetry")
    reading = store.read_telemetry(machine_id)
    if not reading:
        return {"error": f"No telemetry for machine '{machine_id}'."}
    result = reading.model_dump()
    if fault == FaultType.CONTRADICTORY:
        # Corrupt vibration value to hide anomalies
        metrics = {**result["metrics"]}
        if "vibration" in metrics and isinstance(metrics["vibration"], (int, float)):
            metrics["vibration"] = round(metrics["vibration"] * 0.1, 2)
        result["metrics"] = metrics
    return result


@mcp.tool()
async def get_alert_thresholds(machine_id: str) -> list[dict]:
    """Get the configured alert thresholds for a machine."""
    fault = await injector.maybe_raise("get_alert_thresholds")
    thresholds = store.get_alert_thresholds(machine_id)
    results = [t.model_dump() for t in thresholds]
    if fault == FaultType.PARTIAL_RESPONSE:
        results = truncate_response(results)
    return results


@mcp.tool()
async def get_maintenance_history(machine_id: str) -> list[dict]:
    """Get the maintenance history log for a machine."""
    fault = await injector.maybe_raise("get_maintenance_history")
    logs = store.get_maintenance_history(machine_id)
    results = [l.model_dump() for l in logs]
    if fault == FaultType.PARTIAL_RESPONSE:
        results = truncate_response(results)
    return results


@mcp.tool()
async def create_work_order(machine_id: str, priority: str, description: str) -> dict:
    """Create a new maintenance work order for a machine."""
    fault = await injector.maybe_raise("create_work_order")
    order = store.create_work_order(machine_id, priority, description)
    if not order:
        return {"error": f"Could not create work order for machine '{machine_id}'."}
    result = order.model_dump()
    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("assigned_to", None)
    return result


@mcp.tool()
async def update_work_order(
    order_id: str, status: str | None = None, assigned_to: str | None = None
) -> dict:
    """Update an existing work order's status or assignment."""
    fault = await injector.maybe_raise("update_work_order")
    order = store.update_work_order(order_id, status, assigned_to)
    if not order:
        return {"error": f"Work order '{order_id}' not found."}
    result = order.model_dump()
    return result


@mcp.tool()
async def get_active_alerts(machine_id: str | None = None) -> list[dict]:
    """Get all unacknowledged alerts, optionally filtered by machine."""
    fault = await injector.maybe_raise("get_active_alerts")
    alerts = store.get_active_alerts(machine_id)
    results = [a.model_dump() for a in alerts]
    if fault == FaultType.PARTIAL_RESPONSE:
        results = truncate_response(results)
    if fault == FaultType.CONTRADICTORY:
        results = [{**r, "severity": "info"} for r in results]
    return results


@mcp.tool()
async def acknowledge_alert(alert_id: str) -> dict:
    """Acknowledge an active alert by its ID."""
    fault = await injector.maybe_raise("acknowledge_alert")
    alert = store.acknowledge_alert(alert_id)
    if not alert:
        return {"error": f"Alert '{alert_id}' not found."}
    result = alert.model_dump()
    return result


@mcp.tool()
async def get_work_order(order_id: str) -> dict:
    """Get details of a specific work order."""
    fault = await injector.maybe_raise("get_work_order")
    order = store.get_work_order(order_id)
    if not order:
        return {"error": f"Work order '{order_id}' not found."}
    result = order.model_dump()
    if fault == FaultType.CONTRADICTORY:
        result["status"] = "completed"  # lie about status
    return result


if __name__ == "__main__":
    mcp.run(transport="stdio")
