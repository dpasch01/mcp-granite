"""Tests for mock data stores."""

from mcp_granite.mcp_servers.travel._store import TravelStore
from mcp_granite.mcp_servers.helpdesk._store import HelpdeskStore
from mcp_granite.mcp_servers.ecommerce._store import ECommerceStore
from mcp_granite.mcp_servers.smarthome._store import SmartHomeStore
from mcp_granite.mcp_servers.industrial._store import IndustrialStore
from mcp_granite.mcp_servers.fleet._store import FleetStore


# ── Travel Store ─────────────────────────────────────────────────────────────

class TestTravelStore:
    def setup_method(self):
        self.store = TravelStore()

    def test_seed_data(self):
        assert len(self.store.flights) == 8
        assert len(self.store.hotels) == 6

    def test_search_flights(self):
        results = self.store.search_flights("JFK", "LHR", "2025-03-15")
        assert len(results) == 3
        assert results[0].price <= results[1].price  # sorted by price

    def test_search_flights_no_match(self):
        results = self.store.search_flights("JFK", "NRT", "2025-03-15")
        assert len(results) == 0

    def test_search_hotels(self):
        results = self.store.search_hotels("London", "2025-03-15", "2025-03-22")
        assert len(results) == 3

    def test_book_flight(self):
        booking = self.store.book_flight("FL001", "John Smith", "economy")
        assert booking is not None
        assert booking.status == "confirmed"
        assert booking.passenger_name == "John Smith"

    def test_cancel_booking(self):
        booking = self.store.book_flight("FL001", "John Smith", "economy")
        assert booking is not None
        success = self.store.cancel_booking(booking.booking_id)
        assert success is True
        cancelled = self.store.get_booking(booking.booking_id)
        assert cancelled.status == "cancelled"

    def test_seat_availability_decreases(self):
        avail_before = self.store.check_seat_availability("FL001", "economy")
        self.store.book_flight("FL001", "Test", "economy")
        avail_after = self.store.check_seat_availability("FL001", "economy")
        assert avail_after["available"] == avail_before["available"] - 1


# ── Helpdesk Store ───────────────────────────────────────────────────────────

class TestHelpdeskStore:
    def setup_method(self):
        self.store = HelpdeskStore()

    def test_seed_data(self):
        assert len(self.store.users) == 5
        assert len(self.store.systems) == 4
        assert len(self.store.articles) == 6
        assert len(self.store.tickets) == 2

    def test_lookup_user(self):
        user = self.store.lookup_user("USR001")
        assert user is not None
        assert user.name == "Alice Johnson"

    def test_search_kb(self):
        results = self.store.search_knowledge_base("password")
        assert len(results) > 0
        assert "password" in results[0].title.lower()

    def test_create_ticket(self):
        ticket = self.store.create_ticket("USR001", "Test", "Test issue")
        assert ticket is not None
        assert ticket.status == "open"

    def test_escalate_ticket(self):
        ticket = self.store.escalate_ticket("TK001", "Not resolved")
        assert ticket is not None
        assert ticket.status == "escalated"
        assert ticket.assigned_to == "L2 Support"


# ── E-Commerce Store ─────────────────────────────────────────────────────────

class TestECommerceStore:
    def setup_method(self):
        self.store = ECommerceStore()

    def test_seed_data(self):
        assert len(self.store.products) == 8
        assert len(self.store.discount_codes) == 3

    def test_search_products(self):
        results = self.store.search_products("keyboard")
        assert len(results) >= 1
        assert "keyboard" in results[0].name.lower()

    def test_add_to_cart_and_order(self):
        cart = self.store.add_to_cart(None, "PR003", 1)
        assert cart is not None
        order = self.store.place_order(cart.cart_id, "123 Main St", "SAVE10")
        assert order is not None
        assert order.status == "confirmed"
        assert order.discount > 0

    def test_apply_discount(self):
        result = self.store.apply_discount("CT001", "SAVE10")
        assert result is not None
        assert "error" not in result
        assert result["discount_amount"] > 0

    def test_initiate_return(self):
        result = self.store.initiate_return("OR001", "PR001", "Defective")
        assert result is not None
        assert result["status"] == "return_initiated"


# ── Smart Home Store ────────────────────────────────────────────────────────

class TestSmartHomeStore:
    def setup_method(self):
        self.store = SmartHomeStore()

    def test_seed_data(self):
        assert len(self.store.sensors) == 6
        assert len(self.store.devices) == 6
        assert len(self.store.automation_rules) == 3
        assert len(self.store.event_log) == 4

    def test_list_sensors(self):
        all_sensors = self.store.list_sensors()
        assert len(all_sensors) == 6

    def test_list_sensors_by_location(self):
        results = self.store.list_sensors("living room")
        assert len(results) == 1
        assert results[0].sensor_type == "temperature"

    def test_read_sensor(self):
        sensor = self.store.read_sensor("SN001")
        assert sensor is not None
        assert sensor.name == "Living Room Temperature"
        assert sensor.value == 22.5

    def test_list_devices_by_location(self):
        results = self.store.list_devices("living room")
        assert len(results) == 2  # light + thermostat

    def test_set_device(self):
        device = self.store.set_device("DV001", {"brightness": 50})
        assert device is not None
        assert device.settings["brightness"] == 50

    def test_set_device_status(self):
        device = self.store.set_device("DV001", {"status": "off"})
        assert device is not None
        assert device.status == "off"

    def test_create_automation_rule(self):
        rule = self.store.create_automation_rule(
            "Test Rule",
            {"condition": "time", "value": "12:00"},
            {"target": "lights", "command": "on"},
        )
        assert rule is not None
        assert rule.rule_id == "AR004"
        assert rule.enabled is True

    def test_set_automation_rule(self):
        rule = self.store.set_automation_rule("AR001", enabled=False)
        assert rule is not None
        assert rule.enabled is False

    def test_get_event_log(self):
        events = self.store.get_event_log()
        assert len(events) == 4
        # Newest first
        assert events[0].timestamp >= events[-1].timestamp

    def test_get_event_log_filtered(self):
        events = self.store.get_event_log(severity="warning")
        assert len(events) >= 1
        assert all(e.severity == "warning" for e in events)


# ── Industrial Store ────────────────────────────────────────────────────────

class TestIndustrialStore:
    def setup_method(self):
        self.store = IndustrialStore()

    def test_seed_data(self):
        assert len(self.store.machines) == 4
        assert len(self.store.telemetry) == 4
        assert len(self.store.thresholds) == 6
        assert len(self.store.maintenance_logs) == 3
        assert len(self.store.work_orders) == 1
        assert len(self.store.alerts) == 2

    def test_get_machine_status(self):
        machine = self.store.get_machine_status("MC001")
        assert machine is not None
        assert machine.name == "CNC Mill Alpha"
        assert machine.status == "running"

    def test_list_machines(self):
        all_machines = self.store.list_machines()
        assert len(all_machines) == 4

    def test_list_machines_filtered(self):
        running = self.store.list_machines("running")
        assert len(running) >= 1
        assert all(m.status == "running" for m in running)

    def test_read_telemetry(self):
        reading = self.store.read_telemetry("MC003")
        assert reading is not None
        assert reading.metrics["vibration"] == 8.7  # high

    def test_get_alert_thresholds(self):
        thresholds = self.store.get_alert_thresholds("MC001")
        assert len(thresholds) >= 1

    def test_get_maintenance_history(self):
        history = self.store.get_maintenance_history("MC001")
        assert len(history) >= 1

    def test_create_work_order(self):
        wo = self.store.create_work_order("MC001", "high", "Test work order")
        assert wo is not None
        assert wo.order_id == "WO002"
        assert wo.status == "open"
        assert wo.priority == "high"

    def test_update_work_order(self):
        wo = self.store.update_work_order("WO001", status="in_progress", assigned_to="Team A")
        assert wo is not None
        assert wo.status == "in_progress"
        assert wo.assigned_to == "Team A"

    def test_get_active_alerts(self):
        alerts = self.store.get_active_alerts()
        assert len(alerts) == 2
        assert all(not a.acknowledged for a in alerts)

    def test_get_active_alerts_by_machine(self):
        alerts = self.store.get_active_alerts("MC003")
        assert len(alerts) >= 1
        assert all(a.machine_id == "MC003" for a in alerts)

    def test_acknowledge_alert(self):
        alert = self.store.acknowledge_alert("AL001")
        assert alert is not None
        assert alert.acknowledged is True
        # Verify active alerts reduced
        active = self.store.get_active_alerts()
        assert len(active) == 1


# ── Fleet Store ─────────────────────────────────────────────────────────────

class TestFleetStore:
    def setup_method(self):
        self.store = FleetStore()

    def test_seed_data(self):
        assert len(self.store.vehicles) == 4
        assert len(self.store.drivers) == 4
        assert len(self.store.deliveries) == 5
        assert len(self.store.routes) == 3
        assert len(self.store.diagnostics) == 4

    def test_get_vehicle_status(self):
        vehicle = self.store.get_vehicle_status("VH001")
        assert vehicle is not None
        assert vehicle.vehicle_type == "van"
        assert vehicle.status == "available"

    def test_list_vehicles(self):
        all_vehicles = self.store.list_vehicles()
        assert len(all_vehicles) == 4

    def test_list_vehicles_filtered(self):
        available = self.store.list_vehicles("available")
        assert len(available) == 3  # VH001, VH003, VH004

    def test_get_vehicle_diagnostics(self):
        diag = self.store.get_vehicle_diagnostics("VH002")
        assert diag is not None
        assert "tire_pressure_low_rear" in diag.alerts

    def test_get_driver_info(self):
        driver = self.store.get_driver_info("DR001")
        assert driver is not None
        assert driver.name == "Alex Rivera"
        assert driver.status == "available"

    def test_list_drivers_filtered(self):
        available = self.store.list_drivers("available")
        assert len(available) >= 2

    def test_get_delivery_status(self):
        delivery = self.store.get_delivery_status("DL001")
        assert delivery is not None
        assert delivery.status == "in_transit"

    def test_assign_delivery(self):
        delivery = self.store.assign_delivery("DL003", "VH001", "DR001")
        assert delivery is not None
        assert delivery.vehicle_id == "VH001"
        assert delivery.driver_id == "DR001"
        # Vehicle should be en_route
        vehicle = self.store.get_vehicle_status("VH001")
        assert vehicle.status == "en_route"
        # Driver should be on_duty
        driver = self.store.get_driver_info("DR001")
        assert driver.status == "on_duty"

    def test_update_delivery_status(self):
        # First assign
        self.store.assign_delivery("DL003", "VH001", "DR001")
        # Then deliver
        delivery = self.store.update_delivery_status("DL003", "delivered")
        assert delivery is not None
        assert delivery.status == "delivered"

    def test_get_route_info(self):
        route = self.store.get_route_info("Warehouse A", "Customer Zone A")
        assert route is not None
        assert route.distance_km == 15.3
        assert route.conditions == "clear"

    def test_update_route_conditions(self):
        route = self.store.update_route_conditions("RT001", "traffic")
        assert route is not None
        assert route.conditions == "traffic"
