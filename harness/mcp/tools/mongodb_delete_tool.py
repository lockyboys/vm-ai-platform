from __future__ import annotations

from typing import Any

from bson import ObjectId

from common.database import CommonDatabase


def mongodb_delete_document(
    role: str,
    collection_name: str,
    contract_code: str,
    source_identifier: str,
    document_id: str,
    apply: bool = False,
) -> dict[str, Any]:
    """Delete exactly one SPS MongoDB document after a dry-run."""
    if not all(
        value and value.strip()
        for value in (role, collection_name, contract_code, source_identifier, document_id)
    ):
        raise ValueError("role, collection_name, contract_code, source_identifier, document_id are required.")
    try:
        object_id = ObjectId(document_id)
    except Exception as error:
        raise ValueError("document_id must be a valid MongoDB ObjectId.") from error

    database = CommonDatabase(
        database_role=role,
        connect_mariadb=False,
        connect_mongodb=True,
    )
    selector = {
        "_id": object_id,
        "_sps.contract_code": contract_code.strip(),
        "_sps.source_identifier": source_identifier.strip(),
    }
    try:
        if collection_name.strip() not in set(database.list_collection_names()):
            raise LookupError(f"MongoDB collection not found: {collection_name.strip()}")
        matched = database.find(
            collection_name=collection_name.strip(),
            filter_document=selector,
            limit=2,
        )
        if len(matched) != 1:
            raise RuntimeError(
                "MongoDB delete must match exactly one document. "
                f"matched_count={len(matched)}"
            )
        result = {
            "database_role": database.database_role,
            "collection_name": collection_name.strip(),
            "document_id": document_id,
            "source_identifier": source_identifier.strip(),
            "matched_count": 1,
            "applied": bool(apply),
        }
        if not apply:
            return result
        delete_result = database.delete_one(collection_name.strip(), selector)
        if delete_result.deleted_count != 1:
            raise RuntimeError("MongoDB delete did not remove exactly one document.")
        return {**result, "deleted_count": delete_result.deleted_count}
    finally:
        database.close()
