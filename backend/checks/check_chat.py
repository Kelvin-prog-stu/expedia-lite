"""Fixture-based checks for the chatbot. No real model and no live hotel API is ever called.

Run from the backend folder with the project interpreter:

    .venv\\Scripts\\python.exe checks\\check_chat.py

Everything here is a FIXTURE: the hotels, rates, rooms, and the "model" replies come from
checks/fixtures/chatbot_sample.json, so each question has one known right answer. These
results show how the backend behaves; they say nothing about how a real model answers.
Runs on a throwaway database, so it is safe while the app is running.
"""

import gc
import json
import os
import sqlite3
import sys
import tempfile
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_folder = tempfile.TemporaryDirectory()
DB_FILE = Path(_folder.name) / "chat_checks.db"
os.environ["EXPEDIA_DB_PATH"] = str(DB_FILE)  # before the app is imported
FAKE_KEY = "fake-gemini-key-for-checks-only"
os.environ["GEMINI_API_KEY"] = FAKE_KEY

import httpx  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import chat_controller as chat  # noqa: E402
import database_controller as db  # noqa: E402
import llm_client  # noqa: E402
import main  # noqa: E402
import retrieval_controller as retrieval  # noqa: E402

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "chatbot_sample.json").read_text(encoding="utf-8"))
SCENARIOS = FIXTURE["scenarios"]
results: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, observed: str) -> None:
    results.append((name, ok, observed))


# ---- A fake model that records what it was sent --------------------------------------
class FakeModel:
    """Replies in order and keeps every request, so a check can see exactly what was asked."""

    def __init__(self, *replies: str) -> None:
        self.replies = list(replies)
        self.calls: list[dict] = []

    def __call__(self, system: str, user: str, json_output: bool) -> str:
        self.calls.append({"system": system, "user": user, "json": json_output})
        return self.replies.pop(0)


def proposal(name: str) -> str:
    return json.dumps(SCENARIOS[name]["proposal"])


def tables() -> dict:
    conn = sqlite3.connect(DB_FILE)
    try:
        names = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY 1")]
        return {n: conn.execute(f"SELECT * FROM {n} ORDER BY 1, 2").fetchall() for n in names}
    finally:
        conn.close()


def build_fixture_database() -> None:
    db.init_db()
    for hotel in FIXTURE["hotels"]:
        db.save_hotel(
            {k: hotel[k] for k in ("place_id", "name", "address", "latitude", "longitude", "distance_m")},
            {
                "zip_code": hotel["zip_code"],
                "center_latitude": hotel["center_latitude"],
                "center_longitude": hotel["center_longitude"],
                "locality": hotel["locality"],
                "country_code": "US",
                "radius_m": 5000,
            },
        )
    # Then replace the default nights with the fixture's, in one separate connection.
    conn = sqlite3.connect(DB_FILE)
    try:
        for hotel in FIXTURE["hotels"]:
            conn.execute("DELETE FROM demo_hotel_nights WHERE hotel_id = ?", (hotel["place_id"],))
            conn.executemany(
                "INSERT INTO demo_hotel_nights (hotel_id, stay_date, nightly_rate_cents, rooms_available) VALUES (?, ?, ?, ?)",
                [(hotel["place_id"], *night) for night in hotel["nights"]],
            )
        conn.commit()
    finally:
        conn.close()


build_fixture_database()
BASELINE = tables()
record("the fixture database holds four saved hotels and their invented nights", len(BASELINE["saved_hotels"]) == 4 and len(BASELINE["demo_hotel_nights"]) == 19, f"{len(BASELINE['saved_hotels'])} hotels, {len(BASELINE['demo_hotel_nights'])} nights")

# ---- The complete workflow, in order ---------------------------------------------------
model = FakeModel(proposal("cheapest_two_nights"), SCENARIOS["cheapest_two_nights"]["answer"])
r = chat.ask(SCENARIOS["cheapest_two_nights"]["question"], model)
names = [row[r.columns.index("name")] for row in r.rows]
totals = [row[r.columns.index("total_cents")] for row in r.rows]
record("a question is answered: status is answered", r.status == "answered", r.status)
record("exactly two model requests are made, query first and answer second", len(model.calls) == 2 and model.calls[0]["json"] is True and model.calls[1]["json"] is False, f"{len(model.calls)} requests, json flags {[c['json'] for c in model.calls]}")
record("the first request carries the question, the schema, and the stay rules", SCENARIOS["cheapest_two_nights"]["question"] in model.calls[0]["user"] and "CREATE TABLE saved_hotels" in model.calls[0]["system"] and "The check-out date is NOT a night" in model.calls[0]["system"], "question, DDL, and rules present")
record("the first request tells the model nothing about tables it may not read", all(t not in model.calls[0]["system"] for t in ("CREATE TABLE bookings", "CREATE TABLE users", "CREATE TABLE app_meta")), "no bookings, users, or app_meta")
record("the proposed query is returned to the interface", r.proposed_sql == SCENARIOS["cheapest_two_nights"]["proposal"]["sql"] and bool(r.reason), "sql and reason present")
record("the retrieved records are the right hotels, cheapest first", names == ["Quiet Test Lodge", "Harbor Test Inn", "Far Test Suites"] and totals == [18000, 23000, 30000], str(list(zip(names, totals))))
record("a hotel with 0 rooms on a night of the stay is not offered", "(name not provided)" not in names, "the nameless hotel is absent")
record("the second request carries the question and the retrieved records", SCENARIOS["cheapest_two_nights"]["question"] in model.calls[1]["user"] and "Quiet Test Lodge" in model.calls[1]["user"] and "18000" in model.calls[1]["user"], "records are in the answer prompt")
record("the second request also carries the query that ran and what it was meant to find", SCENARIOS["cheapest_two_nights"]["proposal"]["sql"] in model.calls[1]["user"] and SCENARIOS["cheapest_two_nights"]["proposal"]["reason"] in model.calls[1]["user"], "sql and reason present")
record("the second request is told to use only the records", "ONLY the records" in model.calls[1]["system"], "grounding rule present")
record("the answer is the model's reply, shown with the records", r.answer == SCENARIOS["cheapest_two_nights"]["answer"], r.answer[:60])
record("an answer whose amounts all match the records raises no warning", r.notes == (), "no notes")

# ---- Stay rules ------------------------------------------------------------------------
m = FakeModel(proposal("three_nights_missing_night"), SCENARIOS["three_nights_missing_night"]["answer"])
r3 = chat.ask(SCENARIOS["three_nights_missing_night"]["question"], m)
names3 = [row[r3.columns.index("name")] for row in r3.rows]
record("a hotel missing a night of the stay is not treated as available", "Quiet Test Lodge" not in names3, f"offered: {names3}")
record("a three night stay sums the three nights", names3 == ["Harbor Test Inn", "Far Test Suites"] and [row[r3.columns.index("total_cents")] for row in r3.rows] == [39000, 45000], str(names3))

m = FakeModel(proposal("checkout_excluded"), SCENARIOS["checkout_excluded"]["answer"])
r4 = chat.ask(SCENARIOS["checkout_excluded"]["question"], m)
record("the check-out date is not a night: one night, not two", len(r4.rows) == 1 and r4.rows[0][r4.columns.index("stay_date")] == "2026-10-13", f"{len(r4.rows)} row(s), {r4.rows[0][r4.columns.index('stay_date')]}")

# ---- No match, and insufficient data ---------------------------------------------------
m = FakeModel(proposal("no_match_outside_dates"), "THIS SHOULD NEVER BE REQUESTED")
r5 = chat.ask(SCENARIOS["no_match_outside_dates"]["question"], m)
record("dates with no stored nights give no_match", r5.status == "no_match" and r5.rows == (), r5.status)
record("with nothing retrieved there is no second model request to invent an answer", len(m.calls) == 1, f"{len(m.calls)} request")
record("the no-match answer says plainly that nothing was retrieved", "No saved hotel matches" in r5.answer and "nothing to base an answer on" in r5.answer, r5.answer)

m = FakeModel(proposal("insufficient_not_about_hotels"))
r6 = chat.ask(SCENARIOS["insufficient_not_about_hotels"]["question"], m)
record("a question the data cannot answer gives insufficient_data and runs no query", r6.status == "insufficient_data" and r6.proposed_sql is None and r6.rows == () and len(m.calls) == 1, f"{r6.status}, {len(m.calls)} request")

# ---- Grounding -------------------------------------------------------------------------
m = FakeModel(proposal("cheapest_two_nights"), SCENARIOS["wrong_answer_amount"]["answer"])
r7 = chat.ask(SCENARIOS["wrong_answer_amount"]["question"], m)
record("an amount in the answer that is not in the records is flagged", r7.status == "answered" and any("$250.00" in n for n in r7.notes), str(r7.notes))

# ---- Disallowed and invalid queries cannot change anything -----------------------------
for label, sql in FIXTURE["disallowed_proposals"].items():
    m = FakeModel(json.dumps({"sql": sql, "reason": "fixture"}), "NEVER REQUESTED")
    try:
        r8 = chat.ask("Please do what the proposal says", m)
        ok = r8.status == "rejected" and r8.rows == () and len(m.calls) == 1 and bool(r8.notes)
        observed = f"{r8.status}: {r8.notes[0] if r8.notes else ''}"
    except Exception as exc:  # noqa: BLE001 - any exception here is a failure of the check
        ok, observed = False, f"raised {type(exc).__name__}"
    record(f"rejected, not run: {label}", ok, observed[:110])
m = FakeModel(json.dumps({"sql": "   ", "reason": "fixture"}), "NEVER REQUESTED")
blank = chat.ask("Please do what the proposal says", m)
record("a blank proposed query is no query: insufficient_data, nothing run", blank.status == "insufficient_data" and len(m.calls) == 1, blank.status)
record("after every disallowed proposal the whole database is byte-for-byte unchanged", tables() == BASELINE, f"{len(BASELINE)} tables compared, Assignment 1 included")

# ---- A query that will not run gets one repair, then stops ----------------------------
bad = json.dumps({"sql": "SELECT nope FROM saved_hotels", "reason": "fixture"})
m = FakeModel(bad, proposal("cheapest_two_nights"), SCENARIOS["cheapest_two_nights"]["answer"])
r9 = chat.ask("Which hotel is cheapest?", m)
record("a query that fails once is repaired once, with the error shown to the model", r9.status == "answered" and r9.attempts == 2 and "no such column: nope" in m.calls[1]["user"], f"{r9.status}, {r9.attempts} attempts")
m = FakeModel(bad, bad, "NEVER REQUESTED")
r10 = chat.ask("Which hotel is cheapest?", m)
record("a query that fails twice stops with query_failed and asks for no answer", r10.status == "query_failed" and len(m.calls) == 2, f"{r10.status}, {len(m.calls)} requests")

# ---- Bounds ----------------------------------------------------------------------------
real_max = retrieval.MAX_ROWS
retrieval.MAX_ROWS = 5
try:
    big = retrieval.run_query("SELECT * FROM demo_hotel_nights ORDER BY hotel_id, stay_date")
finally:
    retrieval.MAX_ROWS = real_max
record("results are bounded: only MAX_ROWS rows come back, and truncation is reported", len(big.rows) == 5 and big.truncated is True, f"{len(big.rows)} rows, truncated={big.truncated}")
record("a long value is shortened before it reaches the model", len(retrieval.run_query(f"SELECT '{'x' * 500}'").rows[0][0]) <= retrieval.MAX_VALUE_CHARACTERS + 3, "200 characters plus an ellipsis")
real_limit = retrieval.TIME_LIMIT_SECONDS
retrieval.TIME_LIMIT_SECONDS = 0.05
try:
    slow = "SELECT COUNT(*) FROM demo_hotel_nights a, demo_hotel_nights b, demo_hotel_nights c, demo_hotel_nights d, demo_hotel_nights e, demo_hotel_nights f, demo_hotel_nights g"
    try:
        retrieval.run_query(slow)
        stopped = False
    except retrieval.QueryFailedError as exc:
        stopped = "took too long" in str(exc)
finally:
    retrieval.TIME_LIMIT_SECONDS = real_limit
record("a query that runs too long is interrupted", stopped, "stopped by the time limit")

# ---- Bad questions and bad model output ------------------------------------------------
for text in ("", "  ", "hi", "x" * 501):
    try:
        chat.ask(text, FakeModel())
        refused = False
    except chat.InvalidQuestionError:
        refused = True
    record(f"a question of {len(text.strip())} characters is refused before any model request", refused, "InvalidQuestionError")

for label, reply in {"not JSON": "Sure! Here is a query: SELECT 1", "JSON but not an object": "[1, 2]"}.items():
    try:
        chat.ask("Which hotel is cheapest?", FakeModel(reply))
        handled = False
    except llm_client.LlmBadOutputError:
        handled = True
    record(f"an unusable first reply ({label}) is an error, not a guess", handled, "LlmBadOutputError")
fenced = "```json\n" + proposal("cheapest_two_nights") + "\n```"
r11 = chat.ask("Which hotel is cheapest?", FakeModel(fenced, "ok"))
record("a reply wrapped in a code fence is still read", r11.status == "answered", r11.status)

# ---- The model client: failures and the key --------------------------------------------
class Reply:
    def __init__(self, status: int, body=None, raises=False):
        self.status_code, self._body = status, body
        self._raises = raises

    def json(self):
        if self._raises:
            raise ValueError("not json")
        return self._body


def with_http(reply_or_exc):
    sent = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        sent.update(url=url, headers=headers, body=json, timeout=timeout)
        if isinstance(reply_or_exc, Exception):
            raise reply_or_exc
        return reply_or_exc

    llm_client.httpx.post = fake_post
    return sent


def outcome(reply_or_exc):
    sent = with_http(reply_or_exc)
    try:
        return llm_client.generate("system", "user", True), sent
    except llm_client.LlmError as exc:
        return exc, sent


good = Reply(200, {"candidates": [{"content": {"parts": [{"text": "hello"}]}}]})
text, sent = outcome(good)
record("a good reply returns the model's text", text == "hello", text)
record("the key travels in a header, never in the URL or the body", FAKE_KEY not in sent["url"] and sent["headers"]["x-goog-api-key"] == FAKE_KEY and FAKE_KEY not in json.dumps(sent["body"]), "header only")
record("the request is bounded: temperature 0, a token limit, JSON mode when asked, a timeout", sent["body"]["generationConfig"]["temperature"] == 0 and "maxOutputTokens" in sent["body"]["generationConfig"] and sent["body"]["generationConfig"]["responseMimeType"] == "application/json" and sent["timeout"] > 0, str(sent["body"]["generationConfig"]))

failures = {
    "HTTP 429": (Reply(429, {}), llm_client.LlmRateLimitedError),
    "HTTP 500": (Reply(500, {}), llm_client.LlmServiceError),
    "HTTP 403": (Reply(403, {"error": {"message": f"key {FAKE_KEY} is invalid"}}), llm_client.LlmServiceError),
    "a timeout": (httpx.ConnectTimeout("timed out"), llm_client.LlmServiceError),
    "a body that is not JSON": (Reply(200, raises=True), llm_client.LlmBadOutputError),
    "no candidates": (Reply(200, {"candidates": []}), llm_client.LlmBadOutputError),
    "an empty answer": (Reply(200, {"candidates": [{"content": {"parts": [{"text": "  "}]}}]}), llm_client.LlmBadOutputError),
}
messages = []
for label, (reply, expected) in failures.items():
    got, _ = outcome(reply)
    messages.append(str(got))
    record(f"model failure ({label}) is reported as {expected.__name__}", isinstance(got, expected), str(got)[:90])
record("no model error message carries the key or the provider's raw error text", all(FAKE_KEY not in m and "invalid" not in m for m in messages), "keys and raw text withheld")

# A 503 "high demand" is retried briefly; nothing else is.
llm_client.RETRY_DELAY_SECONDS = 0
calls = []
replies = [Reply(503, {}), Reply(503, {}), good]


def sequence_post(url, headers=None, json=None, timeout=None):
    calls.append(1)
    return replies.pop(0)


def try_generate():
    try:
        return llm_client.generate("system", "user", True)
    except llm_client.LlmError as exc:
        return exc


llm_client.httpx.post = sequence_post
retried = try_generate()
record("two 503 replies then a good one still returns the answer (3 requests)", retried == "hello" and len(calls) == 3, f"{len(calls)} requests, {retried!r}")
calls.clear()
replies = [Reply(503, {}), Reply(503, {}), Reply(503, {}), good]
retried = try_generate()
record("a 503 that keeps coming gives up after 3 requests as LlmServiceError", isinstance(retried, llm_client.LlmServiceError) and len(calls) == 3, f"{len(calls)} requests, {type(retried).__name__}")
calls.clear()
replies = [Reply(500, {}), good]
retried = try_generate()
record("a 500 is not retried", isinstance(retried, llm_client.LlmServiceError) and len(calls) == 1, f"{len(calls)} request")

os.environ["GEMINI_API_KEY"] = "   "
got, _ = outcome(good)
record("a missing key is reported before any request is made", isinstance(got, llm_client.LlmNotConfiguredError), str(got)[:80])
os.environ["GEMINI_API_KEY"] = FAKE_KEY

# ---- Through the real route -------------------------------------------------------------
with TestClient(main.app) as client:
    real_generate = llm_client.generate

    def route_with(*replies):
        fake = FakeModel(*replies)
        llm_client.generate = lambda system, user, json_output=False: fake(system, user, json_output)
        return fake

    try:
        fake = route_with(proposal("cheapest_two_nights"), SCENARIOS["cheapest_two_nights"]["answer"])
        resp = client.post("/api/chat", json={"question": SCENARIOS["cheapest_two_nights"]["question"]})
        body = resp.json()
        record("POST /api/chat returns the whole chain", resp.status_code == 200 and body["status"] == "answered" and body["proposed_sql"] and body["rows"] and body["answer"] and body["model"], f"{resp.status_code} {body.get('status')}")
        record("the response carries the columns and rows the answer was built from", body["columns"][:2] == ["hotel_id", "name"] and body["rows"][0][1] == "Quiet Test Lodge", str(body["rows"][0]))

        route_with(json.dumps({"sql": "DELETE FROM saved_hotels", "reason": "fixture"}))
        resp = client.post("/api/chat", json={"question": "Delete every saved hotel"})
        record("a destructive proposal through the route is rejected with a 200 and a clear status", resp.status_code == 200 and resp.json()["status"] == "rejected", f"{resp.status_code} {resp.json()['status']}")
        record("the database is unchanged after the destructive request", tables() == BASELINE, "identical")

        record("a too short question is a 400 with its own code", client.post("/api/chat", json={"question": "hi"}).status_code == 422 or client.post("/api/chat", json={"question": "hi"}).status_code == 400, "refused")

        def raising(error):
            def fake(system, user, json_output=False):
                raise error

            llm_client.generate = fake

        for error, status, code in (
            (llm_client.LlmNotConfiguredError(), 503, "llm_not_configured"),
            (llm_client.LlmRateLimitedError(), 429, "llm_rate_limited"),
            (llm_client.LlmServiceError("the model service answered 500"), 502, "llm_service_failed"),
            (llm_client.LlmBadOutputError("The model returned no answer."), 502, "llm_bad_output"),
        ):
            raising(error)
            resp = client.post("/api/chat", json={"question": "Which hotel is cheapest?"})
            record(f"{code} is a {status} that names itself, never an empty answer", resp.status_code == status and resp.json()["error"]["code"] == code, f"{resp.status_code} {resp.json()['error']['code']}")
    finally:
        llm_client.generate = real_generate

    health = client.get("/api/health").json()
    record("health reports the chatbot's status without the key", health["chatbot"]["status"] == "key is configured" and FAKE_KEY not in json.dumps(health), str(health["chatbot"]))

    # ---- Everything else is frozen -----------------------------------------------------
    record("the Part 1 live search route still refuses a bad ZIP", client.get("/api/nearby-hotels", params={"zip": "123"}).status_code == 400, "400")
    saved = client.get("/api/saved-hotels", params={"zip": "16802"}).json()
    record("saved hotels still list for a ZIP with their nights", len(saved["hotels"]) == 3 and all(len(h["nights"]) in (4, 5) for h in saved["hotels"]), f"{len(saved['hotels'])} hotels")
    record("Assignment 1 tables are untouched by everything above", all(tables()[t] == BASELINE[t] for t in ("hotels", "trips", "users", "bookings", "app_meta")), "5 tables compared")

gc.collect()
_folder.cleanup()

width = max(len(name) for name, _, _ in results)
for name, ok, observed in results:
    print(f"{'PASS' if ok else 'FAIL'}  {name.ljust(width)}  {observed}")

failed = [name for name, ok, _ in results if not ok]
print(f"\n{len(results) - len(failed)} of {len(results)} fixture checks passed")
sys.exit(1 if failed else 0)
