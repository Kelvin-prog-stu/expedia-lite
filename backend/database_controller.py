"""Controller layer: every create, read, update, and delete against SQLite.

FastAPI routes call these functions and nothing else touches the database. This
module imports nothing from FastAPI, so it can be exercised on its own.
"""

import os
import sqlite3
from datetime import date
from pathlib import Path

from models import BOOKING_CANCELLED, BOOKING_CONFIRMED, DEMO_STAY_DATES, SCHEMA
from seed import NEXT_BOOKING_KEY, seed_if_needed

# EXPEDIA_DB_PATH lets a test run against a throwaway database. Normally unset.
DB_PATH = Path(os.environ.get("EXPEDIA_DB_PATH") or Path(__file__).parent / "expedia_lite.db")


class RecordNotFoundError(Exception):
    """A requested traveler, stay, or booking does not exist."""

    def __init__(self, kind: str, record_id: str) -> None:
        super().__init__(f"No {kind} with ID {record_id}.")
        self.kind = kind
        self.record_id = record_id


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> bool:
    """Create the tables if missing and seed on the first run. True if seeded."""
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        return seed_if_needed(conn)


# ---- Read -------------------------------------------------------------------


def search_hotels(name_query: str) -> list[dict]:
    """Hotels whose name contains the query, each with its offered stays."""
    pattern = f"%{name_query.strip()}%"
    with get_connection() as conn:
        hotels = conn.execute(
            "SELECT * FROM hotels WHERE hotel_name LIKE ? COLLATE NOCASE ORDER BY hotel_id",
            (pattern,),
        ).fetchall()
        trips = conn.execute("SELECT * FROM trips ORDER BY check_in, trip_id").fetchall()

    stays_by_hotel: dict[str, list[dict]] = {}
    for trip in trips:
        stays_by_hotel.setdefault(trip["hotel_id"], []).append(dict(trip))

    return [{**dict(h), "trips": stays_by_hotel.get(h["hotel_id"], [])} for h in hotels]


def list_users() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM users ORDER BY user_id").fetchall()
    return [dict(row) for row in rows]


def list_bookings(user_id: str | None = None) -> list[dict]:
    """Bookings joined to their traveler, stay, and hotel, newest first."""
    query = """
        SELECT b.booking_id, b.user_id, u.display_name, b.trip_id, t.trip_name,
               t.check_in, t.check_out, h.hotel_id, h.hotel_name, h.city, h.state,
               h.nightly_rate_usd, b.booked_on, b.status
        FROM bookings b
        JOIN users u ON u.user_id = b.user_id
        JOIN trips t ON t.trip_id = b.trip_id
        JOIN hotels h ON h.hotel_id = t.hotel_id
    """
    params: tuple = ()
    if user_id:
        query += " WHERE b.user_id = ?"
        params = (user_id,)
    query += " ORDER BY b.booked_on DESC, b.booking_id DESC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_booking(booking_id: str) -> dict:
    for booking in list_bookings():
        if booking["booking_id"] == booking_id:
            return booking
    raise RecordNotFoundError("booking", booking_id)


# ---- Create -----------------------------------------------------------------


def _require(conn: sqlite3.Connection, table: str, column: str, value: str, kind: str) -> None:
    row = conn.execute(f"SELECT 1 FROM {table} WHERE {column} = ?", (value,)).fetchone()
    if row is None:
        raise RecordNotFoundError(kind, value)


def create_booking(user_id: str, trip_id: str) -> dict:
    """Book a stay for a traveler. Assigns the next unused booking ID."""
    with get_connection() as conn:
        _require(conn, "users", "user_id", user_id, "traveler")
        _require(conn, "trips", "trip_id", trip_id, "stay")

        number = int(
            conn.execute(
                "SELECT value FROM app_meta WHERE key = ?", (NEXT_BOOKING_KEY,)
            ).fetchone()["value"]
        )
        booking_id = f"B{number:03d}"

        conn.execute(
            "INSERT INTO bookings VALUES (?, ?, ?, ?, ?)",
            (booking_id, user_id, trip_id, date.today().isoformat(), BOOKING_CONFIRMED),
        )
        conn.execute(
            "UPDATE app_meta SET value = ? WHERE key = ?", (str(number + 1), NEXT_BOOKING_KEY)
        )

    return get_booking(booking_id)


# ---- Update -----------------------------------------------------------------


def cancel_booking(booking_id: str) -> dict:
    """Mark a booking cancelled. The record stays in history."""
    with get_connection() as conn:
        _require(conn, "bookings", "booking_id", booking_id, "booking")
        conn.execute(
            "UPDATE bookings SET status = ? WHERE booking_id = ?", (BOOKING_CANCELLED, booking_id)
        )
    return get_booking(booking_id)


# ---- Delete -----------------------------------------------------------------


def delete_booking(booking_id: str) -> None:
    """Remove a booking permanently."""
    with get_connection() as conn:
        _require(conn, "bookings", "booking_id", booking_id, "booking")
        conn.execute("DELETE FROM bookings WHERE booking_id = ?", (booking_id,))


def record_counts() -> dict[str, int]:
    """Row counts per table, used to confirm seeding never duplicates."""
    with get_connection() as conn:
        return {
            table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("hotels", "trips", "users", "bookings")
        }


# ---- Saved hotels (Assignment 2) --------------------------------------------------
#
# Hotels saved from the live API, the ZIP search each came from, and a simulated
# classroom rate and room count for each night in DEMO_STAY_DATES. The rates and rooms
# are never provider data. A save is idempotent: it adds only what is missing and never
# overwrites anything already stored, including a rate someone has edited.
#
# `ON CONFLICT DO NOTHING` skips only a real duplicate. `INSERT OR IGNORE` would also
# swallow a failed CHECK, such as a latitude out of range, and report it as saved.


def _placeholders(values: list) -> str:
    return ",".join("?" * len(values))


def _hotels_with_nights(conn: sqlite3.Connection, rows: list[sqlite3.Row]) -> list[dict]:
    """Saved-hotel rows plus each hotel's simulated nights, oldest date first."""
    ids = [row["hotel_id"] for row in rows]
    nights: dict[str, list[dict]] = {hotel_id: [] for hotel_id in ids}
    if ids:
        for night in conn.execute(
            f"""SELECT hotel_id, stay_date, nightly_rate_cents, rooms_available
                FROM demo_hotel_nights WHERE hotel_id IN ({_placeholders(ids)})
                ORDER BY stay_date""",
            ids,
        ):
            nights[night["hotel_id"]].append(
                {
                    "stay_date": night["stay_date"],
                    "nightly_rate_cents": night["nightly_rate_cents"],
                    "rooms_available": night["rooms_available"],
                }
            )

    return [
        {
            "place_id": row["hotel_id"],
            "name": row["name"],
            "address": row["address"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "distance_m": row["distance_m"],
            "nights": nights[row["hotel_id"]],
        }
        for row in rows
    ]


_SAVED_FOR_ZIP = """
    SELECT h.hotel_id, h.name, h.address, h.latitude, h.longitude,
           z.zip_code, z.center_latitude, z.center_longitude, z.locality,
           z.country_code, z.radius_m, z.distance_m
    FROM saved_hotel_zips z
    JOIN saved_hotels h ON h.hotel_id = z.hotel_id
"""


def _location_of(row: sqlite3.Row) -> dict:
    return {
        "postcode": row["zip_code"],
        "country_code": row["country_code"],
        "latitude": row["center_latitude"],
        "longitude": row["center_longitude"],
        "locality": row["locality"],
    }


def list_saved_hotels(zip_code: str) -> dict:
    """Hotels saved for a ZIP, nearest first, with the stored search centre.

    An empty `hotels` list means nothing is saved for this ZIP. It is a successful
    answer; a storage failure raises instead.
    """
    with get_connection() as conn:
        rows = conn.execute(
            _SAVED_FOR_ZIP
            + " WHERE z.zip_code = ? ORDER BY z.distance_m IS NULL, z.distance_m, h.hotel_id",
            (zip_code,),
        ).fetchall()
        hotels = _hotels_with_nights(conn, rows)

    return {
        "zip_code": zip_code,
        "location": _location_of(rows[0]) if rows else None,
        "radius_m": rows[0]["radius_m"] if rows else None,
        "hotels": hotels,
    }


def saved_hotel_ids(place_ids: list[str]) -> list[str]:
    """Which of these provider ids are saved, according to the database."""
    if not place_ids:
        return []
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT hotel_id FROM saved_hotels WHERE hotel_id IN ({_placeholders(place_ids)})",
            place_ids,
        ).fetchall()
    return [row["hotel_id"] for row in rows]


def save_hotel(hotel: dict, search: dict) -> dict:
    """Save an API hotel for a ZIP search, in one transaction. Safe to repeat.

    Adds the hotel if it is new, links it to this search if that link is new, and adds
    any missing simulated nights. Existing rows are left exactly as they are.
    """
    place_id = hotel["place_id"]
    with get_connection() as conn:
        created = (
            conn.execute("SELECT 1 FROM saved_hotels WHERE hotel_id = ?", (place_id,)).fetchone()
            is None
        )
        conn.execute(
            """INSERT INTO saved_hotels (hotel_id, name, address, latitude, longitude)
               VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING""",
            (place_id, hotel["name"], hotel["address"], hotel["latitude"], hotel["longitude"]),
        )
        conn.execute(
            """INSERT INTO saved_hotel_zips
                   (hotel_id, zip_code, center_latitude, center_longitude, locality,
                    country_code, radius_m, distance_m)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING""",
            (
                place_id,
                search["zip_code"],
                search["center_latitude"],
                search["center_longitude"],
                search["locality"],
                search["country_code"],
                search["radius_m"],
                hotel["distance_m"],
            ),
        )
        conn.executemany(
            "INSERT INTO demo_hotel_nights (hotel_id, stay_date) VALUES (?, ?) ON CONFLICT DO NOTHING",
            [(place_id, stay_date) for stay_date in DEMO_STAY_DATES],
        )
        rows = conn.execute(
            _SAVED_FOR_ZIP + " WHERE h.hotel_id = ? AND z.zip_code = ?",
            (place_id, search["zip_code"]),
        ).fetchall()
        saved = _hotels_with_nights(conn, rows)[0]

    return {"created": created, "hotel": saved}


def remove_saved_hotel(place_id: str) -> None:
    """Remove a saved hotel, its ZIP links, and its nights together, or none of them."""
    with get_connection() as conn:
        _require(conn, "saved_hotels", "hotel_id", place_id, "saved hotel")
        # Children first: the foreign keys refuse to delete a hotel that still has rows.
        conn.execute("DELETE FROM demo_hotel_nights WHERE hotel_id = ?", (place_id,))
        conn.execute("DELETE FROM saved_hotel_zips WHERE hotel_id = ?", (place_id,))
        conn.execute("DELETE FROM saved_hotels WHERE hotel_id = ?", (place_id,))
