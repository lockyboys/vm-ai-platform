"""Repository-first, compensating persistence for pipeline_results.

All Repository reads use CommonDatabase; detailed JSON is stored only in the
contract-selected MongoDB collection. MariaDB keeps the index and execution
link. SpsDistributedTransaction rolls back MariaDB and compensates MongoDB.
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable, Mapping

from common.database import CommonDatabase
from core.transaction.sps_distributed_transaction import SpsDistributedTransaction
from engine.identifier import IdentifierCoordinator
from common.common_function import normalize_required_text

PIPELINE_RESULTS_INDEX_QUERY_NAME = "insert_pipeline_results_index_storage_separation_20261004"
PIPELINE_RESULTS_DOCUMENT_OBJECT_ID = "SP_RP_OBJECT_20260707_212013_00004"
PROGRAM_ID = "PIPELINE_RESULTS_STORAGE"


def _load_object(database: CommonDatabase, object_code: str) -> dict[str, Any]:
    """Load active Object metadata; never substitute an inferred Object ID."""
    row = database.fetch_one(
        """
        SELECT object_id, object_code, object_name, object_description,
               business_code, domain_code, object_type_code, object_level,
               target_identifier_field, identifier_target_code,
               sequence_scope_code, sequence_length, status_code, active_yn
          FROM sp_object
         WHERE object_code = %s AND status_code = 'ACTIVE'
           AND active_yn = 'Y' AND deleted_dt IS NULL
         LIMIT 1
        """,
        (object_code,),
    )
    if not row:
        raise LookupError(f"Active Repository Object not found: {object_code}")
    return dict(row)


def _next_execution_id(database: CommonDatabase, metadata: Mapping[str, Any],
                       actor_id: str, client_ip: str) -> str:
    """Reserve and commit the identifier sequence before starting business writes."""
    coordinator = IdentifierCoordinator(database)
    request, prepared = coordinator.prepare_registered_object(
        object_metadata=dict(metadata), created_by=actor_id, updated_by=actor_id,
        client_ip=client_ip, program_id=PROGRAM_ID,
    )
    coordinator.acquire(prepared)
    try:
        database.begin()
        try:
            result = coordinator.resolve(request=request, prepared=prepared)
            database.commit()
            return result.identifier
        except Exception:
            database.rollback()
            raise
    finally:
        coordinator.release(prepared)


def _verified_index_sql(repository: CommonDatabase,
                        payload_database: CommonDatabase,
                        query_id: str) -> str:
    """Resolve the active Certified SQL and its Mongo payload from the Repository."""
    row = repository.fetch_one(
        """
        SELECT query_id, crud_type, verified_yn, status_code
          FROM cm_verified_sql_query
         WHERE query_id = %s AND verified_yn = 'Y'
           AND status_code = 'ACTIVE' AND deleted_dt IS NULL
        """,
        (query_id,),
    )
    if not row or row.get("crud_type") != "CREATE":
        raise LookupError(f"Active verified index query not found: {query_id}")
    payload_doc = payload_database.find_one(
        "cm_verified_sql_query_payload",
        {"_sps.source_table_name": "cm_verified_sql_query",
         "_sps.source_identifier": query_id},
    )
    payload = (payload_doc or {}).get("payload", {}).get("verified_sql_payload")
    sql_text = str((payload or {}).get("sql_text") or "").strip()
    if not sql_text:
        raise LookupError(f"Verified SQL text missing from payload: {query_id}")
    normalized = re.sub(r"\\s+", " ", sql_text).strip().lower()
    if (not normalized.startswith("insert into pipeline_results ")
            or "data_json" in normalized
            or "user_id" not in normalized or "file_name" not in normalized):
        raise ValueError("Verified SQL does not match the pipeline_results index contract.")
    return sql_text


def save_pipeline_results(
    *, user_id: str, file_name: str, task_type: str, learning_type: str,
    accuracy: float, data: Mapping[str, Any], actor_id: str,
    client_ip: str = "127.0.0.1",
    database_factory: Callable[..., CommonDatabase] = CommonDatabase,
    transaction_factory: Callable[..., SpsDistributedTransaction] = SpsDistributedTransaction,
) -> dict[str, Any]:
    """Persist one result; any later failure rolls back the index and Mongo payload."""
    actor_id = normalize_required_text(actor_id, "actor_id")
    client_ip = normalize_required_text(client_ip, "client_ip")
    story_db = database_factory(database_role="STORY", connect_mongodb=False)
    common_db = database_factory(database_role="COMMON", connect_mongodb=False)
    mongo_db = database_factory(database_role="COMMON", connect_mariadb=False,
                                connect_mongodb=True)
    try:
        # Verify cross-schema transaction uses one MariaDB server and valid schema names.
        story_endpoint = (str(story_db.config.get("host")), str(story_db.config.get("port")))
        common_endpoint = (str(common_db.config.get("host")), str(common_db.config.get("port")))
        if story_endpoint != common_endpoint:
            raise RuntimeError("STORY and COMMON must share a MariaDB server for atomic writes.")
        story_schema = str(story_db.database_name or "")
        common_schema = str(common_db.database_name or "")
        if not re.fullmatch(r"[A-Za-z0-9_]+", story_schema + common_schema):
            raise RuntimeError("Repository returned an invalid database schema name.")

        document_object = _load_object(story_db, "DOCUMENT")
        if document_object["object_id"] != PIPELINE_RESULTS_DOCUMENT_OBJECT_ID:
            raise RuntimeError("DOCUMENT Object ID differs from the approved Repository reference.")
        execution_object = _load_object(story_db, "EXECUTION_HISTORY")
        mongo_objects = {
            code: _load_object(story_db, code) for code in ("MDB", "MCO", "MCM")
        }

        contract_row = common_db.fetch_one(
            """
            SELECT common_code_json FROM cm_common_code
             WHERE group_code = 'STORAGE_SEPARATION_TARGET'
               AND code = 'PIPELINE_RESULTS_PAYLOAD'
               AND status_code = 'ACTIVE' AND deleted_dt IS NULL
            """
        )
        contract = json.loads(contract_row["common_code_json"]) if contract_row else None
        if not isinstance(contract, dict):
            raise LookupError("PIPELINE_RESULTS_PAYLOAD contract is not registered.")
        collection = normalize_required_text(
            contract.get("mongodb_collection_name"), "mongodb_collection_name"
        )
        if (contract.get("source_table_name") != "pipeline_results"
                or contract.get("source_identifier_column_name") != "id"
                or contract.get("execution_link_required_yn") != "Y"
                or contract.get("execution_link_type_code") != "MONGODB"
                or contract.get("source_database_role") != "COMMON"
                or contract.get("mongodb_database_role") != "COMMON"):
            raise ValueError("PIPELINE_RESULTS_PAYLOAD contract does not match Repository schema.")

        query_name = PIPELINE_RESULTS_INDEX_QUERY_NAME
        query_row = common_db.fetch_one(
            """SELECT query_id FROM cm_verified_sql_query
                 WHERE query_name = %s AND verified_yn = 'Y'
                   AND status_code = 'ACTIVE' AND deleted_dt IS NULL""",
            (query_name,),
        )
        if not query_row:
            raise LookupError(f"Active verified index query not found: {query_name}")
        query_id = query_row["query_id"]
        index_sql = _verified_index_sql(common_db, mongo_db, query_id)
        execution_id = _next_execution_id(
            story_db, execution_object, actor_id, client_ip
        )

        with transaction_factory(common_db, mongo_db) as transaction:
            # Keep the certified INSERT text; only qualify its Repository schema.
            qualified_sql = re.sub(
                r"(?i)^\\s*INSERT\\s+INTO\\s+pipeline_results\\b",
                f"INSERT INTO `{common_schema}`.pipeline_results", index_sql, count=1
            )
            affected = common_db.execute(
                qualified_sql, (user_id, file_name, task_type, learning_type, accuracy)
            )
            if affected != 1:
                raise RuntimeError(f"pipeline_results index insert affected {affected} rows.")
            pipeline_result_id = common_db.last_insert_id()

            history_sql = f"""
                INSERT INTO `{story_schema}`.sp_execution_history
                  (execution_history_id, trace_id, engine_code, object_code, object_id,
                   generated_identifier, repository_status_code, mongodb_status_code,
                   execution_status_code, history_status_code, created_by, program_id, client_ip)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            common_db.execute(history_sql, (
                execution_id, execution_id, "PIPELINE_RUNTIME", "DOCUMENT",
                document_object["object_id"], str(pipeline_result_id),
                "READY", "READY", "RUNNING", "READY", actor_id, PROGRAM_ID, client_ip,
            ))

            mongo_document = {
                "_sps": {
                    "source_table_name": "pipeline_results",
                    "source_identifier": pipeline_result_id,
                    "execution_history_id": execution_id,
                    "source_object_id": document_object["object_id"],
                    "source_object_code": document_object["object_code"],
                    "storage_contract_code": "PIPELINE_RESULTS_PAYLOAD",
                },
                "data_json": dict(data),
                "created_by": actor_id,
                "program_id": PROGRAM_ID,
            }
            transaction.insert_mongodb_document(
                collection_name=collection, document=mongo_document,
                compensation_filter={
                    "_sps.source_table_name": "pipeline_results",
                    "_sps.source_identifier": pipeline_result_id,
                },
            )

            link_sql = f"""
                INSERT INTO `{story_schema}`.sp_object_execution_link
                  (object_attempt_id, object_id, target_object_id, execution_link_type_code,
                   mongodb_database_id, mongodb_collection_id, mongodb_document_master_id,
                   created_by, client_ip, program_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            common_db.execute(link_sql, (
                execution_id, document_object["object_id"], mongo_objects["MCM"]["object_id"],
                contract["execution_link_type_code"], mongo_objects["MDB"]["object_id"],
                mongo_objects["MCO"]["object_id"], mongo_objects["MCM"]["object_id"],
                actor_id, client_ip, PROGRAM_ID,
            ))
            common_db.execute(
                f"""
                UPDATE `{story_schema}`.sp_execution_history
                   SET repository_status_code = %s, mongodb_status_code = %s,
                       execution_status_code = %s, history_status_code = %s,
                       updated_by = %s, updated_dt = CURRENT_TIMESTAMP
                 WHERE execution_history_id = %s
                """,
                ("SUCCESS", "SUCCESS", "SUCCESS", "SAVED", actor_id, execution_id),
            )
        return {"pipeline_result_id": pipeline_result_id,
                "execution_history_id": execution_id, "status": "SUCCESS"}
    finally:
        story_db.close()
        common_db.close()
        mongo_db.close()
