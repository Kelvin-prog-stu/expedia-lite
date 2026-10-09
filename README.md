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

The database also holds two tables for hotels saved from the live API:
`saved_hotels`, and `demo_hotel_nights` with a simulated classroom rate and room
count per saved hotel per night. They are created on start if missing, never touch
the supplied tables, and start empty. To check them on throwaway databases, from
`backend/`: `.venv\Scripts\python.exe checks\check_schema.py`.

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
| GET    | `/api/saved-hotels?zip=` | Hotels saved for a ZIP, with simulated nights. Empty is a success |
| GET    | `/api/saved-hotels/status?place_id=` | Which provider ids are saved, from the database |
| POST   | `/api/saved-hotels`      | Save an API hotel for a ZIP: 201 when new, 200 when already saved |
| DELETE | `/api/saved-hotels?place_id=` | Remove a saved hotel, its ZIP links, and its nights together |
| POST   | `/api/chat`              | Ask a question about the saved hotels (Gemini). Read only |
| GET    | `/api/hotels?name=`      | Search hotels by name, with their stays        |
| GET    | `/api/users`             | The demo travelers                             |
| GET    | `/api/bookings?user_id=` | Booking history, optionally for one traveler   |
| POST   | `/api/bookings`          | Create a booking from `user_id` and `trip_id`  |
| PATCH  | `/api/bookings/{id}`     | Cancel a booking; the record is kept           |
| DELETE | `/api/bookings/{id}`     | Delete a booking                               |

### Ask the chatbot (Assignment 2, Part 2)

The **Ask about your saved hotels** panel answers plain questions such as "Which saved
hotel is cheapest for two nights from October 11 to October 13, 2026?". The backend does
the whole job, and the browser never sees the model key:

1. The question, the schema of three tables (`saved_hotels`, `saved_hotel_zips`,
   `demo_hotel_nights`), and the stay rules go to Gemini, which proposes one SQL query.
2. `retrieval_controller.py` checks it (one `SELECT`, only those tables, a few
   functions, no comments) and runs it on a **read-only** connection with a row cap and a
   time limit. Gemini never touches SQLite. A disallowed query is refused and not run.
3. The question, the query, and the retrieved rows go to Gemini again, which writes the
   answer from those records only. The panel shows the question, the proposed query, the
   records, and the answer, so a wrong answer can be traced.

A stay from check-in D to check-out E uses the nights from D up to, but not including, E.
A hotel is available only if every night has a record with a room free. A missing night is
not available. Rates and rooms are simulated classroom data.

Add a Gemini key to the same `.env` (get one at https://aistudio.google.com/apikey), then
restart the backend:

```
GEMINI_API_KEY=your-key-here
GEMINI_MODEL=gemini-3.5-flash-lite   # optional; this is the default
```

Without a key `/api/health` reports `key is not configured` and the panel says so. The
statuses are `answered`, `no_match`, `insufficient_data`, `rejected`, and
`query_failed`; model service problems are 502 (failed or unusable reply), 429 (rate
limit), and 503 (no key).

Checks: `backend/checks/check_chat.py` runs on fixtures with a scripted stand-in for the
model and a throwaway database (no key, no network). `backend/checks/run_live_questions.py`
asks the running backend a fixed set of questions through the real model and writes the
trace as JSON. The fixed sample is `backend/checks/fixtures/chatbot_sample.json`.

### Saving hotels locally

Beside each API result, **Add to Local** saves the hotel in SQLite, along with the
ZIP search it came from and five simulated classroom nights (October 10 to 14, 2026,
each $100.00 with 20 rooms). **Remove from Local** deletes the hotel, its ZIP links, and
its nights together, in one transaction. Saving the same hotel again adds nothing and
overwrites nothing, including a rate you have edited in the database.

A ZIP lookup is **local first**: it asks the database for hotels saved for that ZIP,
shows them as **Saved locally** if there are any, and only when the database answers
with none does it ask the live service (**API results**). A storage error is shown as an
error, never as "nothing saved". The saved view lists only what was saved, never every
hotel in the area, so **Show live API results for this ZIP** is there to add more.

The rates and rooms are simulated classroom data. The hotel API has no prices or
availability. Edit them in a SQLite viewer (`demo_hotel_nights`), refresh, and the app
shows your values.

For tests that change data, `EXPEDIA_DB_PATH` points the backend at a throwaway database,
and `BACKEND_URL` and `FRONTEND_PORT` start a second copy of the frontend against it.
`backend/checks/check_saved_hotels.py` does this for you and never touches the real
database.

The location routes answer 400 for a ZIP that is not five digits, 404 for one the
service cannot place, 429 when the service's request limit is reached, 502 when
the request fails, and 503 when no key is configured.

An unknown traveler, stay, or booking returns 404 with a readable message.
`PATCH` only accepts `{"status": "cancelled"}`; anything else is a 422.
