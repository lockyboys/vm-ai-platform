from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.database import CommonDatabase
from engine.object_definition import ObjectDefinitionEngine


# 이번 Bootstrap 실행 대상 Manifest.
# Engine 내부 정책이 아니라 현재 Sprint의 명시적 등록 대상이다.
TARGETS = (
    {
        "table_name": "cm_role",
        "object_code": "CM_ROLE",
        "object_name": "Role",
        "object_description": (
            "회원 또는 실행 주체에게 부여되는 역할을 정의하는 "
            "Common Repository Object."
        ),
    },
    {
        "table_name": "rl_rule",
        "object_code": "RL_RULE",
        "object_name": "Rule",
        "object_description": (
            "조건, 행위 및 근거를 통해 업무 판단을 정의하는 "
            "Rule Repository Object."
        ),
    },
    {
        "table_name": "cm_role_rule",
        "object_code": "CM_ROLE_RULE",
        "object_name": "Role Rule Mapping",
        "object_description": (
            "cm_role과 rl_rule의 N:N 관계를 해소하는 최소 매핑 Object. "
            "Policy 또는 Rule 실행 속성을 저장하지 않는다."
        ),
    },
)

BOOTSTRAP_CLASSIFICATION = {
    "business_code": "SP",
    "domain_code": "RP",
    "object_type_code": "TABLE",
    "object_level": 3,
    "identifier_target_code": "OB",
    "sequence_scope_code": "DAILY",
    "sequence_length": 5,
}


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


def rows_to_dict(rows: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in (rows or [])]


def validate_bootstrap_classification(
    story_database: CommonDatabase,
) -> None:
    business = story_database.fetch_one(
        """
        SELECT
            business_code,
            business_name
        FROM sp_business
        WHERE business_code = %s
          AND active_yn = 'Y'
          AND deleted_dt IS NULL
        LIMIT 1
        """,
        (BOOTSTRAP_CLASSIFICATION["business_code"],),
    )

    if not business:
        raise LookupError(
            "Bootstrap Business Repository record not found. "
            f"business_code="
            f"{BOOTSTRAP_CLASSIFICATION['business_code']}"
        )

    domain = story_database.fetch_one(
        """
        SELECT
            domain_code,
            business_code,
            domain_name
        FROM sp_domain
        WHERE domain_code = %s
          AND business_code = %s
          AND active_yn = 'Y'
          AND deleted_dt IS NULL
        LIMIT 1
        """,
        (
            BOOTSTRAP_CLASSIFICATION["domain_code"],
            BOOTSTRAP_CLASSIFICATION["business_code"],
        ),
    )

    if not domain:
        raise LookupError(
            "Bootstrap Domain Repository record not found. "
            f"business_code="
            f"{BOOTSTRAP_CLASSIFICATION['business_code']}, "
            f"domain_code="
            f"{BOOTSTRAP_CLASSIFICATION['domain_code']}"
        )

    print_json(
        {
            "business": dict(business),
            "domain": dict(domain),
            "classification": BOOTSTRAP_CLASSIFICATION,
        }
    )


def load_physical_tables(
    common_database: CommonDatabase,
) -> list[dict[str, Any]]:
    table_names = tuple(
        target["table_name"]
        for target in TARGETS
    )

    placeholders = ", ".join(
        ["%s"] * len(table_names)
    )

    rows = common_database.fetch_all(
        f"""
        SELECT
            TABLE_SCHEMA,
            TABLE_NAME,
            ENGINE,
            TABLE_COLLATION,
            TABLE_COMMENT
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME IN ({placeholders})
        ORDER BY TABLE_NAME
        """,
        table_names,
    )

    return rows_to_dict(rows)


def load_existing_object(
    story_database: CommonDatabase,
    object_code: str,
) -> dict[str, Any] | None:
    row = story_database.fetch_one(
        """
        SELECT
            object_id,
            object_code,
            object_name,
            business_code,
            domain_code,
            object_type_code,
            object_level,
            identifier_target_code,
            sequence_scope_code,
            sequence_length,
            status_code,
            active_yn,
            created_dt,
            created_by,
            program_id
        FROM sp_object
        WHERE object_code = %s
          AND deleted_dt IS NULL
        LIMIT 1
        """,
        (object_code,),
    )

    return dict(row) if row else None


def build_request(
    target: dict[str, Any],
) -> dict[str, Any]:
    return {
        **BOOTSTRAP_CLASSIFICATION,
        "object_code": target["object_code"],
        "object_name": target["object_name"],
        "object_description": target["object_description"],
        "status_code": "ACTIVE",
        "active_yn": "Y",
        "version_no": "v1.0",
        "sort_no": 0,
        "created_by": "REPOSITORY_BOOTSTRAP_ENGINE",
        "updated_by": "REPOSITORY_BOOTSTRAP_ENGINE",
        "program_id": "bootstrap_role_rule_objects",
        "client_ip": "127.0.0.1",
    }


def register_objects(
    story_database: CommonDatabase,
) -> list[dict[str, Any]]:
    engine = ObjectDefinitionEngine(story_database)
    results: list[dict[str, Any]] = []

    for target in TARGETS:
        print_section(
            f"REGISTER {target['object_code']}"
        )

        existing = load_existing_object(
            story_database,
            target["object_code"],
        )

        if existing:
            result = {
                "status": "SKIPPED",
                "reason": "ALREADY_EXISTS",
                "object": existing,
            }

            print_json(result)
            results.append(result)
            continue

        request = build_request(target)

        print("REQUEST")
        print_json(request)

        result = engine.create(request)

        saved_object = load_existing_object(
            story_database,
            target["object_code"],
        )

        if not saved_object:
            raise RuntimeError(
                "ObjectDefinitionEngine completed, but the "
                "Repository Object was not found. "
                f"object_code={target['object_code']}"
            )

        if result["object_id"] != saved_object["object_id"]:
            raise RuntimeError(
                "Generated and stored Object identifiers differ. "
                f"generated={result['object_id']}, "
                f"stored={saved_object['object_id']}"
            )

        verified_result = {
            "status": "CREATED",
            "engine_result": result,
            "stored_object": saved_object,
        }

        print("RESULT")
        print_json(verified_result)

        results.append(verified_result)

    return results


def verify_repository(
    story_database: CommonDatabase,
) -> dict[str, Any]:
    object_codes = tuple(
        target["object_code"]
        for target in TARGETS
    )

    placeholders = ", ".join(
        ["%s"] * len(object_codes)
    )

    object_rows = story_database.fetch_all(
        f"""
        SELECT
            object_id,
            object_code,
            object_name,
            business_code,
            domain_code,
            object_type_code,
            object_level,
            identifier_target_code,
            sequence_scope_code,
            sequence_length,
            status_code,
            active_yn,
            created_dt,
            created_by,
            program_id
        FROM sp_object
        WHERE object_code IN ({placeholders})
          AND deleted_dt IS NULL
        ORDER BY object_code
        """,
        object_codes,
    )

    sequence_rows = story_database.fetch_all(
        f"""
        SELECT
            identifier_sequence_id,
            identifier_target_code,
            identifier_prefix,
            sequence_dt,
            current_sequence_no,
            sequence_length,
            status_code,
            created_dt,
            created_by,
            updated_dt,
            updated_by,
            program_id
        FROM sp_identifier_sequence
        WHERE identifier_prefix IN ({placeholders})
          AND deleted_dt IS NULL
        ORDER BY
            identifier_prefix,
            sequence_dt,
            identifier_sequence_id
        """,
        object_codes,
    )

    object_structure = story_database.fetch_all(
        """
        SELECT
            TABLE_NAME,
            ORDINAL_POSITION,
            COLUMN_NAME,
            COLUMN_TYPE,
            IS_NULLABLE,
            COLUMN_DEFAULT,
            COLUMN_KEY,
            COLUMN_COMMENT
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'sp_object'
        ORDER BY ORDINAL_POSITION
        """
    )

    sequence_structure = story_database.fetch_all(
        """
        SELECT
            TABLE_NAME,
            ORDINAL_POSITION,
            COLUMN_NAME,
            COLUMN_TYPE,
            IS_NULLABLE,
            COLUMN_DEFAULT,
            COLUMN_KEY,
            COLUMN_COMMENT
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'sp_identifier_sequence'
        ORDER BY ORDINAL_POSITION
        """
    )

    return {
        "objects": rows_to_dict(object_rows),
        "sequences": rows_to_dict(sequence_rows),
        "sp_object_structure": rows_to_dict(object_structure),
        "sp_identifier_sequence_structure": rows_to_dict(
            sequence_structure
        ),
    }


def main() -> int:
    story_database = CommonDatabase(
        database_role="STORY_PLATFORM"
    )

    common_database = CommonDatabase(
        database_role="COMMON"
    )

    print_section("STEP-001 DATABASE CONNECTIONS")

    print_json(
        {
            "story_platform": dict(
                story_database.fetch_one(
                    """
                    SELECT
                        DATABASE() AS current_database,
                        USER() AS connected_user,
                        CURRENT_USER() AS authenticated_user
                    """
                )
            ),
            "common": dict(
                common_database.fetch_one(
                    """
                    SELECT
                        DATABASE() AS current_database,
                        USER() AS connected_user,
                        CURRENT_USER() AS authenticated_user
                    """
                )
            ),
        }
    )

    print_section("STEP-002 BOOTSTRAP CLASSIFICATION")

    validate_bootstrap_classification(
        story_database
    )

    print_section("STEP-003 PHYSICAL TABLE DISCOVERY")

    physical_tables = load_physical_tables(
        common_database
    )

    print_json(physical_tables)

    expected_tables = {
        target["table_name"]
        for target in TARGETS
    }

    discovered_tables = {
        row["TABLE_NAME"]
        for row in physical_tables
    }

    missing_tables = sorted(
        expected_tables - discovered_tables
    )

    if missing_tables:
        raise LookupError(
            "Bootstrap target physical tables are missing. "
            f"missing_tables={missing_tables}"
        )

    print_section("STEP-004 OBJECT REGISTRATION")

    registration_results = register_objects(
        story_database
    )

    print_section("VERIFY-001 TABLE STRUCTURE AND DATA")

    verification = verify_repository(
        story_database
    )

    print_json(verification)

    expected_count = len(TARGETS)
    actual_object_count = len(
        verification["objects"]
    )
    actual_sequence_count = len(
        verification["sequences"]
    )

    if actual_object_count != expected_count:
        raise RuntimeError(
            "Repository Object count verification failed. "
            f"expected={expected_count}, "
            f"actual={actual_object_count}"
        )

    if actual_sequence_count < expected_count:
        raise RuntimeError(
            "Identifier Sequence count verification failed. "
            f"expected_at_least={expected_count}, "
            f"actual={actual_sequence_count}"
        )

    print_section("BOOTSTRAP RESULT")

    print(f"PHYSICAL TABLES  : {len(physical_tables)}")
    print(f"REGISTER RESULTS : {len(registration_results)}")
    print(f"OBJECT ROWS      : {actual_object_count}")
    print(f"SEQUENCE ROWS    : {actual_sequence_count}")
    print("SP_OBJECT SAVE   : OK")
    print("SEQUENCE SAVE    : OK")
    print("TRANSACTION      : OK")
    print("STATUS           : OK")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
