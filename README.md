# Expedia Lite

A small local travel application. You search hotels by name, book one of the
stays offered at a hotel, and keep a booking history where each booking can be
cancelled or deleted. You can also enter a US ZIP code to see hotels within 5 km,
as a list and on a map. A Vue frontend talks to a FastAPI backend, which stores
bookings in SQLite and fetches nearby hotels from a public location service.

## Layout

```
backend/    FastAPI service, SQLite model and controller, supplied CSV data
frontend/   Vue 3 + Vite single-page app
docs/       design note, research notes, mockups, and verification screenshots
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

A ZIP code is five digits and stays a string, so `01001` keeps its leading
zeros. Anything else is refused before the provider is called, and an
unresolvable ZIP comes back as a readable "no location found" message.

### Hotels near a ZIP code

Under **Hotels by ZIP**, enter a ZIP code and press **Find location**. The backend
resolves it to a point, then asks Geoapify Places for hotels within 5 km of that
point. Results show as a numbered list beside a Leaflet map. Selecting a hotel in
either one selects it in the other, with the mouse or with Enter or Space.

What to know about the data:

- Results are places the service lists as hotels: name, address, coordinates, and
  distance. There are **no prices, ratings, or availability**, because the service
  has none.
- A page is the nearest 20. When it is full the page says there may be more, and
  it never claims to list every hotel.
- A search that finds no hotels is a successful, empty answer. A ZIP the service
  cannot place, a rate limit, a failed request, and an unreachable backend each
  have their own message and never read as "no hotels".
- Map tiles come from OpenStreetMap's standard server and need no key. The map
  shows "© OpenStreetMap contributors" and the results show "Powered by Geoapify",
  as the free plan requires. Please keep both visible.
- The free plan allows 3,000 credits a day and 5 requests a second.

To check the location code without the service, run the mocked checks from
`backend/`. They never make a live request:

```bash
.venv\Scripts\python.exe checks\check_geo.py
```

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
| GET    | `/api/nearby-hotels?zip=`| Hotels within 5 km of that point, nearest first |
| GET    | `/api/hotels?name=`      | Search hotels by name, with their stays        |
| GET    | `/api/users`             | The demo travelers                             |
| GET    | `/api/bookings?user_id=` | Booking history, optionally for one traveler   |
| POST   | `/api/bookings`          | Create a booking from `user_id` and `trip_id`  |
| PATCH  | `/api/bookings/{id}`     | Cancel a booking; the record is kept           |
| DELETE | `/api/bookings/{id}`     | Delete a booking                               |

The location routes answer 400 for a ZIP that is not five digits, 404 for one the
service cannot place, 429 when the service's request limit is reached, 502 when
the request fails, and 503 when no key is configured.

An unknown traveler, stay, or booking returns 404 with a readable message.
`PATCH` only accepts `{"status": "cancelled"}`; anything else is a 422.
