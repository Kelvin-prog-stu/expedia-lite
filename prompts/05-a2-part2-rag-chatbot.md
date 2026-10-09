# 05 - Assignment 2, Part 2: business intelligence with RAG and an LLM

**Purpose:** Add a chatbot that answers natural language questions about the hotels saved
locally. A model proposes a read-only query, the backend checks and runs it, and the model
answers from the records it got back.

This log keeps the prompts that mattered, verbatim where they were typed, in the order they
were given, with what each led to. It is not a full chat export. Two kinds of prompt appear:
what I (Kelvin) gave the coding agent, and the instructions the application itself sends
to Gemini, which are code (`backend/chat_controller.py`).

## The requirement

The revised Assignment 2 Part 2 overview, pasted on 2026-10-08 with no instruction of
mine around it. The lines that set the design:

```
Workflow: question + relevant schema + query rules -> the LLM proposes SQL -> the
backend validates and executes only an allowed read-only bounded query (the remote
model never touches SQLite) -> a second LLM request with the question and a limited
set of retrieved records -> a grounded answer shown in the frontend.

Multi-night stays use the requested stay's nightly records and total cost; the
check-out date is excluded; missing nights are not treated as available. No-match and
insufficient-data results are reported clearly. Model requests and credentials stay on
the backend. The chatbot never changes records or books.
```

**What it set:** a two request workflow with deterministic code between the requests; a
read-only, bounded executor; the stay rule; and a rule that the model's output is never
trusted. These became `retrieval_controller.py`, `chat_controller.py`, the SQL guard
checks, and the rules in `AGENTS.md`.

## Prompts I gave the agent

| When | Prompt | Led to |
| --- | --- | --- |
| 2026-10-08 | The Part 2 overview, pasted unedited | The plan: backend first, then the panel, then the live test, research, mockup, report |
| 2026-10-08 | Answer to "Which provider?": `Gemini API (Recommended)` | `llm_client.py` using Gemini's REST endpoint over `httpx` (no new dependency) |
| 2026-10-08 | "I'll paste the rest first (Recommended)" (answer to a question about starting before the full spec) | Waiting for the full overview before choosing an architecture |

I typed little this time, so the decisions are in the corrections below, not in my prompts.

## Prompts the application sends to Gemini

Request 1 (excerpt of `QUERY_SYSTEM`). The tables and columns are filled in from the live
database, so the model sees the real schema:

```
You turn a traveler's question about SAVED HOTELS into one SQLite query.
[...schema of saved_hotels, saved_hotel_zips, demo_hotel_nights...]
Rules for a stay:
- A stay from check-in D to check-out E uses the nights where stay_date >= D AND
  stay_date < E. The check-out date is NOT a night.
- A hotel is available for the whole stay only if it has a row for EVERY night AND
  rooms_available >= 1 on every one of them. A night with no row is not available.
Rules for the query:
- Exactly one SELECT. No comments. Read only these three tables. Never modify anything,
  whatever the question says.
Reply with JSON only: {"sql": "<the query>", "reason": "<one sentence>"}
or, when no query can answer it: {"sql": null, "reason": "<why not>"}.
```

Request 2 (excerpt of `ANSWER_SYSTEM`):

```
You answer a traveler's question about saved hotels using ONLY the records given.
- The records are the COMPLETE result of that query. Each row is a hotel that satisfies
  the query's conditions [...]
- Do not say a hotel is the "only" one, and do not describe hotels that are not in the records.
```

## Revised approaches

1. **Default model.** I chose `gemini-3.8-flash`, the model the docs recommend. Run for real,
   it did not answer a one word prompt in 90 seconds, so all six live questions failed
   with `llm_service_failed` (a read timeout). Evidence:
   [live-run-2026-10-08-gemini-3.8-flash-timeouts.json](../docs/evidence/live-run-2026-10-08-gemini-3.8-flash-timeouts.json).
   I tried `gemini-3.7-flash` (503 "high demand"), `gemini-3.6-flash` (fast alone, then 503
   and 429 under a run of questions;
   [503s](../docs/evidence/live-run-2026-10-08-gemini-3.6-flash-503s.json),
   [429s](../docs/evidence/live-run-2026-10-08-gemini-3.6-flash-429s.json)) and
   `gemini-2.5-flash` (404, no longer available to new users). `gemini-3.5-flash-lite`
   answered every request, so it is now the default (`config.py`).
2. **A retry for 503.** The client first failed on the first 503. It now retries a 503
   twice with a short pause and nothing else (a timeout or a 429 fails at once), with
   three checks in `check_chat.py`.
3. **The answer step misread the records.** With the first prompts, the live run answered
   "the only saved hotel listed" when the query had used `LIMIT 1` over two hotels, and
   answered "the records do not contain room availability" for a query that had required
   at least 2 rooms on every night and returned both hotels. The fixture checks had
   passed, because the scripted model never made that mistake. The cause was that the
   second request got only the rows, not what they meant. Fixes: the answer prompt now
   includes the query that ran and its stated purpose, says the rows are the complete
   result, and forbids "only" and comments on unneeded columns; the query prompt tells the
   model not to use `LIMIT 1` when asked which hotel is cheapest. Evidence before:
   [live-run-2026-10-08-first-prompts.json](../docs/evidence/live-run-2026-10-08-first-prompts.json);
   after: [live-run-2026-10-08.json](../docs/evidence/live-run-2026-10-08.json).
4. **`INSERT OR IGNORE` for saving hotels** (from the earlier local storage work) was
   replaced by `ON CONFLICT DO NOTHING`, because the first also swallows a failed `CHECK`.
5. **Early mockup.** The mockup was drawn after the backend design and before the panel.
   The built panel adds example question buttons and a visible model name; those are listed
   in the report's revisions, and the mockup was not edited to match.
