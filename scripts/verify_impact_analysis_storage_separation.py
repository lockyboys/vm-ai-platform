"""Verify full MongoDB payload coverage before deleting MariaDB columns.

CHANGE HISTORY
20260830 | OpenAI | Verify the five impact-analysis MongoDB documents before DDL.

Run:
    python scripts/verify_impact_analysis_storage_separation.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Direct execution must resolve the project package root consistently.
_PROJECT_ROOT_PATH = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT_PATH))

from common.database import CommonDatabase


_CONTRACT_CODE = "IMPACT_ANALYSIS_DETAIL"
_COLLECTION_NAME = "sp_impact_analysis_text"
_PAYLOAD_FIELD_NAME = "sp_impact_analysis_text"
_EXPECTED_SOURCE_IDENTIFIERS = (
    "SP_RP_IMPACT_ANALYSIS_20260701_090144_00001",
    "SP_RP_IMPACT_ANALYSIS_20260701_090144_00002",
    "SP_RP_IMPACT_ANALYSIS_20260701_090144_00003",
    "SP_RP_IMPACT_ANALYSIS_20260701_090144_00004",
    "SP_RP_IMPACT_ANALYSIS_20260701_090144_00005",
)


def _payload_field_names(document: dict[str, Any]) -> list[str]:
    """Return source payload names regardless of one-field or multi-field storage."""
    payload = document.get("payload", {}).get(_PAYLOAD_FIELD_NAME)
    if isinstance(payload, dict):
        return sorted(payload)
    return [_PAYLOAD_FIELD_NAME] if payload is not None else []


def main() -> None:
    """Verify each expected source row has one traceable MongoDB document."""
    database = CommonDatabase(
        database_role="HEALTH",
        connect_mariadb=False,
        connect_mongodb=True,
    )
    try:
        documents = database.find(
            collection_name=_COLLECTION_NAME,
            filter_document={"_sps.contract_code": _CONTRACT_CODE},
        )
        documents_by_source_identifier = {
            document.get("_sps", {}).get("source_identifier"): document
            for document in documents
        }

        results: list[dict[str, Any]] = []
        missing_source_identifiers: list[str] = []
        missing_change_target_identifiers: list[str] = []
        missing_execution_link_identifiers: list[str] = []
        missing_affected_file_path_identifiers: list[str] = []
        missing_client_ip_identifiers: list[str] = []

        for source_identifier in _EXPECTED_SOURCE_IDENTIFIERS:
            document = documents_by_source_identifier.get(source_identifier)
            if document is None:
                missing_source_identifiers.append(source_identifier)
                continue

            payload = document.get("payload", {}).get(_PAYLOAD_FIELD_NAME)
            change_target_text = (
                payload.get("change_target_text")
                if isinstance(payload, dict)
                else None
            )
            sps_metadata = document.get("_sps", {})
            if not change_target_text:
                missing_change_target_identifiers.append(source_identifier)
            if not sps_metadata.get("execution_history_id"):
                missing_execution_link_identifiers.append(source_identifier)
            # 원본 MariaDB 값이 NULL일 수 있다. 값의 유무가 아니라 계약 필드가\n            # MongoDB Payload에 보존됐는지를 확인한다.\n            if not isinstance(payload, dict) or "affected_file_path" not in payload:\n                missing_affected_file_path_identifiers.append(source_identifier)\n            if not document.get("audit", {}).get("client_ip"):
                missing_client_ip_identifiers.append(source_identifier)

            results.append(
                {
                    "source_identifier": source_identifier,
                    "mongodb_document_id": str(document.get("_id")),
                    "execution_history_id": sps_metadata.get("execution_history_id"),
                    "document_detail_id": sps_metadata.get("document_detail_id"),
                    "knowledge_type_code": sps_metadata.get("knowledge_type_code"),
                    "payload_field_names": _payload_field_names(document),
                    "change_target_text_present_yn": "Y" if change_target_text else "N",
                }
            )

        verification = {
            "contract_code": _CONTRACT_CODE,
            "collection_name": _COLLECTION_NAME,
            "expected_document_count": len(_EXPECTED_SOURCE_IDENTIFIERS),
            "actual_contract_document_count": len(documents),
            "results": results,
            "missing_source_identifiers": missing_source_identifiers,
            "missing_change_target_identifiers": missing_change_target_identifiers,
            "missing_execution_link_identifiers": missing_execution_link_identifiers,
            "missing_affected_file_path_identifiers": missing_affected_file_path_identifiers,
            "missing_client_ip_identifiers": missing_client_ip_identifiers,
            "ddl_safe_yn": (
                "Y"
                if not (
                    missing_source_identifiers
                    or missing_change_target_identifiers
                    or missing_execution_link_identifiers
                    or missing_affected_file_path_identifiers
                    or missing_client_ip_identifiers
                )
                else "N"
            ),
        }
        print(json.dumps(verification, ensure_ascii=False, indent=2))
        if verification["ddl_safe_yn"] != "Y":
            raise SystemExit("MongoDB verification failed; MariaDB DDL must not run.")
    finally:
        database.close()


if __name__ == "__main__":
    main()
