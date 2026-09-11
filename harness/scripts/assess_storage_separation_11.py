#!/usr/bin/env python3
"""Read-only status report for all eleven storage-separation targets.

The report does not change MariaDB, MongoDB, contracts, or any
*_payload_backup_YYYYMMDD table.  It is the mandatory evidence before
registering a missing migration contract or dropping a source column.
"""

from __future__ import annotations

import json
import re
from typing import Any

from common.database import CommonDatabase

_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")

# Source role, source table, preserved backup table, MongoDB role, collection,
# and every field requested for physical separation.
TARGETS = (
    ("COMMON", "cm_verified_sql_query", "cm_verified_sql_query_payload_backup_20260902", "COMMON", "verified_sql_payload", ("query_description", "sql_text", "verification_description")),
    ("COMMON", "model_history", "model_history_payload_backup_20260902", "COMMON", "model_history_payload", ("features",)),
    ("COMMON", "health_report", "health_report_payload_backup_20260830", "HEALTH", "health_report_content", ("report_content", "change_story")),
    ("COMMON", "cm_repository", "cm_repository_payload_backup_20260902", "COMMON", "cm_repository", ("data_json", "footer_json", "code_description")),
    ("COMMON", "cm_storage_repository", "cm_storage_repository_payload_backup_20260902", "COMMON", "cm_storage_repository", ("change_story",)),
    ("COMMON", "sql_guard_execution_log", "sql_guard_execution_log_payload_backup_20260830", "HEALTH", "sql_guard_execution_message", ("error_message",)),
    ("COMMON", "sql_guard_verification_log", "sql_guard_verification_log_payload_backup_20260830", "HEALTH", "sql_guard_verification_message", ("message", "change_story")),
    ("COMMON", "cron_logs", "cron_logs_payload_backup_20260902", "COMMON", "cron_logs_payload", ("message",)),
    ("COMMON", "cm_code_inspection_result", "cm_code_inspection_result_payload_backup_20260902", "COMMON", "cm_code_inspection_result_payload", ("related_codes", "message")),
    ("COMMON", "pipeline_results", "pipeline_results_payload_backup_20260902", "COMMON", "pipeline_results_payload", ("data_json",)),
    ("STORY", "sp_impact_analysis_result", "sp_impact_analysis_result_payload_backup_20260830", "HEALTH", "sp_impact_analysis_text", ("change_target_text", "affected_file_path", "affected_text", "analysis_note")),
)


def _quote(identifier: str) -> str:
    if not _IDENTIFIER.fullmatch(identifier):
        raise ValueError("Unsafe identifier: " + identifier)
    return chr(96) + identifier + chr(96)


def _payload_row_count(database: CommonDatabase, table_name: str, columns: tuple[str, ...]) -> int:
    conditions = [
        "(" + _quote(column_name) + " IS NOT NULL AND " + _quote(column_name) + " <> '')"
        for column_name in columns
    ]
    row = database.fetch_one(
        "SELECT COUNT(*) AS row_count FROM " + _quote(table_name)
        + " WHERE " + " OR ".join(conditions)
    )
    return int((row or {}).get("row_count", 0))


def _row_count(database: CommonDatabase, table_name: str) -> int:
    row = database.fetch_one("SELECT COUNT(*) AS row_count FROM " + _quote(table_name))
    return int((row or {}).get("row_count", 0))


def _mongo_count(role: str, collection_name: str) -> int:
    database = CommonDatabase(database_role=role, connect_mariadb=False, connect_mongodb=True)
    try:
        return len(database.find(collection_name=collection_name, filter_document={}))
    finally:
        database.close()


def main() -> int:
    mariadb: dict[str, CommonDatabase] = {}
    results: list[dict[str, Any]] = []
    try:
        for source_role, table_name, backup_table_name, mongodb_role, collection_name, columns in TARGETS:
            database = mariadb.setdefault(
                source_role,
                CommonDatabase(database_role=source_role, connect_mongodb=False),
            )
            result = {
                "source_database_role": source_role,
                "source_table_name": table_name,
                "payload_columns": list(columns),
                "backup_table_name": backup_table_name,
                "source_row_count": _row_count(database, table_name),
                "backup_row_count": _row_count(database, backup_table_name),
                "backup_match_yn": "Y" if _row_count(database, table_name) == _row_count(database, backup_table_name) else "N",
                "source_payload_remaining_count": _payload_row_count(database, table_name, columns),
                "mongodb_database_role": mongodb_role,
                "mongodb_collection_name": collection_name,
                "mongodb_document_count": _mongo_count(mongodb_role, collection_name),
            }
            result["migration_complete_yn"] = (
                "Y" if result["source_payload_remaining_count"] == 0
                and result["mongodb_document_count"] > 0 else "N"
            )
            results.append(result)
    finally:
        for database in mariadb.values():
            database.close()

    output = {
        "operation": "read_only_11_target_assessment",
        "backup_tables_changed_yn": "N",
        "target_count": len(results),
        "migration_complete_count": sum(row["migration_complete_yn"] == "Y" for row in results),
        "results": results,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
