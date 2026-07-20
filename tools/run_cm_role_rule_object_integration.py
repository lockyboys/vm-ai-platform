from __future__ import annotations

import json
from typing import Any

from common.database import CommonDatabase
from engine.object_definition import ObjectDefinitionEngine


OBJECT_CODE = "CM_ROLE_RULE"
OBJECT_NAME = "Role Rule Mapping"
OBJECT_DESCRIPTION = (
    "cm_role과 rl_rule의 N:N 관계를 해소하는 최소 매핑 Object. "
    "Policy 또는 Rule 실행 속성을 저장하지 않는다."
)


def to_dict(row: Any) -> dict[str, Any] | None:
    if not row:
        return None

    return dict(row)


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


def load_existing_object(
    database: CommonDatabase,
) -> dict[str, Any] | None:
    return to_dict(
        database.fetch_one(
            """
            SELECT
                object_id,
                object_code,
                object_name,
                business_code,
                domain_code,
                object_type_code,
                object_description,
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
            (OBJECT_CODE,),
        )
    )


def load_template_object(
    database: CommonDatabase,
) -> dict[str, Any]:
    """
    CM_ROLE_RULE의 직접 관련 Object만 생성 기준으로 사용한다.

    무관한 Level 3 Object를 임의 상속하지 않는다.
    """
    row = database.fetch_one(
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
            sequence_length
        FROM sp_object
        WHERE object_code IN ('CM_ROLE', 'RL_RULE')
          AND status_code = 'ACTIVE'
          AND active_yn = 'Y'
          AND deleted_dt IS NULL
        ORDER BY
            CASE object_code
                WHEN 'CM_ROLE' THEN 1
                WHEN 'RL_RULE' THEN 2
                ELSE 3
            END
        LIMIT 1
        """
    )

    if not row:
        raise LookupError(
            "CM_ROLE 또는 RL_RULE Repository Object가 없습니다. "
            "CM_ROLE_RULE의 business_code, domain_code, "
            "object_type_code, identifier_target_code를 "
            "무관한 Object에서 추정하지 않습니다."
        )

    return dict(row)


def build_request(
    template: dict[str, Any],
) -> dict[str, Any]:
    return {
        "object_code": OBJECT_CODE,
        "object_name": OBJECT_NAME,
        "business_code": template["business_code"],
        "domain_code": template["domain_code"],
        "object_type_code": template["object_type_code"],
        "object_level": int(template["object_level"]),
        "identifier_target_code": (
            template["identifier_target_code"]
        ),
        "sequence_scope_code": (
            template["sequence_scope_code"]
        ),
        "sequence_length": int(
            template["sequence_length"]
        ),
        "object_description": OBJECT_DESCRIPTION,
        "status_code": "ACTIVE",
        "active_yn": "Y",
        "version_no": "v1.0",
        "sort_no": 0,
        "created_by": "OBJECT_DEFINITION_INTEGRATION_TEST",
        "updated_by": "OBJECT_DEFINITION_INTEGRATION_TEST",
        "program_id": "run_cm_role_rule_object_integration",
        "client_ip": "127.0.0.1",
        "change_reason": (
            "cm_role_rule N:N Mapping Object Repository 등록"
        ),
    }


def load_sequence_rows(
    database: CommonDatabase,
) -> list[dict[str, Any]]:
    rows = database.fetch_all(
        """
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
        WHERE identifier_prefix = %s
          AND deleted_dt IS NULL
        ORDER BY
            sequence_dt DESC,
            updated_dt DESC,
            identifier_sequence_id DESC
        """,
        (OBJECT_CODE,),
    )

    return [
        dict(row)
        for row in (rows or [])
    ]


def load_relevant_structure(
    database: CommonDatabase,
    table_name: str,
    columns: tuple[str, ...],
) -> list[dict[str, Any]]:
    placeholders = ", ".join(
        ["%s"] * len(columns)
    )

    sql = f"""
        SELECT
            TABLE_NAME,
            ORDINAL_POSITION,
            COLUMN_NAME,
            COLUMN_TYPE,
            IS_NULLABLE,
            COLUMN_DEFAULT,
            COLUMN_KEY,
            EXTRA,
            COLUMN_COMMENT
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME IN ({placeholders})
        ORDER BY ORDINAL_POSITION
    """

    rows = database.fetch_all(
        sql,
        (
            table_name,
            *columns,
        ),
    )

    return [
        dict(row)
        for row in (rows or [])
    ]


def verify_lock_released(
    database: CommonDatabase,
    *,
    request: dict[str, Any],
    sequence_date: str,
) -> dict[str, Any]:
    lock_name = (
        "SPS_IDENTIFIER:"
        f"{request['business_code'].upper()}:"
        f"{request['domain_code'].upper()}:"
        f"{OBJECT_CODE}:"
        f"{sequence_date.upper()}"
    )[:64]

    row = database.fetch_one(
        """
        SELECT
            %s AS lock_name,
            IS_FREE_LOCK(%s) AS is_free
        """,
        (
            lock_name,
            lock_name,
        ),
    )

    return dict(row)


def main() -> int:
    database = CommonDatabase(
        database_role="STORY_PLATFORM"
    )

    print_section("STEP-001 DATABASE CONNECTION")

    connection_row = database.fetch_one(
        """
        SELECT
            DATABASE() AS current_database,
            USER() AS connected_user,
            CURRENT_USER() AS authenticated_user,
            NOW() AS test_started_dt
        """
    )

    print_json(dict(connection_row))

    existing_before = load_existing_object(database)

    print_section("STEP-002 EXISTING OBJECT CHECK")
    print_json(existing_before)

    if existing_before:
        print()
        print("EXECUTION STATUS : SKIPPED")
        print("REASON           : CM_ROLE_RULE already exists")

        saved_object = existing_before
        request = {
            "business_code": saved_object["business_code"],
            "domain_code": saved_object["domain_code"],
        }

    else:
        template = load_template_object(database)

        print_section("STEP-003 REPOSITORY TEMPLATE")
        print_json(template)

        request = build_request(template)

        print_section("STEP-004 GENERATOR REQUEST")
        print_json(request)

        engine = ObjectDefinitionEngine(database)

        print_section("STEP-005 OBJECT DEFINITION ENGINE EXECUTION")

        result = engine.create(request)

        print_json(result)

        saved_object = load_existing_object(database)

        if not saved_object:
            raise RuntimeError(
                "ObjectDefinitionEngine returned successfully, "
                "but CM_ROLE_RULE was not found in sp_object."
            )

        if saved_object["object_id"] != result["object_id"]:
            raise RuntimeError(
                "Generated object_id and stored object_id do not match. "
                f"generated={result['object_id']}, "
                f"stored={saved_object['object_id']}"
            )

    print_section("VERIFY-001 SP_OBJECT STRUCTURE")

    print_json(
        load_relevant_structure(
            database,
            "sp_object",
            (
                "object_id",
                "object_code",
                "object_name",
                "business_code",
                "domain_code",
                "object_type_code",
                "object_description",
                "object_level",
                "identifier_target_code",
                "sequence_scope_code",
                "sequence_length",
                "status_code",
                "active_yn",
                "created_dt",
                "created_by",
                "program_id",
            ),
        )
    )

    print_section("VERIFY-002 SP_OBJECT REGISTERED DATA")
    print_json(saved_object)

    sequence_rows = load_sequence_rows(database)

    print_section("VERIFY-003 IDENTIFIER SEQUENCE STRUCTURE")

    print_json(
        load_relevant_structure(
            database,
            "sp_identifier_sequence",
            (
                "identifier_sequence_id",
                "identifier_target_code",
                "identifier_prefix",
                "sequence_date",
                "current_sequence_no",
                "sequence_length",
                "status_code",
                "created_dt",
                "created_by",
                "updated_dt",
                "updated_by",
                "program_id",
            ),
        )
    )

    print_section("VERIFY-004 IDENTIFIER SEQUENCE DATA")
    print_json(sequence_rows)

    if not sequence_rows:
        raise RuntimeError(
            "CM_ROLE_RULE Identifier Sequence data was not found."
        )

    latest_sequence = sequence_rows[0]

    lock_status = verify_lock_released(
        database,
        request=request,
        sequence_date=str(
            latest_sequence["sequence_date"]
        ),
    )

    print_section("VERIFY-005 NAMED LOCK RELEASE")
    print_json(lock_status)

    if int(lock_status["is_free"]) != 1:
        raise RuntimeError(
            "Identifier Named Lock was not released. "
            f"lock_name={lock_status['lock_name']}"
        )

    print_section("INTEGRATION TEST RESULT")

    print("OBJECT CODE        : CM_ROLE_RULE")
    print(f"OBJECT ID          : {saved_object['object_id']}")
    print(
        "SEQUENCE NO       : "
        f"{latest_sequence['current_sequence_no']}"
    )
    print(
        "LOCK RELEASED     : "
        f"{lock_status['is_free'] == 1}"
    )
    print("SP_OBJECT SAVE     : OK")
    print("SEQUENCE SAVE      : OK")
    print("TRANSACTION        : OK")
    print("STATUS             : OK")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
