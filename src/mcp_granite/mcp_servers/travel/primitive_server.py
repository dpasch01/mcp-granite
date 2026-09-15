"""Travel domain – Primitive MCP server (10 fine-grained tools).

Run standalone:  python -m mcp_granite.mcp_servers.travel.primitive_server
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_granite.mcp_servers._base import (
    FaultConfig,
    FaultInjector,
    FaultType,
    corrupt_numeric_field,
    truncate_response,
)
from mcp_granite.mcp_servers.travel._store import TravelStore

mcp = FastMCP("travel-primitive")
store = TravelStore()
injector = FaultInjector(FaultConfig.from_env())


# ── helpers ──────────────────────────────────────────────────────────────────

def _apply_fault(results: list[dict], fault: FaultType | None) -> list[dict]:
    if fault == FaultType.PARTIAL_RESPONSE:
        return truncate_response(results)
    if fault == FaultType.CONTRADICTORY:
        return [corrupt_numeric_field(r, "price") for r in results]
    return results


# ── tools ────────────────────────────────────────────────────────────────────

@mcp.tool()
async def search_flights(
    origin: str, destination: str, date: str, max_results: int = 5
) -> list[dict]:
    """Search for available flights between two airports on a given date."""
    fault = await injector.maybe_raise("search_flights")
    flights = store.search_flights(origin, destination, date, max_results)
    results = [f.model_dump() for f in flights]
    return _apply_fault(results, fault)


@mcp.tool()
async def get_flight_details(flight_id: str) -> dict:
    """Get detailed information about a specific flight."""
    fault = await injector.maybe_raise("get_flight_details")
    flight = store.get_flight(flight_id)
    if not flight:
        return {"error": f"Flight '{flight_id}' not found."}
    result = flight.model_dump()
    if fault == FaultType.CONTRADICTORY:
        result = corrupt_numeric_field(result, "price")
    return result


@mcp.tool()
async def search_hotels(
    city: str, checkin: str, checkout: str, guests: int = 1, max_results: int = 5
) -> list[dict]:
    """Search for available hotels in a city for given dates."""
    fault = await injector.maybe_raise("search_hotels")
    hotels = store.search_hotels(city, checkin, checkout, guests, max_results)
    results = [h.model_dump() for h in hotels]
    return _apply_fault(results, fault)


@mcp.tool()
async def get_hotel_details(hotel_id: str) -> dict:
    """Get detailed information about a specific hotel."""
    fault = await injector.maybe_raise("get_hotel_details")
    hotel = store.get_hotel(hotel_id)
    if not hotel:
        return {"error": f"Hotel '{hotel_id}' not found."}
    result = hotel.model_dump()
    if fault == FaultType.CONTRADICTORY:
        result = corrupt_numeric_field(result, "price_per_night")
    return result


@mcp.tool()
async def check_seat_availability(flight_id: str, seat_class: str) -> dict:
    """Check seat availability for a specific flight and class."""
    fault = await injector.maybe_raise("check_seat_availability")
    result = store.check_seat_availability(flight_id, seat_class)
    if not result:
        return {"error": f"Flight '{flight_id}' not found."}
    if fault == FaultType.CONTRADICTORY:
        result = {**result, "available": 0}  # lie about availability
    return result


@mcp.tool()
async def book_flight(flight_id: str, passenger_name: str, seat_class: str) -> dict:
    """Book a seat on a specific flight."""
    fault = await injector.maybe_raise("book_flight")
    booking = store.book_flight(flight_id, passenger_name, seat_class)
    if not booking:
        return {"error": f"Could not book flight '{flight_id}' in {seat_class}."}
    result = booking.model_dump()
    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("details", None)
    return result


@mcp.tool()
async def book_hotel(
    hotel_id: str, guest_name: str, checkin: str, checkout: str
) -> dict:
    """Book a hotel room for the specified dates."""
    fault = await injector.maybe_raise("book_hotel")
    booking = store.book_hotel(hotel_id, guest_name, checkin, checkout)
    if not booking:
        return {"error": f"Could not book hotel '{hotel_id}'."}
    result = booking.model_dump()
    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("details", None)
    return result


@mcp.tool()
async def cancel_booking(booking_id: str) -> dict:
    """Cancel an existing booking."""
    await injector.maybe_raise("cancel_booking")
    success = store.cancel_booking(booking_id)
    if not success:
        return {"error": f"Could not cancel booking '{booking_id}'."}
    return {"booking_id": booking_id, "status": "cancelled"}


@mcp.tool()
async def get_booking_status(booking_id: str) -> dict:
    """Get the current status of a booking."""
    fault = await injector.maybe_raise("get_booking_status")
    booking = store.get_booking(booking_id)
    if not booking:
        return {"error": f"Booking '{booking_id}' not found."}
    result = booking.model_dump()
    if fault == FaultType.CONTRADICTORY:
        result["status"] = "pending"  # lie about status
    return result


@mcp.tool()
async def get_payment_options(booking_id: str) -> list[dict]:
    """Get available payment methods for a booking."""
    await injector.maybe_raise("get_payment_options")
    options = store.get_payment_options(booking_id)
    if options is None:
        return [{"error": f"Booking '{booking_id}' not found."}]
    return options


if __name__ == "__main__":
    mcp.run(transport="stdio")
