"""
File Story
UI Runtime Object Definition Common Code 계약을 읽어 ObjectDefinitionEngine으로 등록한다.

Change History
20260731 | Codex | UI Object 정의를 metadata-driven Identifier 발급으로 등록한다.
"""

from __future__ import annotations

import json
from typing import Any

from common.database import CommonDatabase
from engine.object_definition import ObjectDefinitionEngine

PROGRAM_ID = "REGISTER_UI_REPOSITORY_OBJECTS"
ACTOR_ID = "SYSTEM"
CLIENT_IP = "127.0.0.1"
DEFINITION_GROUP_CODE = "UI_RUNTIME_OBJECT_DEFINITION"

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


def load_definitions(database: CommonDatabase) -> list[dict[str, Any]]:
    """Load active UI Object requests only from the Common Repository."""
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
            raise ValueError(f"Invalid UI Object definition: code={row['code']}")
        missing = [field for field in _REQUIRED_FIELDS if contract.get(field) in (None, "")]
        if missing:
            raise ValueError(
                f"Incomplete UI Object definition: code={row['code']}, missing={missing}"
            )
        if contract["object_code"] != row["code"]:
            raise ValueError(
                f"UI Object definition code mismatch: code={row['code']}, "
                f"object_code={contract['object_code']}"
            )
        definitions.append(contract)
    if not definitions:
        raise ValueError("No active UI Runtime Object definitions are registered.")
    return definitions


def register() -> list[dict[str, Any]]:
    """Issue IDs through ObjectDefinitionEngine and persist missing UI Objects."""
    common_database = CommonDatabase(database_role="COMMON")
    story_database = CommonDatabase(database_role="STORY_PLATFORM")
    try:
        engine = ObjectDefinitionEngine(story_database)
        results: list[dict[str, Any]] = []
        for definition in load_definitions(common_database):
            existing = story_database.fetch_one(
                """
                SELECT object_id, object_code
                FROM sp_object
                WHERE object_code = %s
                  AND deleted_dt IS NULL
                """,
                (definition["object_code"],),
            )
            if existing:
                results.append(
                    {
                        "object_code": definition["object_code"],
                        "object_id": existing["object_id"],
                        "status": "ALREADY_EXISTS",
                    }
                )
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
