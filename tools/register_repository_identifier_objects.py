"""Rule 공통코드 계약을 통해 Repository Identifier Object를 등록한다."""

from __future__ import annotations

import argparse
import json
from typing import Any

from common.common_function import (
    load_rule_common_code_contract,
    validate_common_code_value,
)
from common.database import CommonDatabase
from engine.object_definition_engine import ObjectDefinitionEngine


PROGRAM_ID = "REGISTER_REPOSITORY_IDENTIFIER_OBJECTS"


def build_requests(
    common_database: CommonDatabase,
    contract: dict[str, Any],
) -> list[dict[str, Any]]:
    """공통코드 계약을 ObjectDefinitionEngine 요청으로 변환한다."""
    object_codes = contract.get("identifier_object_codes")
    definitions = contract.get("identifier_object_definitions")
    if not isinstance(object_codes, dict) or not isinstance(definitions, dict):
        raise ValueError(
            "Repository Rule common-code contract requires "
            "identifier_object_codes and identifier_object_definitions."
        )

    required_values = (
        "object_definition_business_code",
        "object_definition_domain_code",
        "object_type_code",
        "sequence_scope_code",
        "sequence_length",
    )
    missing = [key for key in required_values if contract.get(key) in (None, "")]
    if missing:
        raise ValueError(f"Repository Identifier Object contract is incomplete: {missing}")

    requests: list[dict[str, Any]] = []
    for bucket, definition in definitions.items():
        if bucket not in object_codes or not isinstance(definition, dict):
            raise ValueError(f"Invalid Identifier Object definition: bucket={bucket}")

        missing_definition_values = [
            key
            for key in ("identifier_target_code", "object_level")
            if definition.get(key) in (None, "")
        ]
        if missing_definition_values:
            raise ValueError(
                "Identifier Object definition is incomplete: "
                f"bucket={bucket}, missing={missing_definition_values}"
            )

        target_code = validate_common_code_value(
            common_database,
            "SPS_IDENTIFIER_TARGET",
            str(definition["identifier_target_code"]),
        )
        requests.append(
            {
                "object_code": str(object_codes[bucket]),
                "object_name": str(definition.get("object_name") or object_codes[bucket]),
                "object_description": str(definition.get("object_description") or ""),
                "business_code": str(contract["object_definition_business_code"]),
                "domain_code": str(contract["object_definition_domain_code"]),
                "object_type_code": str(contract["object_type_code"]),
                "object_level": int(definition["object_level"]),
                "identifier_target_code": target_code,
                "sequence_scope_code": str(contract["sequence_scope_code"]),
                "sequence_length": int(contract["sequence_length"]),
                "status_code": "ACTIVE",
                "active_yn": "Y",
                "version_num": "v1.0",
                "created_by": PROGRAM_ID,
                "updated_by": PROGRAM_ID,
                "client_ip": "127.0.0.1",
                "program_id": PROGRAM_ID,
            }
        )
    return requests


def register(rule_code: str) -> list[dict[str, Any]]:
    """Rule 계약을 읽고 ObjectDefinitionEngine으로 Object를 등록한다."""
    common_database = CommonDatabase(database_role="COMMON")
    story_database = CommonDatabase(database_role="STORY_PLATFORM")
    try:
        contract = load_rule_common_code_contract(common_database, rule_code)
        engine = ObjectDefinitionEngine(story_database)
        return [engine.create(request) for request in build_requests(common_database, contract)]
    finally:
        common_database.close()
        story_database.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rule-code", required=True)
    arguments = parser.parse_args()
    print(json.dumps(register(arguments.rule_code), ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
