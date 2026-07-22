"""Register every sql/runtime SQL batch in cm_verified_sql_query.

Repository First:
- Source identity is stored in query_description as SOURCE_FILE.
- SHA-256 is stored in verification_description.
- Existing rows are updated; missing rows receive a Level 4 query_id.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.database import CommonDatabase

RUNTIME_DIR = PROJECT_ROOT / "sql" / "runtime"
PROGRAM_ID = "CM_CO_SQL_QUERY_20260721_00001"
SOURCE_PREFIX = "SOURCE_FILE: "


def source_description(relative_path: str) -> str:
    return (
        f"{SOURCE_PREFIX}{relative_path}. "
        "Story Programming Repository Runtime Batch의 공식 SQL 원문이다. "
        "Generator, Engine 및 AI는 이 Repository를 SSOT로 사용한다."
    )


def next_query_ids(count: int, existing_ids: set[str]) -> list[str]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result: list[str] = []
    sequence = 1
    while len(result) < count:
        query_id = f"SP_RP_SQL_QUERY_{timestamp}_{sequence:05d}"
        sequence += 1
        if query_id not in existing_ids:
            result.append(query_id)
            existing_ids.add(query_id)
    return result


def main() -> int:
    files = sorted(path for path in RUNTIME_DIR.rglob("*.sql") if path.is_file())
    if not files:
        raise RuntimeError(f"No SQL files found: {RUNTIME_DIR}")

    database = CommonDatabase(database_role="COMMON")
    inserted = 0
    updated = 0

    try:
        existing_rows = database.fetch_all(
            """
            SELECT query_id, query_description
            FROM cm_verified_sql_query
            """
        )
        existing_ids = {str(row["query_id"]) for row in existing_rows}
        existing_by_source = {
            str(row["query_description"]).split(". ", 1)[0][len(SOURCE_PREFIX):]:
                str(row["query_id"])
            for row in existing_rows
            if str(row.get("query_description") or "").startswith(SOURCE_PREFIX)
        }

        missing_count = sum(
            1
            for path in files
            if path.relative_to(PROJECT_ROOT).as_posix() not in existing_by_source
        )
        allocated_ids = iter(next_query_ids(missing_count, existing_ids))

        database.begin()
        for path in files:
            relative_path = path.relative_to(PROJECT_ROOT).as_posix()
            sql_text = path.read_text(encoding="utf-8")
            sha256 = hashlib.sha256(sql_text.encode("utf-8")).hexdigest()
            description = source_description(relative_path)
            verification = (
                f"SHA256={sha256}; Repository Runtime Batch 전수 등록 및 원문 무결성 확인."
            )
            query_name = path.stem[:150]

            existing_id = existing_by_source.get(relative_path)
            if existing_id:
                database.execute(
                    """
                    UPDATE cm_verified_sql_query
                    SET query_name = %s,
                        query_description = %s,
                        crud_type = 'BATCH',
                        sql_text = %s,
                        verified_yn = 'Y',
                        certified_level_code = 'A',
                        verification_description = %s,
                        verified_by = 'SYSTEM',
                        verified_dt = CURRENT_TIMESTAMP,
                        updated_dt = CURRENT_TIMESTAMP,
                        updated_by = 'SYSTEM',
                        status_code = 'ACTIVE',
                        program_id = %s,
                        deleted_dt = NULL,
                        deleted_by = NULL
                    WHERE query_id = %s
                    """,
                    (
                        query_name, description, sql_text, verification,
                        PROGRAM_ID, existing_id,
                    ),
                )
                updated += 1
            else:
                query_id = next(allocated_ids)
                database.execute(
                    """
                    INSERT INTO cm_verified_sql_query
                        (query_id, query_name, query_description, crud_type,
                         sql_text, verified_yn, certified_level_code,
                         verification_description, created_by, verified_by,
                         verified_dt, updated_by, status_code, program_id)
                    VALUES
                        (%s, %s, %s, 'BATCH', %s, 'Y', 'A',
                         %s, 'SYSTEM', 'SYSTEM', CURRENT_TIMESTAMP,
                         'SYSTEM', 'ACTIVE', %s)
                    """,
                    (
                        query_id, query_name, description, sql_text,
                        verification, PROGRAM_ID,
                    ),
                )
                inserted += 1

        database.commit()

        registered = database.fetch_one(
            """
            SELECT COUNT(*) AS registered_runtime_batch_count
            FROM cm_verified_sql_query
            WHERE query_description LIKE 'SOURCE_FILE: sql/runtime/%%'
              AND deleted_dt IS NULL
            """
        )
        result = {
            "status": "SUCCESS",
            "runtime_sql_file_count": len(files),
            "inserted_count": inserted,
            "updated_count": updated,
            "registered_runtime_batch_count": int(
                registered["registered_runtime_batch_count"]
            ),
        }
        if result["registered_runtime_batch_count"] != len(files):
            result["status"] = "FAILED"
            raise RuntimeError(json.dumps(result, ensure_ascii=False))

        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception:
        database.rollback()
        raise
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())
