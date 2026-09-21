# Current handoff

Written 2026-09-21. A handoff records what was true when it was written; the
repository is the authority. Re-check before trusting any line of this.

**Why this exists:** end of Part 2 implementation, not an interruption. The
results below were produced by running the commands and driving the browser, not
recalled. What remains is the demo video and the Part 2 report.

## What works

- Hotel-name search, now backed by SQLite, with each offered stay shown as a row.
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

| Action | Expected | Observed |
| --- | --- | --- |
| First backend start | Seed from CSVs | 8 hotels, 12 trips, 6 users, 6 bookings |
| Book Boston Harbor Weekend as Demo Traveler 6 | New booking in history | `B007` confirmed, toast shown |
| Cancel `B007` | Status changes, record kept | `B007` cancelled, still listed, Cancel button gone |
| Book a second stay, then Delete and Confirm delete | Removed | `B008` created, then gone |
| Browser refresh | Changes remain | `B007` cancelled, `B008` absent |
| Restart backend and frontend | Changes remain, no reseed | Counts 8 / 12 / 6 / 7 before and after; `B001` to `B007` present, 0 duplicates |
| Book after the restart | Next unused ID | `B009`, not a reused `B008` |
| Unknown traveler, bad status | Rejected | 404 and 422 |
| Search `Harbor Lantern` | Part 1 behaviour kept | 1 hotel, 2 stays |
| Search `Sunset Palms` | No-results message | Shown |
| Search `Inn` | The three inns | Maple Square, Liberty Lane, Valley Trail |
| Empty search | Validation | "Enter a hotel name." |
| Calendar | Two months, range, closes | September and October 2026 side by side; results unchanged |
| Page width at a 451px viewport | No horizontal scroll | `scrollWidth` equals viewport |
| `npm run build` | Clean | exit 0, 20 modules transformed |

The local database currently holds `B007` (cancelled) and `B009` (confirmed) for
Demo Traveler 6 from these checks. Delete `backend/expedia_lite.db` for a clean
start before recording.

## Limitations

- No authentication. Anyone can book or delete as any demo traveler; the
  "Booking as" selector is the only notion of identity. The optional bonus
  (demo login and surge pricing) was not attempted.
- Dates and the calendar are planning aids only; they do not filter results.
- A traveler can book the same stay more than once. Nothing prevents it.
- No automated tests. Verification was manual and scripted against the running
  app, as the assignment asks.
- Only Stays works; the other categories link out to Expedia.

## Running it

```bash
cd backend && .venv\Scripts\python.exe -m uvicorn main:app --reload
```

```bash
cd frontend && npm run dev
```

Backend on 8000, frontend on 5173. Vite proxies `/api` to 8000, so both must
run. SQLite is part of Python's standard library, so no dependency was added.

## Next task

Record the demo video, under three minutes, showing search, booking, history,
cancel, delete, and the changes surviving a refresh. Then write the Part 2
`report.md` against the final merged commit on `main`.

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
