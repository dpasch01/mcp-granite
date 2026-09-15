"""In-memory data store for the Agriculture domain with deterministic seed data."""

from __future__ import annotations

from edgetoolbench.mcp_servers._data import generate_id
from edgetoolbench.mcp_servers.agriculture._domain import (
    AlertLog,
    Crop,
    DroneTask,
    IrrigationZone,
    Sensor,
    WeatherStation,
)


class AgricultureStore:
    def __init__(self) -> None:
        self.sensors: dict[str, Sensor] = {}
        self.irrigation_zones: dict[str, IrrigationZone] = {}
        self.crops: dict[str, Crop] = {}
        self.weather_stations: dict[str, WeatherStation] = {}
        self.drone_tasks: dict[str, DroneTask] = {}
        self.alert_log: list[AlertLog] = []
        self._next_drone_task = 4
        self._next_alert = 5
        self._seed_data()

    def _seed_data(self) -> None:
        # ── Sensors ──────────────────────────────────────────────────────
        sensor_data = [
            (
                "North Field Soil Moisture",
                "north field",
                "soil_moisture",
                32.5,
                "%",
                "2025-06-01T08:00:00",
                90.0,
            ),
            (
                "North Field Soil pH",
                "north field",
                "soil_ph",
                6.4,
                "pH",
                "2025-06-01T08:00:00",
                88.0,
            ),
            (
                "South Field Temperature",
                "south field",
                "temperature",
                28.3,
                "°C",
                "2025-06-01T08:15:00",
                95.0,
            ),
            (
                "South Field Humidity",
                "south field",
                "humidity",
                65.0,
                "%",
                "2025-06-01T08:15:00",
                82.0,
            ),
            (
                "East Field Wind Speed",
                "east field",
                "wind_speed",
                12.5,
                "km/h",
                "2025-06-01T08:10:00",
                76.0,
            ),
            (
                "Greenhouse Rainfall Gauge",
                "greenhouse",
                "rainfall",
                0.0,
                "mm",
                "2025-06-01T08:20:00",
                91.0,
            ),
        ]
        for i, (name, zone, stype, value, unit, updated, battery) in enumerate(sensor_data, 1):
            sid = generate_id("AS", i)
            self.sensors[sid] = Sensor(
                sensor_id=sid,
                name=name,
                field_zone=zone,
                sensor_type=stype,
                value=value,
                unit=unit,
                last_updated=updated,
                battery_level=battery,
            )

        # ── Irrigation Zones ─────────────────────────────────────────────
        irrigation_data = [
            (
                "North Drip Line",
                "north field",
                "active",
                15.0,
                {"start": "06:00", "duration_min": 30},
                "2025-06-01T06:30:00",
            ),
            (
                "South Sprinkler",
                "south field",
                "idle",
                25.0,
                {"start": "07:00", "duration_min": 45},
                "2025-05-31T07:45:00",
            ),
            (
                "East Drip Line",
                "east field",
                "scheduled",
                12.0,
                {"start": "05:30", "duration_min": 20},
                "2025-05-31T05:50:00",
            ),
            (
                "Greenhouse Mist",
                "greenhouse",
                "active",
                5.0,
                {"start": "09:00", "duration_min": 15},
                "2025-06-01T09:15:00",
            ),
            (
                "West Flood Zone",
                "west field",
                "fault",
                30.0,
                {"start": "06:30", "duration_min": 60},
                "2025-05-30T07:30:00",
            ),
            (
                "Orchard Micro-spray",
                "orchard",
                "idle",
                8.0,
                {"start": "08:00", "duration_min": 25},
                "2025-05-31T08:25:00",
            ),
        ]
        for i, (name, zone, status, flow, schedule, last_act) in enumerate(irrigation_data, 1):
            zid = generate_id("IZ", i)
            self.irrigation_zones[zid] = IrrigationZone(
                zone_id=zid,
                name=name,
                field_zone=zone,
                status=status,
                flow_rate=flow,
                schedule=schedule,
                last_activated=last_act,
            )

        # ── Crops ────────────────────────────────────────────────────────
        crop_data = [
            (
                "Wheat",
                "north field",
                "Winter Red",
                "2025-03-15",
                "healthy",
                "vegetative",
                "2025-08-20",
            ),
            (
                "Corn",
                "south field",
                "Sweet Yellow",
                "2025-04-01",
                "healthy",
                "flowering",
                "2025-09-10",
            ),
            ("Tomatoes", "greenhouse", "Roma", "2025-04-15", "stressed", "flowering", "2025-08-01"),
            (
                "Soybeans",
                "east field",
                "Roundup Ready",
                "2025-04-10",
                "healthy",
                "vegetative",
                "2025-09-25",
            ),
            ("Apples", "orchard", "Fuji", "2024-01-01", "healthy", "flowering", "2025-10-15"),
            (
                "Lettuce",
                "west field",
                "Iceberg",
                "2025-05-01",
                "diseased",
                "vegetative",
                "2025-07-15",
            ),
        ]
        for i, (name, zone, variety, planted, health, stage, harvest) in enumerate(crop_data, 1):
            cid = generate_id("CR", i)
            self.crops[cid] = Crop(
                crop_id=cid,
                name=name,
                field_zone=zone,
                variety=variety,
                plant_date=planted,
                health_status=health,
                growth_stage=stage,
                expected_harvest=harvest,
            )

        # ── Weather Stations ─────────────────────────────────────────────
        weather_data = [
            ("Main Station", "central hub", 28.3, 65.0, 12.5, 0.0, "clear", "2025-06-01T08:30:00"),
            (
                "North Outpost",
                "north field",
                27.8,
                68.0,
                10.2,
                0.0,
                "cloudy",
                "2025-06-01T08:30:00",
            ),
            ("Hill Station", "east field", 26.1, 72.0, 18.5, 2.5, "rain", "2025-06-01T08:30:00"),
        ]
        for i, (name, loc, temp, hum, wind, rain, forecast, updated) in enumerate(weather_data, 1):
            wid = generate_id("WS", i)
            self.weather_stations[wid] = WeatherStation(
                station_id=wid,
                name=name,
                location=loc,
                temperature=temp,
                humidity=hum,
                wind_speed=wind,
                rainfall_mm=rain,
                forecast=forecast,
                last_updated=updated,
            )

        # ── Drone Tasks ──────────────────────────────────────────────────
        drone_data = [
            (
                "DRONE-A",
                "survey",
                "north field",
                "completed",
                "2025-06-01T06:00:00",
                {"coverage": "95%", "anomalies": 2},
            ),
            ("DRONE-B", "spray", "south field", "in_progress", "2025-06-01T09:00:00", None),
            ("DRONE-A", "monitor", "west field", "pending", "2025-06-01T14:00:00", None),
        ]
        for i, (drone, ttype, zone, status, scheduled, result) in enumerate(drone_data, 1):
            tid = generate_id("DT", i)
            self.drone_tasks[tid] = DroneTask(
                task_id=tid,
                drone_id=drone,
                task_type=ttype,
                field_zone=zone,
                status=status,
                scheduled_time=scheduled,
                result=result,
            )

        # ── Alert Log ────────────────────────────────────────────────────
        alert_data = [
            (
                "2025-06-01T07:00:00",
                "AS001",
                "low_moisture",
                "North field soil moisture below threshold (32.5%)",
                "warning",
                False,
            ),
            (
                "2025-06-01T06:30:00",
                "CR006",
                "disease_detected",
                "Lettuce in west field showing signs of downy mildew",
                "critical",
                False,
            ),
            (
                "2025-06-01T05:00:00",
                "IZ005",
                "equipment_fault",
                "West flood zone pump not responding",
                "critical",
                True,
            ),
            (
                "2025-05-31T22:00:00",
                "WS003",
                "frost_warning",
                "Temperature at hill station dropping near frost levels",
                "warning",
                True,
            ),
        ]
        for i, (ts, source, atype, desc, sev, ack) in enumerate(alert_data, 1):
            aid = generate_id("AL", i)
            self.alert_log.append(
                AlertLog(
                    alert_id=aid,
                    timestamp=ts,
                    source_id=source,
                    alert_type=atype,
                    description=desc,
                    severity=sev,
                    acknowledged=ack,
                )
            )

    # ── Sensor methods ───────────────────────────────────────────────────

    def list_sensors(self, field_zone: str | None = None) -> list[Sensor]:
        if field_zone:
            return [s for s in self.sensors.values() if s.field_zone.lower() == field_zone.lower()]
        return list(self.sensors.values())

    def read_sensor(self, sensor_id: str) -> Sensor | None:
        return self.sensors.get(sensor_id)

    # ── Irrigation methods ───────────────────────────────────────────────

    def list_irrigation_zones(self, field_zone: str | None = None) -> list[IrrigationZone]:
        if field_zone:
            return [
                z
                for z in self.irrigation_zones.values()
                if z.field_zone.lower() == field_zone.lower()
            ]
        return list(self.irrigation_zones.values())

    def get_irrigation_zone(self, zone_id: str) -> IrrigationZone | None:
        return self.irrigation_zones.get(zone_id)

    def set_irrigation_zone(self, zone_id: str, **kwargs) -> IrrigationZone | None:
        zone = self.irrigation_zones.get(zone_id)
        if not zone:
            return None
        if "status" in kwargs:
            zone.status = kwargs["status"]
        if "flow_rate" in kwargs:
            zone.flow_rate = kwargs["flow_rate"]
        if "schedule" in kwargs:
            zone.schedule = kwargs["schedule"]
        return zone

    # ── Crop methods ─────────────────────────────────────────────────────

    def list_crops(self, field_zone: str | None = None) -> list[Crop]:
        if field_zone:
            return [c for c in self.crops.values() if c.field_zone.lower() == field_zone.lower()]
        return list(self.crops.values())

    def get_crop(self, crop_id: str) -> Crop | None:
        return self.crops.get(crop_id)

    def update_crop(self, crop_id: str, **kwargs) -> Crop | None:
        crop = self.crops.get(crop_id)
        if not crop:
            return None
        if "health_status" in kwargs:
            crop.health_status = kwargs["health_status"]
        if "growth_stage" in kwargs:
            crop.growth_stage = kwargs["growth_stage"]
        return crop

    # ── Weather methods ──────────────────────────────────────────────────

    def list_weather_stations(self) -> list[WeatherStation]:
        return list(self.weather_stations.values())

    def get_weather_station(self, station_id: str) -> WeatherStation | None:
        return self.weather_stations.get(station_id)

    # ── Drone methods ────────────────────────────────────────────────────

    def list_drone_tasks(self, status: str | None = None) -> list[DroneTask]:
        if status:
            return [t for t in self.drone_tasks.values() if t.status.lower() == status.lower()]
        return list(self.drone_tasks.values())

    def get_drone_task(self, task_id: str) -> DroneTask | None:
        return self.drone_tasks.get(task_id)

    def schedule_drone_task(
        self, drone_id: str, task_type: str, field_zone: str, scheduled_time: str
    ) -> DroneTask:
        tid = generate_id("DT", self._next_drone_task)
        self._next_drone_task += 1
        task = DroneTask(
            task_id=tid,
            drone_id=drone_id,
            task_type=task_type,
            field_zone=field_zone,
            status="pending",
            scheduled_time=scheduled_time,
        )
        self.drone_tasks[tid] = task
        return task

    # ── Alert methods ────────────────────────────────────────────────────

    def get_alerts(self, severity: str | None = None, limit: int = 10) -> list[AlertLog]:
        alerts = self.alert_log
        if severity:
            alerts = [a for a in alerts if a.severity.lower() == severity.lower()]
        alerts = sorted(alerts, key=lambda a: a.timestamp, reverse=True)
        return alerts[:limit]

    def acknowledge_alert(self, alert_id: str) -> AlertLog | None:
        for alert in self.alert_log:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return alert
        return None

    def _add_alert(
        self, source_id: str, alert_type: str, description: str, severity: str
    ) -> AlertLog:
        aid = generate_id("AL", self._next_alert)
        self._next_alert += 1
        alert = AlertLog(
            alert_id=aid,
            timestamp="2025-06-01T09:00:00",
            source_id=source_id,
            alert_type=alert_type,
            description=description,
            severity=severity,
        )
        self.alert_log.append(alert)
        return alert
