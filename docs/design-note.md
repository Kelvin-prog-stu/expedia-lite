# Design note

Who does what in Expedia Lite, and why the pieces are split this way.

## Responsibilities

**Frontend (`frontend/src/`)** owns what the person sees and types. `App.vue`
holds the search box, the Search button, the results table, and the no-results
message. It keeps the query and the last response in component state. It does no
filtering of its own: whatever the backend returns is what the table shows. All
network access goes through `src/api.js`, so no component contains a `fetch`
call or a URL.

**FastAPI (`backend/main.py`)** is the boundary between the two. It exposes
`GET /api/hotels`, reads the `name` query parameter, calls the data layer, and
validates the response through the Pydantic models in `schemas.py` before it
goes out. It contains no file access and no search logic. A missing CSV is
turned into a structured 500 by one application-level handler rather than a
`try`/`except` in the route.

**Backend data layer (`backend/data_source.py`)** owns the CSV files. It reads
`hotels.csv` and `trips.csv`, filters hotels by name, and attaches each hotel's
offered stays by matching `trips.hotel_id` to `hotels.hotel_id`. It imports
nothing from FastAPI, so the search can be exercised without a running server.

## Request flow

```
[Person types a hotel name and presses Search]
          |
          v
[frontend/src/App.vue]                       Vue interface
          |
          | searchHotels('harbor')
          v
[frontend/src/api.js]                        request boundary
          |
          | GET /api/hotels?name=harbor
          v
[Vite dev server :5173]
          |
          | proxy
          v
[backend/main.py]                            FastAPI route
          |
          | search_hotels('harbor')
          v
[backend/data_source.py]                     reads hotels.csv + trips.csv,
          |                                  joins on hotel_id
          | returns matched hotels with stays
          v
[JSON: {"query": "harbor", "count": 1, "hotels": [...]}]
          |
          v
[App.vue renders one table row per offered stay]
```

## Why the proxy rather than CORS

Vite forwards `/api` to port 8000 in development, so the frontend holds no
backend hostname anywhere. Moving the backend means editing one line of
`vite.config.js`, not application code. It also keeps development requests
same-origin, which matches how a deployed reverse proxy behaves. `main.py` still
installs CORS middleware for any client that calls port 8000 directly; under the
proxy it never fires.

## Why the join happens on the server

The frontend could fetch both CSVs and match them itself, but then the joining
rule would live in the interface and would have to be repeated by anything else
that reads this data. Keeping it in `data_source.py` means Part 2 can swap CSV
reads for SQLite queries without the frontend changing at all.

## What Part 2 changes

Part 2 seeds a SQLite database from the same four CSV files and moves all reads
and writes there, adding booking creation, history, cancellation, and deletion.
The split above is what makes that contained: `data_source.py` is replaced by a
database layer, `main.py` gains routes, and the search interface keeps working
against the same response shape.
