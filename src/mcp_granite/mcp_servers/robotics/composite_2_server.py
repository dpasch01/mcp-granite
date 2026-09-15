"""Robotics domain – Composite-2 MCP server (2 tools: query + control).

Run standalone:  python -m mcp_granite.mcp_servers.robotics.composite_2_server
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

mcp = FastMCP("robotics-composite-2")
store = RoboticsStore()
injector = FaultInjector(FaultConfig.from_env())


@mcp.tool()
async def robotics_query(
    action: str,
    workspace: str | None = None,
    robot_id: str | None = None,
    status: str | None = None,
    task_id: str | None = None,
    reading_id: str | None = None,
    severity: str | None = None,
    limit: int = 10,
) -> dict:
    """Read/observe data from the robotics system. This is a read-only tool.

    Args:
        action: One of 'workspace_overview', 'robot_status', 'waypoints', 'tasks',
                'sensor_readings', 'interlocks', 'operation_log'.
        workspace: Workspace filter (assembly_line, warehouse_floor, clean_room, outdoor,
                   maintenance_bay).
        robot_id: Robot ID (for 'robot_status' detail or 'sensor_readings' filter).
        status: Status filter (for 'robot_status' list or 'tasks').
        task_id: Task ID (for 'tasks' detail).
        reading_id: Sensor reading ID (for 'sensor_readings' detail).
        severity: Severity filter (for 'operation_log').
        limit: Max entries (for 'operation_log', default 10).

    Returns a dict with the requested data.
    """
    fault = await injector.maybe_raise(action)

    if action == "workspace_overview":
        if not workspace:
            return {"error": "workspace_overview requires 'workspace'."}
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

    elif action == "robot_status":
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

    elif action == "waypoints":
        waypoints = store.list_waypoints(workspace)
        result = {"waypoints": [w.model_dump() for w in waypoints]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["waypoints"] = result["waypoints"][:1]
        return result

    elif action == "tasks":
        if task_id:
            task = store.get_task(task_id)
            if not task:
                return {"error": f"Task '{task_id}' not found."}
            return {"task": task.model_dump()}
        tasks = store.list_tasks(status, workspace)
        result = {"tasks": [t.model_dump() for t in tasks]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["tasks"] = result["tasks"][:1]
        return result

    elif action == "sensor_readings":
        if reading_id:
            reading = store.get_sensor_reading(reading_id)
            if not reading:
                return {"error": f"Sensor reading '{reading_id}' not found."}
            result = {"sensor_reading": reading.model_dump()}
            if fault == FaultType.CONTRADICTORY:
                result["sensor_reading"] = corrupt_numeric_field(result["sensor_reading"], "value")
            return result
        readings = store.list_sensor_readings(robot_id)
        result = {"sensor_readings": [s.model_dump() for s in readings]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["sensor_readings"] = result["sensor_readings"][:1]
        if fault == FaultType.CONTRADICTORY:
            result["sensor_readings"] = [
                corrupt_numeric_field(s, "value") for s in result["sensor_readings"]
            ]
        return result

    elif action == "interlocks":
        interlocks = store.list_interlocks(workspace)
        result = {"interlocks": [i.model_dump() for i in interlocks]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["interlocks"] = result["interlocks"][:1]
        return result

    elif action == "operation_log":
        logs = store.get_operation_log(severity, robot_id, limit)
        result = {"operation_log": [entry.model_dump() for entry in logs]}
        if fault == FaultType.PARTIAL_RESPONSE:
            result["operation_log"] = result["operation_log"][:1]
        return result

    else:
        return {
            "error": f"Unknown action '{action}'. Supported: workspace_overview, "
            "robot_status, waypoints, tasks, sensor_readings, interlocks, operation_log."
        }


@mcp.tool()
async def robotics_control(
    action: str,
    robot_id: str | None = None,
    status: str | None = None,
    current_task: str | None = None,
    workspace: str | None = None,
    waypoint_id: str | None = None,
    accessible: bool | None = None,
    interlock_id: str | None = None,
    task_id: str | None = None,
    name: str | None = None,
    task_type: str | None = None,
    priority: int | None = None,
    parameters: dict | None = None,
    assigned_robot: str | None = None,
) -> dict:
    """Write/actuate changes in the robotics system.

    Args:
        action: One of 'set_robot', 'set_waypoint', 'set_interlock', 'create_task',
                'update_task', 'assign_task'.
        robot_id: Robot ID (for 'set_robot', 'assign_task').
        status: New status (for 'set_robot', 'set_interlock', 'update_task').
        current_task: Task ID to assign to robot (for 'set_robot').
        workspace: Workspace (for 'set_robot', 'create_task').
        waypoint_id: Waypoint ID (for 'set_waypoint').
        accessible: Waypoint accessibility (for 'set_waypoint').
        interlock_id: Safety interlock ID (for 'set_interlock').
        task_id: Task ID (for 'update_task', 'assign_task').
        name: Task name (for 'create_task').
        task_type: Task type (for 'create_task').
        priority: Task priority 1-5 (for 'create_task', 'update_task').
        parameters: Task parameters dict (for 'create_task').
        assigned_robot: Robot ID to assign to task (for 'update_task', 'assign_task').

    Returns a dict with results of the action taken.
    """
    await injector.maybe_raise(action)

    if action == "set_robot":
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

    elif action == "set_waypoint":
        if not waypoint_id or accessible is None:
            return {"error": "set_waypoint requires 'waypoint_id' and 'accessible'."}
        wp = store.set_waypoint(waypoint_id, accessible=accessible)
        if not wp:
            return {"error": f"Waypoint '{waypoint_id}' not found."}
        return {"action": "set_waypoint", "waypoint": wp.model_dump()}

    elif action == "set_interlock":
        if not interlock_id or not status:
            return {"error": "set_interlock requires 'interlock_id' and 'status'."}
        interlock = store.set_interlock(interlock_id, status=status)
        if not interlock:
            return {"error": f"Interlock '{interlock_id}' not found."}
        return {"action": "set_interlock", "interlock": interlock.model_dump()}

    elif action == "create_task":
        if not all([name, task_type, workspace]):
            return {"error": "create_task requires 'name', 'task_type', 'workspace'."}
        task = store.create_task(name, task_type, workspace, priority or 3, parameters or {})
        return {"action": "create_task", "task": task.model_dump()}

    elif action == "update_task":
        if not task_id:
            return {"error": "update_task requires 'task_id'."}
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
        return {"action": "update_task", "task": task.model_dump()}

    elif action == "assign_task":
        if not task_id or not assigned_robot:
            return {"error": "assign_task requires 'task_id' and 'assigned_robot'."}
        task = store.update_task(task_id, assigned_robot=assigned_robot, status="assigned")
        if not task:
            return {"error": f"Task '{task_id}' not found."}
        store.set_robot(assigned_robot, current_task=task_id, status="active")
        return {"action": "assign_task", "task": task.model_dump()}

    else:
        return {
            "error": f"Unknown action '{action}'. Supported: set_robot, set_waypoint, "
            "set_interlock, create_task, update_task, assign_task."
        }


if __name__ == "__main__":
    mcp.run(transport="stdio")
