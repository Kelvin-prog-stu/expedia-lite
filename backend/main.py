"""FastAPI application for Expedia Lite.

Routes are thin: they validate input through schemas.py, call the database
controller, and shape the response. All SQL lives in database_controller.py.
"""

import sqlite3
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import config
import database_controller as db
import geo_controller as geo
from schemas import (
    Booking,
    BookingCreate,
    BookingUpdate,
    HotelResult,
    NearbyHotelsResponse,
    SaveHotelRequest,
    SaveHotelResponse,
    SavedHotelsResponse,
    SavedStatusResponse,
    SearchResponse,
    User,
    ZipLocation,
)
from seed import DataFileMissingError

VERSION = "2.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Creates tables and seeds from the CSVs on the first start only.
    db.init_db()
    yield


app = FastAPI(title="Expedia Lite API", version=VERSION, lifespan=lifespan)

# The Vite dev server proxies /api, so requests are same-origin in development.
# This stays for any client that calls port 8000 directly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "version": VERSION,
        "records": db.record_counts(),
        "geoapify": config.geoapify_key_status(),
    }


@app.get("/api/location", response_model=ZipLocation)
async def look_up_location(zip: str = "") -> ZipLocation:
    """Resolve a five digit US ZIP code to a point through the location provider."""
    return ZipLocation(**asdict(geo.look_up_zip(zip)))


@app.get("/api/nearby-hotels", response_model=NearbyHotelsResponse)
async def find_nearby_hotels(zip: str = "") -> NearbyHotelsResponse:
    """Hotels within 5 km of the point a five digit US ZIP code resolves to."""
    return NearbyHotelsResponse(**asdict(geo.hotels_near_zip(zip)))


# Saved hotels. The live search above is unchanged; these read and write SQLite only.


@app.get("/api/saved-hotels", response_model=SavedHotelsResponse)
async def list_saved_hotels(zip: str = "") -> SavedHotelsResponse:
    """Hotels saved for a ZIP. An empty list is a successful answer, not a failure."""
    return SavedHotelsResponse(**db.list_saved_hotels(geo.validated_zip(zip)))


@app.get("/api/saved-hotels/status", response_model=SavedStatusResponse)
async def saved_status(place_id: list[str] = Query(default=[], max_length=200)) -> SavedStatusResponse:
    """Which of these provider ids are saved. Asks the database, so it survives a refresh."""
    return SavedStatusResponse(saved_ids=db.saved_hotel_ids(place_id))


@app.post("/api/saved-hotels", response_model=SaveHotelResponse)
async def save_hotel(payload: SaveHotelRequest, response: Response) -> SaveHotelResponse:
    """Save an API hotel for a ZIP search. 201 when new, 200 when it was already saved."""
    saved = db.save_hotel(
        payload.model_dump(exclude={"search"}), payload.search.model_dump()
    )
    response.status_code = 201 if saved["created"] else 200
    return SaveHotelResponse(**saved)


@app.delete("/api/saved-hotels", status_code=204)
async def remove_saved_hotel(place_id: str = Query(min_length=1)) -> Response:
    """Remove a saved hotel with its ZIP links and nights, or change nothing."""
    db.remove_saved_hotel(place_id)
    return Response(status_code=204)


@app.get("/api/hotels", response_model=SearchResponse)
async def search_hotels(name: str = "") -> SearchResponse:
    """Search hotels by name and return each match with its offered stays."""
    matches = db.search_hotels(name)
    return SearchResponse(
        query=name, count=len(matches), hotels=[HotelResult(**m) for m in matches]
    )


@app.get("/api/users", response_model=list[User])
async def list_users() -> list[User]:
    return [User(**u) for u in db.list_users()]


@app.get("/api/bookings", response_model=list[Booking])
async def list_bookings(user_id: str | None = None) -> list[Booking]:
    """Read: booking history, optionally for one traveler."""
    return [Booking(**b) for b in db.list_bookings(user_id)]


@app.post("/api/bookings", response_model=Booking, status_code=201)
async def create_booking(payload: BookingCreate) -> Booking:
    """Create: book a stay for a traveler."""
    return Booking(**db.create_booking(payload.user_id, payload.trip_id))


@app.patch("/api/bookings/{booking_id}", response_model=Booking)
async def cancel_booking(booking_id: str, payload: BookingUpdate) -> Booking:
    """Update: cancel a booking while keeping the record."""
    return Booking(**db.cancel_booking(booking_id))


@app.delete("/api/bookings/{booking_id}", status_code=204)
async def delete_booking(booking_id: str) -> Response:
    """Delete: remove a booking permanently."""
    db.delete_booking(booking_id)
    return Response(status_code=204)


@app.exception_handler(db.RecordNotFoundError)
async def handle_not_found(request: Request, exc: db.RecordNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404, content={"error": {"code": "not_found", "message": str(exc)}}
    )


@app.exception_handler(sqlite3.Error)
async def handle_storage_error(request: Request, exc: sqlite3.Error) -> JSONResponse:
    # A storage failure is an error, never an empty result. The SQLite message can name
    # tables and files, so only a fixed sentence goes back to the browser.
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "local_storage_error",
                "message": "The local database could not be read or written. Nothing was changed.",
            }
        },
    )


@app.exception_handler(DataFileMissingError)
async def handle_missing_data(request: Request, exc: DataFileMissingError) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "data_file_missing", "message": str(exc)}},
    )


@app.exception_handler(geo.InvalidZipError)
async def handle_invalid_zip(request: Request, exc: geo.InvalidZipError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"error": {"code": "invalid_zip", "message": str(exc)}},
    )


@app.exception_handler(geo.KeyNotConfiguredError)
async def handle_key_missing(request: Request, exc: geo.KeyNotConfiguredError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"error": {"code": "geoapify_not_configured", "message": str(exc)}},
    )


@app.exception_handler(geo.LocationNotFoundError)
async def handle_location_missing(
    request: Request, exc: geo.LocationNotFoundError
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error": {"code": "location_not_found", "message": str(exc)}},
    )


@app.exception_handler(geo.RateLimitedError)
async def handle_rate_limited(request: Request, exc: geo.RateLimitedError) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"error": {"code": "rate_limited", "message": str(exc)}},
    )


@app.exception_handler(geo.LocationServiceError)
async def handle_location_service(request: Request, exc: geo.LocationServiceError) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={"error": {"code": "location_service_failed", "message": str(exc)}},
    )
