"""Controller for the chatbot's retrieval: it runs a model-proposed SQL query, safely.

The remote model never touches SQLite. It proposes SQL as text, and this module decides
whether to run it. That text is untrusted, so nothing here depends on recognising bad SQL
by its shape. Four independent layers each have to agree:

1. **A read-only connection.** The file is opened with `mode=ro` and `PRAGMA query_only`,
   so even a statement that got through could not write.
2. **SQLite's authorizer.** SQLite asks it about every action, table, column, and function
   while it prepares the statement. Only SELECT, reads of the three allowed tables, and a
   short list of plain functions are permitted. DELETE, UPDATE, INSERT, DROP, PRAGMA, ATTACH,
   load_extension, recursive queries, and every other table (bookings, users, app_meta, the
   sqlite_master catalogue) are refused before anything runs.
3. **A shape check.** One statement, starting with SELECT or WITH, no comments, bounded length.
4. **Bounds.** At most MAX_ROWS rows come back, long values are shortened, and a query that
   runs longer than TIME_LIMIT_SECONDS is interrupted.

Contract for `run_query`:

- **Input:** the proposed SQL text.
- **Output:** a `Retrieval` with the column names, the rows, and whether more rows existed.
- **Failure:** `QueryRejectedError` when the query is not allowed (it was not run), and
  `QueryFailedError` when it is allowed but does not work, such as a misspelt column. A
  storage failure (a locked database) is not caught here: it is a different kind of problem.
"""

import sqlite3
import time
from dataclasses import dataclass

import database_controller as db

ALLOWED_TABLES = ("saved_hotels", "saved_hotel_zips", "demo_hotel_nights")
ALLOWED_FUNCTIONS = frozenset(
    {
        "count", "sum", "min", "max", "avg", "total", "round", "abs", "coalesce", "ifnull",
        "nullif", "iif", "lower", "upper", "length", "trim", "ltrim", "rtrim", "substr",
        "replace", "instr", "printf", "group_concat", "date", "julianday", "strftime",
        "typeof", "cast", "like", "glob",
    }
)
MAX_ROWS = 50
MAX_SQL_CHARACTERS = 4000
MAX_VALUE_CHARACTERS = 200
TIME_LIMIT_SECONDS = 3.0

# Friendly names for the actions the authorizer is asked about. Anything not listed is
# reported by number, and refused all the same.
_ACTION_NAMES = {
    1: "CREATE INDEX", 2: "CREATE TABLE", 9: "DELETE", 11: "DROP TABLE", 18: "INSERT",
    19: "PRAGMA", 23: "UPDATE", 24: "ATTACH DATABASE", 25: "DETACH DATABASE",
    26: "ALTER TABLE", 27: "REINDEX", 28: "ANALYZE", 29: "CREATE VIRTUAL TABLE",
    30: "DROP VIRTUAL TABLE", 31: "FUNCTION", 32: "SAVEPOINT", 33: "RECURSIVE",
}
_SELECT, _READ, _FUNCTION, _RECURSIVE = 21, 20, 31, 33


class QueryRejectedError(Exception):
    """The query is not allowed. It was not run."""


class QueryFailedError(Exception):
    """The query is allowed but could not run, for example a column that does not exist."""


@dataclass(frozen=True)
class Retrieval:
    columns: tuple[str, ...]
    rows: tuple[tuple, ...]
    truncated: bool


def _read_only_connection() -> sqlite3.Connection:
    uri = db.DB_PATH.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.execute("PRAGMA query_only = ON")
    return conn


def _check_shape(sql: object) -> str:
    """The statement to run, or a QueryRejectedError saying why not."""
    if not isinstance(sql, str) or not sql.strip():
        raise QueryRejectedError("The proposed query was empty.")
    statement = sql.strip()
    if len(statement) > MAX_SQL_CHARACTERS:
        raise QueryRejectedError(f"The proposed query is longer than {MAX_SQL_CHARACTERS} characters.")
    if statement.endswith(";"):
        statement = statement[:-1].strip()
    if "--" in statement or "/*" in statement:
        raise QueryRejectedError("Comments are not allowed in a proposed query.")
    if ";" in statement:
        raise QueryRejectedError("Only one statement is allowed.")
    if statement.split(None, 1)[0].lower() not in ("select", "with"):
        raise QueryRejectedError("Only a SELECT query is allowed.")
    return statement


def _make_authorizer(denials: list[str]):
    """An authorizer that allows reading the allowed tables and nothing else."""

    def authorize(action, arg1, arg2, database, trigger):
        if action == _SELECT:
            return sqlite3.SQLITE_OK
        if action == _READ:
            if arg1 in ALLOWED_TABLES:
                return sqlite3.SQLITE_OK
            denials.append(f"Reading '{arg1}' is not allowed. Only {', '.join(ALLOWED_TABLES)} can be read.")
            return sqlite3.SQLITE_DENY
        if action == _FUNCTION:
            if (arg2 or "").lower() in ALLOWED_FUNCTIONS:
                return sqlite3.SQLITE_OK
            denials.append(f"The function '{arg2}' is not allowed.")
            return sqlite3.SQLITE_DENY
        if action == _RECURSIVE:
            denials.append("Recursive queries are not allowed.")
            return sqlite3.SQLITE_DENY
        name = _ACTION_NAMES.get(action, f"action {action}")
        denials.append(f"{name} is not allowed. This chatbot can only read.")
        return sqlite3.SQLITE_DENY

    return authorize


def _shorten(value: object) -> object:
    if isinstance(value, bytes):
        return "(binary data)"
    if isinstance(value, str) and len(value) > MAX_VALUE_CHARACTERS:
        return value[:MAX_VALUE_CHARACTERS] + "..."
    return value


def run_query(sql: object) -> Retrieval:
    """Run a model-proposed query if, and only if, every layer allows it."""
    statement = _check_shape(sql)

    denials: list[str] = []
    conn = _read_only_connection()
    try:
        conn.set_authorizer(_make_authorizer(denials))
        deadline = time.monotonic() + TIME_LIMIT_SECONDS
        conn.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 20_000)
        try:
            cursor = conn.execute(statement)
            fetched = cursor.fetchmany(MAX_ROWS + 1)
            columns = tuple(column[0] for column in cursor.description or ())
        except sqlite3.DatabaseError as exc:
            if denials:
                raise QueryRejectedError(denials[0]) from None
            message = str(exc)
            if "locked" in message or "unable to open" in message or "disk I/O" in message:
                raise  # a storage problem, not a bad query
            if "interrupted" in message:
                raise QueryFailedError("The query took too long and was stopped.") from None
            raise QueryFailedError(f"The query could not run: {message}.") from None
        except sqlite3.Warning as exc:
            raise QueryRejectedError("Only one statement is allowed.") from exc
    finally:
        conn.close()

    if denials:
        raise QueryRejectedError(denials[0])

    rows = tuple(tuple(_shorten(value) for value in row) for row in fetched[:MAX_ROWS])
    return Retrieval(columns=columns, rows=rows, truncated=len(fetched) > MAX_ROWS)


def schema_context() -> str:
    """The part of the schema the model may query, plus what data is actually stored.

    Built from the live database so it cannot drift from the real tables, and limited to
    the three allowed tables so the model is never told about the others.
    """
    with db.get_connection() as conn:
        ddl = [
            row["sql"]
            for row in conn.execute(
                f"SELECT sql FROM sqlite_master WHERE type = 'table' AND name IN ({','.join('?' * len(ALLOWED_TABLES))})",
                ALLOWED_TABLES,
            )
        ]
        hotels = conn.execute("SELECT COUNT(*) FROM saved_hotels").fetchone()[0]
        nights = conn.execute(
            "SELECT COUNT(*), MIN(stay_date), MAX(stay_date) FROM demo_hotel_nights"
        ).fetchone()
        zips = [row[0] for row in conn.execute("SELECT DISTINCT zip_code FROM saved_hotel_zips ORDER BY 1")]

    coverage = (
        f"There are {nights[0]} stored nights from {nights[1]} to {nights[2]}."
        if nights[0]
        else "There are no stored nights."
    )
    return (
        "\n\n".join(ddl)
        + f"\n\nWhat is stored right now: {hotels} saved hotel(s). {coverage} "
        + f"ZIP codes with saved hotels: {', '.join(zips) if zips else 'none'}."
    )
