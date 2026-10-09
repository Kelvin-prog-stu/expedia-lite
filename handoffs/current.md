# Current handoff

Written 2026-10-08. A handoff records what was true when it was written; the
repository is the authority. Re-check before trusting any line of this.

**Why this exists:** end of Assignment 2, Part 2 (business intelligence with RAG and an
LLM). Not an interruption. Results below came from running the code, or are marked as
fixture results.

## Where things stand

- Part 2 work is on `feature/rag-chatbot`, which includes the in-class local storage
  commits (`assignment2_part2_in_class`). Part 1 is on `main` (`bdf520f`).
- The report is `reports/assignment-2-part-2/report.md`. The demo video goes in
  `docs/demo/`.

## What works

- **Ask about your saved hotels** panel: question in, answer out, with the proposed query,
  the retrieved records, and the answer shown. States: loading, answered, no match,
  insufficient data, query refused, and failure (not configured, rate limited, service
  failed, unusable reply, backend unreachable).
- `POST /api/chat`: Gemini proposes one SQL query; `retrieval_controller.py` checks it and
  runs it read only (one `SELECT`, three tables, allowed functions, 50 rows, 3 seconds);
  Gemini writes the answer from the rows, the query, and its stated purpose.
- The key is in `.env` (`GEMINI_API_KEY`), read by `backend/config.py`, sent in a header.
  The default model is `gemini-3.5-flash-lite` (see `prompts/05`, revision 1).
- Everything from Part 1 and the local storage work is unchanged.

## What was checked

| Check | Result |
| --- | --- |
| `backend/checks/check_chat.py` (fixtures, scripted model) | 85 of 85 |
| `check_geo.py`, `check_schema.py`, `check_saved_hotels.py` | 24, 32, 36 pass |
| `npm run build` | clean |
| `backend/checks/run_live_questions.py` (live Gemini, real database) | 6 of 6 as expected on 2026-10-08, tables unchanged |

## Known limits

- Model wording varies run to run, so checks look at structure and records, not wording.
- On 2026-10-08 `gemini-3.8-flash` and `gemini-3.6-flash` were unusable (timeout, 503, 429).
  If `gemini-3.5-flash-lite` misbehaves, set `GEMINI_MODEL` in `.env` and restart.
- A live attempt to make the model emit a write statement was refused by the model itself,
  so the refusal of a disallowed query is shown by the fixture checks, not by a live model.
- Only hotels saved with Add to Local are searched. Rates and rooms are simulated.
