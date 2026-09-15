"""In-memory data store for the Industrial IoT domain with deterministic seed data."""

from __future__ import annotations

from mcp_granite.mcp_servers._data import generate_id
from mcp_granite.mcp_servers.industrial._domain import (
    Alert,
    AlertThreshold,
    Machine,
    MaintenanceLog,
    TelemetryReading,
    WorkOrder,
)


class IndustrialStore:
    def __init__(self) -> None:
        self.machines: dict[str, Machine] = {}
        self.telemetry: dict[str, TelemetryReading] = {}
        self.thresholds: dict[str, AlertThreshold] = {}
        self.maintenance_logs: dict[str, MaintenanceLog] = {}
        self.work_orders: dict[str, WorkOrder] = {}
        self.alerts: dict[str, Alert] = {}
        self._next_work_order = 2  # WO001 already seeded
        self._seed_data()

    def _seed_data(self) -> None:
        # ── Machines ────────────────────────────────────────────────────
        machine_data = [
            ("CNC Mill Alpha", "cnc", "Building A - Bay 1", "running", 1250.0, "2025-02-01"),
            ("Hydraulic Press Beta", "press", "Building A - Bay 2", "idle", 890.0, "2025-02-15"),
            ("Conveyor Belt C-Line", "conveyor", "Building B - Line 3", "warning", 2100.0, "2025-03-05"),
            ("Welding Robot Delta", "robot", "Building B - Bay 4", "running", 560.0, "2025-01-20"),
        ]
        for i, (name, mtype, loc, status, uptime, last_maint) in enumerate(machine_data, 1):
            mid = generate_id("MC", i)
            self.machines[mid] = Machine(
                machine_id=mid, name=name, machine_type=mtype, location=loc,
                status=status, uptime_hours=uptime, last_maintenance=last_maint,
            )

        # ── Telemetry Readings (one per machine) ───────────────────────
        telemetry_data = [
            ("MC001", "2025-03-12T08:30:00Z", {"vibration": 2.3, "temperature": 45.2, "pressure": 6.1, "rpm": 3500.0, "power_draw": 12.5}),
            ("MC002", "2025-03-12T08:30:00Z", {"vibration": 0.5, "temperature": 22.0, "pressure": 0.0, "rpm": 0.0, "power_draw": 0.3}),
            ("MC003", "2025-03-12T08:30:00Z", {"vibration": 8.7, "temperature": 72.5, "pressure": 4.2, "rpm": 0.0, "power_draw": 3.1}),
            ("MC004", "2025-03-12T08:30:00Z", {"vibration": 5.1, "temperature": 38.0, "pressure": 5.5, "rpm": 1200.0, "power_draw": 8.3}),
        ]
        for i, (mid, ts, metrics) in enumerate(telemetry_data, 1):
            tid = generate_id("TR", i)
            self.telemetry[tid] = TelemetryReading(
                reading_id=tid, machine_id=mid, timestamp=ts, metrics=metrics,
            )

        # ── Alert Thresholds ───────────────────────────────────────────
        threshold_data = [
            ("MC001", "vibration", None, 5.0, "warning"),
            ("MC001", "temperature", None, 80.0, "critical"),
            ("MC003", "vibration", None, 5.0, "critical"),
            ("MC003", "temperature", None, 70.0, "critical"),
            ("MC004", "vibration", None, 4.0, "warning"),
            ("MC004", "temperature", None, 60.0, "warning"),
        ]
        for i, (mid, metric, min_v, max_v, sev) in enumerate(threshold_data, 1):
            thid = generate_id("TH", i)
            self.thresholds[thid] = AlertThreshold(
                threshold_id=thid, machine_id=mid, metric=metric,
                min_value=min_v, max_value=max_v, severity=sev,
            )

        # ── Maintenance Logs ───────────────────────────────────────────
        log_data = [
            ("MC001", "2025-02-10", "scheduled", "Routine spindle lubrication and calibration",
             ["spindle_bearing", "coolant_filter"], 4.0),
            ("MC003", "2025-03-05", "emergency", "Emergency belt replacement due to excessive vibration",
             ["drive_belt", "tensioner_pulley"], 12.0),
            ("MC004", "2025-01-12", "scheduled", "Welding tip replacement and arm recalibration",
             ["welding_tip_set", "calibration_target"], 3.0),
        ]
        for i, (mid, dt, mtype, desc, parts, downtime) in enumerate(log_data, 1):
            lid = generate_id("ML", i)
            self.maintenance_logs[lid] = MaintenanceLog(
                log_id=lid, machine_id=mid, date=dt, maintenance_type=mtype,
                description=desc, parts_replaced=parts, downtime_hours=downtime,
            )

        # ── Work Orders ────────────────────────────────────────────────
        self.work_orders["WO001"] = WorkOrder(
            order_id="WO001", machine_id="MC003", priority="high",
            description="Investigate conveyor belt vibration",
            status="open", created_at="2025-03-12T09:00:00Z", assigned_to=None,
        )

        # ── Alerts ─────────────────────────────────────────────────────
        alert_data = [
            ("MC003", "vibration", 8.7, "TH003", "critical", "2025-03-12T08:31:00Z"),
            ("MC004", "vibration", 5.1, "TH005", "warning", "2025-03-12T08:31:00Z"),
        ]
        for i, (mid, metric, val, thid, sev, ts) in enumerate(alert_data, 1):
            aid = generate_id("AL", i)
            self.alerts[aid] = Alert(
                alert_id=aid, machine_id=mid, metric=metric, value=val,
                threshold_id=thid, severity=sev, timestamp=ts, acknowledged=False,
            )

    # ── Query methods ──────────────────────────────────────────────────

    def get_machine_status(self, machine_id: str) -> Machine | None:
        return self.machines.get(machine_id)

    def list_machines(self, status_filter: str | None = None) -> list[Machine]:
        machines = list(self.machines.values())
        if status_filter:
            machines = [m for m in machines if m.status == status_filter]
        return machines

    def read_telemetry(self, machine_id: str) -> TelemetryReading | None:
        for reading in self.telemetry.values():
            if reading.machine_id == machine_id:
                return reading
        return None

    def get_alert_thresholds(self, machine_id: str) -> list[AlertThreshold]:
        return [t for t in self.thresholds.values() if t.machine_id == machine_id]

    def get_maintenance_history(self, machine_id: str) -> list[MaintenanceLog]:
        return [l for l in self.maintenance_logs.values() if l.machine_id == machine_id]

    # ── Mutation methods ───────────────────────────────────────────────

    def create_work_order(
        self, machine_id: str, priority: str, description: str
    ) -> WorkOrder | None:
        machine = self.machines.get(machine_id)
        if not machine:
            return None
        oid = generate_id("WO", self._next_work_order)
        self._next_work_order += 1
        order = WorkOrder(
            order_id=oid, machine_id=machine_id, priority=priority,
            description=description, status="open",
            created_at="2025-03-12T10:00:00Z", assigned_to=None,
        )
        self.work_orders[oid] = order
        return order

    def update_work_order(
        self, order_id: str, status: str | None = None, assigned_to: str | None = None
    ) -> WorkOrder | None:
        order = self.work_orders.get(order_id)
        if not order:
            return None
        if status is not None:
            order.status = status
        if assigned_to is not None:
            order.assigned_to = assigned_to
        return order

    def get_active_alerts(self, machine_id: str | None = None) -> list[Alert]:
        alerts = [a for a in self.alerts.values() if not a.acknowledged]
        if machine_id:
            alerts = [a for a in alerts if a.machine_id == machine_id]
        return alerts

    def acknowledge_alert(self, alert_id: str) -> Alert | None:
        alert = self.alerts.get(alert_id)
        if not alert:
            return None
        alert.acknowledged = True
        return alert

    def get_work_order(self, order_id: str) -> WorkOrder | None:
        return self.work_orders.get(order_id)
