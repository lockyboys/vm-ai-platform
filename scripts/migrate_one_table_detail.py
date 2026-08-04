"""Migrate one MariaDB large-text payload to MongoDB with an SPS execution link."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from typing import Any, Mapping

from common.database import CommonDatabase
from core.transaction.sps_distributed_transaction import SpsDistributedTransaction
from engine.identifier.coordinator import IdentifierCoordinator


_IDENTIFIER_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
_AUDIT_COLUMNS = (
    "created_by",
    "created_dt",
    "updated_by",
    "updated_dt",
    "deleted_by",
    "deleted_dt",
    "program_id",
    "client_ip",
)
_PROGRAM_ID = "scripts.migrate_one_table_detail"
_EXECUTION_OBJECT_CODE = "EXECUTION_HISTORY"
_MONGODB_OBJECT_CODES = ("MDB", "MCO", "MCM", "MDD")


def _required_text(value: Any, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} is required.")
    return normalized


def _safe_identifier(value: Any, field_name: str) -> str:
    normalized = _required_text(value, field_name)
    if not _IDENTIFIER_PATTERN.fullmatch(normalized):
        raise ValueError(f"Unsafe SQL identifier: {field_name}={normalized}")
    return normalized


def _load_contract(common_database: CommonDatabase, contract_code: str) -> dict[str, Any]:
    row = common_database.fetch_one(
        """
        SELECT code, common_code_json
        FROM cm_common_code
        WHERE group_code = %s
          AND code = %s
          AND status_code = 'ACTIVE'
          AND deleted_dt IS NULL
        """,
        ("STORAGE_SEPARATION_TARGET", contract_code),
    )
    if not row:
        raise LookupError(f"Active storage separation contract not found: {contract_code}")

    raw_contract = row.get("common_code_json")
    contract = json.loads(raw_contract) if isinstance(raw_contract, str) else dict(raw_contract or {})
    contract["contract_code"] = row["code"]
    return contract


_VERIFIED_QUERY_CRUD = {
    "source_read": "READ",
    "execution_insert": "CREATE",
    "link_insert": "CREATE",
    "finalize_update": "UPDATE",
}


def _load_verified_queries(
    common_database: CommonDatabase,
    contract: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    query_names = contract.get("verified_query_names")
    if not isinstance(query_names, Mapping):
        raise ValueError("verified_query_names must be registered in the storage contract.")

    resolved: dict[str, dict[str, Any]] = {}
    for operation_name, expected_crud_type in _VERIFIED_QUERY_CRUD.items():
        query_name = _required_text(
            query_names.get(operation_name),
            f"verified_query_names.{operation_name}",
        )
        row = common_database.fetch_one(
            """
            SELECT query_id, query_name, crud_type, sql_text
            FROM cm_verified_sql_query
            WHERE query_name = %s
              AND verified_yn = 'Y'
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
            ORDER BY query_id DESC
            LIMIT 1
            """,
            (query_name,),
        )
        if not row:
            raise RuntimeError(
                "Registered Verified SQL Query is required before migration. "
                f"operation_name={operation_name}, query_name={query_name}"
            )
        if row["crud_type"] != expected_crud_type:
            raise RuntimeError(
                "Verified SQL CRUD type mismatch. "
                f"query_id={row['query_id']}, expected={expected_crud_type}, "
                f"actual={row['crud_type']}"
            )
        if not str(row.get("sql_text") or "").strip():
            raise RuntimeError(
                f"Verified SQL text is empty. query_id={row['query_id']}"
            )
        resolved[operation_name] = row
    return resolved


def _load_object(story_database: CommonDatabase, object_code: str) -> dict[str, Any]:
    row = story_database.fetch_one(
        """
        SELECT
            object_id,
            object_code,
            object_name,
            business_code,
            domain_code,
            object_level,
            identifier_target_code,
            sequence_scope_code,
            sequence_length,
            target_identifier_field
        FROM sp_object
        WHERE object_code = %s
          AND active_yn = 'Y'
          AND status_code = 'ACTIVE'
          AND deleted_dt IS NULL
        """,
        (object_code,),
    )
    if not row:
        raise LookupError(f"Active Repository Object not found: {object_code}")
    return row


def _prepare_identifier(
    coordinator: IdentifierCoordinator,
    object_metadata: Mapping[str, Any],
    actor_id: str,
    client_ip: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    return coordinator.prepare_registered_object(
        object_metadata=object_metadata,
        created_by=actor_id,
        updated_by=actor_id,
        client_ip=client_ip,
        program_id=_PROGRAM_ID,
        now=datetime.now(timezone.utc),
    )


def _insert_execution_history(
    database: CommonDatabase,
    *,
    sql_text: str,
    execution_history_id: str,
    source_object: Mapping[str, Any],
    source_identifier: str,
    actor_id: str,
    client_ip: str,
) -> None:
    affected_rows = database.execute(
        sql_text,
        (
            execution_history_id,
            execution_history_id,
            "TABLE_DETAIL_MIGRATION",
            source_object["object_code"],
            source_object["object_id"],
            source_identifier,
            "READY",
            "READY",
            "RUNNING",
            "READY",
            actor_id,
            actor_id,
            _PROGRAM_ID,
            client_ip,
        ),
    )
    if affected_rows != 1:
        raise RuntimeError(
            "Execution history insert did not affect one row. "
            f"execution_history_id={execution_history_id}"
        )


def _insert_execution_link(
    database: CommonDatabase,
    *,
    sql_text: str,
    execution_history_id: str,
    execution_object: Mapping[str, Any],
    mongodb_objects: Mapping[str, Mapping[str, Any]],
    execution_link_type_code: str,
    actor_id: str,
    client_ip: str,
) -> None:
    affected_rows = database.execute(
        sql_text,
        (
            execution_history_id,
            execution_object["object_id"],
            mongodb_objects["MCM"]["object_id"],
            execution_link_type_code,
            mongodb_objects["MDB"]["object_id"],
            mongodb_objects["MCO"]["object_id"],
            mongodb_objects["MCM"]["object_id"],
            actor_id,
            actor_id,
            client_ip,
            _PROGRAM_ID,
        ),
    )
    if affected_rows != 1:
        raise RuntimeError(
            "Execution link insert did not affect one row. "
            f"execution_history_id={execution_history_id}"
        )


def _finalize_execution_history(
    database: CommonDatabase,
    *,
    sql_text: str,
    execution_history_id: str,
    actor_id: str,
    client_ip: str,
) -> None:
    affected_rows = database.execute(
        sql_text,
        (actor_id, _PROGRAM_ID, client_ip, execution_history_id),
    )
    if affected_rows != 1:
        raise RuntimeError(
            "Execution history finalization did not affect one row. "
            f"execution_history_id={execution_history_id}"
        )


def migrate_one(
    *,
    contract_code: str,
    source_identifier: str,
    actor_id: str,
    client_ip: str,
) -> dict[str, Any]:
    common_database = CommonDatabase(database_role="COMMON")
    story_database = CommonDatabase(database_role="STORY")
    mongodb_database: CommonDatabase | None = None
    acquired_preparations: list[dict[str, Any]] = []

    try:
        contract = _load_contract(common_database, contract_code)
        verified_queries = _load_verified_queries(common_database, contract)
        source_database_role = _required_text(
            contract.get("source_database_role"),
            "source_database_role",
        ).upper()
        mongodb_database_role = _required_text(
            contract.get("mongodb_database_role"),
            "mongodb_database_role",
        ).upper()
        if source_database_role not in {"STORY", "STORY_PLATFORM"}:
            raise ValueError(
                "This pilot accepts a STORY source so IdentifierEngine and "
                "MariaDB transaction share one connection."
            )

        source_table_name = _safe_identifier(
            contract.get("source_table_name"),
            "source_table_name",
        )
        source_identifier_column_name = _safe_identifier(
            contract.get("source_identifier_column_name"),
            "source_identifier_column_name",
        )
        collection_name = _safe_identifier(
            contract.get("mongodb_collection_name"),
            "mongodb_collection_name",
        )
        source_object_code = _required_text(
            contract.get("source_object_code"),
            "source_object_code",
        )
        execution_link_type_code = _required_text(
            contract.get("execution_link_type_code"),
            "execution_link_type_code",
        )

        payload_column_names = [
            _safe_identifier(column_name, "payload_column_name")
            for column_name in contract.get("payload_column_names", [])
        ]
        if not payload_column_names:
            raise ValueError("payload_column_names must contain at least one column.")

        configured_audit_columns = contract.get("audit_column_names") or list(_AUDIT_COLUMNS)
        audit_column_names = [
            _safe_identifier(column_name, "audit_column_name")
            for column_name in configured_audit_columns
        ]
        unknown_audit_columns = set(audit_column_names) - set(_AUDIT_COLUMNS)
        if unknown_audit_columns:
            raise ValueError(
                f"Unknown audit columns: {sorted(unknown_audit_columns)}"
            )

        source_object = _load_object(story_database, source_object_code)
        execution_object = _load_object(story_database, _EXECUTION_OBJECT_CODE)
        mongodb_objects = {
            object_code: _load_object(story_database, object_code)
            for object_code in _MONGODB_OBJECT_CODES
        }

        coordinator = IdentifierCoordinator(story_database)
        execution_request, execution_prepared = _prepare_identifier(
            coordinator,
            execution_object,
            actor_id,
            client_ip,
        )
        document_request, document_prepared = _prepare_identifier(
            coordinator,
            mongodb_objects["MDD"],
            actor_id,
            client_ip,
        )
        for prepared in (execution_prepared, document_prepared):
            coordinator.acquire(prepared)
            acquired_preparations.append(prepared)

        mongodb_database = CommonDatabase(
            database_role=mongodb_database_role,
            connect_mariadb=False,
            connect_mongodb=True,
        )

        with SpsDistributedTransaction(
            story_database,
            mongodb_database,
        ) as transaction:
            source_row = story_database.fetch_one(
                verified_queries["source_read"]["sql_text"],
                (source_identifier,),
            )
            if not source_row:
                raise LookupError(
                    f"Source row not found: {source_table_name}.{source_identifier_column_name}="
                    f"{source_identifier}"
                )

            existing_documents = mongodb_database.find(
                collection_name=collection_name,
                filter_document={
                    "_sps.contract_code": contract_code,
                    "_sps.source_identifier": source_identifier,
                },
                limit=1,
            )
            if existing_documents:
                raise RuntimeError(
                    "Source row was already migrated to MongoDB. "
                    f"contract_code={contract_code}, source_identifier={source_identifier}"
                )

            execution_resolution = coordinator.resolve(
                request=execution_request,
                prepared=execution_prepared,
            )
            document_resolution = coordinator.resolve(
                request=document_request,
                prepared=document_prepared,
            )
            execution_history_id = execution_resolution.identifier
            document_detail_id = document_resolution.identifier

            payload = {
                column_name: source_row.get(column_name)
                for column_name in payload_column_names
                if source_row.get(column_name) is not None
            }
            if not payload:
                raise ValueError("The selected source row has no payload values to migrate.")

            sparse_audit = {
                column_name: source_row.get(column_name)
                for column_name in audit_column_names
                if source_row.get(column_name) not in (None, "")
            }

            _insert_execution_history(
                story_database,
                sql_text=verified_queries["execution_insert"]["sql_text"],
                execution_history_id=execution_history_id,
                source_object=source_object,
                source_identifier=source_identifier,
                actor_id=actor_id,
                client_ip=client_ip,
            )

            mongodb_document_id = transaction.insert_mongodb_document(
                collection_name=collection_name,
                document={
                    "_sps": {
                        "contract_code": contract_code,
                        "execution_history_id": execution_history_id,
                        "document_detail_id": document_detail_id,
                        "source_database_role": source_database_role,
                        "source_table_name": source_table_name,
                        "source_identifier_column_name": source_identifier_column_name,
                        "source_identifier": source_identifier,
                        "schema_version": "v1.0",
                    },
                    "payload": payload,
                    "audit": sparse_audit,
                },
                compensation_filter={
                    "_sps.execution_history_id": execution_history_id,
                },
            )

            _insert_execution_link(
                story_database,
                sql_text=verified_queries["link_insert"]["sql_text"],
                execution_history_id=execution_history_id,
                execution_object=execution_object,
                mongodb_objects=mongodb_objects,
                execution_link_type_code=execution_link_type_code,
                actor_id=actor_id,
                client_ip=client_ip,
            )
            _finalize_execution_history(
                story_database,
                sql_text=verified_queries["finalize_update"]["sql_text"],
                execution_history_id=execution_history_id,
                actor_id=actor_id,
                client_ip=client_ip,
            )

        return {
            "contract_code": contract_code,
            "source_table_name": source_table_name,
            "source_identifier": source_identifier,
            "mongodb_collection_name": collection_name,
            "mongodb_document_id": mongodb_document_id,
            "execution_history_id": execution_history_id,
            "document_detail_id": document_detail_id,
            "payload_columns": list(payload),
            "mongodb_audit_columns": list(sparse_audit),
            "source_payload_retained_yn": "Y",
            "verified_query_ids": {
                operation_name: query["query_id"]
                for operation_name, query in verified_queries.items()
            },
        }
    finally:
        for prepared in reversed(acquired_preparations):
            try:
                IdentifierCoordinator(story_database).release(prepared)
            except Exception:
                pass
        if mongodb_database is not None:
            mongodb_database.close()
        story_database.close()
        common_database.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract-code", required=True)
    parser.add_argument("--source-identifier", required=True)
    parser.add_argument("--actor-id", required=True)
    parser.add_argument("--client-ip", default="127.0.0.1")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not args.apply:
        raise SystemExit("--apply is required for the one-record migration.")

    result = migrate_one(
        contract_code=args.contract_code.strip(),
        source_identifier=args.source_identifier.strip(),
        actor_id=args.actor_id.strip(),
        client_ip=args.client_ip.strip(),
    )
    print(json.dumps(result, ensure_ascii=False, default=str, indent=2))


if __name__ == "__main__":
    main()
