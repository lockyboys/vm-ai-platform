"""
File Story
MongoDB Runtime Object Definition Common Code 계약을 읽어 ObjectDefinitionEngine으로 등록하거나
기존 SPS Object를 같은 계약으로 재동기화한다.

Change History
20260801 | Codex | MongoDB Object 정의를 metadata-driven Identifier 발급으로 등록한다.
20260801 | Codex | 기존 MongoDB Object도 Common Repository 계약값으로 재동기화한다.
"""

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


PROGRAM_ID = "REGISTER_MONGODB_RUNTIME_OBJECTS"
ACTOR_ID = "SYSTEM"
CLIENT_IP = "127.0.0.1"
DEFINITION_GROUP_CODE = "MONGODB_RUNTIME_OBJECT_DEFINITION"

_REQUIRED_FIELDS = (
    "object_code",
    "object_name",
    "object_description",
    "business_code",
    "domain_code",
    "object_type_code",
    "object_level",
    "sort_no",
    "target_identifier_field",
    "identifier_target_code",
    "sequence_scope_code",
    "sequence_length",
)
_RECONCILIATION_FIELDS = (
    "object_name",
    "object_description",
    "business_code",
    "domain_code",
    "object_type_code",
    "object_level",
    "target_identifier_field",
    "identifier_target_code",
    "sequence_scope_code",
    "sequence_length",
)


def load_definitions(database: CommonDatabase) -> list[dict[str, Any]]:
    """Load active MongoDB Object definitions only from the Common Repository."""
    rows = database.fetch_all(
        """
        SELECT code, common_code_json
        FROM cm_common_code
        WHERE group_code = %s
          AND status_code = 'ACTIVE'
          AND deleted_dt IS NULL
        ORDER BY sort_no, code
        """,
        (DEFINITION_GROUP_CODE,),
    )
    definitions: list[dict[str, Any]] = []
    for row in rows:
        raw_contract = row.get("common_code_json")
        contract = json.loads(raw_contract) if isinstance(raw_contract, str) else raw_contract
        if not isinstance(contract, dict):
            raise ValueError(f"Invalid MongoDB Object definition: code={row['code']}")
        missing = [field for field in _REQUIRED_FIELDS if contract.get(field) in (None, "")]
        if missing:
            raise ValueError(
                f"Incomplete MongoDB Object definition: code={row['code']}, missing={missing}"
            )
        if contract["object_code"] != row["code"]:
            raise ValueError(
                f"MongoDB Object definition code mismatch: code={row['code']}, "
                f"object_code={contract['object_code']}"
            )
        definitions.append(contract)
    if not definitions:
        raise ValueError("No active MongoDB Runtime Object definitions are registered.")
    return definitions


def reconciliation_values(definition: dict[str, Any]) -> tuple[Any, ...]:
    """Build the mutable Object metadata values from one Common Repository contract."""
    return tuple(definition[field] for field in _RECONCILIATION_FIELDS)


def _reconcile_existing(
    database: CommonDatabase,
    existing: dict[str, Any],
    definition: dict[str, Any],
) -> dict[str, Any]:
    """Preserve Object ID and reconcile only mutable metadata from the active contract."""
    if all(existing.get(field) == definition[field] for field in _RECONCILIATION_FIELDS):
        return {
            "object_code": definition["object_code"],
            "object_id": existing["object_id"],
            "status": "ALREADY_CURRENT",
        }

    database.begin()
    try:
        affected_rows = database.execute(
            """
            UPDATE sp_object
            SET
                object_name = %s,
                object_description = %s,
                business_code = %s,
                domain_code = %s,
                object_type_code = %s,
                object_level = %s,
                target_identifier_field = %s,
                identifier_target_code = %s,
                sequence_scope_code = %s,
                sequence_length = %s,
                updated_dt = CURRENT_TIMESTAMP,
                updated_by = %s,
                client_ip = %s,
                program_id = %s
            WHERE object_id = %s
              AND deleted_dt IS NULL
            """,
            (
                *reconciliation_values(definition),
                ACTOR_ID,
                CLIENT_IP,
                PROGRAM_ID,
                existing["object_id"],
            ),
        )
        if affected_rows != 1:
            raise RuntimeError(
                f"MongoDB Object reconciliation failed: object_id={existing['object_id']}"
            )
        database.commit()
    except Exception:
        database.rollback()
        raise

    return {
        "object_code": definition["object_code"],
        "object_id": existing["object_id"],
        "status": "RECONCILED",
        "affected_rows": affected_rows,
    }


def register() -> list[dict[str, Any]]:
    """Issue missing IDs or reconcile existing MongoDB Objects from Common metadata."""
    common_database = CommonDatabase(database_role="COMMON")
    story_database = CommonDatabase(database_role="STORY_PLATFORM")
    try:
        engine = ObjectDefinitionEngine(story_database)
        results: list[dict[str, Any]] = []
        for definition in load_definitions(common_database):
            existing = story_database.fetch_one(
                """
                SELECT
                    object_id,
                    object_name,
                    object_description,
                    business_code,
                    domain_code,
                    object_type_code,
                    object_level,
                    target_identifier_field,
                    identifier_target_code,
                    sequence_scope_code,
                    sequence_length
                FROM sp_object
                WHERE object_code = %s
                  AND deleted_dt IS NULL
                """,
                (definition["object_code"],),
            )
            if existing:
                results.append(_reconcile_existing(story_database, existing, definition))
                continue
            request = {
                **definition,
                "status_code": "ACTIVE",
                "active_yn": "Y",
                "version_num": "v1.0",
                "created_by": ACTOR_ID,
                "updated_by": ACTOR_ID,
                "client_ip": CLIENT_IP,
                "program_id": PROGRAM_ID,
            }
            results.append(engine.create(request))
        return results
    finally:
        common_database.close()
        story_database.close()


if __name__ == "__main__":
    print(json.dumps(register(), ensure_ascii=False, indent=2, default=str))
