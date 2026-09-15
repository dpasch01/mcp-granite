"""Warehouse domain – Composite-4 MCP server (4 high-level tools).

Run standalone:  python -m mcp_granite.mcp_servers.warehouse.composite_4_server
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_granite.mcp_servers._base import (
    FaultConfig,
    FaultInjector,
    FaultType,
    corrupt_numeric_field,
)
from mcp_granite.mcp_servers.warehouse._store import WarehouseStore

mcp = FastMCP("warehouse-composite-4")
store = WarehouseStore()
injector = FaultInjector(FaultConfig.from_env())


@mcp.tool()
async def get_zone_overview(zone: str) -> dict:
    """Get a complete overview of a warehouse zone including conveyors, robots, inventory, sensors.

    Args:
        zone: Zone name (e.g. 'sorting', 'packing', 'inbound', 'outbound').
    """
    fault = await injector.maybe_raise("get_zone_overview")
    conveyors = store.list_conveyors(zone)
    robots = store.list_robots(zone)
    inventory = store.list_inventory(zone)
    sensors = store.list_sensors(zone)
    result = {
        "zone": zone,
        "conveyors": [c.model_dump() for c in conveyors],
        "robots": [r.model_dump() for r in robots],
        "inventory": [s.model_dump() for s in inventory],
        "sensors": [s.model_dump() for s in sensors],
        "summary": {
            "active_conveyors": sum(1 for c in conveyors if c.status == "running"),
            "active_robots": sum(1 for r in robots if r.status == "active"),
            "total_items": sum(s.quantity for s in inventory),
            "low_stock_items": sum(1 for s in inventory if s.quantity < s.max_capacity * 0.1),
        },
    }
    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("conveyors", None)
        result.pop("sensors", None)
    return result


@mcp.tool()
async def manage_equipment(
    action: str,
    belt_id: str | None = None,
    robot_id: str | None = None,
    door_id: str | None = None,
    status: str | None = None,
    speed_mps: float | None = None,
    current_task: str | None = None,
    zone: str | None = None,
    assigned_truck: str | None = None,
) -> dict:
    """Manage warehouse equipment: conveyors, robots, and dock doors.

    Args:
        action: One of 'conveyor_status', 'set_conveyor', 'robot_status', 'set_robot',
                'dock_status', 'set_dock'.
        belt_id: Conveyor belt ID.
        robot_id: Robot ID.
        door_id: Dock door ID.
        status: New status.
        speed_mps: Conveyor speed.
        current_task: Robot task.
        zone: Zone filter or assignment.
        assigned_truck: Truck for dock door.
    """
    fault = await injector.maybe_raise("manage_equipment")

    if action == "conveyor_status":
        conveyors = store.list_conveyors(zone)
        result = {"conveyors": [c.model_dump() for c in conveyors]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["conveyors"] = result["conveyors"][:1]
        return result
    elif action == "set_conveyor":
        if not belt_id:
            return {"error": "set_conveyor requires 'belt_id'."}
        kwargs = {}
        if status is not None:
            kwargs["status"] = status
        if speed_mps is not None:
            kwargs["speed_mps"] = speed_mps
        belt = store.set_conveyor(belt_id, **kwargs)
        if not belt:
            return {"error": f"Conveyor '{belt_id}' not found."}
        return {"action": "set_conveyor", "conveyor": belt.model_dump()}
    elif action == "robot_status":
        robots = store.list_robots(zone, status)
        result = {"robots": [r.model_dump() for r in robots]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["robots"] = result["robots"][:1]
        return result
    elif action == "set_robot":
        if not robot_id:
            return {"error": "set_robot requires 'robot_id'."}
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
        return {"action": "set_robot", "robot": robot.model_dump()}
    elif action == "dock_status":
        doors = store.list_dock_doors()
        result = {"dock_doors": [d.model_dump() for d in doors]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["dock_doors"] = result["dock_doors"][:1]
        return result
    elif action == "set_dock":
        if not door_id:
            return {"error": "set_dock requires 'door_id'."}
        kwargs = {}
        if status is not None:
            kwargs["status"] = status
        if assigned_truck is not None:
            kwargs["assigned_truck"] = assigned_truck
        door = store.set_dock_door(door_id, **kwargs)
        if not door:
            return {"error": f"Dock door '{door_id}' not found."}
        return {"action": "set_dock", "dock_door": door.model_dump()}
    else:
        return {
            "error": f"Unknown action '{action}'. Supported: conveyor_status, set_conveyor, robot_status, set_robot, dock_status, set_dock."
        }


@mcp.tool()
async def handle_fulfillment(
    action: str,
    order_id: str | None = None,
    customer_id: str | None = None,
    items: list[dict] | None = None,
    priority: int | None = None,
    status: str | None = None,
    assigned_robot: str | None = None,
    slot_id: str | None = None,
    quantity: int | None = None,
) -> dict:
    """Manage order fulfillment and inventory.

    Args:
        action: One of 'list_orders', 'get_order', 'create_order', 'update_order',
                'check_inventory', 'update_inventory'.
        order_id: Order ID.
        customer_id: Customer ID (for create).
        items: Order items list (for create).
        priority: Order priority.
        status: Order status.
        assigned_robot: Robot assigned to order.
        slot_id: Inventory slot ID.
        quantity: New inventory quantity.
    """
    fault = await injector.maybe_raise("handle_fulfillment")

    if action == "list_orders":
        orders = store.list_orders(status)
        result = {"orders": [o.model_dump() for o in orders]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["orders"] = result["orders"][:1]
        return result
    elif action == "get_order":
        if not order_id:
            return {"error": "get_order requires 'order_id'."}
        order = store.get_order(order_id)
        if not order:
            return {"error": f"Order '{order_id}' not found."}
        return {"order": order.model_dump()}
    elif action == "create_order":
        if not customer_id or not items:
            return {"error": "create_order requires 'customer_id' and 'items'."}
        order = store.create_order(customer_id, items, priority or 3)
        return {"action": "create_order", "order": order.model_dump()}
    elif action == "update_order":
        if not order_id:
            return {"error": "update_order requires 'order_id'."}
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
        return {"action": "update_order", "order": order.model_dump()}
    elif action == "check_inventory":
        inventory = store.list_inventory()
        result = {"inventory": [s.model_dump() for s in inventory]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["inventory"] = result["inventory"][:1]
        return result
    elif action == "update_inventory":
        if not slot_id or quantity is None:
            return {"error": "update_inventory requires 'slot_id' and 'quantity'."}
        slot = store.update_inventory(slot_id, quantity)
        if not slot:
            return {"error": f"Slot '{slot_id}' not found."}
        return {"action": "update_inventory", "slot": slot.model_dump()}
    else:
        return {
            "error": f"Unknown action '{action}'. Supported: list_orders, get_order, create_order, update_order, check_inventory, update_inventory."
        }


@mcp.tool()
async def monitor_environment(zone: str | None = None) -> dict:
    """Monitor environment sensors and dock door status across the warehouse.

    Args:
        zone: Optional zone filter for sensors.
    """
    fault = await injector.maybe_raise("monitor_environment")
    sensors = store.list_sensors(zone)
    doors = store.list_dock_doors()
    alerts = []
    for s in sensors:
        if s.value < s.threshold_min or s.value > s.threshold_max:
            alerts.append(
                {
                    "sensor": s.name,
                    "value": s.value,
                    "threshold": f"{s.threshold_min}-{s.threshold_max}",
                }
            )

    result = {
        "sensors": [s.model_dump() for s in sensors],
        "dock_doors": [d.model_dump() for d in doors],
        "alerts": alerts,
        "summary": {
            "total_sensors": len(sensors),
            "out_of_range": len(alerts),
            "docks_active": sum(1 for d in doors if d.status in ("loading", "unloading")),
        },
    }
    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("sensors", None)
    elif fault == FaultType.CONTRADICTORY:
        for s in result.get("sensors", []):
            s = corrupt_numeric_field(s, "value")
    return result


if __name__ == "__main__":
    mcp.run(transport="stdio")
