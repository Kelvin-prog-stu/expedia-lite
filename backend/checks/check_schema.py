"""Checks for the saved_hotels and demo_hotel_nights tables.

Run from the backend folder with the project interpreter:

    .venv\\Scripts\\python.exe checks\\check_schema.py

Everything runs on throwaway databases in a temporary folder. The real database is
never opened, so this is safe to run while the app is running.
"""

import gc
import sqlite3
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import database_controller as db  # noqa: E402
from models import SCHEMA  # noqa: E402

ASSIGNMENT_1_TABLES = ("hotels", "trips", "users", "bookings", "app_meta")
NEW_TABLES = ("saved_hotels", "demo_hotel_nights", "saved_hotel_zips")

results: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, observed: str) -> None:
    results.append((name, ok, observed))


@contextmanager
def session():
    """A connection that commits and then really closes. `with sqlite3.connect()` alone
    leaves the file open, and Windows cannot delete an open file."""
    conn = db.get_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def point_at(path: Path) -> None:
    """Make the controller use a throwaway database."""
    db.DB_PATH = path


def snapshot(conn: sqlite3.Connection) -> dict:
    """Every Assignment 1 row, and the SQL that defines each Assignment 1 table."""
    rows = {t: conn.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall() for t in ASSIGNMENT_1_TABLES}
    sql = {
        name: stmt
        for name, stmt in conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type = 'table' AND name IN (%s)"
            % ",".join("?" * len(ASSIGNMENT_1_TABLES)),
            ASSIGNMENT_1_TABLES,
        )
    }
    return {"rows": [(t, [tuple(r) for r in rs]) for t, rs in rows.items()], "sql": sql}


def tables_of(conn: sqlite3.Connection) -> set[str]:
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def refused(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> bool:
    """True when the database rejects the statement."""
    try:
        conn.execute(sql, params)
    except sqlite3.IntegrityError:
        return True
    return False


with tempfile.TemporaryDirectory() as folder:
    folder = Path(folder)

    # ---- An existing database: the state before this change -------------------------
    existing = folder / "existing.db"
    point_at(existing)
    db.init_db()
    with session() as conn:
        for table in NEW_TABLES:
            conn.execute(f"DROP TABLE {table}")  # recreate the pre-migration state
        before = snapshot(conn)
        before_tables = tables_of(conn)
    record(
        "the existing-database fixture has only the Assignment 1 tables",
        before_tables == set(ASSIGNMENT_1_TABLES),
        str(sorted(before_tables)),
    )

    db.init_db()  # the migration
    with session() as conn:
        after = snapshot(conn)
        after_tables = tables_of(conn)
        seeded = conn.execute("SELECT value FROM app_meta WHERE key = 'seeded'").fetchone()[0]
        new_rows = [conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in NEW_TABLES]
    record(
        "migrating an existing database adds both tables",
        after_tables == set(ASSIGNMENT_1_TABLES) | set(NEW_TABLES),
        str(sorted(after_tables - set(ASSIGNMENT_1_TABLES))),
    )
    record(
        "every Assignment 1 row is unchanged by the migration",
        before["rows"] == after["rows"],
        ", ".join(f"{t}={len(r)}" for t, r in after["rows"]),
    )
    record(
        "every Assignment 1 table definition is unchanged",
        before["sql"] == after["sql"],
        f"{len(after['sql'])} definitions compared",
    )
    record("the seeded marker survives, so nothing is reloaded", seeded == "1", f"seeded={seeded}")
    record("the new tables start empty: no data is invented", new_rows == [0] * len(NEW_TABLES), str(new_rows))

    # ---- Repeatable -----------------------------------------------------------------
    for _ in range(3):
        db.init_db()
    with session() as conn:
        again = snapshot(conn)
        counts = [conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in NEW_TABLES]
        table_sql = [
            conn.execute("SELECT sql FROM sqlite_master WHERE name = ?", (t,)).fetchone()[0]
            for t in NEW_TABLES
        ]
    record(
        "running the migration three more times changes nothing",
        again == after and counts == [0] * len(NEW_TABLES),
        "Assignment 1 data identical, new tables still empty",
    )

    # ---- A fresh database -----------------------------------------------------------
    fresh = folder / "fresh.db"
    point_at(fresh)
    seeded_now = db.init_db()
    with session() as conn:
        fresh_tables = tables_of(conn)
        fresh_counts = db.record_counts()
        fresh_sql = [
            conn.execute("SELECT sql FROM sqlite_master WHERE name = ?", (t,)).fetchone()[0]
            for t in NEW_TABLES
        ]
    record(
        "a fresh database gets every table and seeds once",
        seeded_now is True and fresh_tables == set(ASSIGNMENT_1_TABLES) | set(NEW_TABLES),
        f"seeded={seeded_now} {fresh_counts}",
    )
    record(
        "a fresh database and a migrated one define the new tables identically",
        fresh_sql == table_sql,
        "same CREATE TABLE text",
    )

    # ---- saved_hotels ---------------------------------------------------------------
    with session() as conn:
        insert = "INSERT INTO saved_hotels (hotel_id, name, address, latitude, longitude) VALUES (?, ?, ?, ?, ?)"
        PLACE = "51268f029ffa7653c05961f0" + "ab" * 49  # a 122 character provider-style id

        conn.execute(insert, (PLACE, "Scholar Hotel", "205 East Beaver Avenue", 40.79, -77.86))
        conn.execute(insert, ("OnlyRequired", None, None, 0, 0))
        stored = conn.execute("SELECT hotel_id FROM saved_hotels WHERE hotel_id = ?", (PLACE,)).fetchone()[0]
        record("a full hotel saves and its provider id is kept exactly", stored == PLACE and len(stored) == 122, f"{len(stored)} characters")

        row = conn.execute("SELECT name, address FROM saved_hotels WHERE hotel_id = 'OnlyRequired'").fetchone()
        record("name and address may be missing (stored as NULL)", tuple(row) == (None, None), str(tuple(row)))

        conn.execute(insert, ("abc", "lower", None, 1, 1))
        conn.execute(insert, ("ABC", "upper", None, 1, 1))
        conn.execute(insert, (" abc ", "padded", None, 1, 1))
        distinct = conn.execute("SELECT COUNT(*) FROM saved_hotels WHERE lower(trim(hotel_id)) = 'abc'").fetchone()[0]
        record("ids differing only in case or spaces stay distinct, none rewritten", distinct == 3, f"{distinct} rows")

        record("saving the same provider id again is refused", refused(conn, insert, (PLACE, "Again", None, 1, 1)), "IntegrityError")
        record("a NULL id is refused", refused(conn, insert, (None, "x", None, 1, 1)), "IntegrityError")
        record("an empty id is refused", refused(conn, insert, ("", "x", None, 1, 1)), "IntegrityError")
        record("a blank name is refused (a missing name is NULL)", refused(conn, insert, ("n1", "   ", None, 1, 1)) and refused(conn, insert, ("n2", "", None, 1, 1)), "IntegrityError")
        record("a blank address is refused", refused(conn, insert, ("a1", None, "  ", 1, 1)), "IntegrityError")

        bad_latitudes = (None, 90.0001, -90.0001, 91, "north")
        record("a missing or out of range latitude is refused", all(refused(conn, insert, (f"lat{i}", None, None, v, 0)) for i, v in enumerate(bad_latitudes)), str(bad_latitudes))
        bad_longitudes = (None, 180.0001, -180.0001, 181, "west")
        record("a missing or out of range longitude is refused", all(refused(conn, insert, (f"lon{i}", None, None, 0, v)) for i, v in enumerate(bad_longitudes)), str(bad_longitudes))
        for i, (lat, lon) in enumerate(((90, 180), (-90, -180))):
            conn.execute(insert, (f"edge{i}", None, None, lat, lon))
        record("the exact limits are accepted", True, "90, 180 and -90, -180")

        # ---- demo_hotel_nights ------------------------------------------------------
        night = "INSERT INTO demo_hotel_nights (hotel_id, stay_date, nightly_rate_cents, rooms_available) VALUES (?, ?, ?, ?)"
        conn.execute("INSERT INTO demo_hotel_nights (hotel_id, stay_date) VALUES (?, ?)", (PLACE, "2026-10-09"))
        defaults = tuple(conn.execute("SELECT nightly_rate_cents, rooms_available FROM demo_hotel_nights").fetchone())
        record("the defaults are $100.00 (10000 cents) and 20 rooms", defaults == (10000, 20), str(defaults))

        conn.execute(night, (PLACE, "2026-10-10", 12950, 7))
        conn.execute(night, ("OnlyRequired", "2026-10-09", 0, 0))
        record("the same night for another hotel, and another night for the same hotel, are fine; zero is allowed", True, "3 more rows")

        record("a second row for the same hotel and night is refused", refused(conn, night, (PLACE, "2026-10-09", 5000, 5)), "IntegrityError")
        record("a night for a hotel that is not saved is refused (foreign key)", refused(conn, night, ("nobody", "2026-10-09", 1, 1)), "IntegrityError")
        record("a saved hotel with nights cannot be deleted from under them", refused(conn, "DELETE FROM saved_hotels WHERE hotel_id = ?", (PLACE,)), "IntegrityError")

        bad_dates = ("2026-02-30", "2026-13-01", "2027-02-29", "2026-1-5", "20261005", "2026-10-05 12:00", "10/05/2026", "tomorrow", "", None)
        record("a date that is not a real YYYY-MM-DD calendar date is refused", all(refused(conn, night, (PLACE, d, 1, 1)) for d in bad_dates), f"{len(bad_dates)} bad values")
        conn.execute(night, (PLACE, "2028-02-29", 1, 1))
        record("a real leap day is accepted", True, "2028-02-29")

        record("a negative rate or room count is refused", refused(conn, night, (PLACE, "2026-11-01", -1, 1)) and refused(conn, night, (PLACE, "2026-11-02", 1, -1)), "IntegrityError")
        record("a fractional or text rate or room count is refused", all(refused(conn, night, (PLACE, f"2026-12-0{i}", r, c)) for i, (r, c) in enumerate(((100.5, 1), (1, 2.5), ("abc", 1), (1, "many")), start=1)), "100.5, 2.5, abc, many")

        pragma = conn.execute("PRAGMA foreign_key_list(demo_hotel_nights)").fetchone()
        record("the foreign key is declared against saved_hotels.hotel_id", (pragma[2], pragma[3], pragma[4]) == ("saved_hotels", "hotel_id", "hotel_id"), str((pragma[2], pragma[3], pragma[4])))
        pk = [r[1] for r in sorted(conn.execute("PRAGMA table_info(demo_hotel_nights)"), key=lambda r: r[5]) if r[5]]
        record("the primary key is (hotel_id, stay_date)", pk == ["hotel_id", "stay_date"], str(pk))

    # ---- Assignment 1 behaviour is frozen -------------------------------------------
    point_at(existing)
    booking = db.create_booking("U001", "T001")
    db.cancel_booking(booking["booking_id"])
    cancelled = db.get_booking(booking["booking_id"])["status"]
    db.delete_booking(booking["booking_id"])
    found = db.search_hotels("Harbor")
    record(
        "booking, cancel, delete, and search still work on the migrated database",
        booking["booking_id"] == "B007" and cancelled == "cancelled" and len(found) == 1,
        f"{booking['booking_id']} cancelled then deleted; 'Harbor' finds {len(found)} hotel",
    )

    # The controller's connections are released when Python collects them, not the moment
    # a function returns. Windows cannot delete a database file until then.
    gc.collect()

width = max(len(name) for name, _, _ in results)
for name, ok, observed in results:
    print(f"{'PASS' if ok else 'FAIL'}  {name.ljust(width)}  {observed}")

failed = [name for name, ok, _ in results if not ok]
print(f"\n{len(results) - len(failed)} of {len(results)} checks passed")
sys.exit(1 if failed else 0)
