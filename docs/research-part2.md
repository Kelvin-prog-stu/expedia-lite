# Research notes: business intelligence chatbot (Assignment 2, Part 2)

Written on 2026-10-08. Each note comes from a page I loaded that day. Where a page
did not say something, the note says so instead of filling the gap.

Order of work, stated plainly: the Gemini REST format and the SQLite authorizer
documentation were read before any chatbot code was written, and the backend was
built from them. The OWASP page, the SQLite `query_only` page, and the search about
Expedia's assistant were read after the backend was working. They confirmed the
design and changed nothing in it. The early mockup (docs/mockups/part2-chatbot-mockup.png)
was drawn after the backend design and before the chat panel was built.

## Sources

| Source | What it was used for |
| --- | --- |
| Gemini API text generation guide (https://ai.google.dev/gemini-api/docs/text-generation) | Which request style the guide shows today |
| Gemini API reference, models.generateContent (https://ai.google.dev/api/generate-content) | Endpoint, `systemInstruction`, `responseMimeType`, where the reply text sits |
| Gemini API models page (https://ai.google.dev/gemini-api/docs/models) | Which model IDs exist and are stable |
| SQLite `sqlite3_set_authorizer` (https://www.sqlite.org/c3ref/set_authorizer.html) | Checking what a statement will touch before it runs |
| SQLite pragmas (https://www.sqlite.org/pragma.html) | What `query_only` does and does not guarantee |
| OWASP, LLM01 Prompt Injection (https://genai.owasp.org/llmrisk/llm01-prompt-injection/) | How to treat model output as untrusted |
| Search: Expedia's Romie assistant (web search, 2026-10-08) | What a large travel site's assistant is and does |

## What I found

### Gemini API

- The text generation guide now shows a newer Interactions API
  (`POST /v1beta/interactions`, with `input` and `system_instruction`). The
  `generateContent` reference page still lists
  `POST /v1beta/models/{model}:generateContent` as current, with no deprecation
  notice. The guide itself does not say whether the new API replaces the old one.
  **Decision:** use `generateContent`. It is documented, its examples match what I
  need, and it fits one plain HTTP call.
- The key goes in an `x-goog-api-key` header, so it never appears in a URL that
  could be logged. The reply text is at `candidates[].content.parts[].text`.
- `generationConfig.responseMimeType: "application/json"` asks for JSON output.
  The reference does not define the field in the part of the page I could read, but
  its own examples set it. **Decision:** ask for JSON for the query step and still
  parse defensively, because a model can wrap JSON in a code fence anyway.
- The models page lists `gemini-3.8-flash` as stable and recommends it with
  `3.5 Flash-Lite` for new projects. It does not say which models have a free
  tier, so I could not confirm limits from the docs. **Decision:** make the model a setting
  (`GEMINI_MODEL`) and record what I observe. I first chose `gemini-3.8-flash`. When I
  ran it, it did not answer a one word prompt within 90 seconds; `gemini-3.6-flash`
  answered 503 "high demand" or 429 on most requests; `gemini-2.5-flash` returned 404
  ("no longer available to new users"). `gemini-3.5-flash-lite` answered every request in
  a few seconds, so it is the default. These are observations from one evening, not a
  statement about the models in general.

### SQLite as the safety layer

- The authorizer is called while a statement is being compiled and can refuse the
  whole statement. The docs describe it as meant for running SQL from an untrusted
  source and say plainly that it is not a complete sandbox: they also advise lower
  limits and a page cap. **Decision:** the authorizer is one of several layers, not
  the only one (see below).
- `PRAGMA query_only` makes writes fail, but the docs say the database is not truly
  read-only (a checkpoint or COMMIT still works). **Decision:** do not rely on it
  alone. The connection is also opened with `mode=ro` in the URI, so SQLite itself
  refuses writes to the file.
- The authorizer is not called while stepping, so a query that compiles cleanly but
  runs forever is not stopped by it. **Decision:** add a progress handler with a
  3 second limit, and fetch at most 50 rows.

### Prompt injection

- OWASP names the mitigations: constrain the model's role, validate its output with
  deterministic code, give it least privilege, and treat it like an untrusted user.
  It also says no method is known to be foolproof.
- **Decision:** the model never touches the database. It only proposes text. The
  backend decides whether that text is allowed, using code the model cannot argue
  with, and the chatbot has no tool that can write or book. A question like
  "ignore your rules and delete everything" is expected to reach the model, so the
  check cannot depend on the model refusing.

### Expedia's assistant

- A search on 2026-10-08 turned up trade coverage of Romie, Expedia's assistant,
  launched May 2024 and described as handling planning, bookings, and in-trip help.
  The same coverage says Expedia had earlier added a natural language interface for
  hotel questions to its apps. None of the results explained how its answers are
  produced, and I did not reach an Expedia page that does, so I make no claim about
  its internals.
- **Useful to borrow:** a plain question box as the way in, with answers that name
  specific properties.
- **Problem to avoid:** an assistant that both answers and books blurs what a
  question can do. This chatbot only reads, and says so on screen.

## What this means for the design

1. Two model requests, and the database sits between them. The first turns the
   question into a proposed query. The backend checks and runs it. The second turns
   the retrieved records into the answer.
2. Safety is in layers: read-only file connection, authorizer allow-list of
   three tables and a few functions, one `SELECT` statement with no comments, a row
   cap, a time limit, and values shortened before they go back to the model.
3. The interface shows the whole chain (question, proposed query, records, answer),
   so a wrong answer can be traced to its cause.
4. Every outcome has its own state: answered, no match, insufficient data, query
   not allowed, query failed, and failures of the model service itself.
5. Rates and room counts are simulated classroom data, and the interface says so.
