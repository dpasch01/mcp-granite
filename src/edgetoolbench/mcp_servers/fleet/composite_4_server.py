"""Fleet Management domain -- Composite MCP server (4 high-level tools).

Run standalone:  python -m edgetoolbench.mcp_servers.fleet.composite_4_server
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from edgetoolbench.mcp_servers._base import (
    FaultConfig,
    FaultInjector,
    FaultType,
    corrupt_numeric_field,
)
from edgetoolbench.mcp_servers.fleet._store import FleetStore

mcp = FastMCP("fleet-composite")
store = FleetStore()
injector = FaultInjector(FaultConfig.from_env())


@mcp.tool()
async def dispatch_delivery(
    delivery_id: str,
    vehicle_type: str | None = None,
    preferred_driver: str | None = None,
) -> dict:
    """Dispatch a pending delivery by finding an available vehicle and driver, checking the route, and assigning everything in one step.

    Args:
        delivery_id: The ID of the delivery to dispatch.
        vehicle_type: Optional vehicle type filter (van, truck, motorcycle).
        preferred_driver: Optional preferred driver ID.
    """
    fault = await injector.maybe_raise("dispatch_delivery")

    delivery = store.get_delivery_status(delivery_id)
    if not delivery:
        return {"error": f"Delivery '{delivery_id}' not found."}

    # Find an available vehicle, optionally filtered by type
    available_vehicles = store.list_vehicles(status_filter="available")
    if vehicle_type:
        available_vehicles = [v for v in available_vehicles if v.vehicle_type == vehicle_type]
    if not available_vehicles:
        return {"error": "No available vehicles matching criteria."}
    vehicle = available_vehicles[0]

    # Find an available driver (prefer specified, else first available)
    if preferred_driver:
        driver = store.get_driver_info(preferred_driver)
        if not driver or driver.status != "available":
            return {"error": f"Preferred driver '{preferred_driver}' is not available."}
    else:
        available_drivers = store.list_drivers(status_filter="available")
        if not available_drivers:
            return {"error": "No available drivers."}
        driver = available_drivers[0]

    # Check route
    route = store.get_route_info(delivery.pickup_location, delivery.dropoff_location)

    # Assign delivery
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


@mcp.tool()
async def get_fleet_overview() -> dict:
    """Get a complete overview of the fleet: all vehicles, drivers, active delivery counts, and availability summary.
    """
    fault = await injector.maybe_raise("get_fleet_overview")

    vehicles = store.list_vehicles()
    drivers = store.list_drivers()
    all_deliveries = list(store.deliveries.values())

    active_statuses = {"pending", "picked_up", "in_transit"}
    active_deliveries = [d for d in all_deliveries if d.status in active_statuses]
    vehicles_available = [v for v in vehicles if v.status == "available"]
    drivers_available = [d for d in drivers if d.status == "available"]

    result = {
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


@mcp.tool()
async def handle_vehicle_issue(vehicle_id: str, reassign: bool = True) -> dict:
    """Check vehicle diagnostics, find affected deliveries, and optionally reassign them to another vehicle.

    Args:
        vehicle_id: The vehicle to inspect.
        reassign: If True, attempt to reassign affected deliveries to another available vehicle.
    """
    fault = await injector.maybe_raise("handle_vehicle_issue")

    vehicle = store.get_vehicle_status(vehicle_id)
    if not vehicle:
        return {"error": f"Vehicle '{vehicle_id}' not found."}

    diagnostics = store.get_vehicle_diagnostics(vehicle_id)

    # Find deliveries currently assigned to this vehicle that are not yet delivered
    active_statuses = {"pending", "picked_up", "in_transit"}
    affected_deliveries = [
        d for d in store.deliveries.values()
        if d.vehicle_id == vehicle_id and d.status in active_statuses
    ]

    reassignments = []
    if reassign and affected_deliveries:
        # Mark vehicle as maintenance
        vehicle.status = "maintenance"

        # Find another available vehicle
        available_vehicles = store.list_vehicles(status_filter="available")
        for delivery in affected_deliveries:
            if not available_vehicles:
                break
            new_vehicle = available_vehicles[0]
            # Reassign the delivery to new vehicle
            delivery.vehicle_id = new_vehicle.vehicle_id
            new_vehicle.status = "en_route"
            reassignments.append({
                "delivery_id": delivery.delivery_id,
                "old_vehicle_id": vehicle_id,
                "new_vehicle_id": new_vehicle.vehicle_id,
            })
            # Remove from available pool for subsequent iterations
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


@mcp.tool()
async def get_delivery_summary(delivery_id: str) -> dict:
    """Get a full delivery report including delivery status, assigned vehicle, driver info, and route details.

    Args:
        delivery_id: The delivery to summarise.
    """
    fault = await injector.maybe_raise("get_delivery_summary")

    delivery = store.get_delivery_status(delivery_id)
    if not delivery:
        return {"error": f"Delivery '{delivery_id}' not found."}

    vehicle = store.get_vehicle_status(delivery.vehicle_id) if delivery.vehicle_id else None
    driver = store.get_driver_info(delivery.driver_id) if delivery.driver_id else None
    route = store.get_route_info(delivery.pickup_location, delivery.dropoff_location)

    result: dict = {
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


if __name__ == "__main__":
    mcp.run(transport="stdio")
