"""Industrial IoT domain -- Composite MCP server (4 high-level tools).

Run standalone:  python -m mcp_granite.mcp_servers.industrial.composite_4_server
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_granite.mcp_servers._base import (
    FaultConfig,
    FaultInjector,
    FaultType,
)
from mcp_granite.mcp_servers.industrial._store import IndustrialStore

mcp = FastMCP("industrial-composite")
store = IndustrialStore()
injector = FaultInjector(FaultConfig.from_env())


@mcp.tool()
async def assess_machine_health(machine_id: str) -> dict:
    """Generate a full health report for a machine combining status, telemetry, thresholds, alerts, and maintenance history.

    Args:
        machine_id: The machine identifier (e.g. 'MC001').
    """
    fault = await injector.maybe_raise("assess_machine_health")

    machine = store.get_machine_status(machine_id)
    if not machine:
        return {"error": f"Machine '{machine_id}' not found."}

    telemetry = store.read_telemetry(machine_id)
    thresholds = store.get_alert_thresholds(machine_id)
    alerts = store.get_active_alerts(machine_id)
    history = store.get_maintenance_history(machine_id)

    # Determine health score based on alerts and machine status
    if any(a.severity == "critical" for a in alerts) or machine.status == "fault":
        health_score = "critical"
    elif alerts or machine.status == "warning":
        health_score = "warning"
    else:
        health_score = "good"

    # Pick the most recent maintenance log if available
    last_maintenance = history[-1].model_dump() if history else None

    result = {
        "machine": machine.model_dump(),
        "telemetry": telemetry.model_dump() if telemetry else None,
        "thresholds": [t.model_dump() for t in thresholds],
        "alerts": [a.model_dump() for a in alerts],
        "last_maintenance": last_maintenance,
        "health_score": health_score,
    }

    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("telemetry", None)
        result.pop("alerts", None)
    elif fault == FaultType.CONTRADICTORY:
        result["health_score"] = "good"  # lie about health

    return result


@mcp.tool()
async def handle_fault(
    machine_id: str,
    create_order: bool = True,
    priority: str = "high",
    description: str | None = None,
) -> dict:
    """Diagnose a machine fault: gather status and telemetry, acknowledge all alerts, and optionally create a work order.

    Args:
        machine_id: The machine identifier (e.g. 'MC003').
        create_order: Whether to create a maintenance work order (default True).
        priority: Work order priority (low/medium/high/critical).
        description: Work order description (auto-generated if omitted).
    """
    fault = await injector.maybe_raise("handle_fault")

    machine = store.get_machine_status(machine_id)
    if not machine:
        return {"error": f"Machine '{machine_id}' not found."}

    telemetry = store.read_telemetry(machine_id)

    # Build diagnosis from telemetry
    diagnosis_notes: list[str] = []
    if telemetry:
        metrics = telemetry.metrics
        thresholds = store.get_alert_thresholds(machine_id)
        for th in thresholds:
            val = metrics.get(th.metric)
            if val is not None and th.max_value is not None and val > th.max_value:
                diagnosis_notes.append(
                    f"{th.metric} ({val}) exceeds threshold ({th.max_value}) [{th.severity}]"
                )
            if val is not None and th.min_value is not None and val < th.min_value:
                diagnosis_notes.append(
                    f"{th.metric} ({val}) below threshold ({th.min_value}) [{th.severity}]"
                )

    diagnosis = "; ".join(diagnosis_notes) if diagnosis_notes else "No threshold violations detected."

    # Acknowledge all active alerts for this machine
    active_alerts = store.get_active_alerts(machine_id)
    acknowledged = []
    for alert in active_alerts:
        ack = store.acknowledge_alert(alert.alert_id)
        if ack:
            acknowledged.append(ack.model_dump())

    # Optionally create a work order
    work_order = None
    if create_order:
        desc = description or f"Fault diagnosis for {machine.name}: {diagnosis}"
        wo = store.create_work_order(machine_id, priority, desc)
        if wo:
            work_order = wo.model_dump()

    result = {
        "machine_status": machine.model_dump(),
        "diagnosis": diagnosis,
        "alerts_acknowledged": acknowledged,
        "work_order": work_order,
    }

    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("work_order", None)

    return result


@mcp.tool()
async def get_floor_overview() -> dict:
    """Get a summary of the entire factory floor: all machines, active alert count, open work orders, and machines in fault state."""
    fault = await injector.maybe_raise("get_floor_overview")

    all_machines = store.list_machines()
    active_alerts = store.get_active_alerts()
    open_orders = [
        wo for wo in store.work_orders.values()
        if wo.status in ("open", "in_progress")
    ]
    machines_in_fault = [
        m.machine_id for m in all_machines
        if m.status in ("fault", "warning")
    ]

    result = {
        "machines": [m.model_dump() for m in all_machines],
        "total_alerts": len(active_alerts),
        "open_work_orders": len(open_orders),
        "machines_in_fault": machines_in_fault,
    }

    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("machines", None)

    return result


@mcp.tool()
async def schedule_maintenance(
    machine_id: str, reason: str, priority: str = "medium"
) -> dict:
    """Review maintenance history and current telemetry, then create a maintenance work order.

    Args:
        machine_id: The machine identifier (e.g. 'MC001').
        reason: Reason for scheduling maintenance.
        priority: Work order priority (low/medium/high/critical).
    """
    fault = await injector.maybe_raise("schedule_maintenance")

    machine = store.get_machine_status(machine_id)
    if not machine:
        return {"error": f"Machine '{machine_id}' not found."}

    history = store.get_maintenance_history(machine_id)
    telemetry = store.read_telemetry(machine_id)

    # Create the maintenance work order
    desc = f"Scheduled maintenance: {reason}"
    wo = store.create_work_order(machine_id, priority, desc)

    result = {
        "machine": machine.model_dump(),
        "history": [h.model_dump() for h in history],
        "telemetry": telemetry.model_dump() if telemetry else None,
        "work_order": wo.model_dump() if wo else None,
    }

    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("history", None)

    return result


if __name__ == "__main__":
    mcp.run(transport="stdio")
