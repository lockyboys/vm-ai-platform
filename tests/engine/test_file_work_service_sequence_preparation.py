"""File Work Service registered Object Identifier preparation tests."""
from __future__ import annotations

from typing import Any

from engine.processor.work.file_work_service import FileWorkService


class _Database:
    def __init__(self) -> None:
        self.fetch_all_calls: list[tuple[str, tuple[str, ...]]] = []

    def fetch_all(
        self,
        sql: str,
        params: tuple[str, ...],
    ) -> list[dict[str, object]]:
        self.fetch_all_calls.append((sql, params))
        return [
            {
                "object_code": "WORK_ASSET",
                "object_name": "Work Asset",
                "object_description": "Artifact metadata",
                "business_code": "SP",
                "domain_code": "RP",
                "object_type_code": "TABLE",
                "object_level": 3,
                "identifier_target_code": "OB",
                "sequence_scope_code": "DAILY",
                "sequence_length": 5,
                "status_code": "ACTIVE",
                "active_yn": "Y",
            },
            {
                "object_code": "WORK_SESSION",
                "object_name": "Work Session",
                "object_description": "Work session metadata",
                "business_code": "SP",
                "domain_code": "RP",
                "object_type_code": "TABLE",
                "object_level": 3,
                "identifier_target_code": "OB",
                "sequence_scope_code": "DAILY",
                "sequence_length": 5,
                "status_code": "ACTIVE",
                "active_yn": "Y",
            },
            {
                "object_code": "WORK_ITEM",
                "object_name": "Work Item",
                "object_description": "Work item metadata",
                "business_code": "SP",
                "domain_code": "RP",
                "object_type_code": "TABLE",
                "object_level": 3,
                "identifier_target_code": "OB",
                "sequence_scope_code": "DAILY",
                "sequence_length": 5,
                "status_code": "ACTIVE",
                "active_yn": "Y",
            },
        ]


class _IdentifierCoordinator:
    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []

    def prepare_registered_object(
        self,
        *,
        object_metadata: dict[str, object],
        created_by: str,
        updated_by: str,
        client_ip: str,
        program_id: str,
    ) -> tuple[dict[str, object], dict[str, str]]:
        request = dict(object_metadata)
        request.update(
            {
                "created_by": created_by,
                "updated_by": updated_by,
                "client_ip": client_ip,
                "program_id": program_id,
            }
        )
        self.requests.append(request)
        return request, {"object_code": str(request["object_code"])}


def test_prepare_work_identifier_contexts_uses_registered_object_metadata() -> None:
    database = _Database()
    identifier_coordinator = _IdentifierCoordinator()

    contexts = FileWorkService._prepare_work_identifier_contexts(
        database=database,
        identifier_coordinator=identifier_coordinator,
        requested_by="operator",
        client_ip="127.0.0.1",
    )

    assert database.fetch_all_calls[0][1] == (
        "WORK_SESSION",
        "WORK_ITEM",
        "WORK_ASSET",
    )
    assert [
        request["object_code"]
        for request in identifier_coordinator.requests
    ] == [
        "WORK_SESSION",
        "WORK_ITEM",
        "WORK_ASSET",
    ]
    assert {
        request["created_by"]
        for request in identifier_coordinator.requests
    } == {"operator"}
    assert {
        request["updated_by"]
        for request in identifier_coordinator.requests
    } == {"operator"}
    assert {
        request["client_ip"]
        for request in identifier_coordinator.requests
    } == {"127.0.0.1"}
    assert {
        request["program_id"]
        for request in identifier_coordinator.requests
    } == {"file_work_service.py"}
    assert [
        prepared["object_code"]
        for _request, prepared in contexts
    ] == [
        "WORK_SESSION",
        "WORK_ITEM",
        "WORK_ASSET",
    ]
