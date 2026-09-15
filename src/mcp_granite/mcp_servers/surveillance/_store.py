"""In-memory data store for the Surveillance domain with deterministic seed data."""

from __future__ import annotations

from mcp_granite.mcp_servers._data import generate_id
from mcp_granite.mcp_servers.surveillance._domain import (
    AccessPoint,
    AlarmZone,
    Camera,
    MotionSensor,
    Patrol,
    SecurityEvent,
)


class SurveillanceStore:
    def __init__(self) -> None:
        self.cameras: dict[str, Camera] = {}
        self.motion_sensors: dict[str, MotionSensor] = {}
        self.access_points: dict[str, AccessPoint] = {}
        self.alarm_zones: dict[str, AlarmZone] = {}
        self.events: list[SecurityEvent] = []
        self.patrols: dict[str, Patrol] = {}
        self._next_event = 5
        self._next_patrol = 4
        self._seed_data()

    def _seed_data(self) -> None:
        camera_data = [
            (
                "Main Entrance Cam",
                "main entrance",
                "dome",
                "recording",
                "4k",
                True,
                True,
                "2025-06-01T08:00:00",
            ),
            (
                "Parking Lot A",
                "parking lot",
                "ptz",
                "recording",
                "1080p",
                True,
                True,
                "2025-06-01T08:00:00",
            ),
            (
                "Server Room",
                "server room",
                "fixed",
                "recording",
                "4k",
                False,
                True,
                "2025-06-01T08:00:00",
            ),
            (
                "Loading Dock",
                "loading dock",
                "fixed",
                "idle",
                "1080p",
                True,
                False,
                "2025-06-01T06:00:00",
            ),
            (
                "Perimeter North",
                "north fence",
                "thermal",
                "recording",
                "720p",
                True,
                True,
                "2025-06-01T08:00:00",
            ),
            ("Lobby Cam", "lobby", "dome", "fault", "1080p", False, False, "2025-06-01T07:00:00"),
        ]
        for i, (name, loc, ctype, status, res, nv, rec, updated) in enumerate(camera_data, 1):
            cid = generate_id("CM", i)
            self.cameras[cid] = Camera(
                camera_id=cid,
                name=name,
                location=loc,
                camera_type=ctype,
                status=status,
                resolution=res,
                night_vision=nv,
                recording=rec,
                last_updated=updated,
            )

        sensor_data = [
            (
                "Entrance Motion",
                "main entrance",
                "high",
                "armed",
                "2025-06-01T07:45:00",
                92.0,
                "2025-06-01T08:00:00",
            ),
            (
                "Parking Motion",
                "parking lot",
                "medium",
                "armed",
                "2025-06-01T06:30:00",
                85.0,
                "2025-06-01T08:00:00",
            ),
            (
                "Server Room Motion",
                "server room",
                "high",
                "armed",
                None,
                95.0,
                "2025-06-01T08:00:00",
            ),
            (
                "Loading Dock Motion",
                "loading dock",
                "medium",
                "disarmed",
                "2025-06-01T05:00:00",
                78.0,
                "2025-06-01T08:00:00",
            ),
            (
                "North Perimeter",
                "north fence",
                "high",
                "triggered",
                "2025-06-01T07:55:00",
                88.0,
                "2025-06-01T08:00:00",
            ),
            (
                "Lobby Motion",
                "lobby",
                "low",
                "armed",
                "2025-06-01T07:30:00",
                45.0,
                "2025-06-01T08:00:00",
            ),
        ]
        for i, (name, loc, sens, status, triggered, battery, updated) in enumerate(sensor_data, 1):
            sid = generate_id("MS", i)
            self.motion_sensors[sid] = MotionSensor(
                sensor_id=sid,
                name=name,
                location=loc,
                sensitivity=sens,
                status=status,
                last_triggered=triggered,
                battery_level=battery,
                last_updated=updated,
            )

        access_data = [
            (
                "Front Door",
                "main entrance",
                "door",
                "locked",
                2,
                "2025-06-01T07:50:00",
                "2025-06-01T08:00:00",
            ),
            (
                "Side Gate",
                "parking lot",
                "gate",
                "locked",
                3,
                "2025-06-01T06:00:00",
                "2025-06-01T08:00:00",
            ),
            (
                "Server Room Door",
                "server room",
                "door",
                "locked",
                5,
                "2025-05-31T18:00:00",
                "2025-06-01T08:00:00",
            ),
            (
                "Loading Bay Gate",
                "loading dock",
                "barrier",
                "unlocked",
                2,
                "2025-06-01T07:30:00",
                "2025-06-01T08:00:00",
            ),
            (
                "Lobby Turnstile",
                "lobby",
                "turnstile",
                "unlocked",
                1,
                "2025-06-01T07:55:00",
                "2025-06-01T08:00:00",
            ),
            ("Emergency Exit", "north fence", "door", "locked", 4, None, "2025-06-01T08:00:00"),
        ]
        for i, (name, loc, ptype, status, level, last_access, updated) in enumerate(access_data, 1):
            pid = generate_id("AP", i)
            self.access_points[pid] = AccessPoint(
                point_id=pid,
                name=name,
                location=loc,
                point_type=ptype,
                status=status,
                access_level=level,
                last_access=last_access,
                last_updated=updated,
            )

        zone_data = [
            (
                "Perimeter Zone",
                "perimeter",
                "armed",
                ["MS002", "MS005"],
                ["CM002", "CM005"],
                "2025-06-01T08:00:00",
            ),
            (
                "Interior Zone",
                "interior",
                "armed",
                ["MS001", "MS006"],
                ["CM001", "CM006"],
                "2025-06-01T08:00:00",
            ),
            (
                "High Security Zone",
                "high_security",
                "armed",
                ["MS003"],
                ["CM003"],
                "2025-06-01T08:00:00",
            ),
            ("Parking Zone", "parking", "armed", ["MS002"], ["CM002"], "2025-06-01T08:00:00"),
        ]
        for i, (name, ztype, status, sensors, cameras, updated) in enumerate(zone_data, 1):
            zid = generate_id("AZ", i)
            self.alarm_zones[zid] = AlarmZone(
                zone_id=zid,
                name=name,
                zone_type=ztype,
                status=status,
                sensors=sensors,
                cameras=cameras,
                last_updated=updated,
            )

        event_data = [
            (
                "2025-06-01T07:55:00",
                "MS005",
                "motion_detected",
                "Motion detected at north perimeter fence",
                "warning",
                False,
            ),
            (
                "2025-06-01T07:50:00",
                "AP001",
                "access_granted",
                "Badge access at front door — employee J. Smith",
                "info",
                True,
            ),
            (
                "2025-06-01T07:30:00",
                "AP004",
                "access_granted",
                "Loading bay gate opened for delivery",
                "info",
                True,
            ),
            (
                "2025-06-01T07:00:00",
                "CM006",
                "camera_tamper",
                "Lobby camera feed lost — possible tamper",
                "critical",
                False,
            ),
        ]
        for i, (ts, source, etype, desc, sev, ack) in enumerate(event_data, 1):
            eid = generate_id("SE", i)
            self.events.append(
                SecurityEvent(
                    event_id=eid,
                    timestamp=ts,
                    source_id=source,
                    event_type=etype,
                    description=desc,
                    severity=sev,
                    acknowledged=ack,
                )
            )

        patrol_data = [
            (
                "Morning Perimeter",
                ["north fence", "parking lot", "loading dock", "main entrance"],
                "completed",
                "Guard A",
                "2025-06-01T06:00:00",
                "2025-06-01T06:45:00",
            ),
            (
                "Midday Interior",
                ["lobby", "server room", "main entrance"],
                "in_progress",
                "Guard B",
                "2025-06-01T08:00:00",
                None,
            ),
            (
                "Evening Full",
                [
                    "main entrance",
                    "parking lot",
                    "north fence",
                    "loading dock",
                    "lobby",
                    "server room",
                ],
                "scheduled",
                None,
                "2025-06-01T18:00:00",
                None,
            ),
        ]
        for i, (name, route, status, guard, stime, completed) in enumerate(patrol_data, 1):
            pid = generate_id("PT", i)
            self.patrols[pid] = Patrol(
                patrol_id=pid,
                name=name,
                route=route,
                status=status,
                assigned_guard=guard,
                scheduled_time=stime,
                last_completed=completed,
            )

    # ── Camera methods ───────────────────────────────────────────────────
    def list_cameras(self, location: str | None = None) -> list[Camera]:
        if location:
            return [c for c in self.cameras.values() if c.location.lower() == location.lower()]
        return list(self.cameras.values())

    def get_camera(self, camera_id: str) -> Camera | None:
        return self.cameras.get(camera_id)

    def set_camera(self, camera_id: str, **kwargs) -> Camera | None:
        cam = self.cameras.get(camera_id)
        if not cam:
            return None
        for k in ("status", "recording", "night_vision"):
            if k in kwargs:
                setattr(cam, k, kwargs[k])
        return cam

    # ── Motion Sensor methods ────────────────────────────────────────────
    def list_motion_sensors(self, location: str | None = None) -> list[MotionSensor]:
        if location:
            return [
                s for s in self.motion_sensors.values() if s.location.lower() == location.lower()
            ]
        return list(self.motion_sensors.values())

    def get_motion_sensor(self, sensor_id: str) -> MotionSensor | None:
        return self.motion_sensors.get(sensor_id)

    def set_motion_sensor(self, sensor_id: str, **kwargs) -> MotionSensor | None:
        sensor = self.motion_sensors.get(sensor_id)
        if not sensor:
            return None
        for k in ("status", "sensitivity"):
            if k in kwargs:
                setattr(sensor, k, kwargs[k])
        return sensor

    # ── Access Point methods ─────────────────────────────────────────────
    def list_access_points(self, location: str | None = None) -> list[AccessPoint]:
        if location:
            return [
                a for a in self.access_points.values() if a.location.lower() == location.lower()
            ]
        return list(self.access_points.values())

    def get_access_point(self, point_id: str) -> AccessPoint | None:
        return self.access_points.get(point_id)

    def set_access_point(self, point_id: str, **kwargs) -> AccessPoint | None:
        point = self.access_points.get(point_id)
        if not point:
            return None
        for k in ("status", "access_level"):
            if k in kwargs:
                setattr(point, k, kwargs[k])
        return point

    # ── Alarm Zone methods ───────────────────────────────────────────────
    def list_alarm_zones(self) -> list[AlarmZone]:
        return list(self.alarm_zones.values())

    def get_alarm_zone(self, zone_id: str) -> AlarmZone | None:
        return self.alarm_zones.get(zone_id)

    def set_alarm_zone(self, zone_id: str, **kwargs) -> AlarmZone | None:
        zone = self.alarm_zones.get(zone_id)
        if not zone:
            return None
        if "status" in kwargs:
            zone.status = kwargs["status"]
        return zone

    # ── Event methods ────────────────────────────────────────────────────
    def get_events(self, severity: str | None = None, limit: int = 10) -> list[SecurityEvent]:
        events = self.events
        if severity:
            events = [e for e in events if e.severity.lower() == severity.lower()]
        events = sorted(events, key=lambda e: e.timestamp, reverse=True)
        return events[:limit]

    def acknowledge_event(self, event_id: str) -> SecurityEvent | None:
        for event in self.events:
            if event.event_id == event_id:
                event.acknowledged = True
                return event
        return None

    def _add_event(
        self, source_id: str, event_type: str, description: str, severity: str
    ) -> SecurityEvent:
        eid = generate_id("SE", self._next_event)
        self._next_event += 1
        event = SecurityEvent(
            event_id=eid,
            timestamp="2025-06-01T09:00:00",
            source_id=source_id,
            event_type=event_type,
            description=description,
            severity=severity,
        )
        self.events.append(event)
        return event

    # ── Patrol methods ───────────────────────────────────────────────────
    def list_patrols(self, status: str | None = None) -> list[Patrol]:
        if status:
            return [p for p in self.patrols.values() if p.status.lower() == status.lower()]
        return list(self.patrols.values())

    def get_patrol(self, patrol_id: str) -> Patrol | None:
        return self.patrols.get(patrol_id)

    def schedule_patrol(
        self, name: str, route: list[str], scheduled_time: str, assigned_guard: str | None = None
    ) -> Patrol:
        pid = generate_id("PT", self._next_patrol)
        self._next_patrol += 1
        patrol = Patrol(
            patrol_id=pid,
            name=name,
            route=route,
            status="scheduled",
            assigned_guard=assigned_guard,
            scheduled_time=scheduled_time,
        )
        self.patrols[pid] = patrol
        return patrol

    def update_patrol(self, patrol_id: str, **kwargs) -> Patrol | None:
        patrol = self.patrols.get(patrol_id)
        if not patrol:
            return None
        for k in ("status", "assigned_guard"):
            if k in kwargs:
                setattr(patrol, k, kwargs[k])
        return patrol
