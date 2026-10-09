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

- **Input:** a question of 3 to 500 characters, optionally the function that calls the model
  (the real client by default, a fixture in tests), and optionally the id of a conversation to
  continue. A new id is made when none is given.
- **Output:** a `ChatResult` whose `status` is one of `answered`, `no_match`,
  `insufficient_data`, `rejected`, or `query_failed`. Every step is also saved in
  `chat_messages` as it happens: the question, the proposed query, the executed query, the
  retrieval result, notes, and the answer or the error. A model failure saves its error and
  no answer.
- **Prompts:** read from `prompts/hotel-assistant.md` once, when the backend starts.
- **Failure:** `InvalidQuestionError` for a question that is too short or too long, and the
  `LlmError` family from `llm_client` when the model cannot be reached.
"""

import hashlib
import json
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import database_controller as db
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

PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompts" / "hotel-assistant.md"
SCHEMA_TOKEN = "<<SCHEMA>>"
HISTORY_TURNS = 3  # earlier exchanges shown to the model so a follow-up question makes sense


def _load_prompts(path: Path) -> tuple[str, str, str]:
    """(query prompt, answer prompt, version) from the prompt file.

    Read once when the backend starts, so edit the file and restart. The version is the first
    12 characters of the file's SHA-256 and is saved with every chat message.
    """
    raw = path.read_bytes()
    sections: dict[str, str] = {}
    name = None
    for line in raw.decode("utf-8").splitlines():
        if line.startswith("## "):
            name = line[3:].strip().lower()
            sections[name] = ""
        elif name is not None:
            sections[name] += line + "\n"
    try:
        purpose = sections["purpose"].strip()
        query = f"{purpose}\n\n{sections['query stage'].strip()}"
        answer = f"{purpose}\n\n{sections['answer stage'].strip()}"
    except KeyError as exc:
        raise RuntimeError(f"{path.name} is missing its '## {exc.args[0].title()}' section.") from None
    if SCHEMA_TOKEN not in query:
        raise RuntimeError(f"{path.name} must contain {SCHEMA_TOKEN} in its query stage.")
    return query, answer, hashlib.sha256(raw).hexdigest()[:12]


QUERY_SYSTEM, ANSWER_SYSTEM, PROMPT_VERSION = _load_prompts(PROMPT_FILE)


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
    conversation_id: str


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


def _history_turns(conversation_id: str) -> list[dict]:
    """A saved conversation as one dict per question, oldest first."""
    turns: list[dict] = []
    for message in db.list_chat_messages(conversation_id):
        stage, content = message["stage"], message["content"]
        if stage == "question":
            turns.append(
                {
                    "message_id": message["message_id"],
                    "created_at": message["created_at"],
                    "status": "pending",
                    "question": content,
                    "proposed_sql": None,
                    "reason": None,
                    "columns": [],
                    "rows": [],
                    "truncated": False,
                    "answer": "",
                    "notes": [],
                    "attempts": 0,
                    "prompt_version": message["prompt_version"],
                }
            )
            continue
        if not turns:
            continue
        turn = turns[-1]
        if stage == "proposed_sql":
            proposal = json.loads(content)
            turn["proposed_sql"], turn["reason"] = proposal.get("sql"), proposal.get("reason")
            turn["attempts"] += 1
        elif stage == "retrieval_result":
            found = json.loads(content)
            turn["columns"], turn["rows"], turn["truncated"] = found["columns"], found["rows"], found["truncated"]
        elif stage == "notes":
            turn["notes"] = json.loads(content)
        elif stage in ("answer", "error"):
            turn["status"] = message["status"] or ("error" if stage == "error" else "answered")
            turn["answer"] = content
    for turn in turns:
        if turn["status"] == "pending":
            turn["status"] = "error"
            turn["answer"] = "This question was saved but no answer was recorded."
    return turns


def history(conversation_id: str | None = None) -> tuple[str | None, list[dict]]:
    """(conversation id, turns) for the given conversation, or the most recent one."""
    conversation_id = conversation_id or db.latest_conversation_id()
    if conversation_id is None:
        return None, []
    return conversation_id, _history_turns(conversation_id)


def _earlier_context(conversation_id: str) -> str:
    """The last few exchanges, as plain text for the first request, or an empty string."""
    turns = [t for t in _history_turns(conversation_id) if t["status"] != "error"][-HISTORY_TURNS:]
    if not turns:
        return ""
    lines = ["Earlier in this conversation (oldest first):"]
    for turn in turns:
        lines.append(f"- The traveler asked: {turn['question']}")
        if turn["proposed_sql"]:
            lines.append(f"  The query run was: {turn['proposed_sql']}")
        lines.append(f"  The answer given was: {turn['answer']}")
    return "\n".join(lines) + "\n\nNew question: "


def ask(question: str, llm: LlmCall | None = None, conversation_id: str | None = None) -> ChatResult:
    """Answer a question about the saved hotels. See the module contract."""
    llm = llm or llm_client.generate  # looked up now, so a test can replace it
    question = (question or "").strip()
    if not MIN_QUESTION <= len(question) <= MAX_QUESTION:
        raise InvalidQuestionError()

    conversation_id = conversation_id or f"conv-{uuid.uuid4().hex[:8]}"
    system = QUERY_SYSTEM.replace(SCHEMA_TOKEN, retrieval.schema_context())
    request = _earlier_context(conversation_id) + question
    sql: str | None = None
    reason: str | None = None
    found: retrieval.Retrieval | None = None
    attempts = 0

    def save(role: str, stage: str, content: str, status: str | None = None) -> None:
        db.save_chat_message(conversation_id, role, stage, content, status, PROMPT_VERSION)

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
            conversation_id=conversation_id,
        )

    def finish(status: str, answer: str, notes: tuple[str, ...] = (), stage: str = "answer") -> ChatResult:
        """Save the closing step, then return the result. An error is saved as a 'tool' step."""
        if notes:
            save("tool", "notes", json.dumps(list(notes)))
        save("assistant" if stage == "answer" else "tool", stage, answer, status)
        return result(status, answer, notes)

    save("user", "question", question)
    try:
        while attempts < MAX_ATTEMPTS:
            attempts += 1
            sql, reason = _parse_proposal(llm(system, request, True))
            save("assistant", "proposed_sql", json.dumps({"sql": sql, "reason": reason}))

            if sql is None:
                return finish(
                    STATUS_INSUFFICIENT,
                    "The saved hotel data cannot answer that. "
                    + (reason or "It is not about the saved hotels, their rates, or their rooms."),
                )

            try:
                found = retrieval.run_query(sql)
                break
            except retrieval.QueryRejectedError as exc:
                return finish(
                    STATUS_REJECTED,
                    "The query the model proposed was not allowed, so it was not run and nothing was changed.",
                    (str(exc),),
                    stage="error",
                )
            except retrieval.QueryFailedError as exc:
                if attempts >= MAX_ATTEMPTS:
                    return finish(
                        STATUS_QUERY_FAILED,
                        "The model's query could not be run, even after a second try.",
                        (str(exc),),
                        stage="error",
                    )
                save("tool", "error", f"The query could not run: {exc}", STATUS_QUERY_FAILED)
                # One chance to adjust: show the model what went wrong with its own query.
                request = f"{question}\n\nYour previous query was:\n{sql}\nIt failed: {exc}\nWrite a corrected query."

        save("tool", "executed_sql", sql)
        save(
            "tool",
            "retrieval_result",
            json.dumps(
                {
                    "columns": list(found.columns),
                    "rows": [list(row) for row in found.rows],
                    "row_count": len(found.rows),
                    "truncated": found.truncated,
                },
                default=str,
            ),
        )

        if not found.rows:
            return finish(
                STATUS_NO_MATCH,
                "No saved hotel matches that. Nothing was retrieved, so there is nothing to base an answer on. "
                + retrieval.coverage_summary(),
            )

        answer = llm(ANSWER_SYSTEM, _records_prompt(question, sql, reason, found), False).strip()
    except llm_client.LlmError as exc:
        # Record the failure, never a made-up reply, then let the route turn it into an HTTP error.
        save("tool", "error", str(exc), "llm_error")
        raise

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
    return finish(STATUS_ANSWERED, answer, tuple(notes))
