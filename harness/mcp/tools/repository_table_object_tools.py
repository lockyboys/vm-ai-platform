"""Reconcile the live Repository Table inventory before Lifecycle issuance."""
from __future__ import annotations

from typing import Any

from common.database import CommonDatabase
from engine.batch.business_domain_repository_sync_batch import BusinessDomainRepositorySyncBatch

_PROGRAM_ID = "repository_table_object_reconcile"
_RULE_CODE = "RL_REGISTER_REPOSITORY_OBJECT"
_TARGETS = (
    ("COMMON", "CM"),
    ("STORY", "SP"),
    ("HEALTH", "HC"),
)


def repository_table_object_reconcile(apply: bool = False) -> dict[str, Any]:
    """Synchronize missing physical Table Objects through the registered Repository Rule."""

    common_database = CommonDatabase(database_role="COMMON")
    repository_database = CommonDatabase(database_role="STORY")
    results: list[dict[str, Any]] = []
    try:
        for database_role, business_code in _TARGETS:
            source_database = CommonDatabase(database_role=database_role)
            try:
                batch = BusinessDomainRepositorySyncBatch(
                    source_database,
                    business_code=business_code,
                    rule_code=_RULE_CODE,
                    common_database=common_database,
                    repository_database=repository_database,
                    actor_id="SYSTEM",
                    client_ip="127.0.0.1",
                )
                results.append(batch.run(apply=apply))
            finally:
                source_database.close()
        return {
            "dry_run": not apply,
            "rule_code": _RULE_CODE,
            "targets": [
                {
                    "database_role": database_role,
                    "business_code": business_code,
                }
                for database_role, business_code in _TARGETS
            ],
            "results": results,
        }
    finally:
        repository_database.close()
        common_database.close()
