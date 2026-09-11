#!/usr/bin/env python3
"""Run every row of approved storage-separation contracts through Harness."""
from __future__ import annotations
import argparse
import json
from typing import Any
from common.database import CommonDatabase
from harness.scripts.migrate_one_table_detail import _safe_identifier, migrate_one, _load_contract

DEFAULT_CONTRACT_CODES = (
    "CM_VERIFIED_SQL_DETAIL",
    "COMMON_REPOSITORY_DETAIL",
    "STORAGE_REPOSITORY_CHANGE_STORY",
)

def _source_identifiers(contract_code: str) -> list[str]:
    common_database = CommonDatabase(database_role="COMMON", connect_mongodb=False)
    source_database: CommonDatabase | None = None
    try:
        contract = _load_contract(common_database, contract_code)
        migration_mode = str(contract.get("migration_mode_code") or "").upper()
        parameter_codes = contract.get("source_clear_parameter_codes")
        if migration_mode == "MOVE_PAYLOAD" and (not isinstance(parameter_codes, list) or not parameter_codes):
            raise ValueError(
                "Invalid storage separation contract "
                f"{contract_code}: source_clear_parameter_codes must be a non-empty list."
            )
        role = str(contract["source_database_role"])
        table_name = _safe_identifier(str(contract["source_table_name"]), "source_table_name")
        identifier_column = _safe_identifier(str(contract["source_identifier_column_name"]), "source_identifier_column_name")
        source_database = CommonDatabase(database_role=role, connect_mongodb=False)
        rows = source_database.fetch_all(
            "SELECT " + chr(96) + identifier_column + chr(96)
            + " AS source_identifier FROM " + chr(96) + table_name + chr(96)
            + " ORDER BY " + chr(96) + identifier_column + chr(96)
        )
        return [str(row["source_identifier"]) for row in rows]
    finally:
        if source_database is not None:
            source_database.close()
        common_database.close()

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract-code", action="append", dest="contract_codes")
    parser.add_argument("--actor-id", default="SYSTEM")
    parser.add_argument("--client-ip", default="127.0.0.1")
    parser.add_argument("--apply", action="store_true")
    arguments = parser.parse_args()
    contract_codes = tuple(arguments.contract_codes or DEFAULT_CONTRACT_CODES)
    preview: list[dict[str, Any]] = []
    for contract_code in contract_codes:
        identifiers = _source_identifiers(contract_code)
        preview.append({"contract_code": contract_code, "source_row_count": len(identifiers)})
    if not arguments.apply:
        print(json.dumps({"applied": False, "targets": preview}, ensure_ascii=False, indent=2))
        return 0
    results: list[dict[str, Any]] = []
    for item in preview:
        contract_code = str(item["contract_code"])
        for source_identifier in _source_identifiers(contract_code):
            try:
                results.append(migrate_one(contract_code=contract_code, source_identifier=source_identifier, actor_id=arguments.actor_id, client_ip=arguments.client_ip))
            except RuntimeError as error:
                if "already migrated to MongoDB" not in str(error):
                    raise
                results.append({"contract_code": contract_code, "source_identifier": source_identifier, "skipped_yn": "Y", "skip_reason": "already_migrated_to_mongodb"})
            except ValueError as error:
                if "no payload values to migrate" not in str(error):
                    raise
                results.append({"contract_code": contract_code, "source_identifier": source_identifier, "skipped_yn": "Y", "skip_reason": "source_payload_empty"})
    print(json.dumps({"applied": True, "targets": preview, "results": results}, ensure_ascii=False, indent=2, default=str))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
