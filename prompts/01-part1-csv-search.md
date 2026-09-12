# 01 - Part 1: CSV search

**Purpose:** Build the Part 1 deliverable, a hotel-name search over the supplied
CSV files, with the frontend, FastAPI, and backend responsibilities kept apart.

```
Adapt the course calculator project into a small local travel application called
Expedia Lite. Use Vue for the frontend, Python for the backend, and FastAPI for
communication between them, with separate frontend/ and backend/ folders.

Provide a search input for a hotel name and a Search button. Display matching
hotels and their available stays from the supplied data in a plain table with
clear column labels. Show a clear message when no results match.

The Python backend reads hotels.csv and trips.csv and connects their records
using hotel_id. FastAPI returns the matching records to the Vue frontend.

Follow CHECK, then TAKE ACTION, then VERIFY when adding dependencies.
```

**Boundaries it set:** separate `frontend/` and `backend/` folders; the join
happens on the server; a simple readable interface is enough.

**Decisions worth reusing:** the join lives in `data_source.py`, which imports
nothing from FastAPI, so Part 2 can swap CSV reads for SQLite without touching
the interface. Search is case-insensitive substring matching, so "harbor" finds
"Harbor Lantern Hotel". An empty query returns every hotel, which makes the
table easy to eyeball during development.

**Verification worth reusing:** check both a hotel name that exists in the
supplied data and one that does not, in the browser, and record expected against
observed rather than asserting it works.
