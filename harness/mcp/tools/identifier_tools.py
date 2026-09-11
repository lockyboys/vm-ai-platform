# =============================================================================
# File Name   : harness/mcp/tools/identifier_tools.py
# Purpose     : SPS Harness Repository Identifier Generation Tool
# =============================================================================
# CHANGE HISTORY
# =============================================================================
# 20260830 | OpenAI | Repository Object metadata 기반 Identifier 발급 도구를 추가했음
# 20260903 | OpenAI | Sequence 예약 즉시 Commit 및 후속 실패 시 번호 폐기를 적용했음
# =============================================================================

from __future__ import annotations

from typing import Any

from common.common_function import normalize_required_text
from common.database import CommonDatabase
from engine.identifier import IdentifierCoordinator
from harness.mcp.tools.verified_sql_tools import _load_registered_object_metadata


def identifier_generate(
    object_code: str,
    *,
    actor_id: str = "SPS_HARNESS",
    program_id: str = "SPS_HARNESS_IDENTIFIER_GENERATE",
    client_ip: str = "127.0.0.1",
    apply: bool = False,
) -> dict[str, Any]:
    """Generate one Identifier from one active Repository Object.

    The default validates and reports the Repository-defined allocation target
    without allocating a sequence. Set apply=true only when the returned
    Object metadata has been reviewed.
    """

    normalized_object_code = normalize_required_text(
        object_code,
        "object_code",
    ).upper()
    normalized_actor_id = normalize_required_text(actor_id, "actor_id")
    normalized_program_id = normalize_required_text(program_id, "program_id")
    normalized_client_ip = normalize_required_text(client_ip, "client_ip")

    identifier_database = CommonDatabase(database_role="STORY")
    try:
        object_metadata = _load_registered_object_metadata(
            identifier_database,
            normalized_object_code,
        )
        identifier_coordinator = IdentifierCoordinator(identifier_database)
        identifier_maximum_length = (
            identifier_coordinator.resolve_identifier_maximum_length(
                object_metadata=object_metadata,
            )
        )
        identifier_request, identifier_preparation = (
            identifier_coordinator.prepare_registered_object(
                object_metadata=object_metadata,
                created_by=normalized_actor_id,
                updated_by=normalized_actor_id,
                client_ip=normalized_client_ip,
                program_id=normalized_program_id,
            )
        )
        result: dict[str, Any] = {
            "dry_run": not apply,
            "object_code": normalized_object_code,
            "object_name": object_metadata["object_name"],
            "target_identifier_field": object_metadata["target_identifier_field"],
            "identifier_target_code": object_metadata["identifier_target_code"],
            "sequence_scope_code": identifier_preparation["sequence_scope_code"],
            "sequence_date": identifier_preparation["sequence_date"],
            "maximum_length": identifier_maximum_length,
        }
        if not apply:
            return result

        identifier_database.begin()
        lock_acquired = False
        try:
            identifier_coordinator.acquire(identifier_preparation)
            lock_acquired = True
            try:
                identifier_resolution = identifier_coordinator.reserve(
                    request=identifier_request,
                    prepared=identifier_preparation,
                )
                identifier_database.commit()
            except Exception:
                identifier_database.rollback()
                raise
            finally:
                if lock_acquired:
                    identifier_coordinator.release(identifier_preparation)
        except Exception:
            raise

        # Sequence는 이미 Commit되었다. 이후 렌더링 또는 저장 실패 시
        # 예약 번호를 Rollback하거나 재사용하지 않고 폐기한다.
        generated_identifier = identifier_coordinator.render_resolution(
            request=identifier_request,
            prepared=identifier_preparation,
            resolution=identifier_resolution,
            maximum_length=identifier_maximum_length,
        )

        result.update(
            {
                "identifier": generated_identifier,
                "blueprint_code": identifier_resolution.blueprint_code,
                "sequence_no": identifier_resolution.sequence_no,
                "sequence_length": identifier_resolution.sequence_length,
                "sequence_committed_yn": "Y",
                "failure_policy": "DISCARD_RESERVED_SEQUENCE",
                "rule_id": identifier_resolution.rule_id,
                "rule_code": identifier_resolution.rule_code,
            }
        )
        return result
    finally:
        identifier_database.close()
