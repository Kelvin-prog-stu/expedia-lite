"""Response models. Every value the API returns is validated through these."""

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
    nightly_rate_usd: str
    trips: list[Trip]


class SearchResponse(BaseModel):
    """What a search returns. `count` is 0 when nothing matched."""

    query: str
    count: int
    hotels: list[HotelResult]
