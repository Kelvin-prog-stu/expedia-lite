"""FastAPI application for Expedia Lite.

Routes are thin: they validate input through schemas.py, call the database
controller, and shape the response. All SQL lives in database_controller.py.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import database_controller as db
from schemas import Booking, BookingCreate, BookingUpdate, HotelResult, SearchResponse, User
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
    return {"status": "ok", "version": VERSION, "records": db.record_counts()}


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


@app.exception_handler(DataFileMissingError)
async def handle_missing_data(request: Request, exc: DataFileMissingError) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "data_file_missing", "message": str(exc)}},
    )
