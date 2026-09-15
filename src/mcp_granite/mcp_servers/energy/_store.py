"""In-memory data store for the Energy (microgrid) domain with deterministic seed data."""

from __future__ import annotations

from mcp_granite.mcp_servers._data import generate_id
from mcp_granite.mcp_servers.energy._domain import (
    Battery,
    EnergyAlert,
    LoadZone,
    PowerSource,
    ScheduleEntry,
    SmartMeter,
)


class EnergyStore:
    def __init__(self) -> None:
        self.power_sources: dict[str, PowerSource] = {}
        self.load_zones: dict[str, LoadZone] = {}
        self.batteries: dict[str, Battery] = {}
        self.smart_meters: dict[str, SmartMeter] = {}
        self.alerts: list[EnergyAlert] = []
        self.schedule: dict[str, ScheduleEntry] = {}
        self._next_alert = 5
        self._next_schedule = 4
        self._seed_data()

    def _seed_data(self) -> None:
        # ── Power Sources ────────────────────────────────────────────────
        source_data = [
            (
                "Solar Array A",
                "solar",
                100.0,
                72.5,
                "online",
                "rooftop-east",
                "2025-06-01T08:30:00",
            ),
            ("Solar Array B", "solar", 80.0, 58.0, "online", "rooftop-west", "2025-06-01T08:30:00"),
            ("Wind Turbine 1", "wind", 50.0, 32.0, "online", "hilltop", "2025-06-01T08:30:00"),
            (
                "Diesel Generator",
                "diesel",
                200.0,
                0.0,
                "standby",
                "utility-room",
                "2025-06-01T06:00:00",
            ),
            ("Grid Tie", "grid_tie", 500.0, 45.0, "online", "main-panel", "2025-06-01T08:30:00"),
            (
                "Fuel Cell Unit",
                "fuel_cell",
                25.0,
                0.0,
                "offline",
                "lab-building",
                "2025-05-30T12:00:00",
            ),
        ]
        for i, (name, stype, cap, output, status, loc, updated) in enumerate(source_data, 1):
            sid = generate_id("PS", i)
            self.power_sources[sid] = PowerSource(
                source_id=sid,
                name=name,
                source_type=stype,
                capacity_kw=cap,
                current_output_kw=output,
                status=status,
                location=loc,
                last_updated=updated,
            )

        # ── Load Zones ───────────────────────────────────────────────────
        load_data = [
            ("Building A - Offices", "commercial", 45.0, 80.0, 3, "normal", "2025-06-01T08:30:00"),
            ("Building B - Labs", "critical", 62.0, 100.0, 1, "normal", "2025-06-01T08:30:00"),
            ("Residential Block", "residential", 35.0, 60.0, 4, "normal", "2025-06-01T08:30:00"),
            (
                "Manufacturing Floor",
                "industrial",
                120.0,
                150.0,
                2,
                "overloaded",
                "2025-06-01T08:30:00",
            ),
            ("EV Charging Station", "ev_charging", 25.0, 50.0, 5, "normal", "2025-06-01T08:30:00"),
            ("Data Center", "critical", 80.0, 100.0, 1, "normal", "2025-06-01T08:30:00"),
        ]
        for i, (name, ztype, load, cap, pri, status, updated) in enumerate(load_data, 1):
            zid = generate_id("LZ", i)
            self.load_zones[zid] = LoadZone(
                zone_id=zid,
                name=name,
                zone_type=ztype,
                current_load_kw=load,
                max_capacity_kw=cap,
                priority=pri,
                status=status,
                last_updated=updated,
            )

        # ── Batteries ────────────────────────────────────────────────────
        battery_data = [
            (
                "Main Battery Bank",
                500.0,
                325.0,
                50.0,
                75.0,
                "discharging",
                65.0,
                "2025-06-01T08:30:00",
            ),
            ("Backup Battery", 200.0, 190.0, 25.0, 50.0, "idle", 95.0, "2025-06-01T08:00:00"),
            ("Lab UPS Battery", 50.0, 12.5, 10.0, 25.0, "charging", 25.0, "2025-06-01T08:30:00"),
        ]
        for i, (name, cap, charge, c_rate, d_rate, status, soc, updated) in enumerate(
            battery_data, 1
        ):
            bid = generate_id("BT", i)
            self.batteries[bid] = Battery(
                battery_id=bid,
                name=name,
                capacity_kwh=cap,
                current_charge_kwh=charge,
                charge_rate_kw=c_rate,
                discharge_rate_kw=d_rate,
                status=status,
                soc_percent=soc,
                last_updated=updated,
            )

        # ── Smart Meters ─────────────────────────────────────────────────
        meter_data = [
            (
                "Solar Generation Meter",
                "rooftop-east",
                "generation",
                1250.5,
                0.98,
                240.0,
                "2025-06-01T08:30:00",
            ),
            (
                "Building A Meter",
                "building-a",
                "consumption",
                890.2,
                0.95,
                238.5,
                "2025-06-01T08:30:00",
            ),
            (
                "Building B Meter",
                "building-b",
                "consumption",
                1520.8,
                0.97,
                239.8,
                "2025-06-01T08:30:00",
            ),
            (
                "Grid Interconnect Meter",
                "main-panel",
                "grid_interconnect",
                2100.0,
                0.99,
                240.2,
                "2025-06-01T08:30:00",
            ),
            (
                "Residential Meter",
                "residential",
                "consumption",
                680.3,
                0.92,
                237.5,
                "2025-06-01T08:30:00",
            ),
            (
                "EV Station Meter",
                "ev-station",
                "bidirectional",
                450.0,
                0.94,
                239.0,
                "2025-06-01T08:30:00",
            ),
        ]
        for i, (name, loc, mtype, reading, pf, voltage, updated) in enumerate(meter_data, 1):
            mid = generate_id("SM", i)
            self.smart_meters[mid] = SmartMeter(
                meter_id=mid,
                name=name,
                location=loc,
                meter_type=mtype,
                current_reading_kwh=reading,
                power_factor=pf,
                voltage=voltage,
                last_updated=updated,
            )

        # ── Energy Alerts ────────────────────────────────────────────────
        alert_data = [
            (
                "2025-06-01T08:25:00",
                "LZ004",
                "overload",
                "Manufacturing floor load exceeds 80% capacity",
                "warning",
                False,
            ),
            (
                "2025-06-01T07:30:00",
                "BT003",
                "low_battery",
                "Lab UPS battery below 30% SOC",
                "critical",
                False,
            ),
            (
                "2025-06-01T06:00:00",
                "PS006",
                "grid_fault",
                "Fuel cell unit offline — hydrogen supply issue",
                "critical",
                True,
            ),
            (
                "2025-05-31T23:00:00",
                "PS005",
                "frequency_deviation",
                "Grid frequency deviation detected: 49.8Hz",
                "warning",
                True,
            ),
        ]
        for i, (ts, source, atype, desc, sev, ack) in enumerate(alert_data, 1):
            aid = generate_id("EA", i)
            self.alerts.append(
                EnergyAlert(
                    alert_id=aid,
                    timestamp=ts,
                    source_id=source,
                    alert_type=atype,
                    description=desc,
                    severity=sev,
                    acknowledged=ack,
                )
            )

        # ── Schedule Entries ─────────────────────────────────────────────
        schedule_data = [
            (
                "Morning Solar Ramp",
                "PS001",
                "start",
                "2025-06-01T06:00:00",
                "executed",
                {"mode": "mppt"},
            ),
            (
                "Night Battery Charge",
                "BT001",
                "charge",
                "2025-06-01T22:00:00",
                "pending",
                {"rate_kw": 50},
            ),
            (
                "Peak Shaving",
                "LZ005",
                "shed_load",
                "2025-06-01T14:00:00",
                "pending",
                {"reduce_by_kw": 15},
            ),
        ]
        for i, (name, target, action, stime, status, params) in enumerate(schedule_data, 1):
            eid = generate_id("SE", i)
            self.schedule[eid] = ScheduleEntry(
                entry_id=eid,
                name=name,
                target_id=target,
                action=action,
                scheduled_time=stime,
                status=status,
                parameters=params,
            )

    # ── Power Source methods ─────────────────────────────────────────────

    def list_power_sources(self, status: str | None = None) -> list[PowerSource]:
        if status:
            return [s for s in self.power_sources.values() if s.status.lower() == status.lower()]
        return list(self.power_sources.values())

    def get_power_source(self, source_id: str) -> PowerSource | None:
        return self.power_sources.get(source_id)

    def set_power_source(self, source_id: str, **kwargs) -> PowerSource | None:
        source = self.power_sources.get(source_id)
        if not source:
            return None
        if "status" in kwargs:
            source.status = kwargs["status"]
        if "current_output_kw" in kwargs:
            source.current_output_kw = kwargs["current_output_kw"]
        return source

    # ── Load Zone methods ────────────────────────────────────────────────

    def list_load_zones(self, zone_type: str | None = None) -> list[LoadZone]:
        if zone_type:
            return [z for z in self.load_zones.values() if z.zone_type.lower() == zone_type.lower()]
        return list(self.load_zones.values())

    def get_load_zone(self, zone_id: str) -> LoadZone | None:
        return self.load_zones.get(zone_id)

    def set_load_zone(self, zone_id: str, **kwargs) -> LoadZone | None:
        zone = self.load_zones.get(zone_id)
        if not zone:
            return None
        if "status" in kwargs:
            zone.status = kwargs["status"]
        if "current_load_kw" in kwargs:
            zone.current_load_kw = kwargs["current_load_kw"]
        if "priority" in kwargs:
            zone.priority = kwargs["priority"]
        return zone

    # ── Battery methods ──────────────────────────────────────────────────

    def list_batteries(self) -> list[Battery]:
        return list(self.batteries.values())

    def get_battery(self, battery_id: str) -> Battery | None:
        return self.batteries.get(battery_id)

    def set_battery(self, battery_id: str, **kwargs) -> Battery | None:
        battery = self.batteries.get(battery_id)
        if not battery:
            return None
        if "status" in kwargs:
            battery.status = kwargs["status"]
        if "charge_rate_kw" in kwargs:
            battery.charge_rate_kw = kwargs["charge_rate_kw"]
        if "discharge_rate_kw" in kwargs:
            battery.discharge_rate_kw = kwargs["discharge_rate_kw"]
        return battery

    # ── Smart Meter methods ──────────────────────────────────────────────

    def list_smart_meters(self, meter_type: str | None = None) -> list[SmartMeter]:
        if meter_type:
            return [
                m for m in self.smart_meters.values() if m.meter_type.lower() == meter_type.lower()
            ]
        return list(self.smart_meters.values())

    def get_smart_meter(self, meter_id: str) -> SmartMeter | None:
        return self.smart_meters.get(meter_id)

    # ── Alert methods ────────────────────────────────────────────────────

    def get_alerts(self, severity: str | None = None, limit: int = 10) -> list[EnergyAlert]:
        alerts = self.alerts
        if severity:
            alerts = [a for a in alerts if a.severity.lower() == severity.lower()]
        alerts = sorted(alerts, key=lambda a: a.timestamp, reverse=True)
        return alerts[:limit]

    def acknowledge_alert(self, alert_id: str) -> EnergyAlert | None:
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return alert
        return None

    def _add_alert(
        self, source_id: str, alert_type: str, description: str, severity: str
    ) -> EnergyAlert:
        aid = generate_id("EA", self._next_alert)
        self._next_alert += 1
        alert = EnergyAlert(
            alert_id=aid,
            timestamp="2025-06-01T09:00:00",
            source_id=source_id,
            alert_type=alert_type,
            description=description,
            severity=severity,
        )
        self.alerts.append(alert)
        return alert

    # ── Schedule methods ─────────────────────────────────────────────────

    def list_schedule(self, status: str | None = None) -> list[ScheduleEntry]:
        entries = list(self.schedule.values())
        if status:
            entries = [e for e in entries if e.status.lower() == status.lower()]
        return entries

    def create_schedule_entry(
        self, name: str, target_id: str, action: str, scheduled_time: str, parameters: dict
    ) -> ScheduleEntry:
        eid = generate_id("SE", self._next_schedule)
        self._next_schedule += 1
        entry = ScheduleEntry(
            entry_id=eid,
            name=name,
            target_id=target_id,
            action=action,
            scheduled_time=scheduled_time,
            status="pending",
            parameters=parameters,
        )
        self.schedule[eid] = entry
        return entry
