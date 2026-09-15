"""Energy (microgrid) domain – Composite-4 MCP server (4 high-level tools).

Run standalone:  python -m mcp_granite.mcp_servers.energy.composite_4_server
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_granite.mcp_servers._base import (
    FaultConfig,
    FaultInjector,
    FaultType,
    corrupt_numeric_field,
)
from mcp_granite.mcp_servers.energy._store import EnergyStore

mcp = FastMCP("energy-composite-4")
store = EnergyStore()
injector = FaultInjector(FaultConfig.from_env())


@mcp.tool()
async def get_grid_overview() -> dict:
    """Get a complete overview of the microgrid including all sources, loads, batteries, and meters.

    Returns a dict with power sources, load zones, batteries, smart meters, and a summary
    including total generation, total load, net balance, and battery state.
    """
    fault = await injector.maybe_raise("get_grid_overview")

    sources = store.list_power_sources()
    loads = store.list_load_zones()
    batteries = store.list_batteries()
    meters = store.list_smart_meters()

    total_gen = sum(s.current_output_kw for s in sources)
    total_load = sum(z.current_load_kw for z in loads)
    total_battery_soc = (
        round(sum(b.soc_percent for b in batteries) / len(batteries), 1) if batteries else 0
    )

    result = {
        "power_sources": [s.model_dump() for s in sources],
        "load_zones": [z.model_dump() for z in loads],
        "batteries": [b.model_dump() for b in batteries],
        "smart_meters": [m.model_dump() for m in meters],
        "summary": {
            "total_generation_kw": total_gen,
            "total_load_kw": total_load,
            "net_balance_kw": round(total_gen - total_load, 2),
            "avg_battery_soc": total_battery_soc,
            "sources_online": sum(1 for s in sources if s.status == "online"),
            "zones_overloaded": sum(1 for z in loads if z.status == "overloaded"),
        },
    }

    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("power_sources", None)
        result.pop("smart_meters", None)
    elif fault == FaultType.CONTRADICTORY:
        result["summary"]["total_generation_kw"] = round(total_gen * 0.1, 1)

    return result


@mcp.tool()
async def manage_power(
    action: str,
    source_id: str | None = None,
    battery_id: str | None = None,
    status: str | None = None,
    output_kw: float | None = None,
    charge_rate_kw: float | None = None,
    discharge_rate_kw: float | None = None,
) -> dict:
    """Manage power sources and batteries.

    Args:
        action: One of 'source_status', 'set_source', 'battery_status', 'set_battery', 'list_batteries'.
        source_id: Power source ID.
        battery_id: Battery ID.
        status: New status value.
        output_kw: New output level (for sources).
        charge_rate_kw: New charge rate (for batteries).
        discharge_rate_kw: New discharge rate (for batteries).
    """
    fault = await injector.maybe_raise("manage_power")

    if action == "source_status":
        if source_id:
            source = store.get_power_source(source_id)
            if not source:
                return {"error": f"Power source '{source_id}' not found."}
            result = {"source": source.model_dump()}
            if fault == FaultType.CONTRADICTORY:
                result["source"] = corrupt_numeric_field(result["source"], "current_output_kw")
            return result
        sources = store.list_power_sources()
        result = {"sources": [s.model_dump() for s in sources]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["sources"] = result["sources"][:1]
        return result

    elif action == "set_source":
        if not source_id:
            return {"error": "set_source requires 'source_id'."}
        kwargs = {}
        if status is not None:
            kwargs["status"] = status
        if output_kw is not None:
            kwargs["current_output_kw"] = output_kw
        source = store.set_power_source(source_id, **kwargs)
        if not source:
            return {"error": f"Power source '{source_id}' not found."}
        result = {"action": "set_source", "source": source.model_dump()}
        if fault == FaultType.PARTIAL_RESPONSE:
            result.pop("source", None)
        return result

    elif action == "battery_status":
        if battery_id:
            battery = store.get_battery(battery_id)
            if not battery:
                return {"error": f"Battery '{battery_id}' not found."}
            result = {"battery": battery.model_dump()}
            if fault == FaultType.CONTRADICTORY:
                result["battery"] = corrupt_numeric_field(result["battery"], "soc_percent")
            return result
        batteries = store.list_batteries()
        result = {"batteries": [b.model_dump() for b in batteries]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["batteries"] = result["batteries"][:1]
        return result

    elif action == "set_battery":
        if not battery_id:
            return {"error": "set_battery requires 'battery_id'."}
        kwargs = {}
        if status is not None:
            kwargs["status"] = status
        if charge_rate_kw is not None:
            kwargs["charge_rate_kw"] = charge_rate_kw
        if discharge_rate_kw is not None:
            kwargs["discharge_rate_kw"] = discharge_rate_kw
        battery = store.set_battery(battery_id, **kwargs)
        if not battery:
            return {"error": f"Battery '{battery_id}' not found."}
        result = {"action": "set_battery", "battery": battery.model_dump()}
        if fault == FaultType.PARTIAL_RESPONSE:
            result.pop("battery", None)
        return result

    elif action == "list_batteries":
        batteries = store.list_batteries()
        return {"batteries": [b.model_dump() for b in batteries]}

    else:
        return {
            "error": f"Unknown action '{action}'. Supported: source_status, set_source, battery_status, set_battery, list_batteries."
        }


@mcp.tool()
async def handle_energy_alert(
    alert_id: str | None = None,
    severity: str | None = None,
    acknowledge: bool = False,
    corrective_actions: list[str] | None = None,
) -> dict:
    """View, acknowledge, and respond to energy alerts.

    Args:
        alert_id: Specific alert to handle.
        severity: Filter by severity.
        acknowledge: Whether to acknowledge the alert.
        corrective_actions: Actions to take: 'start_diesel', 'shed_load',
                           'switch_battery', 'island_mode', 'notify_operator'.
    """
    fault = await injector.maybe_raise("handle_energy_alert")

    if not alert_id:
        alerts = store.get_alerts(severity=severity)
        result = {"alerts": [a.model_dump() for a in alerts]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["alerts"] = result["alerts"][:1]
        return result

    alert = store.acknowledge_alert(alert_id) if acknowledge else None
    if not alert:
        for a in store.alerts:
            if a.alert_id == alert_id:
                alert = a
                break
    if not alert:
        return {"error": f"Alert '{alert_id}' not found."}

    actions_taken: list[dict] = []
    for act in corrective_actions or []:
        if act == "start_diesel":
            store.set_power_source("PS004", status="online", current_output_kw=150.0)
            actions_taken.append({"action": "start_diesel", "source": "PS004", "status": "started"})
        elif act == "shed_load":
            low_priority = [z for z in store.list_load_zones() if z.priority >= 4]
            for z in low_priority:
                store.set_load_zone(z.zone_id, status="shed")
                actions_taken.append({"action": "shed_load", "zone": z.name, "status": "shed"})
        elif act == "switch_battery":
            for b in store.list_batteries():
                if b.soc_percent > 50 and b.status != "discharging":
                    store.set_battery(b.battery_id, status="discharging")
                    actions_taken.append(
                        {"action": "switch_battery", "battery": b.name, "status": "discharging"}
                    )
        elif act == "island_mode":
            store.set_power_source("PS005", status="offline")
            actions_taken.append({"action": "island_mode", "grid_tie": "disconnected"})
        elif act == "notify_operator":
            actions_taken.append({"action": "notify_operator", "status": "notification_sent"})
        else:
            actions_taken.append({"action": act, "status": "unknown_action"})

    result = {
        "alert": alert.model_dump(),
        "acknowledged": alert.acknowledged,
        "actions_taken": actions_taken,
    }
    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("actions_taken", None)
    return result


@mcp.tool()
async def manage_load_schedule(
    action: str,
    zone_id: str | None = None,
    status: str | None = None,
    priority: int | None = None,
    current_load_kw: float | None = None,
    name: str | None = None,
    target_id: str | None = None,
    operation: str | None = None,
    scheduled_time: str | None = None,
    parameters: dict | None = None,
) -> dict:
    """Manage load zones and scheduling operations.

    Args:
        action: One of 'load_status', 'set_load', 'list_schedule', 'create_schedule'.
        zone_id: Load zone ID (for load operations).
        status: New status value.
        priority: New priority value.
        current_load_kw: New load value.
        name: Schedule entry name (for 'create_schedule').
        target_id: Target device/zone ID (for 'create_schedule').
        operation: Scheduled action (for 'create_schedule').
        scheduled_time: ISO datetime (for 'create_schedule').
        parameters: Additional parameters dict (for 'create_schedule').
    """
    fault = await injector.maybe_raise("manage_load_schedule")

    if action == "load_status":
        if zone_id:
            zone = store.get_load_zone(zone_id)
            if not zone:
                return {"error": f"Load zone '{zone_id}' not found."}
            return {"zone": zone.model_dump()}
        zones = store.list_load_zones()
        result = {"zones": [z.model_dump() for z in zones]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["zones"] = result["zones"][:1]
        return result

    elif action == "set_load":
        if not zone_id:
            return {"error": "set_load requires 'zone_id'."}
        kwargs = {}
        if status is not None:
            kwargs["status"] = status
        if priority is not None:
            kwargs["priority"] = priority
        if current_load_kw is not None:
            kwargs["current_load_kw"] = current_load_kw
        zone = store.set_load_zone(zone_id, **kwargs)
        if not zone:
            return {"error": f"Load zone '{zone_id}' not found."}
        result = {"action": "set_load", "zone": zone.model_dump()}
        if fault == FaultType.PARTIAL_RESPONSE:
            result.pop("zone", None)
        return result

    elif action == "list_schedule":
        entries = store.list_schedule()
        result = {"schedule": [e.model_dump() for e in entries]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["schedule"] = result["schedule"][:1]
        return result

    elif action == "create_schedule":
        if not all([name, target_id, operation, scheduled_time]):
            return {"error": "create_schedule requires name, target_id, operation, scheduled_time."}
        entry = store.create_schedule_entry(
            name, target_id, operation, scheduled_time, parameters or {}
        )
        result = {"action": "create_schedule", "entry": entry.model_dump()}
        if fault == FaultType.PARTIAL_RESPONSE:
            result.pop("entry", None)
        return result

    else:
        return {
            "error": f"Unknown action '{action}'. Supported: load_status, set_load, list_schedule, create_schedule."
        }


if __name__ == "__main__":
    mcp.run(transport="stdio")
