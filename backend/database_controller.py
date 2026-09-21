"""Controller layer: every create, read, update, and delete against SQLite.

FastAPI routes call these functions and nothing else touches the database. This
module imports nothing from FastAPI, so it can be exercised on its own.
"""

import sqlite3
from datetime import date
from pathlib import Path

from models import BOOKING_CANCELLED, BOOKING_CONFIRMED, SCHEMA
from seed import NEXT_BOOKING_KEY, seed_if_needed

DB_PATH = Path(__file__).parent / "expedia_lite.db"


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
