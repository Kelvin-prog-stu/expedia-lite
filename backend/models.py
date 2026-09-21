"""Model layer: the data Expedia Lite stores and how the records relate.

Four tables mirror the supplied CSV files. Foreign keys encode the relationships
from the data pack: a trip belongs to one hotel, and a booking connects one
traveler to one trip. Several trips can share a hotel, and several bookings can
share a traveler or a trip.
"""

from dataclasses import dataclass

BOOKING_CONFIRMED = "confirmed"
BOOKING_CANCELLED = "cancelled"
BOOKING_STATUSES = (BOOKING_CONFIRMED, BOOKING_CANCELLED)

SCHEMA = """
CREATE TABLE IF NOT EXISTS hotels (
    hotel_id          TEXT PRIMARY KEY,
    hotel_name        TEXT NOT NULL,
    city              TEXT NOT NULL,
    state             TEXT NOT NULL,
    nightly_rate_usd  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS trips (
    trip_id    TEXT PRIMARY KEY,
    hotel_id   TEXT NOT NULL REFERENCES hotels (hotel_id),
    trip_name  TEXT NOT NULL,
    check_in   TEXT NOT NULL,
    check_out  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    user_id       TEXT PRIMARY KEY,
    display_name  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bookings (
    booking_id  TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users (user_id),
    trip_id     TEXT NOT NULL REFERENCES trips (trip_id),
    booked_on   TEXT NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('confirmed', 'cancelled'))
);

-- Bookkeeping that must survive restarts: whether the starter data has been
-- loaded, and the next booking number to hand out.
CREATE TABLE IF NOT EXISTS app_meta (
    key    TEXT PRIMARY KEY,
    value  TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class Hotel:
    hotel_id: str
    hotel_name: str
    city: str
    state: str
    nightly_rate_usd: int


@dataclass(frozen=True)
class Trip:
    """One offered stay with fixed dates. Belongs to a Hotel via hotel_id."""

    trip_id: str
    hotel_id: str
    trip_name: str
    check_in: str
    check_out: str


@dataclass(frozen=True)
class User:
    user_id: str
    display_name: str


@dataclass(frozen=True)
class Booking:
    """Connects a User to a Trip. Cancelling changes status; the row is kept."""

    booking_id: str
    user_id: str
    trip_id: str
    booked_on: str
    status: str
