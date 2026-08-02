"""Register UI Runtime SQL batches in ``cm_verified_sql_query``.

File Story:
    UI Runtime 공통코드 Group과 Code 등록 SQL 원문을 Verified SQL Repository에
    멱등 등록한다.

Change History:
    20260802 | OpenAI | UI Runtime 공통코드 SQL 2건을 Identifier Engine 기반으로
    cm_verified_sql_query에 등록한다.

Repository First:
    - The registered SQL is the exact source stored in ``sql/ui_runtime``.
    - The source file path and SHA-256 are persisted for idempotent verification.
    - A missing query ID is issued by the existing Identifier Engine from the
      ``query_id`` Object metadata; IDs are never composed in this tool.
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
from engine.identifier_engine import IdentifierEngine
from engine.object_definition_engine import ObjectDefinitionEngine


PROGRAM_ID = "CM_CO_UI_RUNTIME_SQL_QUERY_20260802"
SOURCE_PREFIX = "SOURCE_FILE: "
QUERY_TARGET_IDENTIFIER_FIELD = "query_id"
UI_RUNTIME_SQL_DIR = PROJECT_ROOT / "sql" / "ui_runtime"
UI_RUNTIME_SQL_SOURCES: tuple[tuple[str, str], ...] = (
    (
        "00_register_ui_common_code_group_20260730.sql",
        "UI Runtime 공통코드 Group 등록",
    ),
    (
        "01_register_ui_common_code_20260730.sql",
        "UI Runtime 공통코드 등록",
    ),
)


def source_description(relative_path: str) -> str:
    """Build the SSOT source identity kept with the verified query."""
    return (
        f"{SOURCE_PREFIX}{relative_path}. "
        "UI Runtime Common Repository의 공식 SQL 원문이다. "
        "Generator, Engine 및 AI는 이 Repository를 SSOT로 사용한다."
    )


def _load_identifier_object(
    story_database: CommonDatabase,
) -> dict[str, object]:
    row = story_database.fetch_one(
        """
        SELECT
            object_code, object_name, object_description,
            business_code, domain_code, object_type_code, object_level,
            identifier_target_code, sequence_scope_code, sequence_length,
            status_code, active_yn, version_num,
            created_by, updated_by, client_ip, program_id
        FROM sp_object
        WHERE target_identifier_field = %s
          AND active_yn = 'Y'
          AND status_code = 'ACTIVE'
          AND deleted_dt IS NULL
        ORDER BY object_code
        LIMIT 1
        """,
        (QUERY_TARGET_IDENTIFIER_FIELD,),
    )
    if not row:
        raise LookupError(
            "Identifier Object metadata not found: "
            f"target_identifier_field={QUERY_TARGET_IDENTIFIER_FIELD}"
        )
    return dict(row)


def issue_query_id(story_database: CommonDatabase) -> str:
    """Issue a query ID using registered Object and sequence metadata only."""
    metadata = _load_identifier_object(story_database)
    identifier_engine = IdentifierEngine(story_database)
    object_engine = ObjectDefinitionEngine(story_database)
    now = datetime.now()
    blueprint = identifier_engine.load_identifier_blueprint(int(metadata["object_level"]))
    sequence_date = identifier_engine.resolve_sequence_date(
        str(metadata["sequence_scope_code"]), now
    )

    story_database.begin()
    try:
        object_engine._ensure_sequence_metadata(
            metadata,
            blueprint,
            sequence_date,
            int(metadata["sequence_length"]),
            now,
        )
        story_database.commit()
    except Exception:
        story_database.rollback()
        raise

    return str(identifier_engine.generate(str(metadata["object_code"])))


def _load_source_files() -> list[tuple[Path, str]]:
    """Load only the two approved UI common-code SQL sources."""
    sources: list[tuple[Path, str]] = []
    for file_name, query_name in UI_RUNTIME_SQL_SOURCES:
        path = UI_RUNTIME_SQL_DIR / file_name
        if not path.is_file():
            raise FileNotFoundError(f"Required UI Runtime SQL file not found: {path}")
        sources.append((path, query_name))
    return sources


def main() -> int:
    files = _load_source_files()
    common_database = CommonDatabase(database_role="COMMON")
    story_database = CommonDatabase(database_role="STORY_PLATFORM")
    inserted = 0
    updated = 0

    try:
        existing_rows = common_database.fetch_all(
            """
            SELECT query_id, query_description
            FROM cm_verified_sql_query
            WHERE deleted_dt IS NULL
            """
        )
        existing_by_source = {
            str(row["query_description"]).split(". ", 1)[0][len(SOURCE_PREFIX):]:
            str(row["query_id"])
            for row in existing_rows
            if str(row.get("query_description") or "").startswith(SOURCE_PREFIX)
        }

        common_database.begin()
        for path, query_name in files:
            relative_path = path.relative_to(PROJECT_ROOT).as_posix()
            sql_text = path.read_text(encoding="utf-8")
            sha256 = hashlib.sha256(sql_text.encode("utf-8")).hexdigest()
            description = source_description(relative_path)
            verification = (
                f"SHA256={sha256}; UI Runtime Batch 원문 무결성 및 "
                "Common Repository 등록 검증 완료."
            )
            existing_id = existing_by_source.get(relative_path)

            if existing_id:
                common_database.execute(
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
                        status_code = 'ACTIVE',
                        updated_by = 'SYSTEM',
                        updated_dt = CURRENT_TIMESTAMP,
                        program_id = %s,
                        deleted_by = NULL,
                        deleted_dt = NULL
                    WHERE query_id = %s
                    """,
                    (query_name, description, sql_text, verification,
                     PROGRAM_ID, existing_id),
                )
                updated += 1
                continue

            query_id = issue_query_id(story_database)
            common_database.execute(
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
                (query_id, query_name, description, sql_text,
                 verification, PROGRAM_ID),
            )
            inserted += 1

        common_database.commit()
        registered = common_database.fetch_one(
            """
            SELECT COUNT(*) AS registered_count
            FROM cm_verified_sql_query
            WHERE query_description LIKE 'SOURCE_FILE: sql/ui_runtime/%%'
              AND deleted_dt IS NULL
            """
        )
        result = {
            "status": "SUCCESS",
            "ui_runtime_sql_file_count": len(files),
            "inserted_count": inserted,
            "updated_count": updated,
            "registered_count": int(registered["registered_count"]),
        }
        if result["registered_count"] != len(files):
            raise RuntimeError(json.dumps(result, ensure_ascii=False))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception:
        common_database.rollback()
        raise
    finally:
        story_database.close()
        common_database.close()


if __name__ == "__main__":
    raise SystemExit(main())
