# Expedia Lite - Assignment 2, Part 1: Live Hotel Search and Map

## Project access

- Repository: https://github.com/Kelvin-prog-stu/expedia-lite (public)
- Assessed commit: `bdf520f9117a69d95dac328e3a21c5e9130810be` on `main`. It is the
  merge of `feature/public-api` and includes the demo video. This report was added
  in the commit after it and changes no code.
- Assignment 1 is still in the history: its Part 1 checkpoint `6f4b9f0` is an
  ancestor of `main`.
- Manual review: the changes on `feature/public-api` were reviewed in VS Code
  Source Control before the merge.

Every file below is linked at the assessed commit, so the links keep working as the
project changes.

### Start and configure

1. Requirements: Python 3.11 or newer, Node.js 20.19 or newer.
2. Get a free key at https://myprojects.geoapify.com/ and put it in a file named
   `.env` in the project root, beside `backend/` and `frontend/`:
   `GEOAPIFY_API_KEY=your-key`. The file is in `.gitignore` and was never
   committed. Restart the backend after editing it.
3. Backend, from `backend/`: `py -3.12 -m venv .venv`, `.venv\Scripts\activate`,
   `pip install -r requirements.txt`, `uvicorn main:app`.
4. Frontend, from `frontend/`: `npm install`, `npm run dev`. Open
   http://localhost:5173/ and use **Hotels by ZIP**.
5. `GET http://localhost:8000/api/health` reports `key is configured` or
   `key is not configured`, never the key.
6. Mocked checks that make no live request, from `backend/`:
   `.venv\Scripts\python.exe checks\check_geo.py`.

Full instructions: [README.md](https://github.com/Kelvin-prog-stu/expedia-lite/blob/bdf520f9117a69d95dac328e3a21c5e9130810be/README.md).

## Research notes

The full notes, with dates and sources, are in
[docs/research-part1.md](https://github.com/Kelvin-prog-stu/expedia-lite/blob/bdf520f9117a69d95dac328e3a21c5e9130810be/docs/research-part1.md).
They were written before any list or map code. In short:

| Source | Useful | Problematic |
| --- | --- | --- |
| [Expedia hotel search](https://www.expedia.com/Hotel-Search) (2026-09-29) | Result count above the list; a clear card layout | The map is a separate overlay, not beside the list (and stayed blank in my automated session, so I make no claim about its pins); results 12 to 32 miles away are mixed in; "We have 6 left at this price" style claims |
| [Booking.com search and map view](https://www.booking.com/searchresults.html) (2026-09-29) | Filters, list and map side by side; grey placeholders while loading; scale bar and map credit | Opened zoomed out to about 30 miles; its count depends on room availability; ranking tied to payments |
| [Geoapify Places](https://apidocs.geoapify.com/docs/places/) | `accommodation.hotel`, `circle:lon,lat,radius` (longitude first), `bias=proximity` gives a distance | Only locations: no prices, ratings, or availability; a page is 20 by default |
| [Geoapify pricing and terms](https://www.geoapify.com/pricing/) | Free plan is enough | Requires a visible "Powered by Geoapify" as well as OpenStreetMap credit |
| [Leaflet reference](https://leafletjs.com/reference.html) | Markers can be tabbed to; `divIcon` avoids bundler icon problems | Answers Enter only through the deprecated `keypress` event |
| [OpenStreetMap tile policy](https://operations.osmfoundation.org/policies/tiles/) | No key needed | Attribution must stay visible; best-effort service |

Decisions that followed: a list beside a map on one screen; selection shared by the
provider's `place_id`; the search centre is the geocoder's returned point and is
drawn; a separate message for each of the six states; only what the provider
returned is shown; OpenStreetMap tiles so no credential reaches the browser; list
and pins as real buttons.

## Early mockup

![Early mockup](https://github.com/Kelvin-prog-stu/expedia-lite/blob/bdf520f9117a69d95dac328e3a21c5e9130810be/docs/mockups/part1-mockup.png?raw=true)

[SVG source](https://github.com/Kelvin-prog-stu/expedia-lite/blob/bdf520f9117a69d95dac328e3a21c5e9130810be/docs/mockups/part1-mockup.svg),
drawn on 2026-09-29 before any list or map code. The backend hotel search
(`geo_controller.py`) had been written just before, so the mockup precedes the
whole frontend but not the whole backend. The PNG is a rendering of the SVG made
afterwards for viewers that do not show SVG; the SVG itself was not edited.

What changed between the mockup and the finished interface, and why, is a dated
section at the end of the research notes. In short:

- **"Powered by Geoapify" was added**, after reading the plan's attribution terms.
- **The map pans only when it must**, instead of recentring on every click.
- **Enter and Space are handled on `keydown`.** Enter did nothing in testing.
- **A backend that is down has its own message**, not "status 500".
- **Hotel names are treated as untrusted text**, since OpenStreetMap is editable.
- **Markers were in the wrong place**, and **selecting a pin scrolled the page**.
  Both were found in real-size screenshots and measured before and after fixing.

## Demo video

[a2-part1-demo.mp4](https://github.com/Kelvin-prog-stu/expedia-lite/blob/bdf520f9117a69d95dac328e3a21c5e9130810be/docs/demo/a2-part1-demo.mp4)
(2 minutes 56 seconds, no audio, 12.7 MB). On GitHub, open it to play it in the
page, or choose Download. Times below are approximate.

| About | What the video shows |
| --- | --- |
| 0:00 | ZIP `16802` searched: loading placeholders, then State College hotels in a list and on the map with the radius and centre |
| 0:18 | A hotel picked in the list highlights on the map; a pin picked on the map highlights and scrolls to its card |
| 0:36 | ZIP `01001` (leading zero kept): Agawam and its hotels |
| 1:00 | Keyboard selection of a card, and a hotel's website opening in a new tab |
| 1:24 | `123`: the five-digit message |
| 1:36 | `00000`: "ZIP code not found" |
| 1:48 | `99999`: a successful search with no hotels, map still shown |
| 2:00 | The backend stopped in VS Code |
| 2:24 | The same search: "Backend not reachable" |
| 2:42 | The backend restarted; `16802` returns its hotels again |

## Verification record

Live searches were made on **2026-09-29** with ZIPs `16802` (State College, PA),
`01001` (Agawam, MA), `10001` (New York, NY), `99999` (a county in Ohio), and
`00000`. No check depends on how many hotels the service returns, because that
changes. Screenshots were taken from the running app with headless Chrome. Those
marked simulated use a stubbed response so the service's quota is not used up.

| Input or action | Expected | Observed | Evidence |
| --- | --- | --- | --- |
| `check_geo.py` | Mocked answers behave as documented, no live request | 24 of 24 pass: postcode and country must match, centre is the returned point with longitude first, an unresolved ZIP never triggers a hotel search, 429 and 500 are errors not empty lists, missing names kept, places without id or coordinates left out and counted, only http and https websites kept, no message carries the key | run on `main` |
| `16802` | Hotels near State College; list and map agree | 20 cards, 20 pins, one centre marker, all 12 tiles loaded, "Showing the nearest 20; there may be more" | [screenshot](https://github.com/Kelvin-prog-stu/expedia-lite/blob/bdf520f9117a69d95dac328e3a21c5e9130810be/docs/screenshots/a2p1-01-results.png?raw=true), video |
| Select in the list, then on the map | Exactly one hotel highlighted in both, each time | One in both places, in both directions | [from map](https://github.com/Kelvin-prog-stu/expedia-lite/blob/bdf520f9117a69d95dac328e3a21c5e9130810be/docs/screenshots/a2p1-02-selected-from-map.png?raw=true), [from list](https://github.com/Kelvin-prog-stu/expedia-lite/blob/bdf520f9117a69d95dac328e3a21c5e9130810be/docs/screenshots/a2p1-03-selected-from-list.png?raw=true), video |
| Enter and Space on a focused pin | Selects it | Both work after the fix; focus stays on the pin | browser check |
| `01001` | Leading zero survives | Agawam, hotels listed | [screenshot](https://github.com/Kelvin-prog-stu/expedia-lite/blob/bdf520f9117a69d95dac328e3a21c5e9130810be/docs/screenshots/a2p1-07-leading-zero-zip.png?raw=true), video |
| `123` and empty | Message, no request | "A ZIP code is five digits, for example 16802." and "Enter a ZIP code."; 0 requests | [screenshot](https://github.com/Kelvin-prog-stu/expedia-lite/blob/bdf520f9117a69d95dac328e3a21c5e9130810be/docs/screenshots/a2p1-04-invalid-zip.png?raw=true), video |
| `00000` | Unresolved, not a search somewhere else | "ZIP code not found" (amber); no hotel request made | [screenshot](https://github.com/Kelvin-prog-stu/expedia-lite/blob/bdf520f9117a69d95dac328e3a21c5e9130810be/docs/screenshots/a2p1-05-unresolved-zip.png?raw=true), video |
| `99999` | A successful search with no hotels | "No hotels found within 5 km", map and centre still shown, no pins | [screenshot](https://github.com/Kelvin-prog-stu/expedia-lite/blob/bdf520f9117a69d95dac328e3a21c5e9130810be/docs/screenshots/a2p1-06-no-hotels-nearby.png?raw=true), video |
| Slow response (simulated) | Loading state, not empty | Four placeholder cards and a map placeholder, button disabled, heading "Finding hotels..." | [screenshot](https://github.com/Kelvin-prog-stu/expedia-lite/blob/bdf520f9117a69d95dac328e3a21c5e9130810be/docs/screenshots/a2p1-08-loading-simulated.png?raw=true) |
| HTTP 429 (simulated) | Own message, not an empty list | "Too many requests" (red), no hotels section | [screenshot](https://github.com/Kelvin-prog-stu/expedia-lite/blob/bdf520f9117a69d95dac328e3a21c5e9130810be/docs/screenshots/a2p1-09-rate-limited-simulated.png?raw=true) |
| HTTP 502 (simulated) | Own message, not an empty list | "Could not load hotels" (red), no hotels section | [screenshot](https://github.com/Kelvin-prog-stu/expedia-lite/blob/bdf520f9117a69d95dac328e3a21c5e9130810be/docs/screenshots/a2p1-10-service-failed-simulated.png?raw=true) |
| Backend stopped | Not an empty list | "Backend not reachable" (red); after restart the same search returns hotels | video |
| Hotel named `<img onerror=...>` (stubbed) | Shown as text | Literal text in the list, the tooltip, and the pin's label; nothing executed | browser check |
| Marker geometry | Centre diamond at the circle's centre | 0.3 px off; a selected pin is 1.25 times larger and centred on its true position | headless Chrome check |
| Select the 15th hotel at 1280 px and 600 px wide | List scrolls; page and map do not move | List moved 1702 and 1432 px; page and map moved 0 | headless Chrome check |
| Hotel-name search, booking history, an unknown stay | Unchanged | Harbor Lantern gives 2 stays, history shows B007 B002 B001, an unknown stay gives 404 | browser check |
| `npm run build` | Clean | Exit 0 | run on `main` |

### Corrections and remaining limitations

Corrections made while verifying (each is logged with its cause in the research
notes):

- Enter did nothing on a focused pin; only Space worked. Fixed by handling both on `keydown`.
- With the backend down the app first said "Request failed with status 500." It now says the backend could not be reached.
- The centre marker was drawn outside its circle, which my class-based checks had missed and a real-size screenshot showed.
- Selecting a pin scrolled the whole page.

Limitations:

- A page is the nearest 20. The page says when it is full and that there may be more, and never claims to list every hotel. It does not page through the rest.
- The service has no prices, ratings, or availability, so none are shown. Names and addresses come from OpenStreetMap and can be wrong or missing.
- "Five digits" is not "a ZIP the service knows". `99999` resolves to a county in Ohio, and `00501`, a real ZIP, returns nothing.
- The rate-limit, provider-failure, and slow-response checks use stubbed responses. A real 429 was not provoked.
- Tiles come from OpenStreetMap's standard server, which is best-effort and meant for light use.
- Nothing is saved: the shortlist is Part 2. No automated frontend tests; the interface was checked by driving it in a browser.

## AI disclosure and evidence log

**Tools and models**

- **Claude Code**, running **Claude Opus 5** (`claude-opus-5`), wrote the code and
  documentation for Assignment 1 and for the ZIP lookup, entry, validation and
  results table up to 2026-09-24 (commits `3f452a2` to `e2c246b`).
- **Claude Code**, running **Claude Sonnet 5.5** (`claude-sonnet-5-5`), wrote the
  Part 1 work on 2026-09-29: the hotel search, the list and map, the checks, the
  research notes, the mockup, and this report (commits `8d2d2ee` onward).
- Also used: VS Code (review and Source Control), Chrome and the Claude desktop
  browser pane (reading the reference sites), headless Chrome driven over its
  DevTools protocol (screenshots and the geometry and scroll checks), Windows
  Snipping Tool (the demo video), and ffmpeg (compressing it).

**Who did what.** The agent wrote the code and drafted this report from results it
produced. The agent ran the mocked checks, the live API requests, the browser and
headless Chrome checks, and took the screenshots. I directed the work, approved the
Leaflet installation, reviewed the changes in VS Code, and recorded the demo video
myself.

**Prompts and decisions**, with the commits they led to. The full log is
[prompts/04-a2-part1-live-hotel-search.md](https://github.com/Kelvin-prog-stu/expedia-lite/blob/bdf520f9117a69d95dac328e3a21c5e9130810be/prompts/04-a2-part1-live-hotel-search.md).

| Prompt or decision | Led to |
| --- | --- |
| "Add one small backend controller function for a ZIP lookup. [...] Accept a result only if it identifies the requested U.S. postcode and has valid coordinates. [...] Distinguish an unresolved ZIP from a failed provider request." (class activity prompt, 2026-09-24) | `geo_controller.py` and its separate error types, `f38f2d5` |
| "keep going with the ZIP entry and validation" (2026-09-24) | `GET /api/location`, validation in the browser and the controller, `4c23aa7` |
| "yes, add both and commit this" | `python-dotenv` and `httpx` declared after CHECK found them installed, `3f452a2` |
| The Assignment 2 overview, pasted 2026-09-29, with no further instruction | `GET /api/nearby-hotels`, `8d2d2ee`; the list and map, `63beda6` |
| "Approve installing Leaflet 1.9.4 [...]?" answered "Yes, install it" | CHECK, approval, install and verify, `207a42f` |
| Research before code | `docs/research-part1.md` and the mockup, `7d164ae` |

**Failed or revised approaches**

1. **Enter on a map pin did nothing.** Testing with real key presses selected a hotel with Space but not Enter. The cause was Leaflet's reliance on the deprecated `keypress` event. Fixed in `63beda6`.
2. **The centre marker was drawn in the wrong place.** My first checks compared CSS classes and passed. The first real-size screenshot showed the diamond outside its circle. The cause was CSS `rotate` and `scale` applied before Leaflet's own transform. Fixed in `cb17c53` and measured.
3. **Selecting a pin scrolled the whole page**, through `scrollIntoView`. The list now scrolls only itself, `cb17c53`.
4. **I first edited the early mockup to match what I built.** I reverted it, kept the original as drawn, and recorded the differences in a dated revisions section instead.
5. **The backend-down message** first read "Request failed with status 500." and was rewritten.
6. **Expedia's map overlay would not render in my automated browser.** I recorded that limit and made no claim about its pin behaviour.

No credentials appear in this report, the screenshots, the video, or the repository:
`.env` is ignored, and the key is read only by the backend.
