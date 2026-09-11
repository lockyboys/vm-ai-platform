#!/usr/bin/env python3
"""Remove NOT NULL constraints from storage-separation payload columns.

This is a preparatory schema change only.  It does not delete values, rows,
backup tables, or columns.  The corresponding MariaDB payload backup must
already be validated before --apply.
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from common.database import CommonDatabase

TARGETS = (
    ("COMMON", "cm_verified_sql_query", "sql_text", "LONGTEXT"),
    ("COMMON", "cm_code_inspection_result", "message", "TEXT"),
    ("STORY", "sp_impact_analysis_result", "change_target_text", "TEXT"),
)


def _quoted(value: str) -> str:
    return chr(96) + value + chr(96)


def _column(database: CommonDatabase, table_name: str, column_name: str) -> dict[str, Any]:
    row = database.fetch_one(
        "SHOW COLUMNS FROM " + _quoted(table_name) + " LIKE %s",
        (column_name,),
    )
    if not row:
        raise LookupError(f"Column not found: {table_name}.{column_name}")
    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    arguments = parser.parse_args()

    databases: dict[str, CommonDatabase] = {}
    results: list[dict[str, Any]] = []
    try:
        for role, table_name, column_name, column_type in TARGETS:
            database = databases.setdefault(
                role,
                CommonDatabase(database_role=role, connect_mongodb=False),
            )
            before = _column(database, table_name, column_name)
            item = {
                "database_role": role,
                "table_name": table_name,
                "column_name": column_name,
                "before_null_yn": "Y" if before.get("Null") == "YES" else "N",
                "applied": arguments.apply,
            }
            if arguments.apply and before.get("Null") != "YES":
                database.execute(
                    "ALTER TABLE " + _quoted(table_name)
                    + " MODIFY COLUMN " + _quoted(column_name)
                    + " " + column_type + " NULL"
                )
                database.commit()
            after = _column(database, table_name, column_name)
            item["after_null_yn"] = "Y" if after.get("Null") == "YES" else "N"
            results.append(item)
    finally:
        for database in databases.values():
            database.close()

    print(json.dumps({"target_count": len(results), "results": results}, ensure_ascii=False, indent=2))
    return 0 if all(item["after_null_yn"] == "Y" for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
