"""Move one MariaDB detail payload to MongoDB with an SPS execution link."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

# 직접 실행(python scripts/...) 시에도 프로젝트 루트를 import 경로에 넣는다.
# python -m scripts.migrate_one_table_detail 실행과 같은 모듈 해석을 보장한다.
_PROJECT_ROOT_PATH = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT_PATH))

from common.common_function import normalize_required_text
from common.database import CommonDatabase, MariaMongoWriteService
from engine.identifier.coordinator import IdentifierCoordinator


_IDENTIFIER_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
_required_text = normalize_required_text
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
_CHANGE_HISTORY_OBJECT_CODE = "TE_COMMON_CM_CHANGE_HISTORY"
_MONGODB_OBJECT_CODES = ("MDB", "MCO", "MCM", "MDD")


def _safe_identifier(value: Any, field_name: str) -> str:
    normalized = normalize_required_text(value, field_name)
    if not _IDENTIFIER_PATTERN.fullmatch(normalized):
        raise ValueError(f"Unsafe SQL identifier: {field_name}={normalized}")
    return normalized


def _build_mongodb_payload(
    source_row: Mapping[str, Any],
    *,
    payload_column_names: list[str],
    mongodb_payload_field_name: str,
) -> dict[str, Any]:
    """Map MariaDB detail columns into one metadata-defined MongoDB payload field."""
    source_payload = {
        column_name: source_row.get(column_name)
        for column_name in payload_column_names
        if source_row.get(column_name) is not None
    }
    if not source_payload:
        raise ValueError("The selected source row has no payload values to migrate.")
    # Multi-column contracts must preserve the source column names even when
    # this particular row has only one non-null value.
    if len(payload_column_names) == 1:
        return {mongodb_payload_field_name: next(iter(source_payload.values()))}
    return {mongodb_payload_field_name: source_payload}


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
    "source_clear": "UPDATE",
    "execution_insert": "CREATE",
    "link_insert": "CREATE",
    "finalize_update": "UPDATE",
    "change_history_insert": "CREATE",
}

_SOURCE_CLEAR_PARAMETER_CODES = {
    "actor_id",
    "program_id",
    "client_ip",
    "source_identifier",
}


def _resolve_source_clear_parameters(
    contract: Mapping[str, Any],
    *,
    actor_id: str,
    client_ip: str,
    source_identifier: str,
) -> tuple[str, ...]:
    """Build registered source-clear parameters from contract metadata."""
    migration_mode_code = _required_text(
        contract.get("migration_mode_code"),
        "migration_mode_code",
    ).upper()
    if migration_mode_code != "MOVE_PAYLOAD":
        raise ValueError(
            "Physical migration requires migration_mode_code=MOVE_PAYLOAD. "
            f"actual={migration_mode_code}"
        )

    parameter_codes = contract.get("source_clear_parameter_codes")
    if not isinstance(parameter_codes, list) or not parameter_codes:
        raise ValueError(
            "source_clear_parameter_codes must be a non-empty list in the "
            f"storage separation contract: {contract.get('contract_code', '<unknown>')}"
        )

    values = {
        "actor_id": actor_id,
        "program_id": _PROGRAM_ID,
        "client_ip": client_ip,
        "source_identifier": source_identifier,
    }
    resolved_parameters: list[str] = []
    for parameter_code in parameter_codes:
        normalized_code = _required_text(
            parameter_code,
            "source_clear_parameter_code",
        )
        if normalized_code not in _SOURCE_CLEAR_PARAMETER_CODES:
            raise ValueError(
                "Unsupported source clear parameter code: "
                f"{normalized_code}"
            )
        resolved_parameters.append(values[normalized_code])
    return tuple(resolved_parameters)


def _assert_source_queries_share_transaction_scope(
    *,
    source_database: CommonDatabase,
    transaction_database: CommonDatabase,
    source_read_sql: str,
    source_clear_sql: str,
) -> None:
    """Reject cross-server moves before any document or index is written."""
    if source_database is transaction_database:
        return

    differing_connection_fields = [
        field_name
        for field_name in ("host", "port", "user")
        if source_database.config.get(field_name)
        != transaction_database.config.get(field_name)
    ]
    if differing_connection_fields:
        raise RuntimeError(
            "Source and execution MariaDB roles cannot share one transaction. "
            f"differing_fields={differing_connection_fields}"
        )

    source_schema_name = _safe_identifier(
        source_database.database_name,
        "source_database_name",
    )
    qualified_schema_marker = f"{source_schema_name.lower()}."
    for operation_name, sql_text in (
        ("source_read", source_read_sql),
        ("source_clear", source_clear_sql),
    ):
        normalized_sql = sql_text.replace(chr(96), "").lower()
        if qualified_schema_marker not in normalized_sql:
            raise ValueError(
                "Cross-role storage migration requires a schema-qualified "
                "Verified SQL query. "
                f"operation_name={operation_name}, "
                f"source_schema={source_schema_name}"
            )


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


def _load_knowledge_type(
    story_database: CommonDatabase,
    knowledge_type_code: str,
) -> dict[str, Any]:
    row = story_database.fetch_one(
        """
        SELECT knowledge_type_id, knowledge_type_code, knowledge_type_name
        FROM sp_knowledge_type_hold
        WHERE knowledge_type_code = %s
          AND active_yn = 'Y'
          AND deleted_yn = 'N'
          AND deleted_dt IS NULL
        """,
        (knowledge_type_code,),
    )
    if not row:
        raise LookupError(
            f"Active Knowledge Type not found: {knowledge_type_code}"
        )
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


def _insert_change_history(
    database: CommonDatabase,
    *,
    sql_text: str,
    change_history_id: str,
    source_database_name: str,
    source_table_name: str,
    source_identifier: str,
    actor_id: str,
    client_ip: str,
) -> None:
    affected_rows = database.execute(
        sql_text,
        (
            change_history_id,
            source_database_name,
            source_table_name,
            source_identifier,
            "UPDATE",
            "Moved MariaDB detail payload to MongoDB and linked the execution.",
            actor_id,
            client_ip,
            _PROGRAM_ID,
        ),
    )
    if affected_rows != 1:
        raise RuntimeError(
            "Change history insert did not affect one row. "
            f"change_history_id={change_history_id}"
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


def _clear_source_payload(
    database: CommonDatabase,
    *,
    sql_text: str,
    parameters: tuple[str, ...],
    source_table_name: str,
    source_identifier: str,
) -> None:
    affected_rows = database.execute(sql_text, parameters)
    if affected_rows != 1:
        raise RuntimeError(
            "Source payload clear did not affect one row. "
            f"source_table_name={source_table_name}, "
            f"source_identifier={source_identifier}"
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
        source_clear_parameters = _resolve_source_clear_parameters(
            contract,
            actor_id=actor_id,
            client_ip=client_ip,
            source_identifier=source_identifier,
        )
        verified_queries = _load_verified_queries(common_database, contract)
        source_database_role = _required_text(
            contract.get("source_database_role"),
            "source_database_role",
        ).upper()
        mongodb_database_role = _required_text(
            contract.get("mongodb_database_role"),
            "mongodb_database_role",
        ).upper()
        if source_database_role not in {"COMMON", "STORY", "STORY_PLATFORM"}:
            raise ValueError(
                "This pilot accepts only COMMON or STORY MariaDB source roles."
            )
        source_database = (
            common_database
            if source_database_role == "COMMON"
            else story_database
        )
        _assert_source_queries_share_transaction_scope(
            source_database=source_database,
            transaction_database=story_database,
            source_read_sql=verified_queries["source_read"]["sql_text"],
            source_clear_sql=verified_queries["source_clear"]["sql_text"],
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
        configured_source_clear_payload_column_names = contract.get(
            "source_clear_payload_column_names",
            payload_column_names,
        )
        source_clear_payload_column_names = [
            _safe_identifier(column_name, "source_clear_payload_column_name")
            for column_name in configured_source_clear_payload_column_names
        ]
        unknown_source_clear_columns = (
            set(source_clear_payload_column_names) - set(payload_column_names)
        )
        if unknown_source_clear_columns:
            raise ValueError(
                "source_clear_payload_column_names must be included in "
                f"payload_column_names: {sorted(unknown_source_clear_columns)}"
            )
        retained_payload_column_names = sorted(
            set(payload_column_names) - set(source_clear_payload_column_names)
        )
        mongodb_payload_field_name = _safe_identifier(
            contract.get("mongodb_payload_field_name"),
            "mongodb_payload_field_name",
        )

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
        change_history_object = _load_object(
            story_database,
            _CHANGE_HISTORY_OBJECT_CODE,
        )
        knowledge_type = _load_knowledge_type(
            story_database,
            _required_text(
                contract.get("knowledge_type_code"),
                "knowledge_type_code",
            ),
        )
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
        change_history_request, change_history_prepared = _prepare_identifier(
            coordinator,
            change_history_object,
            actor_id,
            client_ip,
        )
        for prepared in (
            execution_prepared,
            document_prepared,
            change_history_prepared,
        ):
            coordinator.acquire(prepared)
            acquired_preparations.append(prepared)

        mongodb_database = CommonDatabase(
            database_role=mongodb_database_role,
            connect_mariadb=False,
            connect_mongodb=True,
        )

        with MariaMongoWriteService(
            story_database,
            mongodb_database,
        ) as database_writer:
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
            change_history_resolution = coordinator.resolve(
                request=change_history_request,
                prepared=change_history_prepared,
            )
            execution_history_id = execution_resolution.identifier
            document_detail_id = document_resolution.identifier
            change_history_id = change_history_resolution.identifier

            payload = _build_mongodb_payload(
                source_row,
                payload_column_names=payload_column_names,
                mongodb_payload_field_name=mongodb_payload_field_name,
            )

            # MongoDB 생성 감사 4개는 모든 상세 문서에 필수다. 수정·삭제 감사
            # 필드는 원본에 실제 값이 있을 때만 보존해 불필요한 null 저장을 막는다.
            sparse_audit = {
                "created_dt": source_row.get("created_dt")
                or datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "created_by": source_row.get("created_by") or actor_id,
                "client_ip": source_row.get("client_ip") or client_ip,
                "program_id": source_row.get("program_id") or _PROGRAM_ID,
            }
            sparse_audit.update(
                {
                    column_name: source_row.get(column_name)
                    for column_name in audit_column_names
                    if column_name
                    not in {"created_dt", "created_by", "client_ip", "program_id"}
                    and source_row.get(column_name) not in (None, "")
                }
            )

            _insert_execution_history(
                story_database,
                sql_text=verified_queries["execution_insert"]["sql_text"],
                execution_history_id=execution_history_id,
                source_object=source_object,
                source_identifier=source_identifier,
                actor_id=actor_id,
                client_ip=client_ip,
            )

            mongodb_document_id = database_writer.insert_mongodb_document(
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
                        "knowledge_type_id": knowledge_type["knowledge_type_id"],
                        "knowledge_type_code": knowledge_type["knowledge_type_code"],
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
            _clear_source_payload(
                story_database,
                sql_text=verified_queries["source_clear"]["sql_text"],
                parameters=source_clear_parameters,
                source_table_name=source_table_name,
                source_identifier=source_identifier,
            )
            _insert_change_history(
                story_database,
                sql_text=verified_queries["change_history_insert"]["sql_text"],
                change_history_id=change_history_id,
                source_database_name=source_database.database_name,
                source_table_name=source_table_name,
                source_identifier=source_identifier,
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
            "change_history_id": change_history_id,
            "knowledge_type_code": knowledge_type["knowledge_type_code"],
            "payload_columns": list(payload),
            "mongodb_audit_columns": list(sparse_audit),
            # NOT NULL payload fields remain only until the separately verified
            # backup and DDL removal; nullable fields were cleared in this transaction.
            "source_payload_retained_yn": "Y" if retained_payload_column_names else "N",
            "source_payload_retained_column_names": retained_payload_column_names,
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
