"""Identifier Engine으로 SPS Object Level 분류 Rule을 멱등 등록한다."""

from __future__ import annotations

import json
from typing import Any

from common.common_function import validate_common_code_value
from common.database import CommonDatabase
from engine.identifier_engine import IdentifierEngine
from engine.object_definition_engine import ObjectDefinitionEngine


PROGRAM_ID = "REGISTER_OBJECT_LEVEL_CLASSIFICATION_RULE"
RULE_OBJECT_CODE = "RL_RULE"
RULE_CODE = "RL_OBJECT_LEVEL_CLASSIFICATION"
RULE_TYPE_GROUP_CODE = "RULE_TYPE"
RULE_TYPE_CODE = "LIFECYCLE"
RULE_GROUP_CODE = "OBJECT_LEVEL"
RULE_DEFINITION = {
    "rule_name": "SPS Object Level 분류 규칙",
    "rule_description": (
        "ERD Object ID는 Level 2이고 Entity·Relationship·Rule Object ID는 Level 3이다. "
        "Rule에 명시되지 않은 Object ID의 기본 Level은 3이다. "
        "target_identifier_field가 있는 Table ID는 명시 Condition으로 Level 4를 적용한다. "
        "테이블명, PK 형태, 저장 위치, SQL 행위로 Level을 결정하지 않는다."
    ),
    "priority_no": 100,
    "version_num": "1.2",
    "remark": "DEFAULT_OBJECT_ID_LEVEL=3; EXPLICIT_TABLE_ID_LEVEL=4; EXPLICIT_CONDITION_FIRST",
    "sort_no": 10,
}


def ensure_identifier_sequence(story_database: CommonDatabase) -> None:
    """기존 RL_RULE Object metadata로 현재 채번 기준 Sequence를 보장한다."""
    object_metadata = story_database.fetch_one(
        """
        SELECT
            object_code, object_name, object_description,
            business_code, domain_code, object_type_code, object_level,
            identifier_target_code, sequence_scope_code, sequence_length,
            status_code, active_yn, version_num,
            created_by, updated_by, client_ip, program_id
        FROM sp_object
        WHERE object_code = %s
          AND active_yn = 'Y'
          AND status_code = 'ACTIVE'
          AND deleted_dt IS NULL
        LIMIT 1
        """,
        (RULE_OBJECT_CODE,),
    )
    if not object_metadata:
        raise ValueError(
            f"Rule Identifier Object metadata not found: object_code={RULE_OBJECT_CODE}"
        )
    ObjectDefinitionEngine(story_database).create(dict(object_metadata))


def resolve_rule_id(
    common_database: CommonDatabase,
    story_database: CommonDatabase,
) -> str:
    """기존 Rule ID를 재사용하고, 없을 때만 Identifier Engine으로 발급한다."""
    existing = common_database.fetch_one(
        """
        SELECT rule_id
        FROM rl_rule
        WHERE rule_code = %s
          AND deleted_dt IS NULL
        LIMIT 1
        """,
        (RULE_CODE,),
    )
    if existing:
        return str(existing["rule_id"])
    ensure_identifier_sequence(story_database)
    return IdentifierEngine(story_database).generate(RULE_OBJECT_CODE)


def register() -> dict[str, Any]:
    """Object Level 분류 Rule을 등록하거나 정책을 갱신한다."""
    common_database = CommonDatabase(database_role="COMMON")
    story_database = CommonDatabase(database_role="STORY_PLATFORM")
    try:
        rule_id = resolve_rule_id(common_database, story_database)
        rule_type_code = validate_common_code_value(
            common_database,
            RULE_TYPE_GROUP_CODE,
            RULE_TYPE_CODE,
        )

        common_database.begin()
        try:
            common_database.execute(
                """
                INSERT INTO rl_rule
                (
                    rule_id, rule_code, rule_name, rule_type_code, rule_group_code,
                    rule_description, priority_no, status_code, version_num, remark, sort_no,
                    created_by, updated_by, program_id, client_ip
                )
                VALUES
                (%s, %s, %s, %s, %s, %s, %s, 'ACTIVE', %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    rule_name = VALUES(rule_name),
                    rule_type_code = VALUES(rule_type_code),
                    rule_group_code = VALUES(rule_group_code),
                    rule_description = VALUES(rule_description),
                    priority_no = VALUES(priority_no),
                    status_code = 'ACTIVE',
                    version_num = VALUES(version_num),
                    remark = VALUES(remark),
                    sort_no = VALUES(sort_no),
                    deleted_by = NULL,
                    deleted_dt = NULL,
                    updated_dt = CURRENT_TIMESTAMP,
                    updated_by = VALUES(updated_by),
                    program_id = VALUES(program_id),
                    client_ip = VALUES(client_ip)
                """,
                (
                    rule_id,
                    RULE_CODE,
                    RULE_DEFINITION["rule_name"],
                    rule_type_code,
                    RULE_GROUP_CODE,
                    RULE_DEFINITION["rule_description"],
                    RULE_DEFINITION["priority_no"],
                    RULE_DEFINITION["version_num"],
                    RULE_DEFINITION["remark"],
                    RULE_DEFINITION["sort_no"],
                    PROGRAM_ID,
                    PROGRAM_ID,
                    PROGRAM_ID,
                    "127.0.0.1",
                ),
            )
            saved = common_database.fetch_one(
                """
                SELECT
                    rule_id, rule_code, rule_name, rule_type_code, rule_group_code,
                    rule_description, priority_no, status_code, version_num, remark, sort_no
                FROM rl_rule
                WHERE rule_code = %s
                  AND deleted_dt IS NULL
                LIMIT 1
                """,
                (RULE_CODE,),
            )
            if not saved:
                raise RuntimeError(
                    f"Object Level classification Rule verification failed: {RULE_CODE}"
                )
            common_database.commit()
            return dict(saved)
        except Exception:
            common_database.rollback()
            raise
    finally:
        common_database.close()
        story_database.close()


def main() -> int:
    print(json.dumps(register(), ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
