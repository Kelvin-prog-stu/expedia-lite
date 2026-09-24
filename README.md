# Expedia Lite

A small local travel application. You search hotels by name, book one of the
stays offered at a hotel, and keep a booking history where each booking can be
cancelled or deleted. A Vue frontend talks to a FastAPI backend, which stores
everything in SQLite.

## Layout

```
backend/    FastAPI service, SQLite model and controller, supplied CSV data
frontend/   Vue 3 + Vite single-page app
docs/       design note, UI research, and verification screenshots
prompts/    the prompts that shaped this project
handoffs/   session handoff notes
```

`docs/design-note.md` explains the Model-View-Controller split and has a
request-flow diagram if you want the shape of the thing before reading code.

## Requirements

- Python 3.11 or newer
- Node.js `^20.19.0 || >=22.12.0`

## Data

The instructor's sample data pack lives in `backend/data/`:

```
backend/data/hotels.csv
backend/data/trips.csv
backend/data/users.csv
backend/data/bookings.csv
```

On the first start the backend creates `backend/expedia_lite.db` and seeds it
from those four files, keeping their IDs. Every later start leaves the database
alone, so your bookings survive restarts and the starter records are never
duplicated. After seeding, the app reads and writes SQLite only.

To reset to the supplied data, stop the backend and delete
`backend/expedia_lite.db`. The next start seeds it again. The database file is
not committed.

## Location service key

The ZIP lookup asks Geoapify to resolve a ZIP code, and the request is made by
the backend so the key never reaches the browser. The key lives in `.env` in the
project root, beside `backend/` and `frontend/`:

```
GEOAPIFY_API_KEY=your-key-here
```

Get a key from https://myprojects.geoapify.com/. `.env` is ignored by Git and is
never committed. `backend/config.py` reads it once at import, so **restart the
backend after editing `.env`**.

Without a key the app still runs: `GET /api/health` reports
`key is not configured`, and the ZIP panel shows that message instead of a
location.

A ZIP code is five digits and stays a string, so `00501` keeps its leading
zeros. Anything else is refused before the provider is called, and an
unresolvable ZIP comes back as a readable "no location found" message.

## Backend setup

```bash
cd backend
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

The API runs on http://localhost:8000, with interactive docs at
http://localhost:8000/docs. SQLite comes with Python, so there is nothing extra
to install.

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

The app runs on http://localhost:5173. Vite proxies `/api` to port 8000, so the
backend needs to be running too.

## Using it

1. Pick who you are booking as from **Booking as**. The six demo travelers come
   from `users.csv`.
2. Type part of a hotel name and press **Search**. Each offered stay appears as a
   row with its dates and nightly rate.
3. Press **Book** on a stay. The booking appears in **Booking history** with the
   next free ID, starting at `B007`.
4. **Cancel** marks a booking cancelled and keeps it in history.
   **Delete** removes it, after a second click to confirm.

The date picker shows two months side by side. Dates are for planning only: every
stay has fixed dates, so they do not filter the results. Flights, Cars, and the
other categories open Expedia in a new tab.

## Endpoints

| Method | Path                     | Purpose                                        |
| ------ | ------------------------ | ---------------------------------------------- |
| GET    | `/api/health`            | Liveness check, record counts, and key status  |
| GET    | `/api/location?zip=`     | Resolve a five digit US ZIP code to a point    |
| GET    | `/api/hotels?name=`      | Search hotels by name, with their stays        |
| GET    | `/api/users`             | The demo travelers                             |
| GET    | `/api/bookings?user_id=` | Booking history, optionally for one traveler   |
| POST   | `/api/bookings`          | Create a booking from `user_id` and `trip_id`  |
| PATCH  | `/api/bookings/{id}`     | Cancel a booking; the record is kept           |
| DELETE | `/api/bookings/{id}`     | Delete a booking                               |

An unknown traveler, stay, or booking returns 404 with a readable message.
`PATCH` only accepts `{"status": "cancelled"}`; anything else is a 422.
