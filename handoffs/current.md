# Current handoff

Written 2026-09-29. A handoff records what was true when it was written; the
repository is the authority. Re-check before trusting any line of this.

**Why this exists:** end of Assignment 2, Part 1 (live hotel search and map), not
an interruption. Every result below came from running the code or driving the app
in a browser. What remains is the demo video, the Part 1 report, and merging.

## Where things stand

- Branch: `feature/public-api`, pushed. `main` still holds Assignment 1, Part 2
  (`ae0d7c3`, with the report commit `1cb6de4` and disclosure commit `ae06818`
  on top).
- Last verified feature commit: `8ffb25a`. Nothing is unfinished in the working
  tree.
- Nothing has been merged into `main` yet. Merge after the demo video and report
  are added and reviewed.

## What works

- Enter a five digit US ZIP code, including leading zeros. FastAPI resolves it with
  Geoapify geocoding, then asks Geoapify Places for hotels within 5 km of the
  point it returned.
- A numbered list beside a Leaflet map, with the search centre and radius drawn.
  Selecting a hotel in either one selects it in the other, by mouse, Enter, or Space.
- Loading, results, invalid ZIP, unresolved ZIP, no hotels nearby, rate limited,
  failed request, and unreachable backend each have their own message.
- The Geoapify key stays in `.env`, read by `backend/config.py`. It never reaches
  the browser, a response, or an error message. The map's tiles need no key.
- The earlier features are unchanged: hotel-name search, booking, history, cancel,
  delete, and the persistent SQLite data.

## What was checked

| Action | Expected | Observed |
| --- | --- | --- |
| `backend/checks/check_geo.py` | Mocked provider answers, no live request | 24 of 24 pass |
| ZIP `16802` | Hotels near State College, list and pins agree | 20 cards, 20 pins, one centre marker, all 12 tiles loaded |
| Select a hotel in the list, then on the map | Exactly one highlighted in both | One each time, in both directions |
| Enter and Space on a focused pin | Selects it | Both work, after fixing Enter |
| `123` and empty | Message, no request | Message shown, 0 requests |
| `00000` | Unresolved, not a search elsewhere | "ZIP code not found" |
| `99999` | A successful search with no hotels | "No hotels found", map and centre still shown |
| `01001` | Leading zero survives | Agawam, hotels listed |
| Stubbed 429 and 502 | Own message, not an empty list | "Too many requests", "Could not load hotels" |
| Backend stopped | Not an empty list | "Backend not reachable" |
| A hotel named with an `<img onerror>` tag | Plain text | Literal text in the list, tooltip, and pin label |
| Marker geometry | Diamond at the circle's centre | 0.3 px off |
| Selecting the 15th hotel at 1280 px and 600 px | List scrolls, page and map do not | List moved 1702 and 1432 px; page and map moved 0 |
| Hotel-name search, booking history, an unknown stay | Unchanged | Unchanged (2 stays for Harbor Lantern, history B007 B002 B001, 404) |
| `npm run build` | Clean | Exit 0 |

The tested live ZIPs were `16802`, `01001`, `10001`, `99999`, and `00000`, on
2026-09-29. Never assert a hotel count from the live service.

## Limitations

- A page is the nearest 20. When it is full the page says there may be more; it does
  not page through the rest.
- The service has no prices, ratings, or availability, so none are shown. Names and
  addresses come from OpenStreetMap and can be wrong or missing.
- `99999` resolves to a county in Ohio and `00501` (a real ZIP) returns nothing, so
  "five digits" is not the same as "a ZIP the service knows".
- Tiles come from OpenStreetMap's standard server, which is best-effort and meant for
  light use. A production app would want its own tile provider.
- Nothing is saved yet: there is no shortlist. That is Part 2.
- No automated frontend tests. The interface was checked by driving it in a browser.
- `App.vue` is over the 400 line limit in `AGENTS.md`, mostly styles. It was over
  before this work.

## Running it

Backend, from `backend/`:

```bash
.venv\Scripts\python.exe -m uvicorn main:app
```

Frontend, from `frontend/`:

```bash
npm run dev
```

Backend on 8000, frontend on 5173. Put `GEOAPIFY_API_KEY=` and your key in `.env` in
the project root, then restart the backend. Never open `.env` while recording.

## Next task

Part 2, due 2026-10-06: a persistent shortlist in SQLite. Save a returned hotel by
its provider place id, list saved hotels, remove one, never duplicate, and keep a
saved record readable when the live search later changes or fails. It needs a
documented structure for external places with no nightly rate, a labelled fixed JSON
sample for repeatable checks, and simulated empty, failure, and quota responses.
Reuse `backend/checks/` for the mocked checks.

## Decisions not to re-litigate

- **The search centre is the geocoder's returned point.** If the ZIP is not
  established, no hotel search is made.
- **Failure is never emptiness.** No hotels is a 200 with an empty list; everything
  else is an error with its own status and message.
- **Only what the provider returned is shown.** No invented prices or ratings.
- **OpenStreetMap tiles, no key.** So the backend key has no reason to be near the
  frontend. Keep both credits visible.
- **Provider text is untrusted.** Render as text; give Leaflet text nodes.
- **Visual effects on Leaflet markers go on an inner element.** CSS `rotate` and
  `scale` on the marker itself mislocate it.
- **Part 1 of Assignment 1 and its checkpoint commit `6f4b9f0` stay in history.**
