"""Robotics domain – Composite-4 MCP server (4 high-level tools).

Run standalone:  python -m mcp_granite.mcp_servers.robotics.composite_4_server
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_granite.mcp_servers._base import (
    FaultConfig,
    FaultInjector,
    FaultType,
    corrupt_numeric_field,
)
from mcp_granite.mcp_servers.robotics._store import RoboticsStore

mcp = FastMCP("robotics-composite-4")
store = RoboticsStore()
injector = FaultInjector(FaultConfig.from_env())


@mcp.tool()
async def get_workspace_overview(workspace: str) -> dict:
    """Get a complete overview of a workspace including robots, waypoints, tasks, interlocks, sensors.

    Args:
        workspace: Workspace name (assembly_line, warehouse_floor, clean_room, outdoor, maintenance_bay).
    """
    fault = await injector.maybe_raise("get_workspace_overview")
    robots = store.list_robots(workspace)
    waypoints = store.list_waypoints(workspace)
    tasks = store.list_tasks(workspace=workspace)
    interlocks = store.list_interlocks(workspace)
    sensor_readings = []
    for r in robots:
        sensor_readings.extend(store.list_sensor_readings(r.robot_id))

    result = {
        "workspace": workspace,
        "robots": [r.model_dump() for r in robots],
        "waypoints": [w.model_dump() for w in waypoints],
        "tasks": [t.model_dump() for t in tasks],
        "interlocks": [i.model_dump() for i in interlocks],
        "sensor_readings": [s.model_dump() for s in sensor_readings],
        "summary": {
            "active_robots": sum(1 for r in robots if r.status == "active"),
            "faulted_robots": sum(1 for r in robots if r.status == "fault"),
            "queued_tasks": sum(1 for t in tasks if t.status == "queued"),
            "active_interlocks": sum(1 for i in interlocks if i.status == "active"),
            "triggered_interlocks": sum(1 for i in interlocks if i.status == "triggered"),
        },
    }
    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("sensor_readings", None)
        result.pop("waypoints", None)
    return result


@mcp.tool()
async def manage_robot_fleet(
    action: str,
    robot_id: str | None = None,
    status: str | None = None,
    current_task: str | None = None,
    workspace: str | None = None,
    interlock_id: str | None = None,
    waypoint_id: str | None = None,
    accessible: bool | None = None,
) -> dict:
    """Manage robots, interlocks, and waypoints.

    Args:
        action: One of 'robot_status', 'set_robot', 'set_interlock', 'set_waypoint',
                'list_interlocks'.
        robot_id: Robot ID.
        status: New status.
        current_task: Task to assign.
        workspace: Workspace filter.
        interlock_id: Safety interlock ID.
        waypoint_id: Waypoint ID.
        accessible: Waypoint accessibility.
    """
    fault = await injector.maybe_raise("manage_robot_fleet")

    if action == "robot_status":
        if robot_id:
            robot = store.get_robot(robot_id)
            if not robot:
                return {"error": f"Robot '{robot_id}' not found."}
            sensors = store.list_sensor_readings(robot_id)
            result = {
                "robot": robot.model_dump(),
                "sensor_readings": [s.model_dump() for s in sensors],
            }
            if fault == FaultType.CONTRADICTORY:
                result["robot"] = corrupt_numeric_field(result["robot"], "battery_level")
            return result
        robots = store.list_robots(workspace, status)
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
        if workspace is not None:
            kwargs["workspace"] = workspace
        robot = store.set_robot(robot_id, **kwargs)
        if not robot:
            return {"error": f"Robot '{robot_id}' not found."}
        return {"action": "set_robot", "robot": robot.model_dump()}
    elif action == "set_interlock":
        if not interlock_id or not status:
            return {"error": "set_interlock requires 'interlock_id' and 'status'."}
        interlock = store.set_interlock(interlock_id, status=status)
        if not interlock:
            return {"error": f"Interlock '{interlock_id}' not found."}
        return {"action": "set_interlock", "interlock": interlock.model_dump()}
    elif action == "set_waypoint":
        if not waypoint_id or accessible is None:
            return {"error": "set_waypoint requires 'waypoint_id' and 'accessible'."}
        wp = store.set_waypoint(waypoint_id, accessible=accessible)
        if not wp:
            return {"error": f"Waypoint '{waypoint_id}' not found."}
        return {"action": "set_waypoint", "waypoint": wp.model_dump()}
    elif action == "list_interlocks":
        interlocks = store.list_interlocks(workspace)
        result = {"interlocks": [i.model_dump() for i in interlocks]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["interlocks"] = result["interlocks"][:1]
        return result
    else:
        return {
            "error": f"Unknown action '{action}'. "
            "Supported: robot_status, set_robot, set_interlock, set_waypoint, list_interlocks."
        }


@mcp.tool()
async def handle_robot_task(
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
    """Manage the task queue.

    Args:
        action: One of 'list', 'get', 'create', 'update', 'assign'.
        task_id: Task ID.
        name: Task name (for create).
        task_type: Type (for create).
        workspace: Workspace (for create or filter).
        priority: Priority (1-5).
        parameters: Task parameters dict (for create).
        status: Task status.
        assigned_robot: Robot to assign.
    """
    fault = await injector.maybe_raise("handle_robot_task")

    if action == "list":
        tasks = store.list_tasks(status, workspace)
        result = {"tasks": [t.model_dump() for t in tasks]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["tasks"] = result["tasks"][:1]
        return result
    elif action == "get":
        if not task_id:
            return {"error": "get requires 'task_id'."}
        task = store.get_task(task_id)
        if not task:
            return {"error": f"Task '{task_id}' not found."}
        return {"task": task.model_dump()}
    elif action == "create":
        if not all([name, task_type, workspace]):
            return {"error": "create requires name, task_type, workspace."}
        task = store.create_task(name, task_type, workspace, priority or 3, parameters or {})
        return {"action": "create", "task": task.model_dump()}
    elif action in ("update", "assign"):
        if not task_id:
            return {"error": f"{action} requires 'task_id'."}
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
        if action == "assign" and assigned_robot:
            store.set_robot(assigned_robot, current_task=task_id, status="active")
        return {"action": action, "task": task.model_dump()}
    else:
        return {
            "error": f"Unknown action '{action}'. Supported: list, get, create, update, assign."
        }


@mcp.tool()
async def monitor_safety(workspace: str | None = None, robot_id: str | None = None) -> dict:
    """Monitor safety systems including interlocks, sensor readings, and operation logs.

    Args:
        workspace: Optional workspace filter.
        robot_id: Optional robot filter for sensor readings and logs.
    """
    fault = await injector.maybe_raise("monitor_safety")
    interlocks = store.list_interlocks(workspace)
    sensors = store.list_sensor_readings(robot_id)
    logs = store.get_operation_log(robot_id=robot_id)

    warnings = []
    for s in sensors:
        if s.status in ("warning", "critical"):
            warnings.append(
                {
                    "sensor": s.sensor_type,
                    "robot": s.robot_id,
                    "value": s.value,
                    "status": s.status,
                }
            )
    for i in interlocks:
        if i.status in ("triggered", "bypassed", "fault"):
            warnings.append({"interlock": i.name, "status": i.status})

    result = {
        "interlocks": [i.model_dump() for i in interlocks],
        "sensor_readings": [s.model_dump() for s in sensors],
        "operation_log": [entry.model_dump() for entry in logs],
        "warnings": warnings,
        "summary": {
            "total_interlocks": len(interlocks),
            "triggered": sum(1 for i in interlocks if i.status == "triggered"),
            "bypassed": sum(1 for i in interlocks if i.status == "bypassed"),
            "sensor_warnings": sum(1 for s in sensors if s.status == "warning"),
            "sensor_critical": sum(1 for s in sensors if s.status == "critical"),
        },
    }
    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("operation_log", None)
    return result


if __name__ == "__main__":
    mcp.run(transport="stdio")
