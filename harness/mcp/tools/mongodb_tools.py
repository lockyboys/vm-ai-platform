# =============================================================================
# File Name   : harness/mcp/tools/mongodb_tools.py
# Purpose     : MongoDB 문서와 컬렉션을 확인하고, 안전하게 바꾸는 도구
# =============================================================================
# CHANGE HISTORY
# =============================================================================
# 20260902 | Codex | Harness 표준 파일 헤더와 dry-run 우선 변경 기준을 보강했음
# =============================================================================
# 이 파일은 무엇을 하나요?
# - 컬렉션 목록과 문서 수를 확인하고, 필요한 문서를 저장하거나 고칩니다.
# - 이름 변경은 먼저 dry-run으로 결과를 보여 준 뒤 apply=true일 때만 실행합니다.
# 주의: Repository에 등록된 역할과 정확한 대상이 확인되지 않으면 바꾸지 않습니다.
from __future__ import annotations

import json
import re
from typing import Any

from bson import ObjectId

from common.database import CommonDatabase


DEFAULT_LIMIT = 20
MAX_LIMIT = 100
VALID_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_collection_name(collection_name: str) -> str:
    normalized_name = collection_name.strip()

    if not VALID_IDENTIFIER_PATTERN.fullmatch(normalized_name):
        raise ValueError("collection_name contains invalid characters.")

    return normalized_name


def _normalize_limit(limit: int) -> int:
    return max(1, min(int(limit), MAX_LIMIT))


def _normalize_mongodb_value(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)

    if isinstance(value, dict):
        return {
            str(key): _normalize_mongodb_value(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            _normalize_mongodb_value(item)
            for item in value
        ]

    return value


def _parse_json_object(
    raw_json: str,
    field_name: str,
) -> dict[str, Any]:
    try:
        value = json.loads(raw_json)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"{field_name} must be valid JSON."
        ) from error

    if not isinstance(value, dict):
        raise ValueError(
            f"{field_name} must contain a JSON object."
        )

    return value


def mongodb_list_collections(role: str) -> list[dict[str, Any]]:
    """List MongoDB collections for one Repository-resolved database role."""

    database = CommonDatabase(
        database_role=role,
        connect_mariadb=False,
        connect_mongodb=True,
    )

    try:
        return [
            {"collection_name": name}
            for name in database.list_collection_names()
        ]
    finally:
        database.close()


def mongodb_collection_stats(
    role: str,
    collection_name: str,
) -> dict[str, Any]:
    """Return a MongoDB collection's document count without changing content."""
    normalized_collection_name = _validate_collection_name(collection_name)
    database = CommonDatabase(
        database_role=role,
        connect_mariadb=False,
        connect_mongodb=True,
    )
    try:
        if normalized_collection_name not in set(database.list_collection_names()):
            raise LookupError(
                f"MongoDB collection not found: {normalized_collection_name}"
            )
        return {
            "database_role": database.database_role,
            "collection_name": normalized_collection_name,
            "document_count": database.count_documents(normalized_collection_name),
        }
    finally:
        database.close()


def mongodb_rename_collection(
    role: str,
    source_collection: str,
    target_collection: str,
    apply: bool = False,
) -> dict[str, Any]:
    """Dry-run 또는 실행으로 MongoDB Collection 이름만 변경한다."""
    source_name = _validate_collection_name(source_collection)
    target_name = _validate_collection_name(target_collection)
    if source_name == target_name:
        raise ValueError("source_collection and target_collection must differ.")

    database = CommonDatabase(
        database_role=role,
        connect_mariadb=False,
        connect_mongodb=True,
    )
    try:
        collection_names = set(database.list_collection_names())
        if source_name not in collection_names:
            raise LookupError(f"MongoDB collection not found: {source_name}")
        if target_name in collection_names:
            raise FileExistsError(f"MongoDB collection already exists: {target_name}")

        source_document_count = database.count_documents(source_name)
        result = {
            "database_role": database.database_role,
            "source_collection_name": source_name,
            "target_collection_name": target_name,
            "source_document_count": source_document_count,
            "content_changed_yn": "N",
            "delete_performed_yn": "N",
            "applied": bool(apply),
        }
        if not apply:
            return result

        renamed_collection_name = database.rename_collection(source_name, target_name)
        target_document_count = database.count_documents(target_name)
        if target_document_count != source_document_count:
            raise RuntimeError(
                "MongoDB rename document count verification failed: "
                f"source={source_document_count}, target={target_document_count}"
            )
        return {
            **result,
            "renamed_collection_name": renamed_collection_name,
            "target_document_count": target_document_count,
        }
    finally:
        database.close()


def mongodb_documents(
    collection_name: str,
    filter_json: str = "{}",
    limit: int = DEFAULT_LIMIT,
) -> list[dict[str, Any]]:
    """Read bounded MongoDB documents from one collection."""

    normalized_collection_name = _validate_collection_name(
        collection_name
    )
    filter_document = _parse_json_object(
        filter_json,
        "filter_json",
    )
    normalized_limit = _normalize_limit(limit)
    database = CommonDatabase(
        database_role="COMMON",
        connect_mariadb=False,
        connect_mongodb=True,
    )

    try:
        documents = database.find(
            collection_name=normalized_collection_name,
            filter_document=filter_document,
            limit=normalized_limit,
        )
        return [
            _normalize_mongodb_value(document)
            for document in documents
        ]
    finally:
        database.close()


def mongodb_save_document(
    collection_name: str,
    document_json: str,
) -> dict[str, Any]:
    """
    Save one MongoDB document.

    Call only after the Object Runtime has generated and saved the
    corresponding Repository identity and execution metadata.
    """

    normalized_collection_name = _validate_collection_name(
        collection_name
    )
    document = _parse_json_object(
        document_json,
        "document_json",
    )
    database = CommonDatabase(
        database_role="COMMON",
        connect_mariadb=False,
        connect_mongodb=True,
    )

    try:
        result = database.insert_one(
            collection_name=normalized_collection_name,
            document=document,
        )
        return {
            "collection_name": normalized_collection_name,
            "mongodb_document_id": str(result.inserted_id),
            "acknowledged": bool(result.acknowledged),
        }
    finally:
        database.close()



def mongodb_update_document(
    role: str,
    collection_name: str,
    filter_json: str,
    set_json: str,
    apply: bool = False,
) -> dict[str, Any]:
    """Dry-run 또는 실행으로 명시적 MongoDB 문서 한 건의 Payload/Audit만 갱신한다."""
    normalized_collection_name = _validate_collection_name(collection_name)
    filter_document = _parse_json_object(filter_json, "filter_json")
    set_document = _parse_json_object(set_json, "set_json")
    if not filter_document or not set_document:
        raise ValueError("filter_json and set_json must not be empty.")
    if set(filter_document) != {"_sps.contract_code", "_sps.source_identifier"}:
        raise ValueError(
            "filter_json must identify exactly one SPS source document by "
            "_sps.contract_code and _sps.source_identifier."
        )
    if any(
        not (field_name.startswith("payload.") or field_name.startswith("audit."))
        for field_name in set_document
    ):
        raise ValueError("set_json may update only payload.* or audit.* fields.")

    database = CommonDatabase(
        database_role=role,
        connect_mariadb=False,
        connect_mongodb=True,
    )
    try:
        if normalized_collection_name not in set(database.list_collection_names()):
            raise LookupError(
                f"MongoDB collection not found: {normalized_collection_name}"
            )
        matched_documents = database.find(
            collection_name=normalized_collection_name,
            filter_document=filter_document,
            limit=2,
        )
        if len(matched_documents) != 1:
            raise RuntimeError(
                "MongoDB update must match exactly one document. "
                f"matched_count={len(matched_documents)}"
            )
        result = {
            "database_role": database.database_role,
            "collection_name": normalized_collection_name,
            "source_identifier": filter_document["_sps.source_identifier"],
            "matched_count": len(matched_documents),
            "updated_field_names": sorted(set_document),
            "applied": bool(apply),
        }
        if not apply:
            return result

        update_result = database.update_one(
            normalized_collection_name,
            filter_document,
            {"$set": set_document},
        )
        if update_result.matched_count != 1:
            raise RuntimeError("MongoDB update did not match exactly one document.")
        return {
            **result,
            "modified_count": update_result.modified_count,
        }
    finally:
        database.close()

def verified_sql(
    query_id: str | None = None,
    include_sql_text: bool = False,
) -> list[dict[str, Any]]:
    """
    Read approved SQL from the Common Repository.

    This tool returns only verified, active, non-deleted queries.
    It does not execute SQL batches.
    """

    selected_sql_text = "sql_text" if include_sql_text else "NULL AS sql_text"
    sql = f"""
    SELECT
        query_id,
        query_name,
        query_description,
        crud_type,
        verified_yn,
        certified_level_code,
        verification_description,
        verified_by,
        verified_dt,
        {selected_sql_text}
    FROM cm_verified_sql_query
    WHERE verified_yn = 'Y'
      AND status_code = 'ACTIVE'
      AND deleted_dt IS NULL
    """
    params: tuple[Any, ...] = ()

    if query_id:
        sql += " AND query_id = %s"
        params = (query_id.strip(),)

    sql += " ORDER BY query_id"

    database = CommonDatabase(database_role="COMMON")
    try:
        return database.fetch_all(sql, params)
    finally:
        database.close()
