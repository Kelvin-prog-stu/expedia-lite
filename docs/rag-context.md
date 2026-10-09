# RAG context: one question, followed end to end

Written on 2026-10-08 from a LIVE run (Gemini `gemini-3.5-flash-lite`, my real database,
instructions version `d6b8ef79f623`). Rates and rooms are simulated classroom data. Wording
of a model's answer changes from run to run; the query, the records, and the amounts are
what to check.

## The question

> Show the three cheapest saved hotels near ZIP 16802 with at least one room available for
> the night of October 11, 2026.

I used ZIP 16802 because that is where my hotels are saved. The same question for ZIP 16803,
where nothing is saved, is the no-match case below.

**Conversation ID:** `conv-35b94626` (the question and one follow-up, "What about October
12?"). Find it in the database:

```sql
SELECT message_id, created_at, role, stage, status, prompt_version, content
FROM chat_messages
WHERE conversation_id = 'conv-35b94626'
ORDER BY message_id;
```

## Relevant schema

The three tables the model may read (full definitions are in
[models.py](../backend/models.py) and are put into the request from the live database):

| Table | Columns used | Meaning |
| --- | --- | --- |
| `saved_hotels` | `hotel_id` (key), `name`, `address`, `latitude`, `longitude` | A hotel saved with Add to Local. `hotel_id` is the provider's place id |
| `saved_hotel_zips` | `hotel_id`, `zip_code`, `locality`, `distance_m`, centre | Which ZIP search a hotel was saved from. Key is (`hotel_id`, `zip_code`) |
| `demo_hotel_nights` | `hotel_id`, `stay_date`, `nightly_rate_cents`, `rooms_available` | One simulated row per hotel per night. Key is (`hotel_id`, `stay_date`). Cents, not dollars |

The instructions the model gets are in [prompts/hotel-assistant.md](../prompts/hotel-assistant.md).
The backend reads that file once at start-up and saves its version (the first 12 characters of
its SHA-256) with every message.

## The two JOINs

1. **`saved_hotels h JOIN saved_hotel_zips z ON z.hotel_id = h.hotel_id`** keeps the hotels
   that were saved from the named ZIP: `z.zip_code = '16802'`.
2. **`... JOIN demo_hotel_nights n ON n.hotel_id = h.hotel_id`** brings in each of those hotels'
   dated rate and room count, so the query can filter the night and the rooms and order by
   price: `n.stay_date = '2026-10-11' AND n.rooms_available >= 1 ORDER BY n.nightly_rate_cents`.

A night with no row means availability is unknown, so that hotel never appears.

## Generated SQL (request 1, saved as `proposed_sql` then `executed_sql`)

```sql
SELECT h.hotel_id, COALESCE(h.name, '(name not provided)') AS name, n.stay_date,
       n.nightly_rate_cents, n.rooms_available
FROM saved_hotels h
JOIN saved_hotel_zips z ON z.hotel_id = h.hotel_id
JOIN demo_hotel_nights n ON n.hotel_id = h.hotel_id
WHERE z.zip_code = '16802' AND n.stay_date = '2026-10-11' AND n.rooms_available >= 1
ORDER BY n.nightly_rate_cents ASC
LIMIT 3
```

(Line breaks added here; it is saved as one line.) The backend allowed it because it is one
`SELECT`, reads only the three tables, has no comments, and ran on a read-only connection.

## Retrieved rows (saved as `retrieval_result`)

| name | stay_date | nightly_rate_cents | rooms_available |
| --- | --- | --- | --- |
| Scholar Hotel State College | 2026-10-11 | 10000 | 20 |
| Nittany Lion Inn | 2026-10-11 | 10000 | 20 |

## Final answer (request 2, saved as `answer`)

> The query returned two hotels near ZIP 16802 for October 11, 2026: Scholar Hotel State
> College and Nittany Lion Inn, both with a nightly rate of $100.00 and 20 rooms available.
> I recommend Scholar Hotel State College because it offers a great nightly rate of $100.00
> with plenty of space (20 rooms available) for your stay on October 11, 2026. Note that these
> rates and rooms are simulated classroom data.

The two hotels tie at $100.00, so "recommend Scholar" is the model's pick, not a ranking the
data supports. Only two hotels are saved, so "three cheapest" returns two.

## Checked against the database

I ran the same JOINs in Python against the database file, outside the chatbot:

| ZIP | Night | Direct query result |
| --- | --- | --- |
| 16802 | 2026-10-11 | Scholar Hotel State College 10000, 20 rooms; Nittany Lion Inn 10000, 20 rooms |
| 16802 | 2026-10-12 | Nittany Lion Inn 10000, 20; Scholar Hotel State College 17550, 20 |
| 16803 | 2026-10-11 | no rows |

The chatbot's rows and amounts match. The follow-up in the same conversation ("What about
October 12?") returned the October 12 rows, and its answer gave $100.00 for the Nittany Lion
Inn and $175.50 for Scholar, as in the table. The follow-up works because the first request
includes the earlier question, query, and answer of the same conversation.

## No match

Question: the same, for ZIP 16803 (conversation `conv-2b71a684`). The query had the same
shape with `z.zip_code = '16803'` and returned no rows. No second model request was made, so
no hotel or price could be invented. The answer shown, written by the backend:

> No saved hotel matches that. Nothing was retrieved, so there is nothing to base an answer on.
> Saved hotels exist for ZIP 16802 with nights from 2026-10-10 to 2026-10-14.

A second no-match, by dates (March 3 to 5, 2027, conversation `conv-c7df2c45`), is in
[the full trace](evidence/live-run-2026-10-08-with-history.json).

## A blocked write

The live model declined every write request I tried (it answered `insufficient_data` and wrote
no query), so the block is shown with fixtures, in `backend/checks/check_chat.py`: 23 disallowed
proposals (`DELETE`, `UPDATE`, `INSERT`, `DROP`, a second statement, a comment, a table outside
the three, and so on, now including `SELECT * FROM chat_messages`) are each refused with status
`rejected`, no query runs, and all the other tables are byte-identical afterwards. The check
database is a throwaway one, not mine. A refusal is saved as an `error` step with status
`rejected` and no assistant answer.

## Conversation history that persists

- Each step is saved as it happens in `chat_messages`: `message_id`, `conversation_id`,
  `created_at`, `role`, `stage`, `content`, `status`, `prompt_version`. Stages are `question`,
  `proposed_sql`, `executed_sql`, `retrieval_result`, `notes`, `answer`, and `error`. Roles
  are `user`, `assistant` (the model's reply or the app's answer), and `tool` (the retrieval
  result and errors).
- The model's queries use a separate read-only connection and cannot see this table. The
  history is written by the app's own connection (`database_controller.save_chat_message`).
- After a page refresh the panel reloads the conversation (the browser remembers the
  conversation id, and the backend can also return its most recent one).
  After I stopped and restarted the backend, `GET /api/chat/history` returned the saved turns
  straight away, because they are in the database file.
- A failed attempt is saved as an `error` step (`llm_error` for a model outage) and no
  assistant reply is created. Checked in `check_chat.py` with a model that always fails.

The conversation rows for `conv-35b94626` are listed by the SQL above. Their stages, in
order, are `question`, `proposed_sql`, `executed_sql`, `retrieval_result`, `answer`, then the
same five again for the follow-up.
