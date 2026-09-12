# Current handoff

Written 2026-09-12. A handoff records what was true when it was written; the
repository is the authority. Re-check before trusting any line of this.

**Why this exists:** end of Part 1, not an interruption. Nothing was in flight.
The results below were produced by running the commands and driving the browser,
not recalled.

## What works

Part 1 is complete: hotel-name search over the supplied CSV files.

- The Vue interface has a labelled hotel-name input and a Search button.
- Matching hotels render in a table with one row per offered stay, headed Hotel,
  City, State, Nightly rate (USD), Stay, Check in, Check out.
- A search with no matches shows a message and renders no table.
- `GET /api/hotels?name=` searches case-insensitively; an empty name returns all
  eight hotels.
- A missing CSV returns a readable structured error rather than a stack trace.

## What was checked

| Action | Expected | Observed |
| --- | --- | --- |
| Search "Harbor Lantern" | Harbor Lantern Hotel with its stays | 1 hotel matched, 2 rows: Boston Harbor Weekend (2026-09-18 to 2026-09-20) and Boston Autumn Weekend (2026-10-02 to 2026-10-04) |
| Search "Sunset Palms" | No-results message, no table | `No hotels match "Sunset Palms". Try another hotel name.`; no table element rendered |
| `GET /api/hotels?name=harbor` | One hotel with two trips | `count: 1`, Harbor Lantern Hotel, Boston MA, 150 |
| `GET /api/hotels?name=zzz` | Empty result, not an error | `{"query":"zzz","count":0,"hotels":[]}` |
| `GET /api/health` | 200 with version | `{"status":"ok","version":"1.0.0"}` |
| Missing CSV | Readable message | `data_file_missing` with the expected path, HTTP 500 |
| `npm run build` | Clean production build | exit 0, 13 modules transformed |

Dependency checkpoint: `fastapi[standard]==0.141.1` into `backend/.venv`
(`fastapi 0.141.1`, `uvicorn 0.52.4`, `pydantic 2.13.5`, `starlette 1.6.0`), and
`vue 3.5.42`, `vite 7.3.6`, `@vitejs/plugin-vue 6.0.8` into
`frontend/node_modules`. Both project-local; no system change.

## Limitations

- Search matches hotel names only. Searching a city or a stay name returns
  nothing, which is what Part 1 asks for but is worth knowing.
- Nothing is stored. Every request re-reads the CSV files, and there is no
  booking or history yet. That is Part 2.
- `nightly_rate_usd` is carried as the string read from the CSV and displayed
  as-is. No currency formatting or arithmetic depends on it yet.
- No automated tests. The assignment asks for manual verification in the browser
  and that is what was done.
- The instructor's `README.md`, `relationships.png` and `relationships.svg` also
  sit in `backend/data/` alongside the CSVs. They are reference material, not
  data the application reads.

## Running it

```bash
cd backend && .venv\Scripts\python.exe -m uvicorn main:app --reload
```

```bash
cd frontend && npm run dev
```

Backend on 8000, frontend on 5173. Vite proxies `/api` to 8000, so both must
run. The backend re-reads the CSVs per request, so changing a CSV needs no
restart.

## Next task

Part 2, due Tuesday 2026-09-15: seed a SQLite database from all four CSV files,
then move every read and write to it. Add booking creation, booking history,
cancellation that keeps the record, and deletion, all driven from the frontend
through FastAPI. Develop on a feature branch and merge into `main`, preserving
the Part 1 checkpoint commit.

The split in `docs/design-note.md` is what keeps that contained: `data_source.py`
is replaced by a database layer, `main.py` gains routes, and the search interface
keeps working against the same response shape.

## Decisions not to re-litigate

- **The join happens on the server.** `data_source.py` matches `trips.hotel_id`
  to `hotels.hotel_id`. Putting it in the interface would mean repeating the rule
  anywhere else that reads this data, and would not survive the move to SQLite.
- **Vite proxy, not CORS.** The frontend holds no backend hostname. `main.py`
  still installs CORS for direct callers; under the proxy it never fires.
- **CSVs are read with `utf-8-sig`.** The supplied files begin with a byte order
  mark; without that encoding the first column name reads as `﻿hotel_id`
  and every lookup fails.
- **The frontend does no filtering.** Whatever the backend returns is what the
  table shows, so the search rule has one home.
- **`main` is the default branch**, because Part 2 requires merging a feature
  branch into `main`.
