# 04 - Assignment 2, Part 1: live hotel search and map

**Purpose:** Replace the supplied local hotel records, for this feature only, with
hotels obtained from a public API. A traveler enters a five digit US ZIP code and
sees hotels within 5 km as a list and on a Leaflet map, with selection shared
between the two.

This log keeps the prompts that mattered, verbatim, in the order they were given,
with what each one led to. It is not a full chat export.

## The requirement

Pasted from the Assignment 2 overview page on 2026-09-29, unedited apart from
trimming to the Part 1 paragraphs:

```
The application accepts a five-digit U.S. ZIP code, including leading zeros.
FastAPI uses Geoapify to resolve it to a U.S. postcode location and obtain hotels
within 5 km of the returned point. The search center is that returned location,
not the traveler's position or every address within the ZIP area. A lookup that
does not establish the requested U.S. ZIP code must not silently become a
different-location search.

Vue presents the returned hotels as a list and on a Leaflet map. Selecting a hotel
in either representation identifies the same hotel in the other. [...] No invented
prices, ratings, room availability, or booking confirmations are permitted.

The interface distinguishes loading, results, invalid input, an unresolved ZIP
code, no nearby results, and a failed request. It must not describe a service
failure as an empty successful search. [...] Store API keys and credentials in a
local .env file and add .env to .gitignore.
```

**What it set:** the search centre comes from the geocoder's answer and nothing
else; six named states that must look different; no invented data; the key stays
in the backend. Each became a rule in `AGENTS.md` and a check in
`backend/checks/check_geo.py`.

## Prompts given

### 2026-09-24: the in-class activity

The class activity page supplied the prompts for the first round trip. Pasted with
"do it", and followed in order. The ones that shaped the code:

```
Add one small backend controller function for a ZIP lookup. [...] Use Geoapify
forward geocoding with postcode, type=postcode, filter=countrycode:us, and
format=json. Read the API key through the configuration helper and supply it only
in the backend request. Use a finite timeout and the inspected HTTP capability.

Accept a result only if it identifies the requested U.S. postcode and has valid
coordinates. [...] Distinguish an unresolved ZIP from a failed provider request.
Never print or return the key, full provider request URL, or raw exception text
containing credentials.
```

Led to `backend/geo_controller.py` and `backend/config.py`
(commit `f38f2d5`, later extended). The "distinguish an unresolved ZIP from a
failed provider request" line is why the controller has separate error types.

```
keep going with the ZIP entry and validation
```

Led to `GET /api/location?zip=`, validation in the browser and again in the
controller, and `01001` keeping its leading zero (commit `4c23aa7`). The
graded activity asked for the result in a table, which changed the definition
list to a real table (commit `e2c246b`).

```
yes, add both and commit this
```

The approval step of CHECK, TAKE ACTION, VERIFY for `python-dotenv` and `httpx`.
Both were already installed through `fastapi[standard]`; declaring them changed
`requirements.txt` only (commit `3f452a2`).

### 2026-09-29: Part 1

The Assignment 2 overview above was the whole instruction: no further prompt was
typed. The agent worked from it, and stopped for one decision.

The CHECK step found Leaflet absent (latest stable 1.9.4, BSD-2-Clause, no
dependencies) and asked:

```
Approve installing Leaflet 1.9.4 into the frontend? Exact command, run in
frontend/: npm install leaflet@1.9.4 --save-exact. It changes only package.json,
package-lock.json and frontend/node_modules. [...]
```

Answer given: `Yes, install it (Recommended)`. Led to commit `207a42f`, then verified
with `npm ls`, a clean build, and a running app.

`push it` (twice) authorised each push of `feature/public-api`.

## Decisions that came out of the work

- **Research before frontend code.** Expedia and Booking.com were read for how they
  pair a list and a map, and the Geoapify, Leaflet, and OpenStreetMap tile
  documentation for what is possible. The result is `docs/research-part1.md`, with
  a wireframe in `docs/mockups/part1-mockup.svg`.
- **Tiles need no key.** OpenStreetMap's standard tiles, so the backend key has no
  reason to be near frontend configuration.
- **Failure is never emptiness.** A successful search with no hotels is a 200 with an
  empty list; a rate limit is 429; a provider failure is 502; an unreachable backend
  has its own message.

## Failed or revised approaches

- **Enter on a map pin did nothing.** Real key presses in the browser selected a
  hotel with Space but not Enter: Leaflet answers Enter only through the deprecated
  `keypress` event. Both keys are now handled on `keydown` (commit `63beda6`).
- **A backend that is down showed "Request failed with status 500."** Vite's proxy
  answers that way. It now says the backend could not be reached.
- **The centre marker landed outside its circle.** The first real-size screenshot
  showed it. CSS `rotate` and `scale` on the marker element are applied before
  Leaflet's own positioning transform. My class-based checks had passed while the
  map was wrong. A geometry check now confirms it (commit `cb17c53`).
- **Selecting a pin scrolled the whole page.** `scrollIntoView` also scrolls the
  window, which would drag the map away when the columns stack. The list now
  scrolls only itself (commit `cb17c53`).

## Verification worth reusing

Never assert a hotel count from the live service; it changes. Assert behaviour: the
number of list cards equals the number of pins, exactly one hotel is selected after
each click, an empty list is not an error, and a stubbed 429 or 500 shows its own
message without using up the service's quota. `backend/checks/check_geo.py` does the
provider side against labelled mock responses.
