#!/usr/bin/env python3
"""Verify row counts for the eleven MariaDB storage-separation backup tables."""

from __future__ import annotations

import json
import re
from typing import Any

from common.database import CommonDatabase

IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
BACKUP_TARGETS = (
    ("COMMON", "health_report", "health_report_payload_backup_20260830"),
    ("COMMON", "sql_guard_execution_log", "sql_guard_execution_log_payload_backup_20260830"),
    ("COMMON", "sql_guard_verification_log", "sql_guard_verification_log_payload_backup_20260830"),
    ("STORY", "sp_impact_analysis_result", "sp_impact_analysis_result_payload_backup_20260830"),
    ("COMMON", "cm_verified_sql_query", "cm_verified_sql_query_payload_backup_20260902"),
    ("COMMON", "model_history", "model_history_payload_backup_20260902"),
    ("COMMON", "cm_repository", "cm_repository_payload_backup_20260902"),
    ("COMMON", "cm_storage_repository", "cm_storage_repository_payload_backup_20260902"),
    ("COMMON", "cron_logs", "cron_logs_payload_backup_20260902"),
    ("COMMON", "cm_code_inspection_result", "cm_code_inspection_result_payload_backup_20260902"),
    ("COMMON", "pipeline_results", "pipeline_results_payload_backup_20260902"),
)


def _identifier(value: str) -> str:
    if not IDENTIFIER_PATTERN.fullmatch(value):
        raise ValueError("Unsafe database identifier: " + value)
    return value


def _row_count(database: CommonDatabase, table_name: str) -> int:
    safe_table_name = _identifier(table_name)
    quoted_table_name = chr(96) + safe_table_name + chr(96)
    row = database.fetch_one("SELECT COUNT(*) AS row_count FROM " + quoted_table_name)
    return int((row or {}).get("row_count", -1))


def main() -> int:
    databases: dict[str, CommonDatabase] = {}
    results: list[dict[str, Any]] = []
    try:
        for role, source_table_name, backup_table_name in BACKUP_TARGETS:
            database = databases.setdefault(
                role,
                CommonDatabase(database_role=role, connect_mongodb=False),
            )
            source_row_count = _row_count(database, source_table_name)
            backup_row_count = _row_count(database, backup_table_name)
            results.append(
                {
                    "database_role": role,
                    "source_table_name": source_table_name,
                    "backup_table_name": backup_table_name,
                    "source_row_count": source_row_count,
                    "backup_row_count": backup_row_count,
                    "row_count_match_yn": "Y" if source_row_count == backup_row_count else "N",
                }
            )
    finally:
        for database in databases.values():
            database.close()

    result = {
        "target_count": len(results),
        "match_count": sum(item["row_count_match_yn"] == "Y" for item in results),
        "mismatch_count": sum(item["row_count_match_yn"] == "N" for item in results),
        "results": results,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["mismatch_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
