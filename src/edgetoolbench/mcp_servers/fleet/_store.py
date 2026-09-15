"""In-memory data store for the Fleet Management domain with deterministic seed data."""

from __future__ import annotations

from edgetoolbench.mcp_servers._data import generate_id
from edgetoolbench.mcp_servers.fleet._domain import (
    Delivery,
    Driver,
    Route,
    Vehicle,
    VehicleDiagnostic,
)


class FleetStore:
    def __init__(self) -> None:
        self.vehicles: dict[str, Vehicle] = {}
        self.drivers: dict[str, Driver] = {}
        self.deliveries: dict[str, Delivery] = {}
        self.routes: dict[str, Route] = {}
        self.diagnostics: dict[str, VehicleDiagnostic] = {}
        self._seed_data()

    def _seed_data(self) -> None:
        # ── Vehicles ────────────────────────────────────────────────────────
        vehicle_data = [
            ("WA-1234", "van", "available", {"lat": 40.71, "lng": -74.01}, 82.0, 45200.0),
            ("TB-5678", "truck", "en_route", {"lat": 40.73, "lng": -73.99}, 65.0, 89100.0),
            ("MC-9012", "motorcycle", "available", {"lat": 40.69, "lng": -74.04}, 90.0, 12300.0),
            ("WA-3456", "van", "available", {"lat": 40.75, "lng": -73.98}, 55.0, 67800.0),
        ]
        for i, (plate, vtype, status, loc, fuel, mileage) in enumerate(vehicle_data, 1):
            vid = generate_id("VH", i)
            self.vehicles[vid] = Vehicle(
                vehicle_id=vid, plate=plate, vehicle_type=vtype,
                status=status, current_location=loc,
                fuel_level=fuel, mileage=mileage,
            )

        # ── Drivers ─────────────────────────────────────────────────────────
        driver_data = [
            ("Alex Rivera", "C", "available", None, 0.0),
            ("Jordan Kim", "C", "on_duty", "VH002", 4.5),
            ("Sam Patel", "A", "available", None, 0.0),
            ("Casey Chen", "B", "available", None, 2.0),
        ]
        for i, (name, lic, status, assigned, hours) in enumerate(driver_data, 1):
            did = generate_id("DR", i)
            self.drivers[did] = Driver(
                driver_id=did, name=name, license_type=lic,
                status=status, assigned_vehicle_id=assigned,
                hours_today=hours,
            )

        # ── Deliveries ──────────────────────────────────────────────────────
        delivery_data = [
            ("VH002", "DR002", "Warehouse A", "Customer Zone A", "in_transit", "normal", "2025-06-01T09:00:00", "14:30"),
            ("VH002", "DR002", "Warehouse A", "Customer Zone C", "pending", "express", "2025-06-01T09:15:00", None),
            (None, None, "Warehouse A", "Customer Zone B", "pending", "urgent", "2025-06-01T09:30:00", None),
            ("VH001", "DR001", "Warehouse B", "Customer Zone A", "delivered", "normal", "2025-06-01T07:00:00", None),
            (None, None, "Warehouse B", "Customer Zone D", "pending", "normal", "2025-06-01T10:00:00", None),
        ]
        for i, (vid, did, pickup, dropoff, status, priority, created, eta) in enumerate(delivery_data, 1):
            dlid = generate_id("DL", i)
            self.deliveries[dlid] = Delivery(
                delivery_id=dlid, vehicle_id=vid, driver_id=did,
                pickup_location=pickup, dropoff_location=dropoff,
                status=status, priority=priority,
                created_at=created, eta=eta,
            )

        # ── Routes ──────────────────────────────────────────────────────────
        route_data = [
            ("Warehouse A", "Customer Zone A", 15.3, 25.0, "clear"),
            ("Warehouse A", "Customer Zone B", 22.7, 40.0, "traffic"),
            ("Warehouse A", "Customer Zone C", 8.1, 15.0, "clear"),
        ]
        for i, (origin, dest, dist, dur, cond) in enumerate(route_data, 1):
            rid = generate_id("RT", i)
            self.routes[rid] = Route(
                route_id=rid, origin=origin, destination=dest,
                distance_km=dist, estimated_duration_min=dur,
                conditions=cond,
            )

        # ── Vehicle Diagnostics ─────────────────────────────────────────────
        diag_data = [
            ("VH001", "2025-06-01T08:00:00", 88.5, {"fl": 32.1, "fr": 32.0, "rl": 31.8, "rr": 32.0}, 8.2, 25.0, 12.6, []),
            ("VH002", "2025-06-01T08:00:00", 95.2, {"fl": 31.5, "fr": 31.8, "rl": 30.2, "rr": 30.0}, 6.1, 45.0, 12.4, ["tire_pressure_low_rear"]),
            ("VH003", "2025-06-01T08:00:00", 72.0, {"fl": 28.5, "fr": 28.3, "rl": 28.5, "rr": 28.2}, 22.5, 15.0, 12.8, []),
            ("VH004", "2025-06-01T08:00:00", 85.0, {"fl": 32.0, "fr": 31.5, "rl": 32.0, "rr": 31.8}, 7.8, 60.0, 11.9, ["brake_wear_high", "battery_low"]),
        ]
        for i, (vid, ts, eng, tires, eff, brake, batt, alerts) in enumerate(diag_data, 1):
            vdid = generate_id("VD", i)
            self.diagnostics[vdid] = VehicleDiagnostic(
                diagnostic_id=vdid, vehicle_id=vid, timestamp=ts,
                engine_temp=eng, tire_pressure=tires,
                fuel_efficiency=eff, brake_wear=brake,
                battery_voltage=batt, alerts=alerts,
            )

    # ----- Query methods -----

    def get_vehicle_status(self, vehicle_id: str) -> Vehicle | None:
        return self.vehicles.get(vehicle_id)

    def list_vehicles(self, status_filter: str | None = None) -> list[Vehicle]:
        vehicles = list(self.vehicles.values())
        if status_filter:
            vehicles = [v for v in vehicles if v.status == status_filter]
        return vehicles

    def get_vehicle_diagnostics(self, vehicle_id: str) -> VehicleDiagnostic | None:
        for diag in self.diagnostics.values():
            if diag.vehicle_id == vehicle_id:
                return diag
        return None

    def get_driver_info(self, driver_id: str) -> Driver | None:
        return self.drivers.get(driver_id)

    def list_drivers(self, status_filter: str | None = None) -> list[Driver]:
        drivers = list(self.drivers.values())
        if status_filter:
            drivers = [d for d in drivers if d.status == status_filter]
        return drivers

    def get_delivery_status(self, delivery_id: str) -> Delivery | None:
        return self.deliveries.get(delivery_id)

    def assign_delivery(
        self, delivery_id: str, vehicle_id: str, driver_id: str
    ) -> Delivery | None:
        delivery = self.deliveries.get(delivery_id)
        vehicle = self.vehicles.get(vehicle_id)
        driver = self.drivers.get(driver_id)
        if not delivery or not vehicle or not driver:
            return None
        delivery.vehicle_id = vehicle_id
        delivery.driver_id = driver_id
        delivery.status = "picked_up"
        driver.status = "on_duty"
        driver.assigned_vehicle_id = vehicle_id
        vehicle.status = "en_route"
        return delivery

    def update_delivery_status(self, delivery_id: str, status: str) -> Delivery | None:
        delivery = self.deliveries.get(delivery_id)
        if not delivery:
            return None
        delivery.status = status
        if status == "delivered":
            # Free up vehicle and driver
            if delivery.vehicle_id:
                vehicle = self.vehicles.get(delivery.vehicle_id)
                if vehicle:
                    vehicle.status = "available"
            if delivery.driver_id:
                driver = self.drivers.get(delivery.driver_id)
                if driver:
                    driver.status = "available"
                    driver.assigned_vehicle_id = None
        return delivery

    def get_route_info(self, origin: str, destination: str) -> Route | None:
        for route in self.routes.values():
            if route.origin.lower() == origin.lower() and route.destination.lower() == destination.lower():
                return route
        return None

    def update_route_conditions(self, route_id: str, conditions: str) -> Route | None:
        route = self.routes.get(route_id)
        if not route:
            return None
        route.conditions = conditions
        return route
