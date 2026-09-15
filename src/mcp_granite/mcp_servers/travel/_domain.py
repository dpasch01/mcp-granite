"""Domain models for the Travel booking mock."""

from __future__ import annotations

from pydantic import BaseModel


class Flight(BaseModel):
    flight_id: str
    airline: str
    origin: str
    destination: str
    date: str
    departure_time: str
    arrival_time: str
    price: float
    seat_classes: dict[str, int]  # class -> available seats


class Hotel(BaseModel):
    hotel_id: str
    name: str
    city: str
    price_per_night: float
    rating: float
    available_rooms: int


class Booking(BaseModel):
    booking_id: str
    booking_type: str  # "flight" or "hotel"
    reference_id: str  # flight_id or hotel_id
    passenger_name: str
    status: str  # "confirmed", "cancelled"
    details: dict
