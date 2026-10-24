"""Bounded Execution Link -> MongoDB identifier repair.

This separate tool does not relax mongodb_update_document. It adds only the
three requested top-level IDs to one existing document. SQL is read-only;
this is not a new execution, a three-way business commit, or evidence creation.
"""
from __future__ import annotations

import config as project_config  # Load root project configuration before DB clients.
from typing import Any
from bson import ObjectId, json_util
from common.database import CommonDatabase
from common.common_function import normalize_required_text
from engine.common.repository_schema_guard import assert_schema_documented

ID_FIELDS = ("mongodb_database_id", "mongodb_collection_id", "mongodb_document_master_id")
LINK_SQL = """
SELECT l.object_attempt_id, h.generated_identifier, c.object_name,
       l.mongodb_database_id, l.mongodb_collection_id, l.mongodb_document_master_id
FROM sp_object_execution_link l
JOIN sp_execution_history h ON h.execution_history_id=l.object_attempt_id
JOIN sp_object c ON c.object_id=l.mongodb_collection_id
JOIN sp_object d ON d.object_id=l.mongodb_database_id
JOIN sp_object m ON m.object_id=l.mongodb_document_master_id
WHERE l.object_attempt_id=%s AND l.deleted_dt IS NULL AND h.deleted_dt IS NULL
  AND h.object_id=l.object_id AND l.execution_link_type_code='MONGODB'
  AND h.history_status_code='SAVED' AND h.execution_status_code='SUCCESS'
  AND h.repository_status_code='SUCCESS' AND h.mongodb_status_code='SUCCESS'
  AND c.deleted_dt IS NULL AND c.status_code='ACTIVE' AND c.active_yn='Y'
  AND d.deleted_dt IS NULL AND d.status_code='ACTIVE' AND d.active_yn='Y'
  AND m.deleted_dt IS NULL AND m.status_code='ACTIVE' AND m.active_yn='Y'
"""

def _document_identifier(raw: str) -> str | ObjectId:
    """Accept only an explicit scalar string or Extended JSON ObjectId; no selectors."""
    value = json_util.loads(normalize_required_text(raw, "document_id_json"))
    if not isinstance(value, (str, ObjectId)) or not str(value).strip():
        raise ValueError("document_id_json must be a nonempty string or Extended JSON ObjectId.")
    return value

def _repair_document(repository: Any, mongo: Any, *, collection_name: str,
                     object_attempt_id: str, document_id: str | ObjectId,
                     apply: bool) -> dict[str, Any]:
    """Validate one committed link and atomically fill missing IDs.

    On apply, hold SQL source-row locks while checking/updating Mongo. A guarded
    single-document $set never overwrites conflicting IDs or changes content.
    Releasing the read-only MariaDB transaction is a rollback, not business commit.
    A read-back failure may leave the safe Mongo update applied; retry is idempotent.
    """
    if apply:
        repository.begin()
    try:
        rows = repository.fetch_all(LINK_SQL + (" FOR UPDATE" if apply else ""),
                                    (object_attempt_id,))
        if len(rows) != 1:
            raise LookupError("Exactly one successful Execution Link with active ID Objects is required.")
        link = rows[0]
        if str(link["generated_identifier"]) != str(document_id):
            raise ValueError("History generated_identifier does not match document _id.")
        db_name = mongo.get_mongodb_database().name
        if link["object_name"] not in {f"MongoDB.{collection_name}", f"{db_name}.{collection_name}"}:
            raise ValueError("Execution Link collection Object does not match collection_name.")
        identifiers = {key: normalize_required_text(link.get(key), key) for key in ID_FIELDS}
        if any(len(value) > 99 for value in identifiers.values()):
            raise ValueError("Execution Link Identifier exceeds Repository length.")
        before = mongo.find_one(collection_name, {"_id": document_id})
        if before is None:
            raise LookupError("Existing Mongo document not found; inserts are not allowed.")
        if before.get("_id") != document_id:
            raise ValueError("Mongo document _id mismatch.")
        changes = {}
        conditions = []
        for key, value in identifiers.items():
            if key in before and before[key] not in (None, value):
                raise ValueError(f"Existing document Identifier conflict: {key}")
            if before.get(key) != value:
                changes[key] = value
            conditions.append({key: before[key]} if key in before else {key: {"$exists": False}})
        result = {"object_attempt_id": object_attempt_id, "document_id": str(document_id),
                  "collection_name": collection_name, "identifiers": identifiers,
                  "updated_field_names": sorted(changes), "applied": bool(apply),
                  "modified_count": 0, "verified": False}
        if not apply:
            return result
        if changes:
            updated = mongo.update_one(collection_name,
                                       {"_id": document_id, "$and": conditions},
                                       {"$set": changes})
            if updated.matched_count != 1:
                raise RuntimeError("Document changed concurrently; no repair success recorded.")
            result["modified_count"] = updated.modified_count
        after = mongo.find_one(collection_name, {"_id": document_id})
        if after is None or any(after.get(key) != value for key, value in identifiers.items()):
            raise RuntimeError("Identifier read-back verification failed.")
        original_content = {key: value for key, value in before.items() if key not in ID_FIELDS}
        current_content = {key: value for key, value in after.items() if key not in ID_FIELDS}
        if original_content != current_content:
            raise RuntimeError("Content changed during repair; inspect before retry.")
        return {**result, "verified": True}
    finally:
        if apply:
            repository.rollback()  # Release source locks; no MariaDB rows were modified.

def mongodb_repair_execution_link_ids(
    role: str, collection_name: str, object_attempt_id: str,
    document_id_json: str, apply: bool = False,
) -> dict[str, Any]:
    """Dry-run or fill one document's three IDs from its verified Execution Link.

    Allowed targets are insurance_policy_terms_payload and agent_long_term_memory.
    Never accepts caller-supplied ID values, arbitrary selectors, or overwrite flags.
    Root config may define SPS_EXECUTION_LINK_REPAIR_TARGETS for these two roles.
    """
    targets = getattr(project_config, "SPS_EXECUTION_LINK_REPAIR_TARGETS",
                      {"agent_long_term_memory": "STORY", "insurance_policy_terms_payload": "HEALTH"})
    collection = normalize_required_text(collection_name, "collection_name")
    if collection not in {"agent_long_term_memory", "insurance_policy_terms_payload"}:
        raise ValueError("Unsupported repair collection.")
    normalized_role = CommonDatabase._normalize_database_role(normalize_required_text(role, "role"))
    expected_role = CommonDatabase._normalize_database_role(targets[collection])
    if normalized_role != expected_role:
        raise ValueError("role does not match the approved collection repair target.")
    attempt = normalize_required_text(object_attempt_id, "object_attempt_id")
    identifier = _document_identifier(document_id_json)
    repository = CommonDatabase(database_role="STORY")
    try:
        assert_schema_documented(repository, repository.database_name,
                                 ("sp_object", "sp_execution_history", "sp_object_execution_link"))
        mongo = CommonDatabase(database_role=normalized_role, connect_mariadb=False,
                               connect_mongodb=True)
        try:
            return _repair_document(repository, mongo, collection_name=collection,
                                    object_attempt_id=attempt, document_id=identifier, apply=apply)
        finally:
            mongo.close()
    finally:
        repository.close()