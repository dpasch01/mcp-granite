"""In-memory data store for the Travel domain with deterministic seed data."""

from __future__ import annotations

from edgetoolbench.mcp_servers._data import generate_id
from edgetoolbench.mcp_servers.travel._domain import Booking, Flight, Hotel


class TravelStore:
    def __init__(self) -> None:
        self.flights: dict[str, Flight] = {}
        self.hotels: dict[str, Hotel] = {}
        self.bookings: dict[str, Booking] = {}
        self._next_booking = 1
        self._seed_data()

    def _seed_data(self) -> None:
        flight_data = [
            ("AA", "JFK", "LHR", "2025-03-15", "08:00", "20:00", 450.0, {"economy": 50, "business": 10}),
            ("BA", "JFK", "LHR", "2025-03-15", "14:00", "02:00", 520.0, {"economy": 30, "business": 8}),
            ("AA", "JFK", "LHR", "2025-03-15", "22:00", "10:00", 380.0, {"economy": 15, "business": 5}),
            ("BA", "LHR", "JFK", "2025-03-22", "09:00", "12:00", 470.0, {"economy": 40, "business": 12}),
            ("AA", "LHR", "JFK", "2025-03-22", "16:00", "19:00", 410.0, {"economy": 25, "business": 6}),
            ("DL", "JFK", "CDG", "2025-04-01", "10:00", "22:00", 550.0, {"economy": 60, "business": 15}),
            ("AF", "CDG", "JFK", "2025-04-08", "11:00", "14:00", 530.0, {"economy": 45, "business": 10}),
            ("UA", "SFO", "NRT", "2025-05-01", "13:00", "16:00", 890.0, {"economy": 70, "business": 20}),
        ]
        for i, (airline, orig, dest, dt, dep, arr, price, seats) in enumerate(flight_data, 1):
            fid = generate_id("FL", i)
            self.flights[fid] = Flight(
                flight_id=fid, airline=airline, origin=orig, destination=dest,
                date=dt, departure_time=dep, arrival_time=arr, price=price, seat_classes=seats,
            )

        hotel_data = [
            ("The Grand London", "London", 180.0, 4.5, 20),
            ("Budget Inn London", "London", 75.0, 3.2, 50),
            ("Riverside Hotel London", "London", 130.0, 4.0, 15),
            ("Hotel Parisien", "Paris", 200.0, 4.3, 10),
            ("Le Petit Paris", "Paris", 90.0, 3.8, 30),
            ("Tokyo Bay Hotel", "Tokyo", 160.0, 4.6, 25),
        ]
        for i, (name, city, price, rating, rooms) in enumerate(hotel_data, 1):
            hid = generate_id("HT", i)
            self.hotels[hid] = Hotel(
                hotel_id=hid, name=name, city=city,
                price_per_night=price, rating=rating, available_rooms=rooms,
            )

    # ----- Query methods -----

    def search_flights(
        self, origin: str, destination: str, date: str, max_results: int = 5
    ) -> list[Flight]:
        matches = [
            f for f in self.flights.values()
            if f.origin.upper() == origin.upper()
            and f.destination.upper() == destination.upper()
            and f.date == date
        ]
        matches.sort(key=lambda f: f.price)
        return matches[:max_results]

    def get_flight(self, flight_id: str) -> Flight | None:
        return self.flights.get(flight_id)

    def search_hotels(
        self, city: str, checkin: str, checkout: str, guests: int = 1, max_results: int = 5
    ) -> list[Hotel]:
        matches = [
            h for h in self.hotels.values()
            if h.city.lower() == city.lower() and h.available_rooms >= guests
        ]
        matches.sort(key=lambda h: h.price_per_night)
        return matches[:max_results]

    def get_hotel(self, hotel_id: str) -> Hotel | None:
        return self.hotels.get(hotel_id)

    def check_seat_availability(self, flight_id: str, seat_class: str) -> dict | None:
        flight = self.flights.get(flight_id)
        if not flight:
            return None
        avail = flight.seat_classes.get(seat_class, 0)
        return {"flight_id": flight_id, "seat_class": seat_class, "available": avail}

    # ----- Mutation methods -----

    def book_flight(self, flight_id: str, passenger_name: str, seat_class: str) -> Booking | None:
        flight = self.flights.get(flight_id)
        if not flight:
            return None
        avail = flight.seat_classes.get(seat_class, 0)
        if avail <= 0:
            return None
        flight.seat_classes[seat_class] = avail - 1
        bid = generate_id("BK", self._next_booking)
        self._next_booking += 1
        booking = Booking(
            booking_id=bid, booking_type="flight", reference_id=flight_id,
            passenger_name=passenger_name, status="confirmed",
            details={"seat_class": seat_class, "price": flight.price, "route": f"{flight.origin}->{flight.destination}", "date": flight.date},
        )
        self.bookings[bid] = booking
        return booking

    def book_hotel(
        self, hotel_id: str, guest_name: str, checkin: str, checkout: str
    ) -> Booking | None:
        hotel = self.hotels.get(hotel_id)
        if not hotel or hotel.available_rooms <= 0:
            return None
        hotel.available_rooms -= 1
        bid = generate_id("BK", self._next_booking)
        self._next_booking += 1
        booking = Booking(
            booking_id=bid, booking_type="hotel", reference_id=hotel_id,
            passenger_name=guest_name, status="confirmed",
            details={"hotel_name": hotel.name, "checkin": checkin, "checkout": checkout, "price_per_night": hotel.price_per_night},
        )
        self.bookings[bid] = booking
        return booking

    def cancel_booking(self, booking_id: str) -> bool:
        booking = self.bookings.get(booking_id)
        if not booking or booking.status == "cancelled":
            return False
        booking.status = "cancelled"
        # Restore capacity
        if booking.booking_type == "flight":
            flight = self.flights.get(booking.reference_id)
            if flight:
                sc = booking.details.get("seat_class", "economy")
                flight.seat_classes[sc] = flight.seat_classes.get(sc, 0) + 1
        elif booking.booking_type == "hotel":
            hotel = self.hotels.get(booking.reference_id)
            if hotel:
                hotel.available_rooms += 1
        return True

    def get_booking(self, booking_id: str) -> Booking | None:
        return self.bookings.get(booking_id)

    def get_payment_options(self, booking_id: str) -> list[dict] | None:
        booking = self.bookings.get(booking_id)
        if not booking:
            return None
        return [
            {"method": "credit_card", "surcharge": 0.0},
            {"method": "bank_transfer", "surcharge": 0.0},
            {"method": "paypal", "surcharge": 2.50},
        ]
