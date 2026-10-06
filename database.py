"""Bounded read-only SQLite queries, independent of model instructions."""
import re
import sqlite3
from pathlib import Path
from time import monotonic
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from config import DATABASE_URL

MAX_ROWS = 200
QUERY_SECONDS = 2
ALLOWED_FUNCTIONS = {
    "abs", "avg", "coalesce", "count", "date", "datetime", "group_concat", "ifnull",
    "instr", "julianday", "length", "lower", "ltrim", "max", "min", "nullif", "replace",
    "round", "rtrim", "strftime", "substr", "substring", "sum", "time", "total", "trim",
    "typeof", "upper", "row_number", "rank", "dense_rank", "lag", "lead", "ntile",
}


def database_path():
    url = make_url(DATABASE_URL)
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        raise ValueError("This demo supports a file-backed SQLite database only.")
    return Path(url.database).resolve()


def read_connection():
    connection = sqlite3.connect(database_path().as_uri() + "?mode=ro", uri=True, timeout=2)
    connection.execute("PRAGMA query_only = ON")
    connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 100_000)
    return connection


def get_engine():
    # SQLAlchemy reflection needs PRAGMA; query execution uses a stricter authorizer below.
    return create_engine("sqlite://", creator=read_connection)


def run_query(sql):
    if not isinstance(sql, str) or len(sql) > 8000 or not re.match(r"^\s*(SELECT|WITH)\b", sql, re.I):
        raise ValueError("Only a single read-only SELECT query is supported.")
    deadline = monotonic() + QUERY_SECONDS
    operations = 0

    def progress():
        nonlocal operations
        operations += 1000
        return int(monotonic() > deadline or operations > 1_000_000)

    def authorize(action, arg1, arg2, db, trigger):
        if action == sqlite3.SQLITE_FUNCTION:
            return sqlite3.SQLITE_OK if (arg2 or "").lower() in ALLOWED_FUNCTIONS else sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK if action in {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_RECURSIVE} else sqlite3.SQLITE_DENY

    connection = read_connection()
    try:
        connection.set_authorizer(authorize)
        connection.set_progress_handler(progress, 1000)
        cursor = connection.execute(sql)
        rows = cursor.fetchmany(MAX_ROWS + 1)
        if len(rows) > MAX_ROWS:
            raise ValueError("The query returned more than 200 rows. Ask for a smaller result or a summary.")
        return pd.DataFrame(rows, columns=[item[0] for item in cursor.description])
    except sqlite3.Error as exc:
        if "interrupted" in str(exc):
            raise ValueError("The query was too expensive. Please narrow your question.") from None
        raise ValueError("The query could not run. Only a single read-only query using supported functions is allowed.") from None
    finally:
        connection.close()


def test_connection():
    try:
        connection = read_connection()
        connection.execute("SELECT 1")
        connection.close()
        return True
    except Exception:
        return False
