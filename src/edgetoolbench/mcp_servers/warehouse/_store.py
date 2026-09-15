"""In-memory data store for the Warehouse domain with deterministic seed data."""

from __future__ import annotations

from edgetoolbench.mcp_servers._data import generate_id
from edgetoolbench.mcp_servers.warehouse._domain import (
    ConveyorBelt,
    DockDoor,
    EnvironmentSensor,
    InventorySlot,
    PickOrder,
    Robot,
)


class WarehouseStore:
    def __init__(self) -> None:
        self.conveyors: dict[str, ConveyorBelt] = {}
        self.robots: dict[str, Robot] = {}
        self.inventory: dict[str, InventorySlot] = {}
        self.dock_doors: dict[str, DockDoor] = {}
        self.sensors: dict[str, EnvironmentSensor] = {}
        self.orders: dict[str, PickOrder] = {}
        self._next_order = 4
        self._seed_data()

    def _seed_data(self) -> None:
        conveyor_data = [
            ("Inbound Main", "inbound", 1.5, "running", 800, "2025-06-01T08:00:00"),
            ("Sorting Line A", "sorting", 2.0, "running", 1200, "2025-06-01T08:00:00"),
            ("Sorting Line B", "sorting", 0.0, "fault", 0, "2025-06-01T07:45:00"),
            ("Packing Line 1", "packing", 1.2, "running", 600, "2025-06-01T08:00:00"),
            ("Outbound Express", "outbound", 2.5, "running", 1500, "2025-06-01T08:00:00"),
            ("Returns Processing", "inbound", 0.8, "stopped", 0, "2025-06-01T06:00:00"),
        ]
        for i, (name, zone, speed, status, iph, updated) in enumerate(conveyor_data, 1):
            cid = generate_id("CB", i)
            self.conveyors[cid] = ConveyorBelt(
                belt_id=cid,
                name=name,
                zone=zone,
                speed_mps=speed,
                status=status,
                items_per_hour=iph,
                last_updated=updated,
            )

        robot_data = [
            ("Picker Alpha", "picker", "sorting", "active", 85.0, "PO001", "2025-06-01T08:00:00"),
            ("Picker Beta", "picker", "sorting", "idle", 92.0, None, "2025-06-01T07:50:00"),
            ("Packer One", "packer", "packing", "active", 78.0, "PO002", "2025-06-01T08:00:00"),
            (
                "Transport Bot",
                "transport",
                "inbound",
                "active",
                60.0,
                "dock_transfer",
                "2025-06-01T08:00:00",
            ),
            ("Scanner Unit", "scanner", "sorting", "fault", 45.0, None, "2025-06-01T07:30:00"),
            ("Picker Gamma", "picker", "sorting", "charging", 15.0, None, "2025-06-01T07:00:00"),
        ]
        for i, (name, rtype, zone, status, battery, task, updated) in enumerate(robot_data, 1):
            rid = generate_id("WR", i)
            self.robots[rid] = Robot(
                robot_id=rid,
                name=name,
                robot_type=rtype,
                zone=zone,
                status=status,
                battery_level=battery,
                current_task=task,
                last_updated=updated,
            )

        inventory_data = [
            ("A-01-01", "sorting", "Widget Pro", "SKU-001", 150, 200, "2025-06-01T07:00:00"),
            ("A-01-02", "sorting", "Gadget Plus", "SKU-002", 5, 100, "2025-06-01T07:00:00"),
            ("B-02-01", "packing", "Sensor Kit", "SKU-003", 80, 80, "2025-06-01T07:00:00"),
            ("B-02-02", "packing", "Cable Bundle", "SKU-004", 200, 300, "2025-06-01T07:00:00"),
            ("C-03-01", "outbound", "Power Supply", "SKU-005", 0, 50, "2025-06-01T07:00:00"),
            ("C-03-02", "outbound", "Display Unit", "SKU-006", 35, 40, "2025-06-01T07:00:00"),
        ]
        for i, (loc, zone, product, sku, qty, cap, updated) in enumerate(inventory_data, 1):
            sid = generate_id("IS", i)
            self.inventory[sid] = InventorySlot(
                slot_id=sid,
                location=loc,
                zone=zone,
                product_name=product,
                sku=sku,
                quantity=qty,
                max_capacity=cap,
                last_updated=updated,
            )

        dock_data = [
            ("Dock A", "loading", "TRUCK-101", "outbound", "2025-06-01T08:00:00"),
            ("Dock B", "unloading", "TRUCK-205", "inbound", "2025-06-01T07:30:00"),
            ("Dock C", "closed", None, "inbound", "2025-06-01T06:00:00"),
        ]
        for i, (name, status, truck, direction, updated) in enumerate(dock_data, 1):
            did = generate_id("DD", i)
            self.dock_doors[did] = DockDoor(
                door_id=did,
                name=name,
                status=status,
                assigned_truck=truck,
                direction=direction,
                last_updated=updated,
            )

        sensor_data = [
            (
                "Sorting Zone Temp",
                "sorting",
                "temperature",
                22.5,
                "°C",
                18.0,
                26.0,
                "2025-06-01T08:00:00",
            ),
            (
                "Cold Storage Temp",
                "packing",
                "temperature",
                -2.0,
                "°C",
                -5.0,
                2.0,
                "2025-06-01T08:00:00",
            ),
            (
                "Inbound Humidity",
                "inbound",
                "humidity",
                55.0,
                "%",
                30.0,
                70.0,
                "2025-06-01T08:00:00",
            ),
            (
                "Outbound Air Quality",
                "outbound",
                "air_quality",
                92.0,
                "AQI",
                0.0,
                100.0,
                "2025-06-01T08:00:00",
            ),
        ]
        for i, (name, zone, stype, value, unit, tmin, tmax, updated) in enumerate(sensor_data, 1):
            sid = generate_id("ES", i)
            self.sensors[sid] = EnvironmentSensor(
                sensor_id=sid,
                name=name,
                zone=zone,
                sensor_type=stype,
                value=value,
                unit=unit,
                threshold_min=tmin,
                threshold_max=tmax,
                last_updated=updated,
            )

        order_data = [
            (
                "CUST-A",
                [
                    {"sku": "SKU-001", "quantity": 5, "slot_id": "IS001"},
                    {"sku": "SKU-004", "quantity": 2, "slot_id": "IS004"},
                ],
                "picking",
                2,
                "WR001",
                "2025-06-01T07:30:00",
            ),
            (
                "CUST-B",
                [{"sku": "SKU-003", "quantity": 1, "slot_id": "IS003"}],
                "packing",
                1,
                "WR003",
                "2025-06-01T07:00:00",
            ),
            (
                "CUST-C",
                [
                    {"sku": "SKU-002", "quantity": 10, "slot_id": "IS002"},
                    {"sku": "SKU-006", "quantity": 3, "slot_id": "IS006"},
                ],
                "pending",
                3,
                None,
                "2025-06-01T08:00:00",
            ),
        ]
        for i, (cust, items, status, priority, robot, created) in enumerate(order_data, 1):
            oid = generate_id("PO", i)
            self.orders[oid] = PickOrder(
                order_id=oid,
                customer_id=cust,
                items=items,
                status=status,
                priority=priority,
                assigned_robot=robot,
                created_at=created,
            )

    # ── Conveyor methods ─────────────────────────────────────────────────
    def list_conveyors(self, zone: str | None = None) -> list[ConveyorBelt]:
        if zone:
            return [c for c in self.conveyors.values() if c.zone.lower() == zone.lower()]
        return list(self.conveyors.values())

    def get_conveyor(self, belt_id: str) -> ConveyorBelt | None:
        return self.conveyors.get(belt_id)

    def set_conveyor(self, belt_id: str, **kwargs) -> ConveyorBelt | None:
        belt = self.conveyors.get(belt_id)
        if not belt:
            return None
        for k in ("status", "speed_mps"):
            if k in kwargs:
                setattr(belt, k, kwargs[k])
        return belt

    # ── Robot methods ────────────────────────────────────────────────────
    def list_robots(self, zone: str | None = None, status: str | None = None) -> list[Robot]:
        robots = list(self.robots.values())
        if zone:
            robots = [r for r in robots if r.zone.lower() == zone.lower()]
        if status:
            robots = [r for r in robots if r.status.lower() == status.lower()]
        return robots

    def get_robot(self, robot_id: str) -> Robot | None:
        return self.robots.get(robot_id)

    def set_robot(self, robot_id: str, **kwargs) -> Robot | None:
        robot = self.robots.get(robot_id)
        if not robot:
            return None
        for k in ("status", "current_task", "zone"):
            if k in kwargs:
                setattr(robot, k, kwargs[k])
        return robot

    # ── Inventory methods ────────────────────────────────────────────────
    def list_inventory(self, zone: str | None = None) -> list[InventorySlot]:
        if zone:
            return [s for s in self.inventory.values() if s.zone.lower() == zone.lower()]
        return list(self.inventory.values())

    def get_inventory_slot(self, slot_id: str) -> InventorySlot | None:
        return self.inventory.get(slot_id)

    def update_inventory(self, slot_id: str, quantity: int) -> InventorySlot | None:
        slot = self.inventory.get(slot_id)
        if not slot:
            return None
        slot.quantity = quantity
        return slot

    # ── Dock methods ─────────────────────────────────────────────────────
    def list_dock_doors(self) -> list[DockDoor]:
        return list(self.dock_doors.values())

    def get_dock_door(self, door_id: str) -> DockDoor | None:
        return self.dock_doors.get(door_id)

    def set_dock_door(self, door_id: str, **kwargs) -> DockDoor | None:
        door = self.dock_doors.get(door_id)
        if not door:
            return None
        for k in ("status", "assigned_truck"):
            if k in kwargs:
                setattr(door, k, kwargs[k])
        return door

    # ── Sensor methods ───────────────────────────────────────────────────
    def list_sensors(self, zone: str | None = None) -> list[EnvironmentSensor]:
        if zone:
            return [s for s in self.sensors.values() if s.zone.lower() == zone.lower()]
        return list(self.sensors.values())

    def get_sensor(self, sensor_id: str) -> EnvironmentSensor | None:
        return self.sensors.get(sensor_id)

    # ── Order methods ────────────────────────────────────────────────────
    def list_orders(self, status: str | None = None) -> list[PickOrder]:
        if status:
            return [o for o in self.orders.values() if o.status.lower() == status.lower()]
        return list(self.orders.values())

    def get_order(self, order_id: str) -> PickOrder | None:
        return self.orders.get(order_id)

    def update_order(self, order_id: str, **kwargs) -> PickOrder | None:
        order = self.orders.get(order_id)
        if not order:
            return None
        for k in ("status", "assigned_robot", "priority"):
            if k in kwargs:
                setattr(order, k, kwargs[k])
        return order

    def create_order(self, customer_id: str, items: list[dict], priority: int = 3) -> PickOrder:
        oid = generate_id("PO", self._next_order)
        self._next_order += 1
        order = PickOrder(
            order_id=oid,
            customer_id=customer_id,
            items=items,
            status="pending",
            priority=priority,
            created_at="2025-06-01T09:00:00",
        )
        self.orders[oid] = order
        return order
