"""FastAPI application for Expedia Lite.

The web layer only validates input, calls data_source, and shapes the response.
Reading and joining the CSV files happens in data_source.py.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from data_source import DataFileMissingError, search_hotels
from schemas import HotelResult, SearchResponse

VERSION = "1.0.0"

app = FastAPI(title="Expedia Lite API", version=VERSION)

# The Vite dev server proxies /api, so requests are same-origin in development.
# This stays for any client that calls port 8000 directly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": VERSION}


@app.get("/api/hotels", response_model=SearchResponse)
async def get_hotels(name: str = "") -> SearchResponse:
    """Search hotels by name and return each match with its offered stays."""
    matches = search_hotels(name)
    return SearchResponse(
        query=name,
        count=len(matches),
        hotels=[HotelResult(**match) for match in matches],
    )


@app.exception_handler(DataFileMissingError)
async def handle_missing_data(request: Request, exc: DataFileMissingError) -> JSONResponse:
    """Turn a missing CSV into a readable message instead of a stack trace."""
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "data_file_missing", "message": str(exc)}},
    )
