"""Checks for saving, listing, and removing hotels, through the real HTTP routes.

Run from the backend folder with the project interpreter:

    .venv\\Scripts\\python.exe checks\\check_saved_hotels.py

Every check runs against a throwaway database chosen with EXPEDIA_DB_PATH before the
app is imported. The real database is never opened, so this is safe to run while the
app is running. No request is made to the hotel API.
"""

import gc
import os
import sqlite3
import sys
import tempfile
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_folder = tempfile.TemporaryDirectory()
DB_FILE = Path(_folder.name) / "checks.db"
os.environ["EXPEDIA_DB_PATH"] = str(DB_FILE)  # must be set before the app is imported

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from models import DEMO_STAY_DATES  # noqa: E402

ASSIGNMENT_1_TABLES = ("hotels", "trips", "users", "bookings", "app_meta")
results: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, observed: str) -> None:
    results.append((name, ok, observed))


def rows(sql: str, params: tuple = ()) -> list[tuple]:
    """Read the throwaway database directly, apart from the app."""
    conn = sqlite3.connect(DB_FILE)
    try:
        return [tuple(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def run(sql: str, params: tuple = ()) -> None:
    conn = sqlite3.connect(DB_FILE)
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


def counts() -> tuple[int, int, int]:
    return (
        rows("SELECT COUNT(*) FROM saved_hotels")[0][0],
        rows("SELECT COUNT(*) FROM saved_hotel_zips")[0][0],
        rows("SELECT COUNT(*) FROM demo_hotel_nights")[0][0],
    )


def assignment_1_snapshot() -> list:
    return [rows(f"SELECT * FROM {t} ORDER BY 1") for t in ASSIGNMENT_1_TABLES]


def payload(place_id="place-1", zip_code="16802", **changes) -> dict:
    body = {
        "place_id": place_id,
        "name": "Scholar Hotel",
        "address": "205 East Beaver Avenue",
        "latitude": 40.7946,
        "longitude": -77.859,
        "distance_m": 968,
        "search": {
            "zip_code": zip_code,
            "center_latitude": 40.8032,
            "center_longitude": -77.8614,
            "locality": "State College",
            "country_code": "US",
            "radius_m": 5000,
        },
    }
    body.update(changes)
    return body


with TestClient(main.app) as client:
    before_a1 = assignment_1_snapshot()
    record("the app starts on the throwaway database", rows("SELECT COUNT(*) FROM hotels")[0][0] == 8, str(DB_FILE.name))

    # ---- Saving ---------------------------------------------------------------------
    r = client.post("/api/saved-hotels", json=payload())
    body = r.json()
    record("saving a new hotel returns 201 and created=true", r.status_code == 201 and body["created"] is True, f"{r.status_code} created={body['created']}")
    record("the hotel, its ZIP link, and five nights are stored", counts() == (1, 1, 5), str(counts()))

    nights = rows("SELECT stay_date, nightly_rate_cents, rooms_available FROM demo_hotel_nights ORDER BY stay_date")
    record(
        "the nights are October 10 to 14, 2026, at $100.00 and 20 rooms",
        [n[0] for n in nights] == list(DEMO_STAY_DATES) and all(n[1:] == (10000, 20) for n in nights),
        f"{nights[0][0]} to {nights[-1][0]}, {nights[0][1]} cents, {nights[0][2]} rooms",
    )
    link = rows("SELECT zip_code, center_latitude, center_longitude, locality, country_code, radius_m, distance_m FROM saved_hotel_zips")[0]
    record("the ZIP link keeps the search centre, radius, and distance", link == ("16802", 40.8032, -77.8614, "State College", "US", 5000, 968), str(link))

    exact = "5126" + "AbCd" * 29 + " "  # mixed case with a trailing space, 121 characters
    client.post("/api/saved-hotels", json=payload(place_id=exact))
    record("a provider id is stored exactly, never trimmed or re-cased", rows("SELECT hotel_id FROM saved_hotels WHERE hotel_id = ?", (exact,)) == [(exact,)], f"{len(exact)} characters")
    client.delete("/api/saved-hotels", params={"place_id": exact})

    # ---- Repeating a save -----------------------------------------------------------
    before_repeat = counts()
    r = client.post("/api/saved-hotels", json=payload())
    record("saving the same hotel again returns 200 and created=false", r.status_code == 200 and r.json()["created"] is False, f"{r.status_code}")
    record("a repeat save duplicates nothing", counts() == before_repeat, str(counts()))

    run("UPDATE demo_hotel_nights SET nightly_rate_cents = 15000, rooms_available = 3 WHERE stay_date = '2026-10-12'")
    r = client.post("/api/saved-hotels", json=payload(name="A Different Name", address="Somewhere else"))
    kept = rows("SELECT nightly_rate_cents, rooms_available FROM demo_hotel_nights WHERE stay_date = '2026-10-12'")[0]
    record("a repeat save does not overwrite an edited rate or room count", kept == (15000, 3), str(kept))
    record("a repeat save does not overwrite the saved name or address", rows("SELECT name, address FROM saved_hotels")[0] == ("Scholar Hotel", "205 East Beaver Avenue"), "first values kept")
    run("DELETE FROM demo_hotel_nights WHERE stay_date = '2026-10-14'")
    client.post("/api/saved-hotels", json=payload())
    record("a repeat save restores only a night that is missing", counts()[2] == 5 and rows("SELECT nightly_rate_cents FROM demo_hotel_nights WHERE stay_date = '2026-10-12'")[0][0] == 15000, "5 nights, edited one kept")

    # ---- A second ZIP, and missing fields ------------------------------------------
    client.post("/api/saved-hotels", json=payload(zip_code="16801"))
    record("the same hotel from another ZIP adds a link, not a hotel or nights", counts() == (1, 2, 5), str(counts()))

    client.post("/api/saved-hotels", json=payload(place_id="no-details", name=None, address="   "))
    row = rows("SELECT name, address FROM saved_hotels WHERE hotel_id = 'no-details'")[0]
    record("a missing or blank name and address are stored as NULL", row == (None, None), str(row))

    # ---- Bad input stores nothing ---------------------------------------------------
    before_bad = counts()
    bad_bodies = {
        "latitude 91": payload(place_id="b1", latitude=91),
        "longitude -181": payload(place_id="b2", longitude=-181),
        "ZIP 1234": payload(place_id="b3", zip_code="1234"),
        "ZIP letters": payload(place_id="b4", zip_code="abcde"),
        "empty id": payload(place_id=""),
        "blank id": payload(place_id="   "),
        "negative distance": payload(place_id="b5", distance_m=-1),
    }
    bad_search = payload(place_id="b6")
    bad_search["search"]["radius_m"] = 0
    bad_bodies["zero radius"] = bad_search
    statuses = {name: client.post("/api/saved-hotels", json=body).status_code for name, body in bad_bodies.items()}
    record("invalid requests are refused with 422", set(statuses.values()) == {422}, str(statuses))
    record("an invalid request stores nothing at all", counts() == before_bad, str(counts()))

    # ---- Reading --------------------------------------------------------------------
    client.post("/api/saved-hotels", json=payload(place_id="near", distance_m=100))
    listed = client.get("/api/saved-hotels", params={"zip": "16802"}).json()
    ids = [h["place_id"] for h in listed["hotels"]]
    record("a ZIP lists its saved hotels, nearest first", ids[0] == "near" and "place-1" in ids and "no-details" in ids, str(ids))
    record("each saved hotel carries its simulated nights", all(len(h["nights"]) == 5 for h in listed["hotels"]), "5 each")
    record("the stored search centre and radius come back", listed["location"] == {"postcode": "16802", "country_code": "US", "latitude": 40.8032, "longitude": -77.8614, "locality": "State College"} and listed["radius_m"] == 5000, "location and radius present")
    edited = next(h for h in listed["hotels"] if h["place_id"] == "place-1")["nights"][2]
    record("an edited value in the database is what the API returns", edited["nightly_rate_cents"] == 15000 and edited["rooms_available"] == 3, str(edited))

    empty = client.get("/api/saved-hotels", params={"zip": "99999"})
    record("a ZIP with nothing saved is a successful empty answer", empty.status_code == 200 and empty.json()["hotels"] == [] and empty.json()["location"] is None, f"{empty.status_code}")
    invalid = client.get("/api/saved-hotels", params={"zip": "12"})
    record("an invalid ZIP is refused with 400", invalid.status_code == 400 and invalid.json()["error"]["code"] == "invalid_zip", f"{invalid.status_code}")

    status = client.get("/api/saved-hotels/status", params=[("place_id", "place-1"), ("place_id", "never-saved")]).json()
    record("saved status is decided by the database, by provider id", status == {"saved_ids": ["place-1"]}, str(status))
    record("a status request with no ids answers with none", client.get("/api/saved-hotels/status").json() == {"saved_ids": []}, "[]")

    # ---- Removing -------------------------------------------------------------------
    keep_hotels = rows("SELECT * FROM saved_hotels WHERE hotel_id != 'place-1' ORDER BY 1")
    keep_links = rows("SELECT hotel_id, zip_code FROM saved_hotel_zips WHERE hotel_id != 'place-1' ORDER BY 1, 2")
    keep_nights = rows("SELECT * FROM demo_hotel_nights WHERE hotel_id != 'place-1' ORDER BY 1, 2")
    r = client.delete("/api/saved-hotels", params={"place_id": "place-1"})
    gone = [
        rows("SELECT COUNT(*) FROM saved_hotels WHERE hotel_id = 'place-1'")[0][0],
        rows("SELECT COUNT(*) FROM saved_hotel_zips WHERE hotel_id = 'place-1'")[0][0],
        rows("SELECT COUNT(*) FROM demo_hotel_nights WHERE hotel_id = 'place-1'")[0][0],
    ]
    record("removing deletes the hotel, both its ZIP links, and its nights together", r.status_code == 204 and gone == [0, 0, 0], f"{r.status_code} {gone}")
    record(
        "removing leaves every other saved hotel's records untouched",
        keep_hotels == rows("SELECT * FROM saved_hotels ORDER BY 1")
        and keep_links == rows("SELECT hotel_id, zip_code FROM saved_hotel_zips ORDER BY 1, 2")
        and keep_nights == rows("SELECT * FROM demo_hotel_nights ORDER BY 1, 2"),
        "other hotels, links, and nights identical",
    )
    record("removing a hotel that is not saved is a 404", client.delete("/api/saved-hotels", params={"place_id": "place-1"}).status_code == 404, "404")
    record("after removal the database no longer reports it saved", client.get("/api/saved-hotels/status", params=[("place_id", "place-1")]).json() == {"saved_ids": []}, "[]")
    client.post("/api/saved-hotels", json=payload())
    fresh = rows("SELECT nightly_rate_cents, rooms_available FROM demo_hotel_nights WHERE hotel_id = 'place-1' AND stay_date = '2026-10-12'")[0]
    record("saving again after a removal starts from the defaults", fresh == (10000, 20), str(fresh))

    # ---- All or nothing -------------------------------------------------------------
    before = counts()
    run("CREATE TRIGGER block_delete BEFORE DELETE ON saved_hotels BEGIN SELECT RAISE(ABORT, 'simulated failure'); END")
    r = client.delete("/api/saved-hotels", params={"place_id": "place-1"})
    record("a removal that fails part way is rolled back completely", r.status_code == 500 and counts() == before, f"{r.status_code} {counts()}")
    run("DROP TRIGGER block_delete")

    run("CREATE TRIGGER block_nights BEFORE INSERT ON demo_hotel_nights BEGIN SELECT RAISE(ABORT, 'simulated failure'); END")
    before = counts()
    r = client.post("/api/saved-hotels", json=payload(place_id="half-saved"))
    record("a save that fails part way leaves no half-saved hotel", r.status_code == 500 and counts() == before and rows("SELECT COUNT(*) FROM saved_hotels WHERE hotel_id = 'half-saved'")[0][0] == 0, f"{r.status_code} {counts()}")
    run("DROP TRIGGER block_nights")

    # ---- A storage error is an error, never an empty result -------------------------
    real = main.db.get_connection

    def locked():
        raise sqlite3.OperationalError(f"database is locked: {DB_FILE}")

    main.db.get_connection = locked
    try:
        read = client.get("/api/saved-hotels", params={"zip": "16802"})
        write = client.post("/api/saved-hotels", json=payload(place_id="x"))
        delete = client.delete("/api/saved-hotels", params={"place_id": "place-1"})
        status_read = client.get("/api/saved-hotels/status", params=[("place_id", "place-1")])
    finally:
        main.db.get_connection = real
    errors = [r.json()["error"] for r in (read, write, delete, status_read)]
    record("a storage failure is a 500 with its own code, never an empty list", all(r.status_code == 500 for r in (read, write, delete, status_read)) and all(e["code"] == "local_storage_error" for e in errors), "read, write, delete, status")
    record("the error message leaks neither SQLite text nor a file path", all("locked" not in e["message"] and str(DB_FILE) not in e["message"] and "Temp" not in e["message"] for e in errors), errors[0]["message"])

    # ---- Everything else is frozen --------------------------------------------------
    record("Assignment 1 tables are identical after every save and removal", assignment_1_snapshot() == before_a1, "5 tables compared")
    booking = client.post("/api/bookings", json={"user_id": "U001", "trip_id": "T001"})
    ok = booking.status_code == 201
    bid = booking.json()["booking_id"]
    cancelled = client.patch(f"/api/bookings/{bid}", json={"status": "cancelled"}).json()["status"]
    deleted = client.delete(f"/api/bookings/{bid}").status_code
    record("booking, cancel, and delete still work", ok and cancelled == "cancelled" and deleted == 204, f"{bid} created, cancelled, deleted")
    record("hotel-name search still works", len(client.get("/api/hotels", params={"name": "Harbor"}).json()["hotels"]) == 1, "1 hotel")
    part1 = client.get("/api/nearby-hotels", params={"zip": "123"})
    record("the Part 1 hotel search route is unchanged (invalid ZIP still 400)", part1.status_code == 400 and part1.json()["error"]["code"] == "invalid_zip", f"{part1.status_code}")

gc.collect()
_folder.cleanup()

width = max(len(name) for name, _, _ in results)
for name, ok, observed in results:
    print(f"{'PASS' if ok else 'FAIL'}  {name.ljust(width)}  {observed}")

failed = [name for name, ok, _ in results if not ok]
print(f"\n{len(results) - len(failed)} of {len(results)} checks passed")
sys.exit(1 if failed else 0)
