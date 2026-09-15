"""Fleet Management domain – Composite-1 MCP server (1 unified tool).

Run standalone:  python -m edgetoolbench.mcp_servers.fleet.composite_1_server
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
from edgetoolbench.mcp_servers.fleet._store import FleetStore

mcp = FastMCP("fleet-composite-1")
store = FleetStore()
injector = FaultInjector(FaultConfig.from_env())


@mcp.tool()
async def fleet(
    action: str,
    delivery_id: str | None = None,
    vehicle_type: str | None = None,
    preferred_driver: str | None = None,
    vehicle_id: str | None = None,
    reassign: bool = True,
) -> dict:
    """Unified fleet management interface. All queries and actions via a single tool.

    **Query actions (read-only):**
    - 'fleet_overview': Get all vehicles, drivers, active delivery counts.
    - 'delivery_summary': Full report for a delivery. Requires: delivery_id.

    **Control actions:**
    - 'dispatch': Dispatch a delivery with auto-selected vehicle/driver. Requires: delivery_id. Optional: vehicle_type, preferred_driver.
    - 'handle_issue': Diagnose vehicle and reassign affected deliveries. Requires: vehicle_id. Optional: reassign (default True).

    Args:
        action: The action to perform (see above).
        delivery_id: Delivery ID (e.g. 'DL001').
        vehicle_type: Vehicle type filter for dispatch (van/truck/motorcycle).
        preferred_driver: Preferred driver ID for dispatch.
        vehicle_id: Vehicle ID for handle_issue.
        reassign: Whether to reassign affected deliveries (default True).
    """
    fault = await injector.maybe_raise(action)

    # ── Queries ───────────────────────────────────────────────────────────
    if action == "fleet_overview":
        vehicles = store.list_vehicles()
        drivers = store.list_drivers()
        all_deliveries = list(store.deliveries.values())
        active_statuses = {"pending", "picked_up", "in_transit"}
        active_deliveries = [d for d in all_deliveries if d.status in active_statuses]
        vehicles_available = [v for v in vehicles if v.status == "available"]
        drivers_available = [d for d in drivers if d.status == "available"]
        result: dict[str, Any] = {
            "vehicles": [v.model_dump() for v in vehicles],
            "drivers": [d.model_dump() for d in drivers],
            "active_deliveries": len(active_deliveries),
            "vehicles_available": len(vehicles_available),
            "drivers_available": len(drivers_available),
        }
        if fault == FaultType.PARTIAL_RESPONSE:
            result.pop("vehicles", None)
            result.pop("drivers", None)
        return result

    elif action == "delivery_summary":
        if not delivery_id:
            return {"error": "delivery_summary requires 'delivery_id'."}
        delivery = store.get_delivery_status(delivery_id)
        if not delivery:
            return {"error": f"Delivery '{delivery_id}' not found."}
        vehicle = store.get_vehicle_status(delivery.vehicle_id) if delivery.vehicle_id else None
        driver = store.get_driver_info(delivery.driver_id) if delivery.driver_id else None
        route = store.get_route_info(delivery.pickup_location, delivery.dropoff_location)
        result = {
            "delivery": delivery.model_dump(),
            "vehicle": vehicle.model_dump() if vehicle else None,
            "driver": driver.model_dump() if driver else None,
            "route": route.model_dump() if route else None,
            "estimated_arrival": delivery.eta,
        }
        if fault == FaultType.PARTIAL_RESPONSE:
            result.pop("vehicle", None)
            result.pop("route", None)
        if fault == FaultType.CONTRADICTORY:
            result["delivery"]["status"] = "delivered"
        return result

    # ── Control actions ───────────────────────────────────────────────────
    elif action == "dispatch":
        if not delivery_id:
            return {"error": "dispatch requires 'delivery_id'."}
        delivery = store.get_delivery_status(delivery_id)
        if not delivery:
            return {"error": f"Delivery '{delivery_id}' not found."}
        available_vehicles = store.list_vehicles(status_filter="available")
        if vehicle_type:
            available_vehicles = [v for v in available_vehicles if v.vehicle_type == vehicle_type]
        if not available_vehicles:
            return {"error": "No available vehicles matching criteria."}
        vehicle = available_vehicles[0]
        if preferred_driver:
            driver = store.get_driver_info(preferred_driver)
            if not driver or driver.status != "available":
                return {"error": f"Preferred driver '{preferred_driver}' is not available."}
        else:
            available_drivers = store.list_drivers(status_filter="available")
            if not available_drivers:
                return {"error": "No available drivers."}
            driver = available_drivers[0]
        route = store.get_route_info(delivery.pickup_location, delivery.dropoff_location)
        assigned = store.assign_delivery(delivery_id, vehicle.vehicle_id, driver.driver_id)
        if not assigned:
            return {"error": "Failed to assign delivery."}
        result = {
            "delivery": assigned.model_dump(),
            "vehicle": vehicle.model_dump(),
            "driver": driver.model_dump(),
            "route": route.model_dump() if route else None,
            "status": "dispatched",
        }
        if fault == FaultType.PARTIAL_RESPONSE:
            result.pop("route", None)
        if fault == FaultType.CONTRADICTORY and result.get("route"):
            result["route"] = corrupt_numeric_field(result["route"], "distance_km")
        return result

    elif action == "handle_issue":
        if not vehicle_id:
            return {"error": "handle_issue requires 'vehicle_id'."}
        vehicle = store.get_vehicle_status(vehicle_id)
        if not vehicle:
            return {"error": f"Vehicle '{vehicle_id}' not found."}
        diagnostics = store.get_vehicle_diagnostics(vehicle_id)
        active_statuses = {"pending", "picked_up", "in_transit"}
        affected_deliveries = [
            d for d in store.deliveries.values()
            if d.vehicle_id == vehicle_id and d.status in active_statuses
        ]
        reassignments = []
        if reassign and affected_deliveries:
            vehicle.status = "maintenance"
            available_vehicles = store.list_vehicles(status_filter="available")
            for delivery in affected_deliveries:
                if not available_vehicles:
                    break
                new_vehicle = available_vehicles[0]
                delivery.vehicle_id = new_vehicle.vehicle_id
                new_vehicle.status = "en_route"
                reassignments.append({
                    "delivery_id": delivery.delivery_id,
                    "old_vehicle_id": vehicle_id,
                    "new_vehicle_id": new_vehicle.vehicle_id,
                })
                available_vehicles = available_vehicles[1:]
        result = {
            "vehicle": vehicle.model_dump(),
            "diagnostics": diagnostics.model_dump() if diagnostics else None,
            "affected_deliveries": [d.model_dump() for d in affected_deliveries],
            "reassignments": reassignments,
        }
        if fault == FaultType.PARTIAL_RESPONSE:
            result.pop("reassignments", None)
        if fault == FaultType.CONTRADICTORY and result.get("diagnostics"):
            result["diagnostics"]["alerts"] = []
        return result

    else:
        return {
            "error": f"Unknown action '{action}'. Supported: fleet_overview, delivery_summary, "
            "dispatch, handle_issue."
        }


if __name__ == "__main__":
    mcp.run(transport="stdio")
