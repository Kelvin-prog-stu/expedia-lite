# Expedia Lite

A small local travel application. You search for a hotel by name and see the
stays offered at each matching hotel. A Vue frontend sends the search to a
FastAPI backend, which reads the supplied CSV files and returns the matches.

## Layout

```
backend/    FastAPI service and the CSV reader
frontend/   Vue 3 + Vite single-page app
docs/       design note
prompts/    the prompts that shaped this project
handoffs/   session handoff notes
```

## Requirements

- Python 3.11 or newer
- Node.js `^20.19.0 || >=22.12.0`

## Data

The application reads the instructor's sample data pack. Extract the ZIP and put
the CSV files in `backend/data/`:

```
backend/data/hotels.csv
backend/data/trips.csv
backend/data/users.csv
backend/data/bookings.csv
```

Part 1 reads `hotels.csv` and `trips.csv`. The other two are seeded in Part 2.
If a file is missing, the API returns a readable message instead of a stack
trace.

## Backend setup

```bash
cd backend
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

The API runs on http://localhost:8000, with interactive docs at
http://localhost:8000/docs.

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

The app runs on http://localhost:5173. Vite proxies `/api` to port 8000, so the
backend needs to be running too. Because the proxy makes every call
same-origin, the frontend never hardcodes the backend's address.

## Endpoints

| Method | Path              | Purpose                                    |
| ------ | ----------------- | ------------------------------------------ |
| GET    | `/api/health`     | Liveness check, returns the app version    |
| GET    | `/api/hotels`     | Search hotels by name, with their stays     |

`GET /api/hotels?name=harbor` matches hotel names case-insensitively and returns
each hotel with its offered stays attached. An empty `name` returns every hotel.
`count` is 0 when nothing matched, which is what the interface uses to show its
no-results message.

## Using it

Type part of a hotel name and press Search. Matching hotels appear in a table,
one row per offered stay, with the hotel, city, state, nightly rate, stay name,
and check-in and check-out dates. If nothing matches, the page says so instead of
showing an empty table.
