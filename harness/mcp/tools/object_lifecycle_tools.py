"""Reconcile Level 3 Table Object lifecycle links through the Identifier Engine."""
from __future__ import annotations

from typing import Any

from common.common_function import validate_common_code_value
from common.database import CommonDatabase
from engine.batch.business_domain_repository_sync_batch import (
    BusinessDomainRepositorySyncBatch,
)
from engine.identifier import IdentifierCoordinator

_PROGRAM_ID = "object_lifecycle_reconcile"
_TABLE_OBJECT_RULE_CODE = "RL_REGISTER_REPOSITORY_OBJECT"
# HEALTH는 MongoDB 상세 저장소이므로 여기서 MariaDB 동기화를 시도하지 않는다.
# COMMON 메타데이터와 STORY Platform Object만 대상으로 Lifecycle을 발급한다.
_TABLE_OBJECT_TARGETS = (("COMMON", "CM"), ("STORY", "SP"))


def _sync_table_objects(apply: bool) -> list[dict[str, Any]]:
    common_database = CommonDatabase(database_role="COMMON")
    repository_database = CommonDatabase(database_role="STORY")
    results: list[dict[str, Any]] = []
    try:
        for database_role, business_code in _TABLE_OBJECT_TARGETS:
            source_database = CommonDatabase(database_role=database_role)
            try:
                results.append(
                    BusinessDomainRepositorySyncBatch(
                        source_database,
                        business_code=business_code,
                        rule_code=_TABLE_OBJECT_RULE_CODE,
                        common_database=common_database,
                        repository_database=repository_database,
                    ).run(apply=apply)
                )
            finally:
                source_database.close()
        return results
    finally:
        repository_database.close()
        common_database.close()


def _load_table_objects(database: CommonDatabase) -> list[dict[str, Any]]:
    return database.fetch_all(
        """
        SELECT DISTINCT
            object_row.object_id,
            object_row.object_code,
            object_row.lifecycle_id,
            lifecycle_row.object_lifecycle_id AS linked_lifecycle_id
        FROM sp_entity AS entity_row
        JOIN sp_object AS object_row
          ON object_row.object_id = entity_row.object_id
        LEFT JOIN sp_object_lifecycle AS lifecycle_row
          ON lifecycle_row.object_lifecycle_id = object_row.lifecycle_id
         AND lifecycle_row.object_id = object_row.object_id
         AND lifecycle_row.deleted_dt IS NULL
        WHERE entity_row.entity_type_code = 'PHYSICAL'
          AND entity_row.enabled_yn = 'Y'
          AND entity_row.deleted_dt IS NULL
          AND object_row.object_type_code = 'TABLE'
          AND object_row.object_level = 3
          AND object_row.active_yn = 'Y'
          AND object_row.status_code = 'ACTIVE'
          AND object_row.deleted_dt IS NULL
        ORDER BY object_row.object_code
        """
    )


def _load_identifier_metadata(database: CommonDatabase) -> dict[str, Any]:
    metadata = database.fetch_one(
        """
        SELECT object_code, business_code, domain_code, object_level,
               identifier_target_code, sequence_scope_code, sequence_length
        FROM sp_object
        WHERE object_code = 'TABLE'
          AND object_type_code = 'TABLE'
          AND object_level = 3
          AND active_yn = 'Y'
          AND status_code = 'ACTIVE'
          AND deleted_dt IS NULL
        """
    )
    if not metadata:
        raise LookupError("Active Level 3 TABLE Identifier metadata was not found.")
    return metadata


def object_lifecycle_reconcile(
    apply: bool = False,
    actor_id: str = "SYSTEM",
    client_ip: str = "127.0.0.1",
) -> dict[str, Any]:
    """Issue and connect Lifecycle rows only for valid Level 3 physical Table Objects."""

    database = CommonDatabase(database_role="STORY")
    common_database = CommonDatabase(database_role="COMMON")
    table_sync_results = _sync_table_objects(apply)
    try:
        registered_status = validate_common_code_value(
            common_database, "OBJECT_LIFECYCLE_STATUS", "REGISTERED"
        )
        register_event = validate_common_code_value(
            common_database, "OBJECT_LIFECYCLE_EVENT", "REGISTER"
        )
        table_objects = _load_table_objects(database)
        missing = [
            row for row in table_objects
            if not row["lifecycle_id"]
        ]
        valid = [
            row for row in table_objects
            if row["linked_lifecycle_id"]
        ]
        invalid = [
            row for row in table_objects
            if row["lifecycle_id"] and not row["linked_lifecycle_id"]
        ]
        result: dict[str, Any] = {
            "dry_run": not apply,
            "table_object_sync": table_sync_results,
            "physical_table_object_count": len(table_objects),
            "valid_lifecycle_link_count": len(valid),
            "lifecycle_to_issue_count": len(missing),
            "invalid_lifecycle_link_count": len(invalid),
            "invalid_lifecycle_object_codes": [
                str(row["object_code"]) for row in invalid
            ],
        }
        if not apply:
            return result
        if invalid:
            raise ValueError(
                "Invalid lifecycle links must be repaired before issuance. "
                f"object_codes={result['invalid_lifecycle_object_codes']}"
            )

        coordinator = IdentifierCoordinator(database)
        metadata = _load_identifier_metadata(database)
        issued: list[dict[str, str]] = []
        database.begin()
        try:
            for table_object in missing:
                request, prepared = coordinator.prepare_registered_object(
                    object_metadata=metadata,
                    created_by=actor_id,
                    updated_by=actor_id,
                    client_ip=client_ip,
                    program_id=_PROGRAM_ID,
                )
                coordinator.acquire(prepared)
                try:
                    lifecycle_id = coordinator.resolve(
                        request=request,
                        prepared=prepared,
                    ).identifier
                finally:
                    coordinator.release(prepared)

                database.execute(
                    """
                    INSERT INTO sp_object_lifecycle (
                        object_lifecycle_id, object_id, lifecycle_status_code,
                        lifecycle_event_code, lifecycle_reason, lifecycle_note,
                        created_by, updated_by, client_ip, program_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        lifecycle_id,
                        table_object["object_id"],
                        registered_status,
                        register_event,
                        "Level 3 Table Object lifecycle reconciliation",
                        "Identifier Engine issued and linked by Harness.",
                        actor_id,
                        actor_id,
                        client_ip,
                        _PROGRAM_ID,
                    ),
                )
                updated_rows = database.execute(
                    """
                    UPDATE sp_object
                    SET lifecycle_id = %s,
                        updated_by = %s,
                        client_ip = %s,
                        program_id = %s
                    WHERE object_id = %s
                      AND lifecycle_id IS NULL
                    """,
                    (
                        lifecycle_id,
                        actor_id,
                        client_ip,
                        _PROGRAM_ID,
                        table_object["object_id"],
                    ),
                )
                if updated_rows != 1:
                    raise RuntimeError(
                        "Lifecycle row was not linked to exactly one Table Object. "
                        f"object_id={table_object['object_id']}"
                    )
                issued.append(
                    {
                        "object_id": str(table_object["object_id"]),
                        "object_code": str(table_object["object_code"]),
                        "object_lifecycle_id": lifecycle_id,
                    }
                )
            database.commit()
        except Exception:
            database.rollback()
            raise
        result["dry_run"] = False
        result["issued_count"] = len(issued)
        result["issued"] = issued
        return result
    finally:
        common_database.close()
        database.close()
