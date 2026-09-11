#!/usr/bin/env python3
"""Verify storage-separation data before any MariaDB payload column is dropped.

This program only reads MariaDB and MongoDB.  It never changes source rows,
MongoDB documents, or *_payload_backup_YYYYMMDD tables.

A table can be marked ddl_safe_yn=Y only when every source row that originally
had a detail value has a corresponding MongoDB DOCUMENT payload, its SPS
execution metadata is present, and no source detail value remains.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping

_PROJECT_ROOT_PATH = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT_PATH))

from common.database import CommonDatabase
from harness.scripts.migrate_one_table_detail import _load_contract, _safe_identifier

# These are the only contracts that have complete approved read/clear queries
# and have been run as a batch.  Other target tables remain outside this
# destructive-DDL gate until their contracts are completed and executed.
CONTRACT_CODES = (
    "CM_VERIFIED_SQL_DETAIL",
    "COMMON_REPOSITORY_DETAIL",
    "STORAGE_REPOSITORY_CHANGE_STORY",
)


def _has_payload_value(value: Any) -> bool:
    """Treat NULL and an empty string as cleared; preserve every other value."""
    return value is not None and (not isinstance(value, str) or value != "")


def _source_rows(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    role = str(contract["source_database_role"])
    table_name = _safe_identifier(str(contract["source_table_name"]), "source_table_name")
    identifier_column = _safe_identifier(
        str(contract["source_identifier_column_name"]),
        "source_identifier_column_name",
    )
    payload_columns = [
        _safe_identifier(str(value), "source_payload_column_name")
        for value in contract["source_payload_column_names"]
    ]
    selected_columns = [
        chr(96) + identifier_column + chr(96) + " AS source_identifier",
        *[chr(96) + column_name + chr(96) for column_name in payload_columns],
    ]
    database = CommonDatabase(database_role=role, connect_mongodb=False)
    try:
        return database.fetch_all(
            "SELECT " + ", ".join(selected_columns)
            + " FROM " + chr(96) + table_name + chr(96)
            + " ORDER BY " + chr(96) + identifier_column + chr(96)
        )
    finally:
        database.close()


def _contract_documents(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    mongodb_role = str(contract.get("mongodb_database_role") or contract["source_database_role"])
    database = CommonDatabase(
        database_role=mongodb_role,
        connect_mariadb=False,
        connect_mongodb=True,
    )
    try:
        return database.find(
            collection_name=str(contract["mongodb_collection_name"]),
            filter_document={"_sps.contract_code": str(contract["contract_code"])},
        )
    finally:
        database.close()


def verify_contract(contract_code: str) -> dict[str, Any]:
    """Return a compact, auditable no-data-loss decision for one contract."""
    common_database = CommonDatabase(database_role="COMMON", connect_mongodb=False)
    try:
        contract = _load_contract(common_database, contract_code)
    finally:
        common_database.close()

    payload_columns = [str(value) for value in contract["source_payload_column_names"]]
    source_rows = _source_rows(contract)
    documents = _contract_documents(contract)
    documents_by_identifier = {
        str(document.get("_sps", {}).get("source_identifier")): document
        for document in documents
        if document.get("_sps", {}).get("source_identifier") is not None
    }

    source_with_payload = [
        str(row["source_identifier"])
        for row in source_rows
        if any(_has_payload_value(row.get(column_name)) for column_name in payload_columns)
    ]
    source_with_residual_payload = list(source_with_payload)
    missing_mongodb_identifiers: list[str] = []
    missing_execution_identifiers: list[str] = []
    missing_document_payload_identifiers: list[str] = []
    payload_field_name = str(contract["mongodb_payload_field_name"])

    # If the source is already clear, an expected MongoDB document is every
    # source identifier that has a contract document.  For recovery from a
    # partially failed run, also check every source identifier with a value.
    required_identifiers = set(source_with_payload)
    required_identifiers.update(documents_by_identifier)

    for source_identifier in sorted(required_identifiers):
        document = documents_by_identifier.get(source_identifier)
        if document is None:
            missing_mongodb_identifiers.append(source_identifier)
            continue
        sps_metadata = document.get("_sps", {})
        if not sps_metadata.get("execution_history_id") or not sps_metadata.get("document_detail_id"):
            missing_execution_identifiers.append(source_identifier)
        if document.get("payload", {}).get(payload_field_name) is None:
            missing_document_payload_identifiers.append(source_identifier)

    # All source identifiers with residual detail must be proven by an actual
    # document before an operator can run a clear/reconciliation action.
    residual_without_document_identifiers = sorted(
        set(source_with_residual_payload) - set(documents_by_identifier)
    )
    ddl_safe = not (
        source_with_residual_payload
        or missing_mongodb_identifiers
        or missing_execution_identifiers
        or missing_document_payload_identifiers
    )
    return {
        "contract_code": contract_code,
        "source_database_role": contract["source_database_role"],
        "source_table_name": contract["source_table_name"],
        "payload_columns": payload_columns,
        "mongodb_collection_name": contract["mongodb_collection_name"],
        "source_row_count": len(source_rows),
        "mongodb_contract_document_count": len(documents),
        "source_payload_remaining_count": len(source_with_residual_payload),
        "source_payload_remaining_identifiers": source_with_residual_payload[:20],
        "residual_without_mongodb_identifiers": residual_without_document_identifiers[:20],
        "missing_mongodb_identifiers": missing_mongodb_identifiers[:20],
        "missing_execution_identifiers": missing_execution_identifiers[:20],
        "missing_document_payload_identifiers": missing_document_payload_identifiers[:20],
        "ddl_safe_yn": "Y" if ddl_safe else "N",
    }


def main() -> int:
    results = [verify_contract(contract_code) for contract_code in CONTRACT_CODES]
    output = {
        "applied": False,
        "operation": "read_only_verification",
        "backup_tables_changed_yn": "N",
        "contract_count": len(results),
        "ddl_safe_yn": "Y" if all(item["ddl_safe_yn"] == "Y" for item in results) else "N",
        "results": results,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))
    return 0 if output["ddl_safe_yn"] == "Y" else 1


if __name__ == "__main__":
    raise SystemExit(main())
