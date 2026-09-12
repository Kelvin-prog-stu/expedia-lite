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

- Type-hint every function signature.
- Validate responses with the Pydantic models in `schemas.py`.
- Keep route handlers thin. File reading and record joining belong in
  `data_source.py`, which imports nothing from FastAPI.
- Return structured errors, not raw exception text.

## Frontend

- Composition API with `<script setup>`. No Options API.
- Keep API calls in `src/api.js`; components do not call `fetch` directly.
- Every input needs a label. Every error message needs `role="alert"`.
- Tables need real `<th scope="col">` headers with readable labels.

## Data

- The CSV files in `backend/data/` are the instructor's supplied records. Do not
  edit them by hand.
- Preserve the supplied IDs. New records get new unique IDs.

## Verification

- Manually scan every change in VS Code before committing.
- Check both a search that matches and a search that does not, in the browser.
- Record the action, the expected result, and the observed result.

## Style

- Python: 100-column lines, early returns over nested conditionals.
- Files stay under 400 lines; functions under 50.
- No typographic dashes in committed files.

## Commits

- Format: `<type>: <description>` with types feat, fix, refactor, docs, test, chore.
- One logical change per commit.
- `main` is the default branch. Part 2 develops on a feature branch and merges
  into `main`, preserving the Part 1 checkpoint commit.

## Working loop

```
describe -> predict the blast radius -> plan -> implement
    -> inspect the Git diff -> verify behavior -> correct or commit
```

State which files a change will touch before editing, then check the actual diff
against that prediction. Verify behaviour in the running app, not only from the
diff.
