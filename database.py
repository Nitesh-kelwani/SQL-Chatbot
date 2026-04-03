# database.py — handles database connection and query execution

import pandas as pd
from sqlalchemy import create_engine, text
from config import DATABASE_URL


def get_engine():
    """Create and return a SQLAlchemy engine using the DATABASE_URL from config."""
    return create_engine(DATABASE_URL)


def run_query(sql: str) -> pd.DataFrame:
    """
    Execute a SQL SELECT query and return results as a pandas DataFrame.
    Only SELECT statements are allowed to keep the database safe.
    """
    # Basic safety check — block any write operations
    sql_upper = sql.strip().upper()
    forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE"]
    for keyword in forbidden:
        if sql_upper.startswith(keyword):
            raise ValueError(f"Only SELECT queries are allowed. '{keyword}' is not permitted.")

    engine = get_engine()
    with engine.connect() as conn:
        result = pd.read_sql(text(sql), conn)
    return result


def test_connection() -> bool:
    """Try a simple query to verify the database is reachable."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
