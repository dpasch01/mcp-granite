"""Energy (microgrid) domain – Composite-2 MCP server (2 tools: query + control).

Run standalone:  python -m mcp_granite.mcp_servers.energy.composite_2_server
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
from mcp_granite.mcp_servers.energy._store import EnergyStore

mcp = FastMCP("energy-composite-2")
store = EnergyStore()
injector = FaultInjector(FaultConfig.from_env())


@mcp.tool()
async def energy_query(
    action: str,
    source_id: str | None = None,
    zone_id: str | None = None,
    battery_id: str | None = None,
    meter_id: str | None = None,
    severity: str | None = None,
    zone_type: str | None = None,
    meter_type: str | None = None,
    status: str | None = None,
    limit: int = 10,
) -> dict:
    """Read-only queries for the energy microgrid.

    Args:
        action: One of 'grid_overview', 'source_status', 'load_status',
                'battery_status', 'meter_reading', 'alerts', 'schedule'.
        source_id: Power source ID.
        zone_id: Load zone ID.
        battery_id: Battery ID.
        meter_id: Smart meter ID.
        severity: Alert severity filter.
        zone_type: Load zone type filter.
        meter_type: Smart meter type filter.
        status: Status filter for sources.
        limit: Max alert entries.
    """
    fault = await injector.maybe_raise(action)

    if action == "grid_overview":
        sources = store.list_power_sources()
        loads = store.list_load_zones()
        batteries = store.list_batteries()
        meters = store.list_smart_meters()
        total_gen = sum(s.current_output_kw for s in sources)
        total_load = sum(z.current_load_kw for z in loads)
        avg_soc = (
            round(sum(b.soc_percent for b in batteries) / len(batteries), 1) if batteries else 0
        )
        result: dict[str, Any] = {
            "power_sources": [s.model_dump() for s in sources],
            "load_zones": [z.model_dump() for z in loads],
            "batteries": [b.model_dump() for b in batteries],
            "smart_meters": [m.model_dump() for m in meters],
            "summary": {
                "total_generation_kw": total_gen,
                "total_load_kw": total_load,
                "net_balance_kw": round(total_gen - total_load, 2),
                "avg_battery_soc": avg_soc,
            },
        }
        if fault == FaultType.PARTIAL_RESPONSE:
            result.pop("power_sources", None)
        elif fault == FaultType.CONTRADICTORY:
            result["summary"]["total_generation_kw"] = round(total_gen * 0.1, 1)
        return result

    elif action == "source_status":
        if source_id:
            source = store.get_power_source(source_id)
            if not source:
                return {"error": f"Power source '{source_id}' not found."}
            result = {"source": source.model_dump()}
            if fault == FaultType.CONTRADICTORY:
                result["source"] = corrupt_numeric_field(result["source"], "current_output_kw")
            return result
        sources = store.list_power_sources(status)
        result = {"sources": [s.model_dump() for s in sources]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["sources"] = result["sources"][:1]
        return result

    elif action == "load_status":
        if zone_id:
            zone = store.get_load_zone(zone_id)
            if not zone:
                return {"error": f"Load zone '{zone_id}' not found."}
            return {"zone": zone.model_dump()}
        zones = store.list_load_zones(zone_type)
        result = {"zones": [z.model_dump() for z in zones]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["zones"] = result["zones"][:1]
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

    elif action == "meter_reading":
        if not meter_id:
            meters = store.list_smart_meters(meter_type)
            result = {"meters": [m.model_dump() for m in meters]}
            if fault == FaultType.PARTIAL_RESPONSE:
                result["meters"] = result["meters"][:1]
            return result
        meter = store.get_smart_meter(meter_id)
        if not meter:
            return {"error": f"Smart meter '{meter_id}' not found."}
        result = {"meter": meter.model_dump()}
        if fault == FaultType.CONTRADICTORY:
            result["meter"] = corrupt_numeric_field(result["meter"], "current_reading_kwh")
        return result

    elif action == "alerts":
        alerts = store.get_alerts(severity=severity, limit=limit)
        result = {"alerts": [a.model_dump() for a in alerts]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["alerts"] = result["alerts"][:1]
        return result

    elif action == "schedule":
        entries = store.list_schedule(status)
        result = {"schedule": [e.model_dump() for e in entries]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["schedule"] = result["schedule"][:1]
        return result

    else:
        return {
            "error": f"Unknown action '{action}'. Supported: grid_overview, source_status, "
            "load_status, battery_status, meter_reading, alerts, schedule."
        }


@mcp.tool()
async def energy_control(
    action: str,
    source_id: str | None = None,
    battery_id: str | None = None,
    zone_id: str | None = None,
    alert_id: str | None = None,
    status: str | None = None,
    output_kw: float | None = None,
    charge_rate_kw: float | None = None,
    discharge_rate_kw: float | None = None,
    priority: int | None = None,
    current_load_kw: float | None = None,
    acknowledge: bool = False,
    corrective_actions: list[str] | None = None,
    name: str | None = None,
    target_id: str | None = None,
    operation: str | None = None,
    scheduled_time: str | None = None,
    parameters: dict | None = None,
) -> dict:
    """Write/actuate changes in the energy microgrid.

    Args:
        action: One of 'set_source', 'set_battery', 'set_load',
                'handle_alert', 'create_schedule'.
        source_id: Power source ID.
        battery_id: Battery ID.
        zone_id: Load zone ID.
        alert_id: Alert ID.
        status: New status.
        output_kw: Source output.
        charge_rate_kw: Battery charge rate.
        discharge_rate_kw: Battery discharge rate.
        priority: Zone priority.
        current_load_kw: Zone load.
        acknowledge: Acknowledge alert.
        corrective_actions: Alert response actions.
        name: Schedule entry name.
        target_id: Schedule target.
        operation: Schedule operation.
        scheduled_time: Schedule time.
        parameters: Schedule parameters.
    """
    fault = await injector.maybe_raise(action)

    if action == "set_source":
        if not source_id:
            return {"error": "set_source requires 'source_id'."}
        kwargs: dict[str, Any] = {}
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

    elif action == "handle_alert":
        if not alert_id:
            return {"error": "handle_alert requires 'alert_id'."}
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
                actions_taken.append(
                    {"action": "start_diesel", "source": "PS004", "status": "started"}
                )
            elif act == "shed_load":
                for z in store.list_load_zones():
                    if z.priority >= 4:
                        store.set_load_zone(z.zone_id, status="shed")
                        actions_taken.append(
                            {"action": "shed_load", "zone": z.name, "status": "shed"}
                        )
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
            "error": f"Unknown action '{action}'. Supported: set_source, set_battery, set_load, "
            "handle_alert, create_schedule."
        }


if __name__ == "__main__":
    mcp.run(transport="stdio")
