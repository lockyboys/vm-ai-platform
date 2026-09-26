"""Fail closed when an SPS Repository table or field lacks its description."""
from __future__ import annotations

from collections.abc import Iterable

from common.database import CommonDatabase


def assert_schema_documented(
    database: CommonDatabase, schema_name: str, table_names: Iterable[str],
) -> dict[str, int]:
    """Read table descriptions and every column COMMENT before a related write."""
    counts = {}
    for table_name in table_names:
        table = database.fetch_one(
            """SELECT table_comment FROM information_schema.tables
               WHERE table_schema = %s AND table_name = %s""",
            (schema_name, table_name),
        )
        columns = database.fetch_all(
            """SELECT column_name, column_comment FROM information_schema.columns
               WHERE table_schema = %s AND table_name = %s""",
            (schema_name, table_name),
        )
        if not table or not str(table.get("table_comment") or "").strip():
            raise RuntimeError(f"Missing table description: {schema_name}.{table_name}")
        if not columns:
            raise RuntimeError(f"Missing field schema: {schema_name}.{table_name}")
        missing = [str(row["column_name"]) for row in columns
                   if not str(row.get("column_comment") or "").strip()]
        if missing:
            raise RuntimeError(
                f"Missing field COMMENT: {schema_name}.{table_name} ({', '.join(missing)})"
            )
        counts[table_name] = len(columns)
    return counts
