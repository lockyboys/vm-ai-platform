# =============================================================================
# File Name   : tools/run_sp_relationship_data_type_alter_20260720.py
# Purpose     : One-time sp_relationship Data Type Migration Batch
# =============================================================================
# This is an intentionally hardcoded one-time migration batch.
# Flow:
#   1. Validate original table and pre/post state
#   2. Create structure backup
#   3. Copy backup rows inside a transaction
#   4. Verify original/backup counts
#   5. Execute one atomic ALTER TABLE statement
#   6. Verify 18 target columns and preserved row count
#   7. On rerun, verify completed state without changing data
# =============================================================================

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.database import CommonDatabase


DATABASE_ROLE = "STORY_PLATFORM"
TARGET_TABLE = "sp_relationship"
BACKUP_TABLE = "sp_relationship_backup_20260720_01"
EXPECTED_ROW_COUNT = 4

BEFORE_TYPES = {
    "relationship_id": "varchar(150)",
    "relationship_scope_code": "varchar(30)",
    "erd_id": "varchar(30)",
    "source_entity_id": "varchar(30)",
    "source_object_id": "varchar(150)",
    "source_object_type_code": "varchar(50)",
    "target_entity_id": "varchar(30)",
    "target_object_id": "varchar(150)",
    "target_object_type_code": "varchar(50)",
    "relationship_code": "varchar(100)",
    "relationship_type_code": "varchar(30)",
    "delete_rule_code": "varchar(30)",
    "update_rule_code": "varchar(30)",
    "created_by": "varchar(50)",
    "updated_by": "varchar(50)",
    "deleted_by": "varchar(50)",
    "client_ip": "varchar(45)",
    "program_id": "varchar(100)",
}
AFTER_TYPES = {column_name: "varchar(99)" for column_name in BEFORE_TYPES}

SHRINK_LIMITS = {
    "relationship_id": 99,
    "source_object_id": 99,
    "target_object_id": 99,
    "relationship_code": 99,
    "program_id": 99,
}

ALTER_SQL = """
ALTER TABLE sp_relationship
    MODIFY COLUMN relationship_id VARCHAR(99) NOT NULL
        COMMENT 'Relationship Object ID. Identifier Engine이 생성한 Level 3 정식 식별자',
    MODIFY COLUMN relationship_scope_code VARCHAR(99) NOT NULL DEFAULT 'ERD'
        COMMENT 'Relationship Scope Code. ERD 또는 OBJECT',
    MODIFY COLUMN erd_id VARCHAR(99) DEFAULT NULL
        COMMENT 'ERD Scope에서 사용하는 ERD ID',
    MODIFY COLUMN source_entity_id VARCHAR(99) DEFAULT NULL
        COMMENT 'ERD Scope에서 사용하는 Source Entity ID',
    MODIFY COLUMN source_object_id VARCHAR(99) DEFAULT NULL
        COMMENT 'OBJECT Scope에서 사용하는 Source Object 식별자',
    MODIFY COLUMN source_object_type_code VARCHAR(99) DEFAULT NULL
        COMMENT 'Source Object 유형 코드. KNOWLEDGE, LIFECYCLE, RULE, VERIFIED_SQL 등',
    MODIFY COLUMN target_entity_id VARCHAR(99) DEFAULT NULL
        COMMENT 'ERD Scope에서 사용하는 Target Entity ID',
    MODIFY COLUMN target_object_id VARCHAR(99) DEFAULT NULL
        COMMENT 'OBJECT Scope에서 사용하는 Target Object 식별자',
    MODIFY COLUMN target_object_type_code VARCHAR(99) DEFAULT NULL
        COMMENT 'Target Object 유형 코드. KNOWLEDGE, LIFECYCLE, RULE, VERIFIED_SQL 등',
    MODIFY COLUMN relationship_code VARCHAR(99) NOT NULL
        COMMENT 'Relationship Code. 사람이 이해하고 Generator가 참조할 수 있는 의미 기반 식별 코드',
    MODIFY COLUMN relationship_type_code VARCHAR(99) NOT NULL DEFAULT 'FK'
        COMMENT 'Relationship Type Code. Engine과 Generator의 처리 방식을 결정한다',
    MODIFY COLUMN delete_rule_code VARCHAR(99) DEFAULT NULL
        COMMENT '삭제 시 Relationship 처리 규칙',
    MODIFY COLUMN update_rule_code VARCHAR(99) DEFAULT NULL
        COMMENT '변경 시 Relationship 처리 규칙',
    MODIFY COLUMN created_by VARCHAR(99) NOT NULL DEFAULT 'SYSTEM'
        COMMENT 'Relationship 최초 생성 주체',
    MODIFY COLUMN updated_by VARCHAR(99) DEFAULT NULL
        COMMENT 'Relationship 최종 수정 주체',
    MODIFY COLUMN deleted_by VARCHAR(99) DEFAULT NULL
        COMMENT 'Relationship 삭제 처리 주체',
    MODIFY COLUMN client_ip VARCHAR(99) DEFAULT NULL
        COMMENT 'Relationship 변경 요청 클라이언트 IP',
    MODIFY COLUMN program_id VARCHAR(99) DEFAULT NULL
        COMMENT 'Relationship 변경 프로그램 또는 Generator'
""".strip()


def table_exists(database: CommonDatabase, table_name: str) -> bool:
    row = database.fetch_one(
        """
        SELECT COUNT(*) AS table_count
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND table_type = 'BASE TABLE'
        """,
        (table_name,),
    )
    return int(row["table_count"]) == 1


def row_count(database: CommonDatabase, table_name: str) -> int:
    # table_name is an internal hardcoded constant in this one-time batch.
    row = database.fetch_one(f"SELECT COUNT(*) AS row_count FROM `{table_name}`")
    return int(row["row_count"])


def column_types(database: CommonDatabase, table_name: str) -> dict[str, str]:
    rows = database.fetch_all(
        """
        SELECT column_name, column_type
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table_name,),
    )
    return {
        str(row["column_name"]): str(row["column_type"]).lower()
        for row in rows
    }


def mismatches(
    actual_types: dict[str, str],
    expected_types: dict[str, str],
) -> dict[str, dict[str, str | None]]:
    return {
        column_name: {
            "actual": actual_types.get(column_name),
            "expected": expected_type,
        }
        for column_name, expected_type in expected_types.items()
        if actual_types.get(column_name) != expected_type
    }


def validate_shrink_lengths(database: CommonDatabase) -> dict[str, int]:
    expressions = ",\n            ".join(
        f"MAX(CHAR_LENGTH(`{column_name}`)) AS `{column_name}`"
        for column_name in SHRINK_LIMITS
    )
    row = database.fetch_one(
        f"""
        SELECT
            {expressions}
        FROM `{TARGET_TABLE}`
        """
    )
    profile = {
        column_name: int(row.get(column_name) or 0)
        for column_name in SHRINK_LIMITS
    }
    violations = {
        column_name: actual_length
        for column_name, actual_length in profile.items()
        if actual_length > SHRINK_LIMITS[column_name]
    }
    if violations:
        raise RuntimeError(
            "Shrink validation failed: "
            + json.dumps(violations, ensure_ascii=False, sort_keys=True)
        )
    return profile


def verify_backup(
    database: CommonDatabase,
    original_count: int,
) -> dict[str, Any]:
    if not table_exists(database, BACKUP_TABLE):
        raise RuntimeError(f"Backup table not found: {BACKUP_TABLE}")

    backup_count = row_count(database, BACKUP_TABLE)
    if backup_count != original_count:
        raise RuntimeError(
            f"Backup row count mismatch: original={original_count}, "
            f"backup={backup_count}"
        )

    backup_types = column_types(database, BACKUP_TABLE)
    backup_type_mismatches = mismatches(backup_types, BEFORE_TYPES)
    if backup_type_mismatches:
        raise RuntimeError(
            "Backup does not preserve the pre-migration column types: "
            + json.dumps(
                backup_type_mismatches,
                ensure_ascii=False,
                sort_keys=True,
            )
        )

    return {
        "backup_table": BACKUP_TABLE,
        "backup_row_count": backup_count,
        "backup_type_status": "PASS",
    }


def create_and_copy_backup(
    database: CommonDatabase,
    original_count: int,
) -> dict[str, Any]:
    database.execute(
        f"CREATE TABLE `{BACKUP_TABLE}` LIKE `{TARGET_TABLE}`"
    )

    try:
        database.begin()
        database.execute(
            f"""
            INSERT INTO `{BACKUP_TABLE}`
            SELECT *
            FROM `{TARGET_TABLE}`
            """
        )
        backup_count = row_count(database, BACKUP_TABLE)
        if backup_count != original_count:
            raise RuntimeError(
                f"Backup row count mismatch: original={original_count}, "
                f"backup={backup_count}"
            )
        database.commit()
    except Exception:
        database.rollback()
        raise

    return verify_backup(database, original_count)


def output_result(result: dict[str, Any]) -> None:
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


def main() -> None:
    database = CommonDatabase(database_role=DATABASE_ROLE)
    try:
        resolved = database.fetch_one("SELECT DATABASE() AS database_name")
        if not table_exists(database, TARGET_TABLE):
            raise RuntimeError(f"Target table not found: {TARGET_TABLE}")

        original_count = row_count(database, TARGET_TABLE)
        if original_count != EXPECTED_ROW_COUNT:
            raise RuntimeError(
                f"Unexpected row count: expected={EXPECTED_ROW_COUNT}, "
                f"actual={original_count}"
            )

        actual_types = column_types(database, TARGET_TABLE)
        before_mismatches = mismatches(actual_types, BEFORE_TYPES)
        after_mismatches = mismatches(actual_types, AFTER_TYPES)

        if not after_mismatches:
            backup_result = verify_backup(database, original_count)
            output_result(
                {
                    "status": "ALREADY_COMPLETED",
                    "database_role": DATABASE_ROLE,
                    "resolved_database": resolved["database_name"],
                    "target_table": TARGET_TABLE,
                    "target_column_count": len(AFTER_TYPES),
                    "row_count": original_count,
                    **backup_result,
                }
            )
            return

        if before_mismatches:
            raise RuntimeError(
                "Mixed or unknown pre-migration schema state: "
                + json.dumps(
                    before_mismatches,
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )

        shrink_profile = validate_shrink_lengths(database)

        if table_exists(database, BACKUP_TABLE):
            backup_result = verify_backup(database, original_count)
        else:
            backup_result = create_and_copy_backup(database, original_count)

        database.execute(ALTER_SQL)
        database.commit()

        post_types = column_types(database, TARGET_TABLE)
        post_mismatches = mismatches(post_types, AFTER_TYPES)
        if post_mismatches:
            raise RuntimeError(
                "Post-migration schema verification failed: "
                + json.dumps(
                    post_mismatches,
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )

        post_count = row_count(database, TARGET_TABLE)
        if post_count != original_count:
            raise RuntimeError(
                f"Post-migration row count mismatch: before={original_count}, "
                f"after={post_count}"
            )

        output_result(
            {
                "status": "SUCCESS",
                "database_role": DATABASE_ROLE,
                "resolved_database": resolved["database_name"],
                "target_table": TARGET_TABLE,
                "target_column_count": len(AFTER_TYPES),
                "row_count_before": original_count,
                "row_count_after": post_count,
                "shrink_profile": shrink_profile,
                **backup_result,
            }
        )
    except Exception as error:
        try:
            database.rollback()
        except Exception:
            pass
        output_result(
            {
                "status": "FAILED",
                "database_role": DATABASE_ROLE,
                "target_table": TARGET_TABLE,
                "error_type": type(error).__name__,
                "error": str(error),
            }
        )
        raise
    finally:
        database.close()


if __name__ == "__main__":
    main()
