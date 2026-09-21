# Project Rules

Rules for anyone, human or agent, working in this repo.

## Scope

- Backend code and its data reader live in `backend/`.
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
- Type-hint every function signature.
- Use parameterized queries. Never build SQL from user input.
- Return structured errors, not raw exception text.

## Frontend

- Composition API with `<script setup>`. No Options API.
- Keep API calls in `src/api.js`; components do not call `fetch` directly.
- Every input needs a label. Every error message needs `role="alert"`.
- Tables need real `<th scope="col">` headers with readable labels.

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

## Verification

- Manually scan every change in VS Code before committing.
- Check a search that matches and one that does not, in the browser.
- Run each CRUD action through the frontend, including a booking created after
  seeding.
- Confirm additions, updates, and deletions survive a browser refresh and a
  restart of both servers, and that record counts do not grow on restart.
- Record the action, the expected result, and the observed result.

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
