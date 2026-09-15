"""Fleet Management domain -- Primitive MCP server (10 fine-grained tools).

Run standalone:  python -m edgetoolbench.mcp_servers.fleet.primitive_server
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
from edgetoolbench.mcp_servers.fleet._store import FleetStore

mcp = FastMCP("fleet-primitive")
store = FleetStore()
injector = FaultInjector(FaultConfig.from_env())


# ── tools ────────────────────────────────────────────────────────────────────


@mcp.tool()
async def get_vehicle_status(vehicle_id: str) -> dict:
    """Get the current status and details of a specific vehicle."""
    fault = await injector.maybe_raise("get_vehicle_status")
    vehicle = store.get_vehicle_status(vehicle_id)
    if not vehicle:
        return {"error": f"Vehicle '{vehicle_id}' not found."}
    result = vehicle.model_dump()
    if fault == FaultType.CONTRADICTORY:
        result["fuel_level"] = 100.0
    return result


@mcp.tool()
async def list_vehicles(status_filter: str | None = None) -> list[dict]:
    """List all vehicles in the fleet, optionally filtered by status."""
    fault = await injector.maybe_raise("list_vehicles")
    vehicles = store.list_vehicles(status_filter)
    results = [v.model_dump() for v in vehicles]
    if fault == FaultType.PARTIAL_RESPONSE:
        results = truncate_response(results)
    return results


@mcp.tool()
async def get_vehicle_diagnostics(vehicle_id: str) -> dict:
    """Get diagnostic data for a specific vehicle including engine, tires, brakes, and battery."""
    fault = await injector.maybe_raise("get_vehicle_diagnostics")
    diag = store.get_vehicle_diagnostics(vehicle_id)
    if not diag:
        return {"error": f"Diagnostics for vehicle '{vehicle_id}' not found."}
    result = diag.model_dump()
    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("alerts", None)
    if fault == FaultType.CONTRADICTORY:
        result = corrupt_numeric_field(result, "engine_temp")
    return result


@mcp.tool()
async def get_driver_info(driver_id: str) -> dict:
    """Get information about a specific driver."""
    fault = await injector.maybe_raise("get_driver_info")
    driver = store.get_driver_info(driver_id)
    if not driver:
        return {"error": f"Driver '{driver_id}' not found."}
    result = driver.model_dump()
    if fault == FaultType.CONTRADICTORY:
        result["status"] = "available"
    return result


@mcp.tool()
async def list_drivers(status_filter: str | None = None) -> list[dict]:
    """List all drivers, optionally filtered by status."""
    fault = await injector.maybe_raise("list_drivers")
    drivers = store.list_drivers(status_filter)
    results = [d.model_dump() for d in drivers]
    if fault == FaultType.PARTIAL_RESPONSE:
        results = truncate_response(results)
    return results


@mcp.tool()
async def get_delivery_status(delivery_id: str) -> dict:
    """Get the current status of a delivery."""
    fault = await injector.maybe_raise("get_delivery_status")
    delivery = store.get_delivery_status(delivery_id)
    if not delivery:
        return {"error": f"Delivery '{delivery_id}' not found."}
    result = delivery.model_dump()
    if fault == FaultType.CONTRADICTORY:
        result["status"] = "delivered"
    return result


@mcp.tool()
async def assign_delivery(delivery_id: str, vehicle_id: str, driver_id: str) -> dict:
    """Assign a vehicle and driver to a pending delivery."""
    fault = await injector.maybe_raise("assign_delivery")
    delivery = store.assign_delivery(delivery_id, vehicle_id, driver_id)
    if not delivery:
        return {"error": f"Could not assign delivery '{delivery_id}'."}
    result = delivery.model_dump()
    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("eta", None)
    return result


@mcp.tool()
async def update_delivery_status(delivery_id: str, status: str) -> dict:
    """Update the status of a delivery (e.g. picked_up, in_transit, delivered, failed)."""
    fault = await injector.maybe_raise("update_delivery_status")
    delivery = store.update_delivery_status(delivery_id, status)
    if not delivery:
        return {"error": f"Delivery '{delivery_id}' not found."}
    return delivery.model_dump()


@mcp.tool()
async def get_route_info(origin: str, destination: str) -> dict:
    """Get route information between an origin and destination."""
    fault = await injector.maybe_raise("get_route_info")
    route = store.get_route_info(origin, destination)
    if not route:
        return {"error": f"No route found from '{origin}' to '{destination}'."}
    result = route.model_dump()
    if fault == FaultType.CONTRADICTORY:
        result = corrupt_numeric_field(result, "distance_km")
    return result


@mcp.tool()
async def update_route_conditions(route_id: str, conditions: str) -> dict:
    """Update the current conditions for a route (clear, traffic, construction, closed)."""
    fault = await injector.maybe_raise("update_route_conditions")
    route = store.update_route_conditions(route_id, conditions)
    if not route:
        return {"error": f"Route '{route_id}' not found."}
    return route.model_dump()


if __name__ == "__main__":
    mcp.run(transport="stdio")
