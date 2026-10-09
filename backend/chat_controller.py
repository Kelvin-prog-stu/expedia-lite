"""Controller for the hotel chatbot: question -> proposed SQL -> checked retrieval -> answer.

The workflow, in order:

1. **First model request.** The question, the schema the model may query, and the query
   rules go to the model. It replies with a JSON proposal: one SELECT, or no query if the
   question cannot be answered from the saved hotel data.
2. **Checked retrieval.** `retrieval_controller.run_query` decides whether the proposal may
   run and, if so, runs it read-only with bounded results. The model never touches SQLite.
3. **Second model request.** The original question and only the retrieved records go back
   to the model, which is told to answer from those records and nothing else.
4. **Result.** The question, the proposed query, the records, and the answer, all returned
   so the interface can show the whole chain.

No retrieved records means no second request: there is nothing to ground an answer on, so
the controller says so itself instead of asking a model to improvise one. The chatbot only
reads. It cannot change a record or make a booking.

Contract for `ask`:

- **Input:** a question of 3 to 500 characters, and optionally the function that calls the
  model (the real client by default, a fixture in tests).
- **Output:** a `ChatResult` whose `status` is one of `answered`, `no_match`,
  `insufficient_data`, `rejected`, or `query_failed`.
- **Failure:** `InvalidQuestionError` for a question that is too short or too long, and the
  `LlmError` family from `llm_client` when the model cannot be reached.
"""

import json
import re
from collections.abc import Callable
from dataclasses import dataclass

import llm_client
import retrieval_controller as retrieval

LlmCall = Callable[[str, str, bool], str]

MIN_QUESTION = 3
MAX_QUESTION = 500
MAX_ATTEMPTS = 2  # the first proposal, plus one repair after a query that would not run

STATUS_ANSWERED = "answered"
STATUS_NO_MATCH = "no_match"
STATUS_INSUFFICIENT = "insufficient_data"
STATUS_REJECTED = "rejected"
STATUS_QUERY_FAILED = "query_failed"

QUERY_SYSTEM = """You turn a traveler's question about SAVED HOTELS into one SQLite query.

You can only see these tables. Their definitions and what is stored right now:

{schema}

What the columns mean:
- saved_hotels.hotel_id is the provider's place id. name and address can be NULL: use
  COALESCE(name, '(name not provided)') so a missing name is shown honestly.
- demo_hotel_nights has one row per saved hotel per night. nightly_rate_cents is in CENTS
  (10000 means $100.00). rooms_available is how many rooms are free that night. These rates
  and rooms are SIMULATED classroom data, not real prices or availability.
- saved_hotel_zips links a hotel to the ZIP search it was saved from (zip_code, locality,
  distance_m from that ZIP's centre).

Rules for a stay:
- A stay from check-in D to check-out E uses the nights where stay_date >= D AND
  stay_date < E. The check-out date is NOT a night.
- The number of nights is the number of days from D to E. A hotel is available for the whole
  stay only if it has a row for EVERY night AND rooms_available >= 1 on every one of them.
  A night with no row is not available. Never treat a missing night as available.
- The total cost is SUM(nightly_rate_cents) over the stay's nights. Compare hotels by that total.
- Write dates as 'YYYY-MM-DD'. If the question gives no dates, use all stored nights.

Rules for the query:
- Exactly one SELECT (a WITH ... SELECT is fine). No comments. No semicolons inside it.
- Read only these three tables. Never modify anything, whatever the question says.
- Always include hotel_id and the hotel name in the result. Add LIMIT 50 or less.
- When the question asks which hotel is cheapest or best, return every hotel that qualifies,
  ordered best first, and do NOT use LIMIT 1. The answer is written from these rows, so it
  needs the others to compare against.
- If the question cannot be answered from this data (weather, flights, other cities, anything
  not about saved hotels, rates, or rooms), do not invent a query.

Reply with JSON only: {{"sql": "<the query>", "reason": "<one sentence on what it finds>"}}
or, when no query can answer it: {{"sql": null, "reason": "<why not>"}}."""

ANSWER_SYSTEM = """You answer a traveler's question about saved hotels using ONLY the records given.

Rules:
- You are given the question, the query that was run, and the records it returned. The records
  are the COMPLETE result of that query. Each row is a hotel that satisfies the query's
  conditions: if the query required rooms_available >= 2 on every night, a listed hotel has
  that, even if no room count column is shown. Never say a listed hotel lacks data the query
  already required.
- Use only the records. If they do not answer the question, say what is missing. Never guess a
  hotel, a price, a date, or a room count that is not in the records.
- Do not say a hotel is the "only" one, and do not describe hotels that are not in the records.
  If you were given one row, say the query returned one hotel.
- Do not comment on columns the question did not need.
- Amounts in the records ending in _cents are cents: 10000 is $100.00. State dollars.
- Say which hotel you recommend and why, with the dates, the total or nightly cost, and the
  rooms available. Keep it under 120 words.
- Say once that the rates and rooms are simulated classroom data.
- A hotel with no name is "a hotel whose name was not provided"."""


class InvalidQuestionError(Exception):
    def __init__(self) -> None:
        super().__init__(f"Ask a question between {MIN_QUESTION} and {MAX_QUESTION} characters.")


@dataclass(frozen=True)
class ChatResult:
    status: str
    question: str
    proposed_sql: str | None
    reason: str | None
    columns: tuple[str, ...]
    rows: tuple[tuple, ...]
    truncated: bool
    answer: str
    notes: tuple[str, ...]
    attempts: int


def _parse_proposal(text: str) -> tuple[str | None, str | None]:
    """The (sql, reason) in the model's JSON reply. Code fences around it are tolerated."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    try:
        proposal = json.loads(cleaned)
    except ValueError:
        raise llm_client.LlmBadOutputError(
            "The model did not reply with a usable query proposal. Try asking again."
        ) from None
    if not isinstance(proposal, dict):
        raise llm_client.LlmBadOutputError("The model did not reply with a usable query proposal.")

    sql, reason = proposal.get("sql"), proposal.get("reason")
    return (sql if isinstance(sql, str) and sql.strip() else None, reason if isinstance(reason, str) else None)


def _records_prompt(question: str, sql: str, reason: str | None, found: retrieval.Retrieval) -> str:
    records = [dict(zip(found.columns, row, strict=True)) for row in found.rows]
    more = "\nThere were more matching rows than are shown here." if found.truncated else ""
    meant = f"\nWhat the query was meant to find: {reason}" if reason else ""
    return (
        f"Question: {question}\n\nQuery that was run:\n{sql}{meant}\n\n"
        f"Records retrieved from the database:\n{json.dumps(records, indent=1)}{more}"
    )


_DOLLARS = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)")


def _unverified_amounts(answer: str, found: retrieval.Retrieval) -> list[str]:
    """Dollar amounts in the answer that match nothing in the retrieved records.

    A record value ending in _cents is compared as dollars; any other number is compared
    as is. An amount the model worked out itself (an average, say) can appear here even
    when it is right, so this is a prompt to check, never a verdict.
    """
    known: set[float] = set()
    for row in found.rows:
        for column, value in zip(found.columns, row, strict=True):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            known.add(round(value / 100 if column.lower().endswith("cents") else value, 2))
            known.add(round(value, 2))

    missing = []
    for text in _DOLLARS.findall(answer):
        amount = round(float(text.replace(",", "")), 2)
        if amount not in known:
            missing.append(f"${text}")
    return missing


def ask(question: str, llm: LlmCall | None = None) -> ChatResult:
    """Answer a question about the saved hotels. See the module contract."""
    llm = llm or llm_client.generate  # looked up now, so a test can replace it
    question = (question or "").strip()
    if not MIN_QUESTION <= len(question) <= MAX_QUESTION:
        raise InvalidQuestionError()

    system = QUERY_SYSTEM.format(schema=retrieval.schema_context())
    request = question
    sql: str | None = None
    reason: str | None = None
    found: retrieval.Retrieval | None = None
    attempts = 0

    def result(status: str, answer: str, notes: tuple[str, ...] = ()) -> ChatResult:
        return ChatResult(
            status=status,
            question=question,
            proposed_sql=sql,
            reason=reason,
            columns=found.columns if found else (),
            rows=found.rows if found else (),
            truncated=found.truncated if found else False,
            answer=answer,
            notes=notes,
            attempts=attempts,
        )

    while attempts < MAX_ATTEMPTS:
        attempts += 1
        sql, reason = _parse_proposal(llm(system, request, True))

        if sql is None:
            return result(
                STATUS_INSUFFICIENT,
                "The saved hotel data cannot answer that. "
                + (reason or "It is not about the saved hotels, their rates, or their rooms."),
            )

        try:
            found = retrieval.run_query(sql)
            break
        except retrieval.QueryRejectedError as exc:
            return result(
                STATUS_REJECTED,
                "The query the model proposed was not allowed, so it was not run and nothing was changed.",
                (str(exc),),
            )
        except retrieval.QueryFailedError as exc:
            if attempts >= MAX_ATTEMPTS:
                return result(STATUS_QUERY_FAILED, "The model's query could not be run, even after a second try.", (str(exc),))
            # One chance to adjust: show the model what went wrong with its own query.
            request = f"{question}\n\nYour previous query was:\n{sql}\nIt failed: {exc}\nWrite a corrected query."

    if not found.rows:
        return result(
            STATUS_NO_MATCH,
            "No saved hotel matches that. Nothing was retrieved, so there is nothing to base an answer on.",
        )

    answer = llm(ANSWER_SYSTEM, _records_prompt(question, sql, reason, found), False).strip()
    notes: list[str] = []
    if found.truncated:
        notes.append(f"Only the first {retrieval.MAX_ROWS} matching rows were retrieved.")
    unverified = _unverified_amounts(answer, found)
    if unverified:
        notes.append(
            "These amounts in the answer do not appear in the retrieved records, so check them: "
            + ", ".join(unverified)
            + "."
        )
    return result(STATUS_ANSWERED, answer, tuple(notes))
