"""Repair one legacy impact-analysis MongoDB document to the current payload contract.

CHANGE HISTORY
20260830 | OpenAI | Repair legacy payload and knowledge-type metadata before DDL.

Run:
    python scripts/repair_impact_analysis_legacy_mongodb_document.py \
      --source-identifier SP_RP_IMPACT_ANALYSIS_20260701_090144_00005 --apply
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Direct execution must resolve common and scripts packages from project root.
_PROJECT_ROOT_PATH = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT_PATH))

from common.database import CommonDatabase
from scripts.migrate_one_table_detail import (
    _build_mongodb_payload,
    _load_contract,
    _load_knowledge_type,
    _load_verified_queries,
)


_CONTRACT_CODE = "IMPACT_ANALYSIS_DETAIL"
_PROGRAM_ID = "scripts.repair_impact_analysis_legacy_mongodb_document"


def repair_legacy_document(*, source_identifier: str) -> dict[str, Any]:
    """Fill missing payload and DOCUMENT metadata on one already-linked MongoDB document.

    Args:
        source_identifier: Existing sp_impact_analysis_result.impact_analysis_id.
            The method never creates a new MongoDB document and never changes
            MariaDB payload values; it updates only the matched legacy document.

    Returns:
        Updated MongoDB document ID and the restored payload field names.

    Raises:
        LookupError: The source row or its legacy MongoDB document does not exist.
        RuntimeError: The matched MongoDB document already has the required
            change_target_text or the update does not match exactly one document.
    """
    common_database = CommonDatabase(database_role="COMMON")
    story_database = CommonDatabase(database_role="STORY")
    mongodb_database: CommonDatabase | None = None
    try:
        contract = _load_contract(common_database, _CONTRACT_CODE)
        verified_queries = _load_verified_queries(common_database, contract)
        source_row = story_database.fetch_one(
            verified_queries["source_read"]["sql_text"],
            (source_identifier,),
        )
        if not source_row:
            raise LookupError(f"Impact analysis source row not found: {source_identifier}")

        collection_name = contract["mongodb_collection_name"]
        payload_field_name = contract["mongodb_payload_field_name"]
        payload_column_names = contract["payload_column_names"]
        mongodb_database = CommonDatabase(
            database_role="HEALTH",
            connect_mariadb=False,
            connect_mongodb=True,
        )
        legacy_document = mongodb_database.find_one(
            collection_name,
            {
                "_sps.contract_code": _CONTRACT_CODE,
                "_sps.source_identifier": source_identifier,
            },
        )
        if legacy_document is None:
            raise LookupError(
                "Legacy MongoDB document not found for source identifier: "
                f"{source_identifier}"
            )

        existing_payload = legacy_document.get("payload", {}).get(payload_field_name)
        if isinstance(existing_payload, dict) and existing_payload.get("change_target_text"):
            raise RuntimeError(
                "Legacy MongoDB document already contains change_target_text; "
                "repair is unnecessary."
            )

        knowledge_type = _load_knowledge_type(
            story_database,
            contract["knowledge_type_code"],
        )
        restored_payload = _build_mongodb_payload(
            source_row,
            payload_column_names=payload_column_names,
            mongodb_payload_field_name=payload_field_name,
        )
        restored_detail = restored_payload[payload_field_name]
        legacy_payload = legacy_document.get("payload", {})
        for field_name in payload_column_names:
            if restored_detail.get(field_name) is None and field_name in legacy_payload:
                restored_detail[field_name] = legacy_payload[field_name]

        update_result = mongodb_database.update_one(
            collection_name,
            {"_id": legacy_document["_id"]},
            {
                "$set": {
                    f"payload.{payload_field_name}": restored_payload[payload_field_name],
                    "_sps.knowledge_type_id": knowledge_type["knowledge_type_id"],
                    "_sps.knowledge_type_code": knowledge_type["knowledge_type_code"],
                    "_sps.schema_version": "v1.0",
                    "_sps.legacy_payload_repaired_by": _PROGRAM_ID,
                }
            },
        )
        if update_result.matched_count != 1:
            raise RuntimeError(
                "Legacy MongoDB payload repair did not match exactly one document. "
                f"source_identifier={source_identifier}"
            )

        payload_value = restored_payload[payload_field_name]
        return {
            "source_identifier": source_identifier,
            "mongodb_document_id": str(legacy_document["_id"]),
            "knowledge_type_code": knowledge_type["knowledge_type_code"],
            "restored_payload_field_names": (
                sorted(payload_value) if isinstance(payload_value, dict) else [payload_field_name]
            ),
            "modified_count": update_result.modified_count,
        }
    finally:
        if mongodb_database is not None:
            mongodb_database.close()
        story_database.close()
        common_database.close()


def main() -> None:
    """Require an explicit apply flag before mutating the legacy MongoDB document."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-identifier", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.apply:
        raise SystemExit("--apply is required for the legacy MongoDB repair.")

    result = repair_legacy_document(source_identifier=args.source_identifier.strip())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
