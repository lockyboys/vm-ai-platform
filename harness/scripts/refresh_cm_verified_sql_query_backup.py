#!/usr/bin/env python3
"""Refresh the physical MariaDB backup for cm_verified_sql_query safely."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from common.database import CommonDatabase

SOURCE_TABLE = "cm_verified_sql_query"
BACKUP_TABLE = "cm_verified_sql_query_payload_backup_20260902"
STAGING_TABLE = "cm_verified_sql_query_payload_backup_20260902_staging"
ARCHIVE_TABLE_PREFIX = "cm_verified_sql_query_payload_backup_20260902_r_"
STAGING_STALE_TABLE_PREFIX = "cm_verified_sql_query_payload_backup_20260902_s_"


def _quoted(table_name: str) -> str:
    """Quote the fixed, internal table names used by this script."""
    return chr(96) + table_name + chr(96)


def _row_count(database: CommonDatabase, table_name: str) -> int:
    row = database.fetch_one("SELECT COUNT(*) AS row_count FROM " + _quoted(table_name))
    return int((row or {}).get("row_count", -1))


def _table_exists(database: CommonDatabase, table_name: str) -> bool:
    return database.fetch_one("SHOW TABLES LIKE %s", (table_name,)) is not None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    arguments = parser.parse_args()

    database = CommonDatabase(database_role="COMMON", connect_mongodb=False)
    try:
        # MariaDB identifiers may not exceed 64 characters.  The compact UTC
        # stamp preserves each prior physical backup without deleting it.
        refresh_stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        archive_table = ARCHIVE_TABLE_PREFIX + refresh_stamp
        staging_stale_table = STAGING_STALE_TABLE_PREFIX + refresh_stamp
        current_source_count = _row_count(database, SOURCE_TABLE)
        current_backup_count = _row_count(database, BACKUP_TABLE)
        preview = {
            "source_table_name": SOURCE_TABLE,
            "active_backup_table_name": BACKUP_TABLE,
            "current_source_row_count": current_source_count,
            "current_backup_row_count": current_backup_count,
            "staging_table_name": STAGING_TABLE,
            "archive_table_name": archive_table,
            "applied": arguments.apply,
        }
        if not arguments.apply:
            print(json.dumps(preview, ensure_ascii=False, indent=2))
            return 0

        if _table_exists(database, archive_table) or _table_exists(database, staging_stale_table):
            raise FileExistsError("Generated archive or stale staging table already exists; retry the refresh.")

        if _table_exists(database, STAGING_TABLE):
            # A partial staging copy is retained for audit; it is never dropped.
            copied_row_count = _row_count(database, STAGING_TABLE)
            if copied_row_count != current_source_count:
                database.execute(
                    "RENAME TABLE " + _quoted(STAGING_TABLE)
                    + " TO " + _quoted(staging_stale_table)
                )

        if not _table_exists(database, STAGING_TABLE):
            database.execute(
                "CREATE TABLE " + _quoted(STAGING_TABLE) + " LIKE " + _quoted(SOURCE_TABLE)
            )
            database.execute(
                "INSERT INTO " + _quoted(STAGING_TABLE) + " SELECT * FROM " + _quoted(SOURCE_TABLE)
            )

        copied_row_count = _row_count(database, STAGING_TABLE)
        current_source_count = _row_count(database, SOURCE_TABLE)
        if copied_row_count != current_source_count:
            raise RuntimeError("New staging row count does not match the current source; retry the refresh.")

        # One atomic rename keeps the old backup available as an archive while
        # the validated staging copy becomes the active backup.
        database.execute(
            "RENAME TABLE "
            + _quoted(BACKUP_TABLE) + " TO " + _quoted(archive_table)
            + ", " + _quoted(STAGING_TABLE) + " TO " + _quoted(BACKUP_TABLE)
        )

        refreshed_source_count = _row_count(database, SOURCE_TABLE)
        refreshed_backup_count = _row_count(database, BACKUP_TABLE)
        result = {
            **preview,
            "applied": True,
            "archive_backup_row_count": current_backup_count,
            "refreshed_source_row_count": refreshed_source_count,
            "refreshed_backup_row_count": refreshed_backup_count,
            "row_count_match_yn": "Y" if refreshed_source_count == refreshed_backup_count else "N",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["row_count_match_yn"] == "Y" else 1
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())
