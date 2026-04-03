# schema_inspector.py — reads the database schema and formats it for the LLM prompt

from sqlalchemy import inspect
from database import get_engine


def get_schema_text() -> str:
    """
    Inspect all tables in the database and return a formatted schema string.
    This schema is injected into the system prompt so the LLM knows the structure.

    Example output:
        Table: customers
          - id (INTEGER)
          - name (VARCHAR)
          - email (VARCHAR)
    """
    engine = get_engine()
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    if not table_names:
        return "No tables found in the database."

    schema_lines = []

    for table in table_names:
        schema_lines.append(f"Table: {table}")
        columns = inspector.get_columns(table)

        for col in columns:
            col_name = col["name"]
            col_type = str(col["type"])
            nullable = "" if col.get("nullable", True) else " NOT NULL"
            schema_lines.append(f"  - {col_name} ({col_type}{nullable})")

        schema_lines.append("")  # blank line between tables

    return "\n".join(schema_lines)


def get_table_names() -> list[str]:
    """Return a list of all table names in the database."""
    engine = get_engine()
    inspector = inspect(engine)
    return inspector.get_table_names()
