# Project Rules

Rules for anyone, human or agent, working in this repo.

## Scope

- Backend code, the SQLite model and controller, and the supplied data live in
  `backend/`.
- Frontend code lives in `frontend/src/`.
- The application name is Expedia Lite. Use it in the folder, the interface, and
  the documentation.

## Dependencies

- Pin versions in `backend/requirements.txt` and `frontend/package.json`.
- Follow CHECK, then TAKE ACTION, then VERIFY before adding anything:
  report what is installed and what the tool requires; state the exact install
  and stop for approval; then confirm the installed version and that the app
  still runs.
- Do not add a dependency the assignment does not need.

## Backend

The booking features follow Model-View-Controller:

- `models.py` is the Model: table definitions and their foreign-key
  relationships. Schema changes go here.
- `database_controller.py` is the Controller: every create, read, update, and
  delete. No other module runs SQL, and this one imports nothing from FastAPI.
- `main.py` routes are thin: validate through `schemas.py`, make one controller
  call, return the result.
- `geo_controller.py` is the controller for the public location API. It is the
  only module that calls Geoapify, it imports nothing from FastAPI, and its
  contract is written at the top of the file. `config.py` reads `.env`.
- Type-hint every function signature.
- Use parameterized queries. Never build SQL from user input.
- Return structured errors, not raw exception text.
- Never put the API key, the request URL, or provider exception text in a
  response or a log. The key travels in the query string.
- A provider failure is never reported as an empty result, and a ZIP the provider
  did not establish is never turned into a search somewhere else.

## Frontend

- Composition API with `<script setup>`. No Options API.
- Keep API calls in `src/api.js`; components do not call `fetch` directly.
- Every input needs a label. Every error message needs `role="alert"`.
- Tables need real `<th scope="col">` headers with readable labels.
- Text from the location service is untrusted: hotel names come from
  OpenStreetMap, which anyone can edit. Render it as text. Never use `v-html`,
  and never hand Leaflet a string to show; give it a text node.
- Show only what the provider returned. No invented prices, ratings, photos, or
  availability. A missing field gets an honest label or is left out.
- Keep both credits visible: "© OpenStreetMap contributors" on the map and
  "Powered by Geoapify" with the results.
- The Geoapify key stays in the backend. Never copy it into frontend code, a
  `VITE_` variable, or a screenshot. The map's tiles need no key.
- Selecting a hotel in the list or on the map selects it in the other, by
  provider place id, and both work from the keyboard.

## Data

- The CSV files in `backend/data/` are the instructor's supplied records. Do not
  edit them by hand.
- `seed.py` loads them into SQLite once, on the first start. After that every
  read and write uses SQLite. Never reseed over existing data.
- Preserve the supplied IDs. New bookings get the next unused ID, and an ID is
  never reused after a deletion.
- Cancelling keeps the record and changes its status. Only Delete removes it.
- `backend/expedia_lite.db` is not committed. Deleting it resets the app to the
  supplied data on the next start.
- `saved_hotels` holds hotels saved from the live API, keyed by the provider's
  place id exactly as given. `demo_hotel_nights` holds one simulated classroom rate
  and room count per saved hotel per night. That rate and those rooms are never
  provider data, and the interface must say so. Both tables are separate from
  `hotels`, which stays the supplied sample records.
- `saved_hotel_zips` records which ZIP search a saved hotel came from, with that
  search's centre and radius. Saving and removing touch all three tables in one
  transaction, and a repeat save adds only what is missing and never overwrites. Use
  `ON CONFLICT DO NOTHING`, never `INSERT OR IGNORE`, which would also swallow a failed
  CHECK and report invalid data as saved.
- The ZIP lookup is local first: saved hotels for the ZIP, and only if that request
  succeeds with none, the live search. A storage error is an error, never an empty
  result, and never falls through to the live search.
- Tests that change data run against a throwaway database (`EXPEDIA_DB_PATH`), never the
  real one.
- Schema changes are additive and repeatable: `CREATE TABLE IF NOT EXISTS` in
  `models.py`, applied on every start. Never alter or drop an Assignment 1 table.

## Verification

- Manually scan every change in VS Code before committing.
- Check a search that matches and one that does not, in the browser.
- Run each CRUD action through the frontend, including a booking created after
  seeding.
- Confirm additions, updates, and deletions survive a browser refresh and a
  restart of both servers, and that record counts do not grow on restart.
- Record the action, the expected result, and the observed result.

## SmokeTest

A repeatable check of the running app, done through the browser without editing
code. It uses a known record from the supplied data: Valley Trail Inn (`H008`)
and its one stay, State College Trail Weekend (`T008`).

1. Search `Valley Trail`. Expect Valley Trail Inn, State College, PA, nightly
   rate $100.00, with State College Trail Weekend, Oct 2 - Oct 4.
2. Search `Sunset Palms`. Expect the no-results message and no table.
3. As Demo Traveler 6, book State College Trail Weekend. Expect a new booking
   with the next unused ID, `confirmed`, at the top of the history.
4. Cancel it. Expect `cancelled`, still listed.
5. Book it again, then Delete and Confirm delete. Expect that booking gone.
6. Note the record counts from `GET /api/health`, refresh the browser, and
   restart both servers. Expect steps 3 to 5 unchanged and the same counts.

Report the observed result for each step.

Live hotel search, added for Assignment 2. Never depend on how many hotels the
service returns for a ZIP; check behaviour, not a count.

7. Enter `16802`. Expect a summary naming State College, a numbered list and the
   same number of pins, one centre marker, and both credits.
8. Select a hotel in the list, then a different one on the map. Expect exactly
   one hotel highlighted in both places each time.
9. Enter `123`. Expect the five-digit message and no request. Enter `00000`.
   Expect "ZIP code not found". Enter `99999`. Expect a successful search with no
   hotels and the map still shown.
10. Stop the backend and search again. Expect "Backend not reachable", not an
    empty list.
11. Run `backend/checks/check_geo.py`. Expect every check to pass.

## AutoLoop

Run the SmokeTest, inspect any failure, make the smallest in-scope fix, and run
it again. Stop when it passes, after five correction cycles, or when a fix needs
permission this file does not give. Report what passed and what remains
unverified.

## Style

- Python: 100-column lines, early returns over nested conditionals.
- Files stay under 400 lines; functions under 50.
- No typographic dashes in committed files.

## Commits

- Format: `<type>: <description>` with types feat, fix, refactor, docs, test, chore.
- One logical change per commit.
- `main` is the default branch. Substantial work happens on a feature branch
  and merges into `main` once reviewed and checked. The Part 1 checkpoint commit
  stays in history.

## Working loop

```
describe -> predict the blast radius -> plan -> implement
    -> inspect the Git diff -> verify behavior -> correct or commit
```

State which files a change will touch before editing, then check the actual diff
against that prediction. Verify behaviour in the running app, not only from the
diff.
