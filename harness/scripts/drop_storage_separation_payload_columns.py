#!/usr/bin/env python3
"""Drop all eleven MariaDB payload columns after a strict read-only safety gate.

The gate requires every preserved *_payload_backup_YYYYMMDD table to have the
same row count as its source and every listed source payload column to contain
only NULL/empty values.  If either check fails, no DDL is issued.  Backup
tables are never altered or deleted.
"""

from __future__ import annotations

import json
import re
from typing import Any

from common.database import CommonDatabase

_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")

TARGETS = (
    ("COMMON","cm_verified_sql_query","cm_verified_sql_query_payload_backup_20260902",("query_description","sql_text","verification_description")),
    ("COMMON","model_history","model_history_payload_backup_20260902",("features",)),
    ("COMMON","health_report","health_report_payload_backup_20260830",("report_content","change_story")),
    ("COMMON","cm_repository","cm_repository_payload_backup_20260902",("data_json","footer_json","code_description")),
    ("COMMON","cm_storage_repository","cm_storage_repository_payload_backup_20260902",("change_story",)),
    ("COMMON","sql_guard_execution_log","sql_guard_execution_log_payload_backup_20260830",("error_message",)),
    ("COMMON","sql_guard_verification_log","sql_guard_verification_log_payload_backup_20260830",("message","change_story")),
    ("COMMON","cron_logs","cron_logs_payload_backup_20260902",("message",)),
    ("COMMON","cm_code_inspection_result","cm_code_inspection_result_payload_backup_20260902",("related_codes","message")),
    ("COMMON","pipeline_results","pipeline_results_payload_backup_20260902",("data_json",)),
    ("STORY","sp_impact_analysis_result","sp_impact_analysis_result_payload_backup_20260830",("change_target_text","affected_file_path","affected_text","analysis_note")),
)

def _q(value: str) -> str:
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError("Unsafe identifier: " + value)
    return chr(96) + value + chr(96)

def _count(db: CommonDatabase, table: str) -> int:
    row = db.fetch_one("SELECT COUNT(*) AS row_count FROM " + _q(table))
    return int((row or {}).get("row_count", 0))

def _payload_count(db: CommonDatabase, table: str, columns: tuple[str, ...]) -> int:
    where = " OR ".join("(" + _q(c) + " IS NOT NULL AND " + _q(c) + " <> '')" for c in columns)
    row = db.fetch_one("SELECT COUNT(*) AS row_count FROM " + _q(table) + " WHERE " + where)
    return int((row or {}).get("row_count", 0))

def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    databases: dict[str, CommonDatabase] = {}
    checks: list[dict[str, Any]] = []
    try:
        for role, table, backup, columns in TARGETS:
            db = databases.setdefault(role, CommonDatabase(database_role=role, connect_mongodb=False))
            source_count, backup_count = _count(db, table), _count(db, backup)
            remaining = _payload_count(db, table, columns)
            checks.append({
                "database_role": role, "table_name": table, "backup_table_name": backup,
                "source_row_count": source_count, "backup_row_count": backup_count,
                "backup_match_yn": "Y" if source_count == backup_count else "N",
                "payload_remaining_count": remaining,
                "columns": list(columns),
            })
        safe = all(c["backup_match_yn"] == "Y" and c["payload_remaining_count"] == 0 for c in checks)
        result: dict[str, Any] = {"applied": False, "safety_gate_yn": "Y" if safe else "N", "backup_tables_changed_yn": "N", "checks": checks}
        if args.apply and safe:
            for role, table, backup, columns in TARGETS:
                db = databases[role]
                # The impact-analysis prefix index depends on a column being removed.
                if table == "sp_impact_analysis_result":
                    db.execute("ALTER TABLE " + _q(table) + " DROP INDEX " + _q("idx_sp_impact_analysis_result_01"))
                db.execute("ALTER TABLE " + _q(table) + " " + ", ".join("DROP COLUMN " + _q(c) for c in columns))
                db.commit()
            result["applied"] = True
            result["dropped_target_count"] = len(TARGETS)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if safe else 1
    finally:
        for db in databases.values():
            db.close()

if __name__ == "__main__":
    raise SystemExit(main())
