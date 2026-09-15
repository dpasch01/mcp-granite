"""Robotics domain – Primitive MCP server (10 fine-grained tools).

Run standalone:  python -m mcp_granite.mcp_servers.robotics.primitive_server
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
from mcp_granite.mcp_servers.robotics._store import RoboticsStore

mcp = FastMCP("robotics-primitive")
store = RoboticsStore()
injector = FaultInjector(FaultConfig.from_env())


@mcp.tool()
async def list_robots(workspace: str | None = None, status: str | None = None) -> list[dict]:
    """List all robots, optionally filtered by workspace or status."""
    fault = await injector.maybe_raise("list_robots")
    results = [r.model_dump() for r in store.list_robots(workspace, status)]
    if fault == FaultType.PARTIAL_RESPONSE:
        return truncate_response(results)
    return results


@mcp.tool()
async def set_robot(
    robot_id: str,
    status: str | None = None,
    current_task: str | None = None,
    workspace: str | None = None,
) -> dict:
    """Update a robot's status, task, or workspace assignment."""
    await injector.maybe_raise("set_robot")
    kwargs = {}
    if status is not None:
        kwargs["status"] = status
    if current_task is not None:
        kwargs["current_task"] = current_task
    if workspace is not None:
        kwargs["workspace"] = workspace
    robot = store.set_robot(robot_id, **kwargs)
    if not robot:
        return {"error": f"Robot '{robot_id}' not found."}
    return robot.model_dump()


@mcp.tool()
async def list_waypoints(workspace: str | None = None) -> list[dict]:
    """List all waypoints, optionally filtered by workspace."""
    fault = await injector.maybe_raise("list_waypoints")
    results = [w.model_dump() for w in store.list_waypoints(workspace)]
    if fault == FaultType.PARTIAL_RESPONSE:
        return truncate_response(results)
    return results


@mcp.tool()
async def manage_task(
    action: str,
    task_id: str | None = None,
    name: str | None = None,
    task_type: str | None = None,
    workspace: str | None = None,
    priority: int | None = None,
    parameters: dict | None = None,
    status: str | None = None,
    assigned_robot: str | None = None,
) -> dict:
    """Manage task queue: list, get, create, or update tasks."""
    fault = await injector.maybe_raise("manage_task")
    if action == "list":
        tasks = store.list_tasks(status, workspace)
        results = [t.model_dump() for t in tasks]
        if fault == FaultType.PARTIAL_RESPONSE:
            return {"tasks": truncate_response(results)}
        return {"tasks": results}
    elif action == "get":
        if not task_id:
            return {"error": "get requires 'task_id'."}
        task = store.get_task(task_id)
        if not task:
            return {"error": f"Task '{task_id}' not found."}
        return task.model_dump()
    elif action == "create":
        if not all([name, task_type, workspace]):
            return {"error": "create requires 'name', 'task_type', 'workspace'."}
        task = store.create_task(name, task_type, workspace, priority or 3, parameters or {})
        return task.model_dump()
    elif action == "update":
        if not task_id:
            return {"error": "update requires 'task_id'."}
        kwargs = {}
        if status is not None:
            kwargs["status"] = status
        if assigned_robot is not None:
            kwargs["assigned_robot"] = assigned_robot
        if priority is not None:
            kwargs["priority"] = priority
        task = store.update_task(task_id, **kwargs)
        if not task:
            return {"error": f"Task '{task_id}' not found."}
        return task.model_dump()
    else:
        return {"error": f"Unknown action '{action}'. Supported: list, get, create, update."}


@mcp.tool()
async def get_sensor_readings(robot_id: str | None = None) -> list[dict]:
    """Get sensor readings, optionally filtered by robot ID."""
    fault = await injector.maybe_raise("get_sensor_readings")
    results = [s.model_dump() for s in store.list_sensor_readings(robot_id)]
    if fault == FaultType.PARTIAL_RESPONSE:
        return truncate_response(results)
    if fault == FaultType.CONTRADICTORY:
        return [corrupt_numeric_field(r, "value") for r in results]
    return results


@mcp.tool()
async def list_interlocks(workspace: str | None = None) -> list[dict]:
    """List all safety interlocks, optionally filtered by workspace."""
    fault = await injector.maybe_raise("list_interlocks")
    results = [i.model_dump() for i in store.list_interlocks(workspace)]
    if fault == FaultType.PARTIAL_RESPONSE:
        return truncate_response(results)
    return results


@mcp.tool()
async def set_interlock(interlock_id: str, status: str) -> dict:
    """Update a safety interlock's status."""
    await injector.maybe_raise("set_interlock")
    interlock = store.set_interlock(interlock_id, status=status)
    if not interlock:
        return {"error": f"Interlock '{interlock_id}' not found."}
    return interlock.model_dump()


@mcp.tool()
async def get_operation_log(
    severity: str | None = None, robot_id: str | None = None, limit: int = 10
) -> list[dict]:
    """Get operation log entries, optionally filtered by severity or robot."""
    fault = await injector.maybe_raise("get_operation_log")
    results = [entry.model_dump() for entry in store.get_operation_log(severity, robot_id, limit)]
    if fault == FaultType.PARTIAL_RESPONSE:
        return truncate_response(results)
    return results


@mcp.tool()
async def set_waypoint(waypoint_id: str, accessible: bool) -> dict:
    """Update a waypoint's accessibility status."""
    await injector.maybe_raise("set_waypoint")
    wp = store.set_waypoint(waypoint_id, accessible=accessible)
    if not wp:
        return {"error": f"Waypoint '{waypoint_id}' not found."}
    return wp.model_dump()


@mcp.tool()
async def get_robot_detail(robot_id: str) -> dict:
    """Get detailed info about a specific robot including its sensor readings."""
    fault = await injector.maybe_raise("get_robot_detail")
    robot = store.get_robot(robot_id)
    if not robot:
        return {"error": f"Robot '{robot_id}' not found."}
    sensors = store.list_sensor_readings(robot_id)
    result = {
        "robot": robot.model_dump(),
        "sensor_readings": [s.model_dump() for s in sensors],
    }
    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("sensor_readings", None)
    elif fault == FaultType.CONTRADICTORY:
        result["robot"] = corrupt_numeric_field(result["robot"], "battery_level")
    return result


if __name__ == "__main__":
    mcp.run(transport="stdio")
