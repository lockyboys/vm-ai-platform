"""Object Level 분류 Rule의 Action Metadata 연결을 멱등 등록한다."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from common.database import CommonDatabase
from engine.identifier_engine import IdentifierEngine
from engine.object_definition_engine import ObjectDefinitionEngine
from tools.register_object_level_classification_rule import RULE_CODE

PROGRAM_ID = "REGISTER_OBJECT_LEVEL_CLASSIFICATION_RULE_ACTION"
ACTION_TYPE_GROUP_CODE = "ACTION_TYPE"
ACTION_TYPE_CODE = "OBJECT_LEVEL_CLASSIFICATION"
QUERY_NAME = "Object Level 기본 분류 Stored Procedure"
QUERY_TARGET_IDENTIFIER_FIELD = "query_id"
RULE_ACTION_TARGET_IDENTIFIER_FIELD = "rule_action_id"
PROCEDURE_NAME = "sp_resolve_object_level_classification"


def build_action_value(verified_query_id: str) -> str:
    """Runtime이 해석할 Rule Action 계약 JSON을 만든다."""
    return json.dumps(
        {
            "verified_query_id": verified_query_id,
            "resolution_order": ["EXPLICIT_RULE", "DEFAULT"],
            "default_object_level": 4,
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def _load_identifier_object(
    story_database: CommonDatabase, target_identifier_field: str
) -> dict[str, Any]:
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
        (target_identifier_field,),
    )
    if not row:
        raise ValueError(
            "Identifier Object metadata not found: "
            f"target_identifier_field={target_identifier_field}"
        )
    return dict(row)


def _issue_identifier(story_database: CommonDatabase, target_identifier_field: str) -> str:
    """기존 Object metadata의 Sequence만 보장한 뒤 Identifier를 발급한다."""
    metadata = _load_identifier_object(story_database, target_identifier_field)
    identifier_engine = IdentifierEngine(story_database)
    object_engine = ObjectDefinitionEngine(story_database)
    blueprint = identifier_engine.load_identifier_blueprint(int(metadata["object_level"]))
    sequence_length = int(metadata["sequence_length"])
    now = datetime.now()
    sequence_date = identifier_engine.resolve_sequence_date(
        metadata["sequence_scope_code"], now
    )

    story_database.begin()
    try:
        object_engine._ensure_sequence_metadata(
            metadata, blueprint, sequence_date, sequence_length, now
        )
        story_database.commit()
    except Exception:
        story_database.rollback()
        raise
    return identifier_engine.generate(metadata["object_code"])


def _resolve_rule_id(common_database: CommonDatabase) -> str:
    row = common_database.fetch_one(
        """
        SELECT rule_id
        FROM rl_rule
        WHERE rule_code = %s
          AND status_code = 'ACTIVE'
          AND deleted_dt IS NULL
        LIMIT 1
        """,
        (RULE_CODE,),
    )
    if not row:
        raise LookupError(f"Active Object Level Rule not found: {RULE_CODE}")
    return str(row["rule_id"])


def _resolve_query_id(
    common_database: CommonDatabase, story_database: CommonDatabase
) -> str:
    row = common_database.fetch_one(
        """
        SELECT query_id
        FROM cm_verified_sql_query
        WHERE query_name = %s
          AND deleted_dt IS NULL
        ORDER BY query_id
        LIMIT 1
        """,
        (QUERY_NAME,),
    )
    return str(row["query_id"]) if row else _issue_identifier(
        story_database, QUERY_TARGET_IDENTIFIER_FIELD
    )


def _resolve_rule_action_id(
    common_database: CommonDatabase,
    story_database: CommonDatabase,
    rule_id: str,
) -> str:
    row = common_database.fetch_one(
        """
        SELECT rule_action_id
        FROM rl_rule_action
        WHERE rule_id = %s
          AND action_type_code = %s
          AND deleted_dt IS NULL
        ORDER BY rule_action_id
        LIMIT 1
        """,
        (rule_id, ACTION_TYPE_CODE),
    )
    return str(row["rule_action_id"]) if row else _issue_identifier(
        story_database, RULE_ACTION_TARGET_IDENTIFIER_FIELD
    )


def _register_action_metadata(common_database: CommonDatabase) -> None:
    common_database.execute(
        """
        INSERT INTO cm_common_code
        (
            group_code, code, code_name, common_code_description, sort_no,
            status_code, created_by, updated_by, client_ip, program_id,
            common_code_json, lifecycle_status_code
        )
        SELECT
            %s, %s, %s, %s, %s,
            'ACTIVE', 'SYSTEM', 'SYSTEM', '127.0.0.1', %s,
            %s, 'CREATE_MAINTAIN'
        WHERE EXISTS
        (
            SELECT 1
            FROM cm_common_code_group
            WHERE group_code = %s
              AND status_code = 'ACTIVE'
        )
        ON DUPLICATE KEY UPDATE
            code_name = VALUES(code_name),
            common_code_description = VALUES(common_code_description),
            sort_no = VALUES(sort_no),
            status_code = VALUES(status_code),
            updated_dt = CURRENT_TIMESTAMP,
            updated_by = VALUES(updated_by),
            deleted_by = NULL,
            deleted_dt = NULL,
            client_ip = VALUES(client_ip),
            program_id = VALUES(program_id),
            common_code_json = VALUES(common_code_json),
            lifecycle_status_code = VALUES(lifecycle_status_code)
        """,
        (
            ACTION_TYPE_GROUP_CODE,
            ACTION_TYPE_CODE,
            "Object Level 기본 분류",
            "Rule에 명시된 Level이 없을 때 기본 Object Level 4를 반환하는 Action Metadata.",
            130,
            PROGRAM_ID,
            json.dumps(
                {
                    "action_code": ACTION_TYPE_CODE,
                    "procedure_name": PROCEDURE_NAME,
                    "default_object_level": 4,
                    "resolution_order": ["EXPLICIT_RULE", "DEFAULT"],
                    "hardcoding_allowed": False,
                },
                ensure_ascii=False,
            ),
            ACTION_TYPE_GROUP_CODE,
        ),
    )


def register() -> dict[str, Any]:
    """Procedure가 준비된 뒤 Query와 Rule Action Repository 계약을 저장한다."""
    common_database = CommonDatabase(database_role="COMMON")
    story_database = CommonDatabase(database_role="STORY_PLATFORM")
    try:
        rule_id = _resolve_rule_id(common_database)
        query_id = _resolve_query_id(common_database, story_database)
        rule_action_id = _resolve_rule_action_id(
            common_database, story_database, rule_id
        )
        query_contract = {
            "procedure_name": PROCEDURE_NAME,
            "parameter_definition": {"type": "object", "required": []},
            "result_definition": {
                "type": "object",
                "required": ["rule_code", "default_object_level"],
            },
            "database_role": "COMMON",
            "transaction_required_yn": "N",
            "transaction_required": False,
            "rollback_policy": "NONE",
            "rollback_on_error": False,
            "timeout_seconds": 30,
        }
        common_database.begin()
        try:
            _register_action_metadata(common_database)
            common_database.execute(
                """
                INSERT INTO cm_verified_sql_query
                (
                    query_id, query_name, query_description, crud_type, sql_text,
                    verified_yn, certified_level_code, verification_description,
                    created_by, verified_by, verified_dt,
                    story_programming_rule_pass_yn, snake_case_pass_yn,
                    table_exists_pass_yn, column_exists_pass_yn, crud_match_pass_yn,
                    where_clause_pass_yn, status_code, program_id, client_ip
                )
                VALUES
                (
                    %s, %s, %s, 'PROCEDURE', %s,
                    'Y', 'A', %s,
                    'SYSTEM', 'SYSTEM', CURRENT_TIMESTAMP,
                    'Y', 'Y', 'Y', 'Y', 'Y', 'Y',
                    'ACTIVE', %s, '127.0.0.1'
                )
                ON DUPLICATE KEY UPDATE
                    query_name = VALUES(query_name),
                    query_description = VALUES(query_description),
                    crud_type = VALUES(crud_type),
                    sql_text = VALUES(sql_text),
                    verified_yn = VALUES(verified_yn),
                    certified_level_code = VALUES(certified_level_code),
                    verification_description = VALUES(verification_description),
                    verified_by = VALUES(verified_by),
                    verified_dt = VALUES(verified_dt),
                    story_programming_rule_pass_yn = VALUES(story_programming_rule_pass_yn),
                    snake_case_pass_yn = VALUES(snake_case_pass_yn),
                    table_exists_pass_yn = VALUES(table_exists_pass_yn),
                    column_exists_pass_yn = VALUES(column_exists_pass_yn),
                    crud_match_pass_yn = VALUES(crud_match_pass_yn),
                    where_clause_pass_yn = VALUES(where_clause_pass_yn),
                    status_code = VALUES(status_code),
                    updated_dt = CURRENT_TIMESTAMP,
                    updated_by = VALUES(created_by),
                    deleted_by = NULL,
                    deleted_dt = NULL,
                    program_id = VALUES(program_id),
                    client_ip = VALUES(client_ip)
                """,
                (
                    query_id,
                    QUERY_NAME,
                    json.dumps(query_contract, ensure_ascii=False),
                    f"CALL {PROCEDURE_NAME}(?)",
                    "Object Level Rule 기본값 4를 반환하는 Stored Procedure 계약 검증 완료.",
                    PROGRAM_ID,
                ),
            )
            common_database.execute(
                """
                INSERT INTO rl_rule_action
                (
                    rule_action_id, rule_id, action_type_code, action_value,
                    sort_no, remark, created_by, updated_by, program_id,
                    client_ip, status_code
                )
                VALUES
                (%s, %s, %s, %s, %s, %s, 'SYSTEM', 'SYSTEM', %s, '127.0.0.1', 'ACTIVE')
                ON DUPLICATE KEY UPDATE
                    action_value = VALUES(action_value),
                    sort_no = VALUES(sort_no),
                    remark = VALUES(remark),
                    updated_by = VALUES(updated_by),
                    deleted_by = NULL,
                    deleted_dt = NULL,
                    program_id = VALUES(program_id),
                    client_ip = VALUES(client_ip),
                    status_code = VALUES(status_code)
                """,
                (
                    rule_action_id,
                    rule_id,
                    ACTION_TYPE_CODE,
                    build_action_value(query_id),
                    10,
                    "Rule 등록값이 없으면 Object Level 4를 적용하는 Action Metadata 계약.",
                    PROGRAM_ID,
                ),
            )
            common_database.commit()
        except Exception:
            common_database.rollback()
            raise
        return {
            "rule_id": rule_id,
            "rule_code": RULE_CODE,
            "rule_action_id": rule_action_id,
            "action_type_code": ACTION_TYPE_CODE,
            "verified_query_id": query_id,
            "procedure_name": PROCEDURE_NAME,
        }
    finally:
        common_database.close()
        story_database.close()


def main() -> int:
    print(json.dumps(register(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
