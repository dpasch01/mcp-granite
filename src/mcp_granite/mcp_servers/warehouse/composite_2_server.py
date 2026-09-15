"""Warehouse domain – Composite-2 MCP server (2 tools: query + control).

Run standalone:  python -m mcp_granite.mcp_servers.warehouse.composite_2_server
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
from mcp_granite.mcp_servers.warehouse._store import WarehouseStore

mcp = FastMCP("warehouse-composite-2")
store = WarehouseStore()
injector = FaultInjector(FaultConfig.from_env())


@mcp.tool()
async def warehouse_query(
    action: str,
    zone: str | None = None,
    belt_id: str | None = None,
    robot_id: str | None = None,
    slot_id: str | None = None,
    door_id: str | None = None,
    sensor_id: str | None = None,
    order_id: str | None = None,
    status: str | None = None,
) -> dict:
    """Read-only queries for the warehouse.

    Args:
        action: One of 'zone_overview', 'conveyor_status', 'robot_status',
                'inventory', 'dock_status', 'sensors', 'orders'.
        zone: Zone filter.
        belt_id: Conveyor ID (for specific conveyor).
        robot_id: Robot ID.
        slot_id: Inventory slot ID.
        door_id: Dock door ID.
        sensor_id: Sensor ID.
        order_id: Order ID.
        status: Status filter.
    """
    fault = await injector.maybe_raise(action)

    if action == "zone_overview":
        if not zone:
            return {"error": "zone_overview requires 'zone'."}
        conveyors = store.list_conveyors(zone)
        robots = store.list_robots(zone)
        inventory = store.list_inventory(zone)
        sensors = store.list_sensors(zone)
        result: dict[str, Any] = {
            "zone": zone,
            "conveyors": [c.model_dump() for c in conveyors],
            "robots": [r.model_dump() for r in robots],
            "inventory": [s.model_dump() for s in inventory],
            "sensors": [s.model_dump() for s in sensors],
            "summary": {
                "active_conveyors": sum(1 for c in conveyors if c.status == "running"),
                "active_robots": sum(1 for r in robots if r.status == "active"),
                "total_items": sum(s.quantity for s in inventory),
            },
        }
        if fault == FaultType.PARTIAL_RESPONSE:
            result.pop("conveyors", None)
        return result
    elif action == "conveyor_status":
        if belt_id:
            belt = store.get_conveyor(belt_id)
            if not belt:
                return {"error": f"Conveyor '{belt_id}' not found."}
            return {"conveyor": belt.model_dump()}
        result = {"conveyors": [c.model_dump() for c in store.list_conveyors(zone)]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["conveyors"] = result["conveyors"][:1]
        return result
    elif action == "robot_status":
        if robot_id:
            robot = store.get_robot(robot_id)
            if not robot:
                return {"error": f"Robot '{robot_id}' not found."}
            return {"robot": robot.model_dump()}
        result = {"robots": [r.model_dump() for r in store.list_robots(zone, status)]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["robots"] = result["robots"][:1]
        return result
    elif action == "inventory":
        if slot_id:
            slot = store.get_inventory_slot(slot_id)
            if not slot:
                return {"error": f"Slot '{slot_id}' not found."}
            return {"slot": slot.model_dump()}
        result = {"inventory": [s.model_dump() for s in store.list_inventory(zone)]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["inventory"] = result["inventory"][:1]
        return result
    elif action == "dock_status":
        if door_id:
            door = store.get_dock_door(door_id)
            if not door:
                return {"error": f"Dock door '{door_id}' not found."}
            return {"dock_door": door.model_dump()}
        return {"dock_doors": [d.model_dump() for d in store.list_dock_doors()]}
    elif action == "sensors":
        if sensor_id:
            sensor = store.get_sensor(sensor_id)
            if not sensor:
                return {"error": f"Sensor '{sensor_id}' not found."}
            result = {"sensor": sensor.model_dump()}
            if fault == FaultType.CONTRADICTORY:
                result["sensor"] = corrupt_numeric_field(result["sensor"], "value")
            return result
        result = {"sensors": [s.model_dump() for s in store.list_sensors(zone)]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["sensors"] = result["sensors"][:1]
        return result
    elif action == "orders":
        if order_id:
            order = store.get_order(order_id)
            if not order:
                return {"error": f"Order '{order_id}' not found."}
            return {"order": order.model_dump()}
        result = {"orders": [o.model_dump() for o in store.list_orders(status)]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["orders"] = result["orders"][:1]
        return result
    else:
        return {
            "error": f"Unknown action '{action}'. Supported: zone_overview, conveyor_status, robot_status, inventory, dock_status, sensors, orders."
        }


@mcp.tool()
async def warehouse_control(
    action: str,
    belt_id: str | None = None,
    robot_id: str | None = None,
    door_id: str | None = None,
    order_id: str | None = None,
    slot_id: str | None = None,
    status: str | None = None,
    speed_mps: float | None = None,
    current_task: str | None = None,
    zone: str | None = None,
    assigned_truck: str | None = None,
    assigned_robot: str | None = None,
    priority: int | None = None,
    quantity: int | None = None,
    customer_id: str | None = None,
    items: list[dict] | None = None,
) -> dict:
    """Write/actuate changes in the warehouse.

    Args:
        action: One of 'set_conveyor', 'set_robot', 'set_dock',
                'create_order', 'update_order', 'update_inventory'.
    """
    await injector.maybe_raise(action)

    if action == "set_conveyor":
        if not belt_id:
            return {"error": "set_conveyor requires 'belt_id'."}
        kwargs: dict[str, Any] = {}
        if status is not None:
            kwargs["status"] = status
        if speed_mps is not None:
            kwargs["speed_mps"] = speed_mps
        belt = store.set_conveyor(belt_id, **kwargs)
        if not belt:
            return {"error": f"Conveyor '{belt_id}' not found."}
        return {"action": "set_conveyor", "conveyor": belt.model_dump()}
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
    elif action == "update_inventory":
        if not slot_id or quantity is None:
            return {"error": "update_inventory requires 'slot_id' and 'quantity'."}
        slot = store.update_inventory(slot_id, quantity)
        if not slot:
            return {"error": f"Slot '{slot_id}' not found."}
        return {"action": "update_inventory", "slot": slot.model_dump()}
    else:
        return {
            "error": f"Unknown action '{action}'. Supported: set_conveyor, set_robot, set_dock, create_order, update_order, update_inventory."
        }


if __name__ == "__main__":
    mcp.run(transport="stdio")
