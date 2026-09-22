# Current handoff

Written 2026-09-21. A handoff records what was true when it was written; the
repository is the authority. Re-check before trusting any line of this.

**Why this exists:** end of Part 2, not an interruption. The results below were
produced by running the commands, driving the browser, and recording the demo
video, not recalled.

## Where things stand

- Branch: `main`, in sync with `origin/main`.
- Last verified feature commit: `b87b9fa`, the merge of `feature/sqlite-crud`
  into `main`. The commit on top of it adds the Part 2 report, screenshots, demo
  video, and documentation only; no application code changed after the merge.
- Part 1's checkpoint commit `6f4b9f0` is still in `main`'s history.
- Nothing is left unfinished in the working tree after the Part 2 commit.

## What works

- Hotel-name search, backed by SQLite, with each offered stay shown as a row.
- Booking a stay for any of the six demo travelers, from the frontend.
- Booking history per traveler, newest first, with status labels.
- Cancel: changes status to `cancelled` and keeps the record in history.
- Delete: removes a booking after an inline second click to confirm.
- Seeding from the four CSVs on the first start only; later starts leave the
  data alone.
- New booking IDs continue after the supplied ones and are never reused.
- The redesigned interface from `docs/ui-research.md`: Expedia-style hero and
  illustrated categories, Priceline-style two-month calendar.

## What was checked

On camera, in `docs/demo/part2-demo.mp4`, against a freshly seeded database:

| Action | Expected | Observed |
| --- | --- | --- |
| Search `Sunset Palms` | No-results message | Shown |
| Search `Harbor Lantern` | Part 1 behaviour kept | 1 hotel, 2 stays |
| Book Boston Autumn Weekend as Demo Traveler 1 | New booking in history | `B007` confirmed |
| Cancel `B007` | Status changes, record kept | `B007` cancelled, still listed |
| Book again, Delete, Confirm delete | Removed | `B008` created, then gone |
| Cancel supplied `B001` | Starter record updates | `B001` cancelled |
| Browser refresh | Changes remain | Unchanged |
| Restart backend and frontend | Changes remain, no reseed | Counts 8 / 12 / 6 / 7 before and after; `B001` still cancelled |

Off camera:

| Action | Expected | Observed |
| --- | --- | --- |
| Book with trip `T999` or traveler `U999` | Rejected, nothing saved | 404 with a readable message, count unchanged |
| Cancel the deleted `B008` | Not found | 404 |
| Next ID after deleting `B008` | Not reused | Stored counter is 9 |
| Search `Inn` | The three inns | Maple Square, Liberty Lane, Valley Trail |
| Empty search | Validation | "Enter a hotel name." |
| Page width at a 451px viewport | No horizontal scroll | `scrollWidth` equals viewport |
| `npm run build` | Clean | Exit 0 |
| SQLite support in `backend/.venv` | Available | Python 3.12.5, SQLite 3.45.3, nothing installed |

The local database holds the demo's changes: `B001` and `B007` cancelled,
`B008` deleted, next booking `B009`. Delete `backend/expedia_lite.db` with the
backend stopped to start clean.

The SmokeTest in `AGENTS.md` was written after these checks and has not been run
as a whole yet; the demo covers the same behaviour with Harbor Lantern instead
of Valley Trail Inn.

## Limitations

- No authentication. Anyone can book, cancel, or delete as any demo traveler;
  the "Booking as" selector is the only notion of identity. The optional bonus
  (demo login and surge pricing) was not attempted.
- Dates and the calendar are planning aids only; they do not filter results.
- A traveler can book the same stay more than once. Nothing prevents it.
- The booking history has no loading state. After the restart in the demo it
  showed "No bookings yet" for a few seconds before the bookings arrived.
- No automated tests. Verification was manual, as the assignment asks.
- Only Stays works; the other categories link out to Expedia.

## Running it

Backend, from `backend/`:

```bash
.venv\Scripts\python.exe -m uvicorn main:app
```

Frontend, from `frontend/`:

```bash
npm run dev
```

Backend on 8000, frontend on 5173. Vite proxies `/api` to 8000, so both must
run. SQLite is part of Python's standard library, so no dependency was added.

## Next task

Give the booking history a loading state, so it shows "Loading" rather than
"No bookings yet" while the first request is in flight. Then run the SmokeTest
from `AGENTS.md` once end to end.

## Decisions not to re-litigate

- **Seeding uses a marker, not a row count.** `app_meta.seeded` means deleting
  every booking can never trigger a reseed.
- **The next booking number is stored**, not derived from existing rows, so a
  deleted ID is never handed out again.
- **Cancel keeps the row.** Only Delete removes it; the two are separate routes.
- **Delete confirms inline**, not with `window.confirm`, so it works the same in
  every browser and under automated checks.
- **The database file is not committed.** Each machine seeds its own.
- **Part 1's checkpoint commit `6f4b9f0` stays in history.** Part 2 was built on
  `feature/sqlite-crud` and merged.
