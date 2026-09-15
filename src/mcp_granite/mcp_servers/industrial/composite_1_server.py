"""Industrial IoT domain – Composite-1 MCP server (1 unified tool).

Run standalone:  python -m mcp_granite.mcp_servers.industrial.composite_1_server
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_granite.mcp_servers._base import (
    FaultConfig,
    FaultInjector,
    FaultType,
)
from mcp_granite.mcp_servers.industrial._store import IndustrialStore

mcp = FastMCP("industrial-composite-1")
store = IndustrialStore()
injector = FaultInjector(FaultConfig.from_env())


@mcp.tool()
async def industrial(
    action: str,
    machine_id: str | None = None,
    create_order: bool = True,
    priority: str = "medium",
    description: str | None = None,
    reason: str | None = None,
    alert_id: str | None = None,
    order_id: str | None = None,
    status: str | None = None,
    assigned_to: str | None = None,
) -> dict:
    """Unified industrial IoT interface. All monitoring and actions via a single tool.

    **Monitoring actions (read-only):**
    - 'machine_health': Full health report for a machine. Requires: machine_id.
    - 'floor_overview': Summary of all machines, alerts, and work orders.

    **Control actions:**
    - 'handle_fault': Diagnose fault, acknowledge alerts, create work order. Requires: machine_id. Optional: create_order, priority, description.
    - 'schedule_maintenance': Review history and create maintenance work order. Requires: machine_id. Optional: reason, priority.
    - 'acknowledge_alert': Mark an alert as acknowledged. Requires: alert_id.
    - 'update_work_order': Update work order status/assignment. Requires: order_id. Optional: status, assigned_to.

    Args:
        action: The action to perform (see above).
        machine_id: Machine ID (e.g. 'MC001').
        create_order: Whether to create work order for handle_fault (default True).
        priority: Work order priority (low/medium/high/critical).
        description: Work order description for handle_fault.
        reason: Maintenance reason for schedule_maintenance.
        alert_id: Alert ID for acknowledge_alert.
        order_id: Work order ID for update_work_order.
        status: New status for update_work_order.
        assigned_to: Assignee for update_work_order.
    """
    fault = await injector.maybe_raise(action)

    # ── Monitoring ────────────────────────────────────────────────────────
    if action == "machine_health":
        if not machine_id:
            return {"error": "machine_health requires 'machine_id'."}
        machine = store.get_machine_status(machine_id)
        if not machine:
            return {"error": f"Machine '{machine_id}' not found."}
        telemetry = store.read_telemetry(machine_id)
        thresholds = store.get_alert_thresholds(machine_id)
        alerts = store.get_active_alerts(machine_id)
        history = store.get_maintenance_history(machine_id)
        if any(a.severity == "critical" for a in alerts) or machine.status == "fault":
            health_score = "critical"
        elif alerts or machine.status == "warning":
            health_score = "warning"
        else:
            health_score = "good"
        last_maintenance = history[-1].model_dump() if history else None
        result: dict[str, Any] = {
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
            result["health_score"] = "good"
        return result

    elif action == "floor_overview":
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

    # ── Control actions ───────────────────────────────────────────────────
    elif action == "handle_fault":
        if not machine_id:
            return {"error": "handle_fault requires 'machine_id'."}
        machine = store.get_machine_status(machine_id)
        if not machine:
            return {"error": f"Machine '{machine_id}' not found."}
        telemetry = store.read_telemetry(machine_id)
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
        active_alerts = store.get_active_alerts(machine_id)
        acknowledged = []
        for alert in active_alerts:
            ack = store.acknowledge_alert(alert.alert_id)
            if ack:
                acknowledged.append(ack.model_dump())
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

    elif action == "schedule_maintenance":
        if not machine_id:
            return {"error": "schedule_maintenance requires 'machine_id'."}
        machine = store.get_machine_status(machine_id)
        if not machine:
            return {"error": f"Machine '{machine_id}' not found."}
        history = store.get_maintenance_history(machine_id)
        telemetry = store.read_telemetry(machine_id)
        desc = f"Scheduled maintenance: {reason or 'routine'}"
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

    elif action == "acknowledge_alert":
        if not alert_id:
            return {"error": "acknowledge_alert requires 'alert_id'."}
        ack = store.acknowledge_alert(alert_id)
        if not ack:
            return {"error": f"Alert '{alert_id}' not found or already acknowledged."}
        return {"alert": ack.model_dump()}

    elif action == "update_work_order":
        if not order_id:
            return {"error": "update_work_order requires 'order_id'."}
        wo = store.update_work_order(order_id, status=status, assigned_to=assigned_to)
        if not wo:
            return {"error": f"Work order '{order_id}' not found."}
        return {"work_order": wo.model_dump()}

    else:
        return {
            "error": f"Unknown action '{action}'. Supported: machine_health, floor_overview, "
            "handle_fault, schedule_maintenance, acknowledge_alert, update_work_order."
        }


if __name__ == "__main__":
    mcp.run(transport="stdio")
