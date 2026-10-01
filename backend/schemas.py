"""Request and response models. Every value crossing the API is validated here."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


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


class ZipLocation(BaseModel):
    """A ZIP code resolved to a point by the location provider."""

    postcode: str
    country_code: str
    latitude: float
    longitude: float
    locality: str | None = None


class NearbyHotel(BaseModel):
    """A place the provider calls a hotel. It has no price: the provider supplies none."""

    place_id: str
    name: str | None = None
    latitude: float
    longitude: float
    address: str | None = None
    distance_m: int | None = None
    website: str | None = None


class NearbyHotelsResponse(BaseModel):
    """Hotels near the point a ZIP code resolved to. An empty list is a real answer."""

    location: ZipLocation
    radius_m: int
    limit: int
    may_have_more: bool
    omitted_count: int
    attribution: str | None = None
    hotels: list[NearbyHotel]


class SavedNight(BaseModel):
    """One night of simulated classroom data. Not supplied by the hotel API."""

    stay_date: str
    nightly_rate_cents: int
    rooms_available: int


class SavedHotelResult(BaseModel):
    """A hotel saved from the live API, with its simulated nights."""

    place_id: str
    name: str | None = None
    address: str | None = None
    latitude: float
    longitude: float
    distance_m: int | None = None
    nights: list[SavedNight]


class SavedHotelsResponse(BaseModel):
    """What is saved for one ZIP. Empty is a real answer, and never the whole area."""

    zip_code: str
    location: ZipLocation | None = None
    radius_m: int | None = None
    hotels: list[SavedHotelResult]


class SaveSearch(BaseModel):
    """The ZIP search a hotel is being saved from."""

    zip_code: str = Field(pattern=r"^\d{5}$")
    center_latitude: float = Field(ge=-90, le=90)
    center_longitude: float = Field(ge=-180, le=180)
    locality: str | None = None
    country_code: str = Field(default="US", min_length=2, max_length=2)
    radius_m: int = Field(gt=0)

    @field_validator("locality")
    @classmethod
    def _blank_locality_is_missing(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class SaveHotelRequest(BaseModel):
    """An API hotel to save, plus the search it came from."""

    place_id: str = Field(min_length=1)
    name: str | None = None
    address: str | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    distance_m: int | None = Field(default=None, ge=0)
    search: SaveSearch

    @field_validator("place_id")
    @classmethod
    def _id_is_not_blank(cls, value: str) -> str:
        # Checked, never changed: a provider id is kept exactly as given.
        if not value.strip():
            raise ValueError("place_id must not be blank")
        return value

    @field_validator("name", "address")
    @classmethod
    def _blank_text_is_missing(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class SaveHotelResponse(BaseModel):
    """`created` is False when the hotel was already saved and nothing was overwritten."""

    created: bool
    hotel: SavedHotelResult


class SavedStatusResponse(BaseModel):
    saved_ids: list[str]
