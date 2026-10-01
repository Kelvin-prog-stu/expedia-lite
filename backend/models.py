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

# The nights a saved hotel gets simulated classroom rows for: October 10 to 14, 2026,
# both ends included. Chosen for the classroom demonstration, not by any provider.
DEMO_STAY_DATES = ("2026-10-10", "2026-10-11", "2026-10-12", "2026-10-13", "2026-10-14")

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

-- Hotels saved from the live API (Assignment 2). The provider's place id is the key,
-- stored exactly as given, so the same place can never be saved twice. These are
-- separate from `hotels`, whose price column is required and which holds only the
-- supplied sample records. NOT NULL is spelled out on every key because SQLite
-- otherwise lets a TEXT primary key be NULL.
CREATE TABLE IF NOT EXISTS saved_hotels (
    hotel_id   TEXT NOT NULL PRIMARY KEY CHECK (length(hotel_id) > 0),
    name       TEXT CHECK (name IS NULL OR length(trim(name)) > 0),
    address    TEXT CHECK (address IS NULL OR length(trim(address)) > 0),
    latitude   REAL NOT NULL CHECK (typeof(latitude) IN ('real', 'integer')
                                    AND latitude BETWEEN -90 AND 90),
    longitude  REAL NOT NULL CHECK (typeof(longitude) IN ('real', 'integer')
                                    AND longitude BETWEEN -180 AND 180)
);

-- One simulated classroom row per saved hotel per night. The rate and the room count
-- are fictional defaults, not anything the hotel API supplied: the API has no prices
-- and no availability. The composite key allows at most one row per hotel per night.
-- The date must be a real calendar date written exactly YYYY-MM-DD: date() returns NULL
-- for an impossible date and a differently written one comes back changed.
CREATE TABLE IF NOT EXISTS demo_hotel_nights (
    hotel_id            TEXT NOT NULL REFERENCES saved_hotels (hotel_id),
    stay_date           TEXT NOT NULL CHECK (date(stay_date) IS NOT NULL
                                             AND date(stay_date) = stay_date),
    nightly_rate_cents  INTEGER NOT NULL DEFAULT 10000
                        CHECK (typeof(nightly_rate_cents) = 'integer' AND nightly_rate_cents >= 0),
    rooms_available     INTEGER NOT NULL DEFAULT 20
                        CHECK (typeof(rooms_available) = 'integer' AND rooms_available >= 0),
    PRIMARY KEY (hotel_id, stay_date)
);

-- Which ZIP search a hotel was saved from, kept apart from the hotel itself so one hotel
-- can belong to several searches without being saved twice. The search centre is stored
-- with it, so a later local lookup can draw the same map without calling the API again.
CREATE TABLE IF NOT EXISTS saved_hotel_zips (
    hotel_id          TEXT NOT NULL REFERENCES saved_hotels (hotel_id),
    zip_code          TEXT NOT NULL CHECK (zip_code GLOB '[0-9][0-9][0-9][0-9][0-9]'),
    center_latitude   REAL NOT NULL CHECK (typeof(center_latitude) IN ('real', 'integer')
                                           AND center_latitude BETWEEN -90 AND 90),
    center_longitude  REAL NOT NULL CHECK (typeof(center_longitude) IN ('real', 'integer')
                                           AND center_longitude BETWEEN -180 AND 180),
    locality          TEXT CHECK (locality IS NULL OR length(trim(locality)) > 0),
    country_code      TEXT NOT NULL DEFAULT 'US' CHECK (length(country_code) = 2),
    radius_m          INTEGER NOT NULL CHECK (typeof(radius_m) = 'integer' AND radius_m > 0),
    distance_m        INTEGER CHECK (distance_m IS NULL
                                     OR (typeof(distance_m) = 'integer' AND distance_m >= 0)),
    saved_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    PRIMARY KEY (hotel_id, zip_code)
);

CREATE INDEX IF NOT EXISTS idx_saved_hotel_zips_zip ON saved_hotel_zips (zip_code);

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


@dataclass(frozen=True)
class SavedHotel:
    """A hotel saved from the live API.

    Field mapping from the API response (`NearbyHotel`): `hotel_id` is `place_id`, kept
    exactly as the provider gave it, and `name`, `address`, `latitude`, and `longitude`
    keep their names. `name` and `address` are None when the provider omitted them.
    """

    hotel_id: str
    name: str | None
    address: str | None
    latitude: float
    longitude: float


@dataclass(frozen=True)
class DemoHotelNight:
    """Simulated classroom rate and room count for one saved hotel on one night.

    Not provider data. The defaults are $100.00 (10000 cents) and 20 rooms.
    """

    hotel_id: str
    stay_date: str
    nightly_rate_cents: int = 10000
    rooms_available: int = 20


@dataclass(frozen=True)
class SavedHotelZip:
    """The ZIP search a saved hotel came from, with that search's centre and radius."""

    hotel_id: str
    zip_code: str
    center_latitude: float
    center_longitude: float
    locality: str | None
    country_code: str
    radius_m: int
    distance_m: int | None
