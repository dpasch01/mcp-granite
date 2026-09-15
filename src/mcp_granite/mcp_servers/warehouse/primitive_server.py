"""Warehouse domain – Primitive MCP server (10 fine-grained tools).

Run standalone:  python -m mcp_granite.mcp_servers.warehouse.primitive_server
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
from mcp_granite.mcp_servers.warehouse._store import WarehouseStore

mcp = FastMCP("warehouse-primitive")
store = WarehouseStore()
injector = FaultInjector(FaultConfig.from_env())


@mcp.tool()
async def list_conveyors(zone: str | None = None) -> list[dict]:
    """List all conveyor belts, optionally filtered by zone."""
    fault = await injector.maybe_raise("list_conveyors")
    results = [c.model_dump() for c in store.list_conveyors(zone)]
    if fault == FaultType.PARTIAL_RESPONSE:
        return truncate_response(results)
    return results


@mcp.tool()
async def set_conveyor(
    belt_id: str, status: str | None = None, speed_mps: float | None = None
) -> dict:
    """Update a conveyor belt's status or speed."""
    await injector.maybe_raise("set_conveyor")
    kwargs = {}
    if status is not None:
        kwargs["status"] = status
    if speed_mps is not None:
        kwargs["speed_mps"] = speed_mps
    belt = store.set_conveyor(belt_id, **kwargs)
    if not belt:
        return {"error": f"Conveyor '{belt_id}' not found."}
    return belt.model_dump()


@mcp.tool()
async def list_robots(zone: str | None = None, status: str | None = None) -> list[dict]:
    """List all warehouse robots, optionally filtered by zone or status."""
    fault = await injector.maybe_raise("list_robots")
    results = [r.model_dump() for r in store.list_robots(zone, status)]
    if fault == FaultType.PARTIAL_RESPONSE:
        return truncate_response(results)
    return results


@mcp.tool()
async def set_robot(
    robot_id: str,
    status: str | None = None,
    current_task: str | None = None,
    zone: str | None = None,
) -> dict:
    """Update a robot's status, task, or zone assignment."""
    await injector.maybe_raise("set_robot")
    kwargs = {}
    if status is not None:
        kwargs["status"] = status
    if current_task is not None:
        kwargs["current_task"] = current_task
    if zone is not None:
        kwargs["zone"] = zone
    robot = store.set_robot(robot_id, **kwargs)
    if not robot:
        return {"error": f"Robot '{robot_id}' not found."}
    return robot.model_dump()


@mcp.tool()
async def list_inventory(zone: str | None = None) -> list[dict]:
    """List all inventory slots, optionally filtered by zone."""
    fault = await injector.maybe_raise("list_inventory")
    results = [s.model_dump() for s in store.list_inventory(zone)]
    if fault == FaultType.PARTIAL_RESPONSE:
        return truncate_response(results)
    return results


@mcp.tool()
async def update_inventory(slot_id: str, quantity: int) -> dict:
    """Update the quantity of an inventory slot."""
    await injector.maybe_raise("update_inventory")
    slot = store.update_inventory(slot_id, quantity)
    if not slot:
        return {"error": f"Inventory slot '{slot_id}' not found."}
    return slot.model_dump()


@mcp.tool()
async def get_dock_door(door_id: str) -> dict:
    """Get the status of a specific dock door."""
    fault = await injector.maybe_raise("get_dock_door")
    door = store.get_dock_door(door_id)
    if not door:
        return {"error": f"Dock door '{door_id}' not found."}
    result = door.model_dump()
    if fault == FaultType.CONTRADICTORY:
        result["status"] = "closed" if result["status"] != "closed" else "open"
    return result


@mcp.tool()
async def set_dock_door(
    door_id: str, status: str | None = None, assigned_truck: str | None = None
) -> dict:
    """Update a dock door's status or truck assignment."""
    await injector.maybe_raise("set_dock_door")
    kwargs = {}
    if status is not None:
        kwargs["status"] = status
    if assigned_truck is not None:
        kwargs["assigned_truck"] = assigned_truck
    door = store.set_dock_door(door_id, **kwargs)
    if not door:
        return {"error": f"Dock door '{door_id}' not found."}
    return door.model_dump()


@mcp.tool()
async def list_sensors(zone: str | None = None) -> list[dict]:
    """List all environment sensors, optionally filtered by zone."""
    fault = await injector.maybe_raise("list_sensors")
    results = [s.model_dump() for s in store.list_sensors(zone)]
    if fault == FaultType.PARTIAL_RESPONSE:
        return truncate_response(results)
    if fault == FaultType.CONTRADICTORY:
        return [corrupt_numeric_field(r, "value") for r in results]
    return results


@mcp.tool()
async def manage_order(
    action: str,
    order_id: str | None = None,
    customer_id: str | None = None,
    items: list[dict] | None = None,
    priority: int | None = None,
    status: str | None = None,
    assigned_robot: str | None = None,
) -> dict:
    """Manage pick orders: list, get, create, or update."""
    fault = await injector.maybe_raise("manage_order")
    if action == "list":
        orders = store.list_orders(status)
        results = [o.model_dump() for o in orders]
        if fault == FaultType.PARTIAL_RESPONSE:
            return {"orders": truncate_response(results)}
        return {"orders": results}
    elif action == "get":
        if not order_id:
            return {"error": "get requires 'order_id'."}
        order = store.get_order(order_id)
        if not order:
            return {"error": f"Order '{order_id}' not found."}
        return order.model_dump()
    elif action == "create":
        if not customer_id or not items:
            return {"error": "create requires 'customer_id' and 'items'."}
        order = store.create_order(customer_id, items, priority or 3)
        return order.model_dump()
    elif action == "update":
        if not order_id:
            return {"error": "update requires 'order_id'."}
        kwargs = {}
        if status is not None:
            kwargs["status"] = status
        if assigned_robot is not None:
            kwargs["assigned_robot"] = assigned_robot
        if priority is not None:
            kwargs["priority"] = priority
        order = store.update_order(order_id, **kwargs)
        if not order:
            return {"error": f"Order '{order_id}' not found."}
        return order.model_dump()
    else:
        return {"error": f"Unknown action '{action}'. Supported: list, get, create, update."}


if __name__ == "__main__":
    mcp.run(transport="stdio")
