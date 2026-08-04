"""Object Level 분류 Rule의 Action Metadata 연결을 멱등 등록한다."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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
RULE_CONDITION_TARGET_IDENTIFIER_FIELD = "condition_id"
DEFAULT_CONDITION_FIELD_CODE = "rule_resolution_source"
DEFAULT_CONDITION_OPERATOR_CODE = "EQ"
DEFAULT_CONDITION_VALUE = "DEFAULT"
DEFAULT_CONDITION_SORT_NO = 40
CONDITION_FIELD_CODE = "object_code"
CONDITION_OPERATOR_CODE = "EQ"
DEFAULT_OBJECT_LEVEL = 4
OBJECT_LEVEL_BRANCHES: tuple[dict[str, Any], ...] = (
    {
        "condition_value": "ERD",
        "object_level": 2,
        "sort_no": 10,
    },
    {
        "condition_value": "ENTITY",
        "object_level": 3,
        "sort_no": 20,
    },
    {
        "condition_value": "RELATIONSHIP",
        "object_level": 3,
        "sort_no": 30,
    },
)


def build_action_value(*, verified_query_id: str, condition_id: str) -> str:
    """Negative(Default) Condition에 바인딩된 Rule Action 계약 JSON을 만든다."""
    normalized_condition_id = condition_id.strip()
    if not normalized_condition_id:
        raise ValueError("condition_id is required for a Negative Default Action.")
    return json.dumps(
        {
            "verified_query_id": verified_query_id,
            "action_type_group_code": ACTION_TYPE_GROUP_CODE,
            "condition_id": normalized_condition_id,
            "condition_context": {
                DEFAULT_CONDITION_FIELD_CODE: DEFAULT_CONDITION_VALUE,
            },
            "resolution_order": ["DEFAULT"],
            "default_object_level": DEFAULT_OBJECT_LEVEL,
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def build_explicit_action_value(*, condition_id: str, object_level: int) -> str:
    """condition_id에 바인딩된 Positive 분기의 Rule Action 계약을 만든다."""
    normalized_condition_id = condition_id.strip()
    if not normalized_condition_id:
        raise ValueError("condition_id is required for an explicit Object Level Action.")
    return json.dumps(
        {
            "action_type_group_code": ACTION_TYPE_GROUP_CODE,
            "condition_id": normalized_condition_id,
            "object_level": object_level,
            "resolution_order": ["EXPLICIT_RULE"],
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


def _resolve_rule_condition_id(
    common_database: CommonDatabase,
    story_database: CommonDatabase,
    rule_id: str,
    field_code: str,
    operator_code: str,
    condition_value: str,
) -> str:
    rows = list(
        common_database.fetch_all(
            """
            SELECT condition_id
            FROM rl_rule_condition
            WHERE rule_id = %s
              AND field_code = %s
              AND operator_code = %s
              AND condition_value = %s
              AND deleted_dt IS NULL
            ORDER BY condition_id
            """,
            (rule_id, field_code, operator_code, condition_value),
        )
    )
    if len(rows) > 1:
        raise LookupError(
            "Object Level Rule has duplicate Condition definitions. "
            f"rule_id={rule_id}, field_code={field_code}, "
            f"operator_code={operator_code}, condition_value={condition_value}"
        )
    return str(rows[0]["condition_id"]) if rows else _issue_identifier(
        story_database, RULE_CONDITION_TARGET_IDENTIFIER_FIELD
    )


def _resolve_rule_action_id(
    common_database: CommonDatabase,
    story_database: CommonDatabase,
    rule_id: str,
    condition_id: str | None,
) -> str:
    rows = list(
        common_database.fetch_all(
            """
            SELECT rule_action_id, action_value
            FROM rl_rule_action
            WHERE rule_id = %s
              AND action_type_code = %s
              AND deleted_dt IS NULL
            ORDER BY rule_action_id
            """,
            (rule_id, ACTION_TYPE_CODE),
        )
    )
    matching_action_ids: list[str] = []
    for row in rows:
        raw_contract = row.get("action_value")
        if raw_contract in (None, ""):
            contract: dict[str, Any] = {}
        else:
            try:
                contract = json.loads(raw_contract)
            except (TypeError, json.JSONDecodeError) as error:
                raise ValueError(
                    "Rule Action contract must be valid JSON. "
                    f"rule_action_id={row['rule_action_id']}"
                ) from error
            if not isinstance(contract, dict):
                raise ValueError(
                    "Rule Action contract must be an object. "
                    f"rule_action_id={row['rule_action_id']}"
                )

        stored_condition_id = contract.get("condition_id")
        if stored_condition_id not in (None, ""):
            stored_condition_id = str(stored_condition_id).strip()
        if stored_condition_id == "":
            raise ValueError(
                "Rule Action condition_id must not be blank. "
                f"rule_action_id={row['rule_action_id']}"
            )
        if stored_condition_id == condition_id:
            matching_action_ids.append(str(row["rule_action_id"]))

    if len(matching_action_ids) > 1:
        raise LookupError(
            "Object Level Rule has duplicate Condition-to-Action bindings. "
            f"rule_id={rule_id}, condition_id={condition_id}"
        )
    return (
        matching_action_ids[0]
        if matching_action_ids
        else _issue_identifier(story_database, RULE_ACTION_TARGET_IDENTIFIER_FIELD)
    )


def _resolve_default_rule_action_id(
    common_database: CommonDatabase,
    story_database: CommonDatabase,
    rule_id: str,
) -> str:
    rows = list(
        common_database.fetch_all(
            """
            SELECT rule_action_id, action_value
            FROM rl_rule_action
            WHERE rule_id = %s
              AND action_type_code = %s
              AND deleted_dt IS NULL
            ORDER BY rule_action_id
            """,
            (rule_id, ACTION_TYPE_CODE),
        )
    )
    matching_action_ids: list[str] = []
    for row in rows:
        raw_contract = row.get("action_value")
        if raw_contract in (None, ""):
            continue
        try:
            contract = json.loads(str(raw_contract))
        except (TypeError, json.JSONDecodeError) as error:
            raise ValueError(
                "Rule Action contract must be valid JSON. "
                f"rule_action_id={row['rule_action_id']}"
            ) from error
        if not isinstance(contract, dict):
            raise ValueError(
                "Rule Action contract must be an object. "
                f"rule_action_id={row['rule_action_id']}"
            )
        resolution_order = contract.get("resolution_order")
        if not isinstance(resolution_order, list):
            raise ValueError(
                "Rule Action resolution_order must be a JSON array. "
                f"rule_action_id={row['rule_action_id']}"
            )
        if "DEFAULT" in {
            str(resolution_source).strip().upper()
            for resolution_source in resolution_order
            if str(resolution_source).strip()
        }:
            matching_action_ids.append(str(row["rule_action_id"]))

    if len(matching_action_ids) > 1:
        raise LookupError(
            "Object Level Rule has multiple Default Actions. "
            f"rule_id={rule_id}, rule_action_ids={matching_action_ids}"
        )
    return (
        matching_action_ids[0]
        if matching_action_ids
        else _issue_identifier(story_database, RULE_ACTION_TARGET_IDENTIFIER_FIELD)
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
            "Condition에 바인딩된 명시 Level 또는 Negative Default Level을 반환하는 Action Metadata.",
            130,
            PROGRAM_ID,
            json.dumps(
                {
                    "action_code": ACTION_TYPE_CODE,
                    "procedure_name": PROCEDURE_NAME,
                    "default_object_level": DEFAULT_OBJECT_LEVEL,
                    "resolution_order": ["DEFAULT"],
                    "hardcoding_allowed": False,
                },
                ensure_ascii=False,
            ),
            ACTION_TYPE_GROUP_CODE,
        ),
    )


def _upsert_rule_condition(
    common_database: CommonDatabase,
    *,
    condition_id: str,
    rule_id: str,
    field_code: str,
    operator_code: str,
    condition_value: str,
    sort_no: int,
    remark: str,
) -> None:
    common_database.execute(
        """
        INSERT INTO rl_rule_condition
        (
            condition_id, rule_id, sort_no, field_code, operator_code, condition_value,
            logical_operator_code, remark, created_by, updated_by, program_id,
            client_ip, status_code
        )
        VALUES
        (%s, %s, %s, %s, %s, %s, NULL, %s, 'SYSTEM', 'SYSTEM', %s, '127.0.0.1', 'ACTIVE')
        ON DUPLICATE KEY UPDATE
            sort_no = VALUES(sort_no),
            field_code = VALUES(field_code),
            operator_code = VALUES(operator_code),
            condition_value = VALUES(condition_value),
            logical_operator_code = VALUES(logical_operator_code),
            remark = VALUES(remark),
            updated_by = VALUES(updated_by),
            deleted_by = NULL,
            deleted_dt = NULL,
            program_id = VALUES(program_id),
            client_ip = VALUES(client_ip),
            status_code = VALUES(status_code)
        """,
        (
            condition_id,
            rule_id,
            sort_no,
            field_code,
            operator_code,
            condition_value,
            remark,
            PROGRAM_ID,
        ),
    )


def _upsert_rule_action(
    common_database: CommonDatabase,
    *,
    rule_action_id: str,
    rule_id: str,
    action_value: str,
    sort_no: int,
    remark: str,
) -> None:
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
            action_value,
            sort_no,
            remark,
            PROGRAM_ID,
        ),
    )


def register() -> dict[str, Any]:
    """Positive Condition→Action 분기와 Negative Default Action을 멱등 등록한다."""
    common_database = CommonDatabase(database_role="COMMON")
    story_database = CommonDatabase(database_role="STORY_PLATFORM")
    try:
        rule_id = _resolve_rule_id(common_database)
        query_id = _resolve_query_id(common_database, story_database)
        default_condition_id = _resolve_rule_condition_id(
            common_database,
            story_database,
            rule_id,
            DEFAULT_CONDITION_FIELD_CODE,
            DEFAULT_CONDITION_OPERATOR_CODE,
            DEFAULT_CONDITION_VALUE,
        )
        branches: list[dict[str, Any]] = []
        for branch in OBJECT_LEVEL_BRANCHES:
            condition_id = _resolve_rule_condition_id(
                common_database,
                story_database,
                rule_id,
                CONDITION_FIELD_CODE,
                CONDITION_OPERATOR_CODE,
                str(branch["condition_value"]),
            )
            rule_action_id = _resolve_rule_action_id(
                common_database,
                story_database,
                rule_id,
                condition_id,
            )
            branches.append(
                {
                    **branch,
                    "condition_id": condition_id,
                    "rule_action_id": rule_action_id,
                }
            )

        default_rule_action_id = _resolve_default_rule_action_id(
            common_database,
            story_database,
            rule_id,
        )
        query_contract = {
            "procedure_name": PROCEDURE_NAME,
            "parameter_definition": {
                "type": "object",
                "required": [
                    "rule_id",
                    "rule_action_id",
                    "action_type_code",
                    "action_type_group_code",
                ],
            },
            "result_definition": {
                "type": "object",
                "required": [
                    "rule_id",
                    "rule_code",
                    "rule_action_id",
                    "action_type_code",
                    "default_object_level",
                    "resolution_source",
                ],
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
                    f"CALL {PROCEDURE_NAME}(%s)",
                    (
                        "Object Level Negative Default Action의 "
                        f"Repository 등록값 {DEFAULT_OBJECT_LEVEL}을 검증하는 Procedure 계약."
                    ),
                    PROGRAM_ID,
                ),
            )

            _upsert_rule_condition(
                common_database,
                condition_id=default_condition_id,
                rule_id=rule_id,
                field_code=DEFAULT_CONDITION_FIELD_CODE,
                operator_code=DEFAULT_CONDITION_OPERATOR_CODE,
                condition_value=DEFAULT_CONDITION_VALUE,
                sort_no=DEFAULT_CONDITION_SORT_NO,
                remark=(
                    "명시 Object Level Condition이 하나도 일치하지 않을 때 "
                    "Rule Resolution Source를 DEFAULT로 제공하는 Negative Condition."
                ),
            )
            for branch in branches:
                _upsert_rule_condition(
                    common_database,
                    condition_id=str(branch["condition_id"]),
                    rule_id=rule_id,
                    field_code=CONDITION_FIELD_CODE,
                    operator_code=CONDITION_OPERATOR_CODE,
                    condition_value=str(branch["condition_value"]),
                    sort_no=int(branch["sort_no"]),
                    remark=(
                        f"Repository Object Code EQ {branch['condition_value']} 분기."
                    ),
                )
                _upsert_rule_action(
                    common_database,
                    rule_action_id=str(branch["rule_action_id"]),
                    rule_id=rule_id,
                    action_value=build_explicit_action_value(
                        condition_id=str(branch["condition_id"]),
                        object_level=int(branch["object_level"]),
                    ),
                    sort_no=int(branch["sort_no"]),
                    remark=(
                        f"{CONDITION_FIELD_CODE} EQ {branch['condition_value']} "
                        f"일 때 Object Level {branch['object_level']}을 반환하는 Action."
                    ),
                )

            _upsert_rule_action(
                common_database,
                rule_action_id=default_rule_action_id,
                rule_id=rule_id,
                action_value=build_action_value(
                    verified_query_id=query_id,
                    condition_id=default_condition_id,
                ),
                sort_no=90,
                remark=(
                    "Negative Condition이 일치할 때 "
                    f"Rule 등록 기본 Level {DEFAULT_OBJECT_LEVEL}을 반환하는 Default Action."
                ),
            )
            common_database.commit()
        except Exception:
            common_database.rollback()
            raise

        return {
            "rule_id": rule_id,
            "rule_code": RULE_CODE,
            "default_rule_action_id": default_rule_action_id,
            "action_type_code": ACTION_TYPE_CODE,
            "default_condition": {
                "condition_id": default_condition_id,
                "field_code": DEFAULT_CONDITION_FIELD_CODE,
                "operator_code": DEFAULT_CONDITION_OPERATOR_CODE,
                "condition_value": DEFAULT_CONDITION_VALUE,
                "sort_no": DEFAULT_CONDITION_SORT_NO,
            },
            "verified_query_id": query_id,
            "procedure_name": PROCEDURE_NAME,
            "branches": [
                {
                    "condition_id": str(branch["condition_id"]),
                    "condition_value": str(branch["condition_value"]),
                    "rule_action_id": str(branch["rule_action_id"]),
                    "object_level": int(branch["object_level"]),
                }
                for branch in branches
            ],
        }
    finally:
        common_database.close()
        story_database.close()


def main() -> int:
    print(json.dumps(register(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
