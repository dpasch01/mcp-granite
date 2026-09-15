"""In-memory data store for the Robotics domain with deterministic seed data."""

from __future__ import annotations

from mcp_granite.mcp_servers._data import generate_id
from mcp_granite.mcp_servers.robotics._domain import (
    OperationLog,
    Robot,
    SafetyInterlock,
    SensorReading,
    TaskQueue,
    Waypoint,
)


class RoboticsStore:
    def __init__(self) -> None:
        self.robots: dict[str, Robot] = {}
        self.waypoints: dict[str, Waypoint] = {}
        self.tasks: dict[str, TaskQueue] = {}
        self.sensor_readings: dict[str, SensorReading] = {}
        self.interlocks: dict[str, SafetyInterlock] = {}
        self.operation_log: list[OperationLog] = []
        self._next_task = 7
        self._next_log = 5
        self._seed_data()

    def _seed_data(self) -> None:
        robot_data = [
            (
                "Assembly Arm A",
                "arm",
                "assembly_line",
                "active",
                95.0,
                "TQ001",
                {"x": 2.0, "y": 1.0, "z": 0.5},
                "2025-06-01T08:00:00",
            ),
            (
                "Assembly Arm B",
                "arm",
                "assembly_line",
                "idle",
                88.0,
                None,
                {"x": 4.0, "y": 1.0, "z": 0.5},
                "2025-06-01T07:55:00",
            ),
            (
                "Mobile Bot Alpha",
                "mobile",
                "warehouse_floor",
                "active",
                72.0,
                "TQ003",
                {"x": 10.0, "y": 5.0, "z": 0.0},
                "2025-06-01T08:00:00",
            ),
            (
                "AGV Carrier 1",
                "agv",
                "warehouse_floor",
                "fault",
                45.0,
                None,
                {"x": 8.0, "y": 12.0, "z": 0.0},
                "2025-06-01T07:30:00",
            ),
            (
                "Cobot Helper",
                "cobot",
                "clean_room",
                "active",
                82.0,
                "TQ004",
                {"x": 1.0, "y": 3.0, "z": 0.8},
                "2025-06-01T08:00:00",
            ),
            (
                "Inspection Drone",
                "drone",
                "outdoor",
                "charging",
                20.0,
                None,
                {"x": 0.0, "y": 0.0, "z": 0.0},
                "2025-06-01T07:00:00",
            ),
        ]
        for i, (name, rtype, ws, status, battery, task, pos, updated) in enumerate(robot_data, 1):
            rid = generate_id("RB", i)
            self.robots[rid] = Robot(
                robot_id=rid,
                name=name,
                robot_type=rtype,
                workspace=ws,
                status=status,
                battery_level=battery,
                current_task=task,
                position=pos,
                last_updated=updated,
            )

        waypoint_data = [
            (
                "Assembly Start",
                "assembly_line",
                {"x": 0.0, "y": 0.0, "z": 0.5},
                "pickup",
                True,
                "2025-06-01T08:00:00",
            ),
            (
                "Assembly End",
                "assembly_line",
                {"x": 6.0, "y": 0.0, "z": 0.5},
                "dropoff",
                True,
                "2025-06-01T08:00:00",
            ),
            (
                "Charging Station A",
                "warehouse_floor",
                {"x": 0.0, "y": 0.0, "z": 0.0},
                "charging",
                True,
                "2025-06-01T08:00:00",
            ),
            (
                "Inspection Point 1",
                "outdoor",
                {"x": 20.0, "y": 10.0, "z": 5.0},
                "inspection",
                True,
                "2025-06-01T08:00:00",
            ),
            (
                "Home Position",
                "maintenance_bay",
                {"x": 0.0, "y": 0.0, "z": 0.0},
                "home",
                True,
                "2025-06-01T08:00:00",
            ),
            (
                "Transit Corridor",
                "warehouse_floor",
                {"x": 5.0, "y": 8.0, "z": 0.0},
                "transit",
                False,
                "2025-06-01T07:30:00",
            ),
        ]
        for i, (name, ws, pos, wtype, accessible, updated) in enumerate(waypoint_data, 1):
            wid = generate_id("WP", i)
            self.waypoints[wid] = Waypoint(
                waypoint_id=wid,
                name=name,
                workspace=ws,
                position=pos,
                waypoint_type=wtype,
                accessible=accessible,
                last_updated=updated,
            )

        task_data = [
            (
                "Assemble Widget A",
                "assemble",
                "RB001",
                "assembly_line",
                1,
                "in_progress",
                {"part_a": "SKU-100", "part_b": "SKU-101"},
                "2025-06-01T07:30:00",
            ),
            (
                "Weld Frame B",
                "weld",
                None,
                "assembly_line",
                2,
                "queued",
                {"joint_type": "spot", "material": "steel"},
                "2025-06-01T08:00:00",
            ),
            (
                "Transport Pallet",
                "transport",
                "RB003",
                "warehouse_floor",
                3,
                "in_progress",
                {"from": "WP001", "to": "WP002", "weight_kg": 50},
                "2025-06-01T07:45:00",
            ),
            (
                "Inspect Clean Room",
                "inspect",
                "RB005",
                "clean_room",
                2,
                "in_progress",
                {"check_points": ["particle_count", "temperature", "humidity"]},
                "2025-06-01T07:50:00",
            ),
            (
                "Calibrate Arm B",
                "calibrate",
                None,
                "assembly_line",
                4,
                "queued",
                {"axes": ["x", "y", "z", "rotation"]},
                "2025-06-01T08:00:00",
            ),
            (
                "Pick and Place Components",
                "pick_and_place",
                None,
                "assembly_line",
                1,
                "queued",
                {"source_bin": "BIN-A", "target_fixture": "FIX-1"},
                "2025-06-01T08:05:00",
            ),
        ]
        for i, (name, ttype, robot, ws, pri, status, params, created) in enumerate(task_data, 1):
            tid = generate_id("TQ", i)
            self.tasks[tid] = TaskQueue(
                task_id=tid,
                name=name,
                task_type=ttype,
                assigned_robot=robot,
                workspace=ws,
                priority=pri,
                status=status,
                parameters=params,
                created_at=created,
            )

        sensor_data = [
            ("RB001", "force_torque", 45.2, "Nm", "normal", "2025-06-01T08:00:00"),
            ("RB001", "temperature", 42.0, "°C", "normal", "2025-06-01T08:00:00"),
            ("RB003", "proximity", 0.3, "m", "warning", "2025-06-01T08:00:00"),
            ("RB004", "vibration", 8.5, "mm/s", "critical", "2025-06-01T07:30:00"),
            ("RB005", "vision", 98.5, "%clarity", "normal", "2025-06-01T08:00:00"),
            ("RB006", "lidar", 15.0, "m_range", "normal", "2025-06-01T07:00:00"),
        ]
        for i, (robot, stype, value, unit, status, ts) in enumerate(sensor_data, 1):
            sid = generate_id("SR", i)
            self.sensor_readings[sid] = SensorReading(
                reading_id=sid,
                robot_id=robot,
                sensor_type=stype,
                value=value,
                unit=unit,
                status=status,
                timestamp=ts,
            )

        interlock_data = [
            (
                "Assembly Line Curtain",
                "assembly_line",
                "light_curtain",
                "active",
                None,
                "2025-06-01T08:00:00",
            ),
            ("Assembly E-Stop", "assembly_line", "e_stop", "active", None, "2025-06-01T08:00:00"),
            (
                "Clean Room Door",
                "clean_room",
                "door_switch",
                "active",
                "2025-06-01T07:50:00",
                "2025-06-01T08:00:00",
            ),
            (
                "Warehouse Pressure Mat",
                "warehouse_floor",
                "pressure_mat",
                "triggered",
                "2025-06-01T07:55:00",
                "2025-06-01T08:00:00",
            ),
            ("Outdoor Fence Gate", "outdoor", "fence_gate", "active", None, "2025-06-01T08:00:00"),
            (
                "Maintenance Bay Door",
                "maintenance_bay",
                "door_switch",
                "bypassed",
                "2025-06-01T06:00:00",
                "2025-06-01T08:00:00",
            ),
        ]
        for i, (name, ws, itype, status, triggered, updated) in enumerate(interlock_data, 1):
            iid = generate_id("SI", i)
            self.interlocks[iid] = SafetyInterlock(
                interlock_id=iid,
                name=name,
                workspace=ws,
                interlock_type=itype,
                status=status,
                last_triggered=triggered,
                last_updated=updated,
            )

        log_data = [
            (
                "2025-06-01T08:00:00",
                "RB001",
                "task_started",
                "Assembly Arm A started assembling Widget A",
                "info",
            ),
            (
                "2025-06-01T07:50:00",
                "RB005",
                "task_started",
                "Cobot Helper started clean room inspection",
                "info",
            ),
            (
                "2025-06-01T07:30:00",
                "RB004",
                "fault_detected",
                "AGV Carrier 1 motor vibration exceeds threshold",
                "critical",
            ),
            (
                "2025-06-01T07:00:00",
                "RB006",
                "maintenance_due",
                "Inspection Drone battery below 25% — charging initiated",
                "warning",
            ),
        ]
        for i, (ts, robot, etype, desc, sev) in enumerate(log_data, 1):
            lid = generate_id("OL", i)
            self.operation_log.append(
                OperationLog(
                    log_id=lid,
                    timestamp=ts,
                    robot_id=robot,
                    event_type=etype,
                    description=desc,
                    severity=sev,
                )
            )

    # ── Robot methods ────────────────────────────────────────────────────
    def list_robots(self, workspace: str | None = None, status: str | None = None) -> list[Robot]:
        robots = list(self.robots.values())
        if workspace:
            robots = [r for r in robots if r.workspace.lower() == workspace.lower()]
        if status:
            robots = [r for r in robots if r.status.lower() == status.lower()]
        return robots

    def get_robot(self, robot_id: str) -> Robot | None:
        return self.robots.get(robot_id)

    def set_robot(self, robot_id: str, **kwargs) -> Robot | None:
        robot = self.robots.get(robot_id)
        if not robot:
            return None
        for k in ("status", "current_task", "workspace", "position"):
            if k in kwargs:
                setattr(robot, k, kwargs[k])
        return robot

    # ── Waypoint methods ─────────────────────────────────────────────────
    def list_waypoints(self, workspace: str | None = None) -> list[Waypoint]:
        if workspace:
            return [w for w in self.waypoints.values() if w.workspace.lower() == workspace.lower()]
        return list(self.waypoints.values())

    def get_waypoint(self, waypoint_id: str) -> Waypoint | None:
        return self.waypoints.get(waypoint_id)

    def set_waypoint(self, waypoint_id: str, **kwargs) -> Waypoint | None:
        wp = self.waypoints.get(waypoint_id)
        if not wp:
            return None
        if "accessible" in kwargs:
            wp.accessible = kwargs["accessible"]
        return wp

    # ── Task methods ─────────────────────────────────────────────────────
    def list_tasks(
        self, status: str | None = None, workspace: str | None = None
    ) -> list[TaskQueue]:
        tasks = list(self.tasks.values())
        if status:
            tasks = [t for t in tasks if t.status.lower() == status.lower()]
        if workspace:
            tasks = [t for t in tasks if t.workspace.lower() == workspace.lower()]
        return tasks

    def get_task(self, task_id: str) -> TaskQueue | None:
        return self.tasks.get(task_id)

    def create_task(
        self,
        name: str,
        task_type: str,
        workspace: str,
        priority: int,
        parameters: dict,
    ) -> TaskQueue:
        tid = generate_id("TQ", self._next_task)
        self._next_task += 1
        task = TaskQueue(
            task_id=tid,
            name=name,
            task_type=task_type,
            workspace=workspace,
            priority=priority,
            status="queued",
            parameters=parameters,
            created_at="2025-06-01T09:00:00",
        )
        self.tasks[tid] = task
        return task

    def update_task(self, task_id: str, **kwargs) -> TaskQueue | None:
        task = self.tasks.get(task_id)
        if not task:
            return None
        for k in ("status", "assigned_robot", "priority"):
            if k in kwargs:
                setattr(task, k, kwargs[k])
        return task

    # ── Sensor Reading methods ───────────────────────────────────────────
    def list_sensor_readings(self, robot_id: str | None = None) -> list[SensorReading]:
        if robot_id:
            return [s for s in self.sensor_readings.values() if s.robot_id == robot_id]
        return list(self.sensor_readings.values())

    def get_sensor_reading(self, reading_id: str) -> SensorReading | None:
        return self.sensor_readings.get(reading_id)

    # ── Interlock methods ────────────────────────────────────────────────
    def list_interlocks(self, workspace: str | None = None) -> list[SafetyInterlock]:
        if workspace:
            return [i for i in self.interlocks.values() if i.workspace.lower() == workspace.lower()]
        return list(self.interlocks.values())

    def get_interlock(self, interlock_id: str) -> SafetyInterlock | None:
        return self.interlocks.get(interlock_id)

    def set_interlock(self, interlock_id: str, **kwargs) -> SafetyInterlock | None:
        interlock = self.interlocks.get(interlock_id)
        if not interlock:
            return None
        if "status" in kwargs:
            interlock.status = kwargs["status"]
        return interlock

    # ── Operation Log methods ────────────────────────────────────────────
    def get_operation_log(
        self,
        severity: str | None = None,
        robot_id: str | None = None,
        limit: int = 10,
    ) -> list[OperationLog]:
        logs = self.operation_log
        if severity:
            logs = [entry for entry in logs if entry.severity.lower() == severity.lower()]
        if robot_id:
            logs = [entry for entry in logs if entry.robot_id == robot_id]
        logs = sorted(logs, key=lambda entry: entry.timestamp, reverse=True)
        return logs[:limit]

    def _add_log(
        self, robot_id: str, event_type: str, description: str, severity: str
    ) -> OperationLog:
        lid = generate_id("OL", self._next_log)
        self._next_log += 1
        log = OperationLog(
            log_id=lid,
            timestamp="2025-06-01T09:00:00",
            robot_id=robot_id,
            event_type=event_type,
            description=description,
            severity=severity,
        )
        self.operation_log.append(log)
        return log
