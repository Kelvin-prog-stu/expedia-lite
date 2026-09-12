"""Reads the supplied CSV files and joins hotels to their offered stays.

This module owns all file access. It knows nothing about HTTP, so it can be run
or tested on its own.
"""

import csv
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


class DataFileMissingError(Exception):
    """Raised when a required CSV is not present in the data directory."""

    def __init__(self, filename: str) -> None:
        super().__init__(
            f"{filename} was not found in {DATA_DIR}. "
            "Extract the supplied data pack into that folder."
        )
        self.filename = filename


def _read_csv(filename: str) -> list[dict[str, str]]:
    path = DATA_DIR / filename
    if not path.exists():
        raise DataFileMissingError(filename)

    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_hotels() -> list[dict[str, str]]:
    """Every hotel row, as read from hotels.csv."""
    return _read_csv("hotels.csv")


def load_trips() -> list[dict[str, str]]:
    """Every offered stay, as read from trips.csv."""
    return _read_csv("trips.csv")


def search_hotels(name_query: str) -> list[dict]:
    """Hotels whose name contains the query, each with its offered stays attached.

    An empty query returns every hotel. Matching is case-insensitive so that
    "harbor" finds "Harbor Lantern Hotel".
    """
    query = name_query.strip().lower()
    hotels = load_hotels()
    trips = load_trips()

    if query:
        hotels = [h for h in hotels if query in h["hotel_name"].lower()]

    matches = []
    for hotel in hotels:
        stays = [t for t in trips if t["hotel_id"] == hotel["hotel_id"]]
        matches.append({**hotel, "trips": stays})

    return matches
