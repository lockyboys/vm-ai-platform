from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.database import CommonDatabase


TARGET_METADATA_CODES = (
    "COLUMN_SUFFIX_ID",
    "COLUMN_SUFFIX_CODE",
    "COLUMN_SUFFIX_NAME",
    "COLUMN_SUFFIX_DESCRIPTION",
    "COLUMN_SUFFIX_JSON",
    "COLUMN_SUFFIX_NO",
    "COLUMN_SUFFIX_NUM",
    "COLUMN_SUFFIX_DT",
    "COLUMN_SUFFIX_YN",
    "COLUMN_SUFFIX_IP",
    "COLUMN_SUFFIX_BY",
)

REGISTRATION_DRAFT = (
    {
        "metadata_code": "COLUMN_SUFFIX_ID",
        "suffix": "_id",
        "data_type": "VARCHAR",
        "length": 99,
        "meaning": "Identifier",
    },
    {
        "metadata_code": "COLUMN_SUFFIX_CODE",
        "suffix": "_code",
        "data_type": "VARCHAR",
        "length": 99,
        "meaning": "Code",
    },
    {
        "metadata_code": "COLUMN_SUFFIX_NAME",
        "suffix": "_name",
        "data_type": "VARCHAR",
        "length": 150,
        "meaning": "Name",
    },
    {
        "metadata_code": "COLUMN_SUFFIX_DESCRIPTION",
        "suffix": "_description",
        "data_type": "VARCHAR",
        "length": 2000,
        "meaning": "Description",
    },
    {
        "metadata_code": "COLUMN_SUFFIX_JSON",
        "suffix": "_json",
        "data_type": "VARCHAR",
        "length": 2000,
        "meaning": "Structured Knowledge JSON",
    },
    {
        "metadata_code": "COLUMN_SUFFIX_NO",
        "suffix": "_no",
        "data_type": "INT",
        "length": None,
        "meaning": "Ordinal Number",
    },
    {
        "metadata_code": "COLUMN_SUFFIX_NUM",
        "suffix": "_num",
        "data_type": "VARCHAR",
        "length": 99,
        "meaning": "Logical Number",
    },
    {
        "metadata_code": "COLUMN_SUFFIX_DT",
        "suffix": "_dt",
        "data_type": "DATETIME",
        "length": None,
        "meaning": "Date Time",
    },
    {
        "metadata_code": "COLUMN_SUFFIX_YN",
        "suffix": "_yn",
        "data_type": "CHAR",
        "length": 1,
        "meaning": "Yes or No",
    },
    {
        "metadata_code": "COLUMN_SUFFIX_IP",
        "suffix": "_ip",
        "data_type": "VARCHAR",
        "length": 99,
        "meaning": "IP Address",
    },
    {
        "metadata_code": "COLUMN_SUFFIX_BY",
        "suffix": "_by",
        "data_type": "VARCHAR",
        "length": 150,
        "meaning": "Execution Subject",
    },
)


def rows_to_dict(rows: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in (rows or [])]


def print_section(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def print_json(value: Any) -> None:
    print(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


def load_columns(
    database: CommonDatabase,
    table_name: str,
) -> list[dict[str, Any]]:
    return rows_to_dict(
        database.fetch_all(
            """
            SELECT
                ORDINAL_POSITION,
                COLUMN_NAME,
                COLUMN_TYPE,
                IS_NULLABLE,
                COLUMN_DEFAULT,
                COLUMN_KEY,
                EXTRA,
                CHARACTER_SET_NAME,
                COLLATION_NAME,
                COLUMN_COMMENT
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
            """,
            (table_name,),
        )
    )


def load_constraints(
    database: CommonDatabase,
    table_name: str,
) -> list[dict[str, Any]]:
    return rows_to_dict(
        database.fetch_all(
            """
            SELECT
                tc.CONSTRAINT_NAME,
                tc.CONSTRAINT_TYPE,
                kcu.COLUMN_NAME,
                kcu.ORDINAL_POSITION,
                kcu.REFERENCED_TABLE_NAME,
                kcu.REFERENCED_COLUMN_NAME
            FROM information_schema.TABLE_CONSTRAINTS tc
            LEFT JOIN information_schema.KEY_COLUMN_USAGE kcu
              ON kcu.CONSTRAINT_SCHEMA = tc.CONSTRAINT_SCHEMA
             AND kcu.TABLE_NAME = tc.TABLE_NAME
             AND kcu.CONSTRAINT_NAME = tc.CONSTRAINT_NAME
            WHERE tc.CONSTRAINT_SCHEMA = DATABASE()
              AND tc.TABLE_NAME = %s
            ORDER BY
                tc.CONSTRAINT_TYPE,
                tc.CONSTRAINT_NAME,
                kcu.ORDINAL_POSITION
            """,
            (table_name,),
        )
    )


def load_indexes(
    database: CommonDatabase,
    table_name: str,
) -> list[dict[str, Any]]:
    return rows_to_dict(
        database.fetch_all(
            """
            SELECT
                INDEX_NAME,
                NON_UNIQUE,
                SEQ_IN_INDEX,
                COLUMN_NAME,
                INDEX_TYPE
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
            ORDER BY
                INDEX_NAME,
                SEQ_IN_INDEX
            """,
            (table_name,),
        )
    )


def load_sample_rows(
    database: CommonDatabase,
    table_name: str,
) -> list[dict[str, Any]]:
    return rows_to_dict(
        database.fetch_all(
            f"""
            SELECT *
            FROM `{table_name}`
            ORDER BY 1
            LIMIT 10
            """
        )
    )


def load_existing_suffix_metadata(
    database: CommonDatabase,
    metadata_columns: set[str],
) -> list[dict[str, Any]]:
    searchable_columns = [
        column_name
        for column_name in (
            "metadata_code",
            "metadata_name",
            "metadata_description",
            "metadata_json",
        )
        if column_name in metadata_columns
    ]

    if not searchable_columns:
        return []

    predicates = " OR ".join(
        f"UPPER(CAST({column_name} AS CHAR)) "
        "LIKE '%COLUMN_SUFFIX%'"
        for column_name in searchable_columns
    )

    deleted_filter = (
        "AND deleted_dt IS NULL"
        if "deleted_dt" in metadata_columns
        else ""
    )

    return rows_to_dict(
        database.fetch_all(
            f"""
            SELECT *
            FROM sp_metadata
            WHERE ({predicates})
            {deleted_filter}
            ORDER BY 1
            """
        )
    )


def main() -> int:
    database = CommonDatabase(
        database_role="STORY_PLATFORM"
    )

    print_section("STEP-001 DATABASE CONNECTION")

    print_json(
        dict(
            database.fetch_one(
                """
                SELECT
                    DATABASE() AS current_database,
                    USER() AS connected_user,
                    CURRENT_USER() AS authenticated_user,
                    NOW() AS checked_dt
                """
            )
        )
    )

    print_section("STEP-002 SP_METADATA STRUCTURE")

    metadata_structure = load_columns(
        database,
        "sp_metadata",
    )

    print_json(metadata_structure)

    if not metadata_structure:
        raise LookupError(
            "sp_metadata table structure was not found."
        )

    metadata_columns = {
        row["COLUMN_NAME"]
        for row in metadata_structure
    }

    print_section("STEP-003 SP_METADATA CONSTRAINTS")

    print_json(
        load_constraints(
            database,
            "sp_metadata",
        )
    )

    print_section("STEP-004 SP_METADATA INDEXES")

    print_json(
        load_indexes(
            database,
            "sp_metadata",
        )
    )

    print_section("STEP-005 SP_METADATA SAMPLE DATA")

    print_json(
        load_sample_rows(
            database,
            "sp_metadata",
        )
    )

    print_section("STEP-006 EXISTING COLUMN SUFFIX METADATA")

    existing_metadata = load_existing_suffix_metadata(
        database,
        metadata_columns,
    )

    print_json(existing_metadata)

    print_section("STEP-007 IDENTIFIER SUPPORT STRUCTURE")

    support_result = {
        "sp_object": {
            "structure": load_columns(
                database,
                "sp_object",
            ),
            "metadata_objects": rows_to_dict(
                database.fetch_all(
                    """
                    SELECT
                        object_id,
                        object_code,
                        object_name,
                        object_level,
                        identifier_target_code,
                        sequence_scope_code,
                        sequence_length,
                        status_code
                    FROM sp_object
                    WHERE
                        (
                            UPPER(object_code) LIKE '%METADATA%'
                            OR UPPER(object_name) LIKE '%METADATA%'
                        )
                      AND deleted_dt IS NULL
                    ORDER BY object_code
                    """
                )
            ),
        },
        "sp_identifier_blueprint": {
            "structure": load_columns(
                database,
                "sp_identifier_blueprint",
            ),
            "level_candidates": rows_to_dict(
                database.fetch_all(
                    """
                    SELECT *
                    FROM sp_identifier_blueprint
                    WHERE deleted_dt IS NULL
                    ORDER BY 1
                    """
                )
            ),
        },
        "sp_identifier_sequence": {
            "structure": load_columns(
                database,
                "sp_identifier_sequence",
            ),
        },
    }

    print_json(support_result)

    print_section("STEP-008 COLUMN SUFFIX REGISTRATION DRAFT")

    print_json(
        {
            "metadata_category": "COLUMN_SUFFIX_STANDARD",
            "metadata_responsibility": (
                "컬럼 접미사별 데이터 타입, 길이, 의미, "
                "검증 및 Generator 생성 기준"
            ),
            "negative_metadata": True,
            "hardcoding_allowed": False,
            "registration_count": len(
                REGISTRATION_DRAFT
            ),
            "registration_rows": REGISTRATION_DRAFT,
            "approval_required": True,
        }
    )

    print_section("INSPECTION RESULT")

    print(
        f"SP_METADATA COLUMNS : "
        f"{len(metadata_structure)}"
    )
    print(
        f"EXISTING SUFFIX ROWS: "
        f"{len(existing_metadata)}"
    )
    print(
        f"DRAFT ROWS          : "
        f"{len(REGISTRATION_DRAFT)}"
    )
    print("DB MODIFICATION      : NONE")
    print("STATUS               : OK")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
