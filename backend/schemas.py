"""Request and response models. Every value crossing the API is validated here."""

from typing import Literal

from pydantic import BaseModel


class Trip(BaseModel):
    """One offered hotel stay with fixed dates."""

    trip_id: str
    hotel_id: str
    trip_name: str
    check_in: str
    check_out: str


class HotelResult(BaseModel):
    """A hotel plus the stays offered at it."""

    hotel_id: str
    hotel_name: str
    city: str
    state: str
    nightly_rate_usd: int
    trips: list[Trip]


class SearchResponse(BaseModel):
    """What a search returns. `count` is 0 when nothing matched."""

    query: str
    count: int
    hotels: list[HotelResult]


class User(BaseModel):
    user_id: str
    display_name: str


class Booking(BaseModel):
    """A booking joined to its traveler, stay, and hotel for display."""

    booking_id: str
    user_id: str
    display_name: str
    trip_id: str
    trip_name: str
    check_in: str
    check_out: str
    hotel_id: str
    hotel_name: str
    city: str
    state: str
    nightly_rate_usd: int
    booked_on: str
    status: Literal["confirmed", "cancelled"]


class BookingCreate(BaseModel):
    user_id: str
    trip_id: str


class BookingUpdate(BaseModel):
    """Only cancellation is allowed; the record is kept."""

    status: Literal["cancelled"]
