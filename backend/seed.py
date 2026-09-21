"""Loads the supplied CSV files into SQLite exactly once.

Seeding is recorded in app_meta. Every later start sees the marker and leaves
the database alone, so saved bookings survive restarts and the starter records
are never duplicated or reloaded.
"""

import csv
import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
SEEDED_KEY = "seeded"
NEXT_BOOKING_KEY = "next_booking_number"


class DataFileMissingError(Exception):
    """Raised when a CSV needed for the first seed is not present."""

    def __init__(self, filename: str) -> None:
        super().__init__(
            f"{filename} was not found in {DATA_DIR}. "
            "Extract the supplied data pack into that folder."
        )


def _read_csv(filename: str) -> list[dict[str, str]]:
    path = DATA_DIR / filename
    if not path.exists():
        raise DataFileMissingError(filename)

    # The supplied files begin with a byte order mark; utf-8-sig strips it so
    # the first column is "hotel_id" rather than "﻿hotel_id".
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def is_seeded(conn: sqlite3.Connection) -> bool:
    row = conn.execute("SELECT value FROM app_meta WHERE key = ?", (SEEDED_KEY,)).fetchone()
    return row is not None


def _booking_number(booking_id: str) -> int:
    return int(booking_id.lstrip("B"))


def seed_if_needed(conn: sqlite3.Connection) -> bool:
    """Seed from the CSVs on the first run only. Returns True if it seeded."""
    if is_seeded(conn):
        return False

    hotels = _read_csv("hotels.csv")
    trips = _read_csv("trips.csv")
    users = _read_csv("users.csv")
    bookings = _read_csv("bookings.csv")

    with conn:
        conn.executemany(
            "INSERT INTO hotels VALUES (:hotel_id, :hotel_name, :city, :state, :nightly_rate_usd)",
            hotels,
        )
        conn.executemany(
            "INSERT INTO trips VALUES (:trip_id, :hotel_id, :trip_name, :check_in, :check_out)",
            trips,
        )
        conn.executemany("INSERT INTO users VALUES (:user_id, :display_name)", users)
        conn.executemany(
            "INSERT INTO bookings VALUES (:booking_id, :user_id, :trip_id, :booked_on, :status)",
            bookings,
        )

        # New bookings continue after the highest supplied ID and never reuse
        # one, even after a booking is deleted.
        highest = max((_booking_number(b["booking_id"]) for b in bookings), default=0)
        conn.execute(
            "INSERT INTO app_meta VALUES (?, ?)", (NEXT_BOOKING_KEY, str(highest + 1))
        )
        conn.execute("INSERT INTO app_meta VALUES (?, ?)", (SEEDED_KEY, "1"))

    return True
