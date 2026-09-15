"""Travel domain – Composite MCP server (4 high-level tools).

Run standalone:  python -m mcp_granite.mcp_servers.travel.composite_4_server
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_granite.mcp_servers._base import (
    FaultConfig,
    FaultInjector,
    FaultType,
)
from mcp_granite.mcp_servers.travel._store import TravelStore

mcp = FastMCP("travel-composite")
store = TravelStore()
injector = FaultInjector(FaultConfig.from_env())


@mcp.tool()
async def plan_trip(
    origin: str,
    destination: str,
    depart_date: str,
    return_date: str,
    guests: int = 1,
    preferences: dict | None = None,
) -> dict:
    """Search and rank flights + hotels for a roundtrip, returning a complete trip plan.

    Args:
        origin: Departure airport code (e.g. 'JFK').
        destination: Arrival airport code (e.g. 'LHR').
        depart_date: Outbound date (YYYY-MM-DD).
        return_date: Return date (YYYY-MM-DD).
        guests: Number of travellers.
        preferences: Optional dict with 'class' (economy/business) and 'sort_by' (price/rating).
    """
    fault = await injector.maybe_raise("plan_trip")
    prefs = preferences or {}
    seat_class = prefs.get("class", "economy")
    sort_by = prefs.get("sort_by", "price")

    # Search outbound + return flights
    outbound = store.search_flights(origin, destination, depart_date)
    inbound = store.search_flights(destination, origin, return_date)

    # Determine destination city from destination code for hotel search
    dest_city_map = {"LHR": "London", "CDG": "Paris", "NRT": "Tokyo"}
    dest_city = dest_city_map.get(destination.upper(), destination)

    hotels = store.search_hotels(dest_city, depart_date, return_date, guests)

    if sort_by == "price":
        outbound.sort(key=lambda f: f.price)
        inbound.sort(key=lambda f: f.price)
    elif sort_by == "rating":
        hotels.sort(key=lambda h: -h.rating)

    # Filter flights by seat class availability
    outbound = [f for f in outbound if f.seat_classes.get(seat_class, 0) > 0]
    inbound = [f for f in inbound if f.seat_classes.get(seat_class, 0) > 0]

    plan = {
        "trip_plan_id": "TP001",
        "origin": origin,
        "destination": destination,
        "depart_date": depart_date,
        "return_date": return_date,
        "outbound_options": [f.model_dump() for f in outbound[:3]],
        "return_options": [f.model_dump() for f in inbound[:3]],
        "hotel_options": [h.model_dump() for h in hotels[:3]],
        "recommended": {
            "outbound_flight": outbound[0].flight_id if outbound else None,
            "return_flight": inbound[0].flight_id if inbound else None,
            "hotel": hotels[0].hotel_id if hotels else None,
        },
    }

    if fault == FaultType.PARTIAL_RESPONSE:
        plan.pop("hotel_options", None)
        plan["recommended"].pop("hotel", None)
    elif fault == FaultType.CONTRADICTORY:
        for opt in plan.get("outbound_options", []):
            opt["price"] = round(opt["price"] * 0.1, 2)

    return plan


@mcp.tool()
async def book_trip(
    trip_plan_id: str,
    passenger_details: dict,
    payment_method: str = "default",
    outbound_flight: str | None = None,
    return_flight: str | None = None,
    hotel: str | None = None,
    seat_class: str = "economy",
    checkin: str | None = None,
    checkout: str | None = None,
) -> dict:
    """Book a complete trip (flights + optional hotel) in a single operation.

    Args:
        trip_plan_id: ID from plan_trip result.
        passenger_details: Dict with at least 'name'.
        payment_method: Payment method string.
        outbound_flight: Flight ID for outbound (uses plan recommendation if omitted).
        return_flight: Flight ID for return (uses plan recommendation if omitted).
        hotel: Hotel ID (uses plan recommendation if omitted, pass 'none' to skip).
        seat_class: Seat class for flights.
        checkin: Hotel check-in date.
        checkout: Hotel check-out date.
    """
    fault = await injector.maybe_raise("book_trip")
    name = passenger_details.get("name", "Guest")

    bookings = []

    # Book outbound flight
    if outbound_flight:
        ob = store.book_flight(outbound_flight, name, seat_class)
        if ob:
            bookings.append(ob.model_dump())
        else:
            return {"error": f"Failed to book outbound flight '{outbound_flight}'."}

    # Book return flight
    if return_flight:
        rb = store.book_flight(return_flight, name, seat_class)
        if rb:
            bookings.append(rb.model_dump())
        else:
            return {"error": f"Failed to book return flight '{return_flight}'."}

    # Book hotel
    if hotel and hotel.lower() != "none":
        ci = checkin or ""
        co = checkout or ""
        hb = store.book_hotel(hotel, name, ci, co)
        if hb:
            bookings.append(hb.model_dump())
        else:
            return {"error": f"Failed to book hotel '{hotel}'."}

    result = {
        "trip_plan_id": trip_plan_id,
        "status": "confirmed",
        "bookings": bookings,
        "total_bookings": len(bookings),
        "payment_method": payment_method,
    }

    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("bookings", None)

    return result


@mcp.tool()
async def modify_trip(booking_id: str, changes: dict) -> dict:
    """Modify an existing trip booking (cancel and rebook components).

    Args:
        booking_id: The booking ID to modify.
        changes: Dict describing changes, e.g. {'new_date': '2025-03-25', 'action': 'rebook'}.
    """
    fault = await injector.maybe_raise("modify_trip")
    booking = store.get_booking(booking_id)
    if not booking:
        return {"error": f"Booking '{booking_id}' not found."}

    action = changes.get("action", "cancel")

    if action == "cancel":
        success = store.cancel_booking(booking_id)
        return {"booking_id": booking_id, "action": "cancelled", "success": success}

    if action == "rebook":
        # Cancel existing, then rebook with new parameters
        store.cancel_booking(booking_id)
        new_date = changes.get("new_date")
        if booking.booking_type == "flight":
            flight = store.get_flight(booking.reference_id)
            if flight and new_date:
                # Find flights on new date for same route
                alt_flights = store.search_flights(flight.origin, flight.destination, new_date)
                if alt_flights:
                    new_booking = store.book_flight(
                        alt_flights[0].flight_id,
                        booking.passenger_name,
                        booking.details.get("seat_class", "economy"),
                    )
                    if new_booking:
                        result = {
                            "original_booking": booking_id,
                            "action": "rebooked",
                            "new_booking": new_booking.model_dump(),
                        }
                        if fault == FaultType.PARTIAL_RESPONSE:
                            result.pop("new_booking", None)
                        return result
        return {"error": "Could not rebook — no alternatives found."}

    return {"error": f"Unknown action '{action}'."}


@mcp.tool()
async def get_trip_summary(booking_id: str) -> dict:
    """Get a complete summary of a trip booking including all details.

    Args:
        booking_id: Any booking ID from the trip.
    """
    fault = await injector.maybe_raise("get_trip_summary")
    booking = store.get_booking(booking_id)
    if not booking:
        return {"error": f"Booking '{booking_id}' not found."}

    summary: dict = {
        "booking_id": booking.booking_id,
        "passenger": booking.passenger_name,
        "status": booking.status,
        "type": booking.booking_type,
        "details": booking.details,
    }

    # Enrich with current resource data
    if booking.booking_type == "flight":
        flight = store.get_flight(booking.reference_id)
        if flight:
            summary["flight_info"] = flight.model_dump()
    elif booking.booking_type == "hotel":
        hotel = store.get_hotel(booking.reference_id)
        if hotel:
            summary["hotel_info"] = hotel.model_dump()

    payment = store.get_payment_options(booking_id)
    if payment:
        summary["payment_options"] = payment

    if fault == FaultType.PARTIAL_RESPONSE:
        summary.pop("payment_options", None)
        summary.pop("flight_info", None)
        summary.pop("hotel_info", None)
    elif fault == FaultType.CONTRADICTORY:
        summary["status"] = "pending"

    return summary


if __name__ == "__main__":
    mcp.run(transport="stdio")
