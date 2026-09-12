"""FileRuntimeAdapter storage-separation tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from engine.runtime.file_runtime_adapter import FileRuntimeAdapter


class _InsertResult:
    def __init__(self, inserted_id: str) -> None:
        self.inserted_id = inserted_id


class _IdentifierResolution:
    def __init__(self, identifier: str) -> None:
        self.identifier = identifier
        self.rule_id = "RULE_OBJECT_LEVEL"
        self.rule_code = "RL_OBJECT_LEVEL_CLASSIFICATION"
        self.rule_action_id = "ACTION_OBJECT_LEVEL"
        self.rule_action_type_code = "OBJECT_LEVEL_CLASSIFICATION"
        self.object_level = 3
        self.resolution_source = "EXPLICIT_RULE"


class _IdentifierCoordinator:
    def __init__(self) -> None:
        self.prepare_requests: list[dict[str, Any]] = []
        self.acquired: list[str] = []
        self.resolved: list[str] = []
        self.released: list[str] = []

    def prepare_registered_object(
        self,
        *,
        object_metadata: dict[str, Any],
        created_by: str,
        updated_by: str,
        client_ip: str,
        program_id: str,
    ) -> tuple[dict[str, Any], dict[str, str]]:
        request = dict(object_metadata)
        request.update(
            {
                "created_by": created_by,
                "updated_by": updated_by,
                "client_ip": client_ip,
                "program_id": program_id,
            }
        )
        self.prepare_requests.append(request)
        return request, {"object_code": str(request["object_code"])}

    def acquire(self, prepared: dict[str, str]) -> None:
        self.acquired.append(prepared["object_code"])

    def resolve(
        self,
        *,
        request: dict[str, Any],
        prepared: dict[str, str],
    ) -> _IdentifierResolution:
        object_code = str(request["object_code"])
        assert prepared["object_code"] == object_code
        self.resolved.append(object_code)
        return _IdentifierResolution(
            {
                "EXECUTION_HISTORY": "EH_20260802_00001",
                "DOCUMENT": "DC_20260802_00001",
                "MDD": "MDD_20260802_00001",
            }[object_code]
        )

    def release(self, prepared: dict[str, str]) -> None:
        self.released.append(prepared["object_code"])


class _CommonDatabase:
    def __init__(
        self,
        contract_rows: list[dict[str, Any]],
        definition_rows: list[dict[str, Any]],
    ) -> None:
        self.contract_rows = contract_rows
        self.definition_rows = definition_rows
        self.mapping_rows = [
            {
                "code": "DOCUMENT",
                "code_name": "Document File Runtime Mapping",
                "common_code_json": json.dumps(
                    {
                        "extensions": [".pdf", ".txt"],
                        "object_code": "DOCUMENT",
                        "analyzer_module": "document_analyzer",
                        "analyzer_method": "extract_document_text",
                    }
                ),
            },
            {
                "code": "FILE",
                "code_name": "Default File Runtime Mapping",
                "common_code_json": json.dumps(
                    {
                        "extensions": [],
                        "default_yn": "Y",
                        "object_code": "FILE",
                        "analyzer_module": None,
                        "analyzer_method": None,
                    }
                ),
            },
        ]
        self.closed = False

    def fetch_all(
        self,
        _sql: str,
        parameters: tuple[str],
    ) -> list[dict[str, Any]]:
        if parameters == ("STORAGE_SEPARATION_TARGET",):
            return self.contract_rows
        if parameters == ("MONGODB_RUNTIME_OBJECT_DEFINITION",):
            return self.definition_rows
        if parameters == ("FILE_RUNTIME_MAPPING",):
            return self.mapping_rows
        raise AssertionError(f"Unexpected Common query parameters: {parameters}")

    def close(self) -> None:
        self.closed = True


class _RuntimeDatabase:
    def __init__(self, *, fail_execution_link: bool = False) -> None:
        self.fail_execution_link = fail_execution_link
        self.closed = False
        self.events: list[str] = []
        self.executed: list[tuple[str, tuple[Any, ...]]] = []
        self.mongodb_documents: list[dict[str, Any]] = []
        self.deleted_filters: list[dict[str, Any]] = []
        self.object_by_code = {
            "EXECUTION_HISTORY": {
                "object_id": "OBJECT_EXECUTION_HISTORY",
                "object_code": "EXECUTION_HISTORY",
                "target_identifier_field": "execution_history_id",
                "identifier_target_code": "EG",
            },
            "DOCUMENT": {
                "object_id": "OBJECT_DOCUMENT",
                "object_code": "DOCUMENT",
                "target_identifier_field": "document_id",
                "identifier_target_code": "DC",
            },
            "MDB": {
                "object_id": "OBJECT_MDB",
                "object_code": "MDB",
                "target_identifier_field": "mongodb_database_id",
                "identifier_target_code": "MDB",
            },
            "MCO": {
                "object_id": "OBJECT_MCO",
                "object_code": "MCO",
                "target_identifier_field": "mongodb_collection_id",
                "identifier_target_code": "MCO",
            },
            "MCM": {
                "object_id": "OBJECT_MCM",
                "object_code": "MCM",
                "target_identifier_field": "mongodb_document_master_id",
                "identifier_target_code": "MCM",
            },
            "MDD": {
                "object_id": "OBJECT_MDD",
                "object_code": "MDD",
                "target_identifier_field": "mongodb_document_details_id",
                "identifier_target_code": "MDD",
            },
        }
        for object_metadata in self.object_by_code.values():
            object_metadata.update(
                {
                    "object_name": f"{object_metadata['object_code']} Object",
                    "object_description": "Storage separation test object.",
                    "business_code": "SP",
                    "domain_code": "RP",
                    "object_type_code": "OBJECT",
                    "object_level": 3,
                    "sequence_scope_code": "DAILY",
                    "sequence_length": 5,
                    "status_code": "ACTIVE",
                    "active_yn": "Y",
                }
            )
        self.object_by_code["DOCUMENT"].update(
            object_type_code="OBJECT",
            object_level=2,
        )
        self.object_by_code["MDB"].update(
            object_type_code="DATABASE",
            object_level=1,
            sequence_scope_code="YEARLY",
        )
        self.object_by_code["MCO"].update(
            object_type_code="REPOSITORY",
            object_level=2,
            sequence_scope_code="MONTHLY",
        )
        self.object_by_code["MCM"].update(
            object_type_code="REPOSITORY",
            object_level=3,
        )
        self.object_by_code["MDD"].update(
            object_type_code="DOCUMENT",
            object_level=4,
        )

    def ping_mariadb(self) -> bool:
        return True

    def ping_mongodb(self) -> bool:
        return True

    def begin(self) -> None:
        self.events.append("begin")

    def commit(self) -> None:
        self.events.append("commit")

    def rollback(self) -> None:
        self.events.append("rollback")

    def fetch_one(
        self,
        _sql: str,
        parameters: tuple[str],
    ) -> dict[str, Any] | None:
        return self.object_by_code.get(parameters[0])

    def list_collection_names(self) -> list[str]:
        return ["runtime_execution_payload"]

    def execute(self, sql: str, params: tuple[Any, ...]) -> int:
        normalized_sql = " ".join(sql.split())
        if "generated_identifier" in normalized_sql:
            self.events.append("mariadb_index")
        elif "INSERT INTO sp_object_execution_link" in normalized_sql:
            self.events.append("execution_link")
            if self.fail_execution_link:
                raise RuntimeError("execution link write failed")
        elif "repository_status_code" in normalized_sql:
            self.events.append("mariadb_finalize")
        else:
            raise AssertionError(f"Unexpected Runtime SQL: {normalized_sql}")

        self.executed.append((normalized_sql, params))
        return 1

    def insert_one(
        self,
        collection_name: str,
        document: dict[str, Any],
    ) -> _InsertResult:
        assert collection_name == "runtime_execution_payload"
        self.events.append("mongodb_document")
        self.mongodb_documents.append(dict(document))
        return _InsertResult("mongo-object-id-1")

    def delete_one(
        self,
        collection_name: str,
        filter_document: dict[str, Any],
    ) -> None:
        assert collection_name == "runtime_execution_payload"
        self.events.append("mongodb_compensation")
        self.deleted_filters.append(dict(filter_document))

    def close(self) -> None:
        self.closed = True


def _contract_rows() -> list[dict[str, Any]]:
    return [
        {
            "code": "RUNTIME_EXECUTION_PAYLOAD",
            "code_name": "Runtime Execution Payload",
            "common_code_json": json.dumps(
                {
                    "source_database_role": "STORY",
                    "mongodb_database_role": "STORY",
                    "source_table_name": "sp_execution_history",
                    "source_object_code": "EXECUTION_HISTORY",
                    "source_identifier_column_name": "execution_history_id",
                    "mariadb_ssot": "INDEX_ONLY",
                    "mongodb_collection_name": "runtime_execution_payload",
                    "mongodb_ssot": "EXECUTION_PAYLOAD",
                    "payload_column_names": [],
                    "execution_link_required_yn": "Y",
                    "execution_link_type_code": "MONGODB",
                    "migration_mode_code": "FUTURE_PAYLOAD",
                }
            ),
        }
    ]


def _definition_rows() -> list[dict[str, Any]]:
    return [
        {
            "code": "MDB",
            "common_code_json": json.dumps(
                {
                    "object_code": "MDB",
                    "object_level": 1,
                    "object_type_code": "DATABASE",
                    "target_identifier_field": "mongodb_database_id",
                    "identifier_target_code": "MDB",
                    "mongodb_internal_yn": "N",
                }
            ),
        },
        {
            "code": "MCO",
            "common_code_json": json.dumps(
                {
                    "object_code": "MCO",
                    "object_level": 2,
                    "object_type_code": "REPOSITORY",
                    "target_identifier_field": "mongodb_collection_id",
                    "identifier_target_code": "MCO",
                    "mongodb_internal_yn": "N",
                }
            ),
        },
        {
            "code": "MCM",
            "common_code_json": json.dumps(
                {
                    "object_code": "MCM",
                    "object_level": 3,
                    "object_type_code": "REPOSITORY",
                    "target_identifier_field": "mongodb_document_master_id",
                    "identifier_target_code": "MCM",
                    "mongodb_internal_yn": "N",
                }
            ),
        },
        {
            "code": "MDD",
            "common_code_json": json.dumps(
                {
                    "object_code": "MDD",
                    "object_level": 4,
                    "object_type_code": "DOCUMENT",
                    "target_identifier_field": "mongodb_document_details_id",
                    "identifier_target_code": "MDD",
                    "mongodb_internal_yn": "Y",
                }
            ),
        },
    ]


def _build_adapter(
    runtime_database: _RuntimeDatabase,
) -> tuple[
    FileRuntimeAdapter,
    _CommonDatabase,
    _IdentifierCoordinator,
]:
    common_database = _CommonDatabase(
        _contract_rows(),
        _definition_rows(),
    )
    identifier_coordinator = _IdentifierCoordinator()

    def database_factory(*, database_role: str, connect_mariadb: bool = True, connect_mongodb: bool = False):
        if database_role == "COMMON":
            assert connect_mongodb is False
            return common_database
        assert database_role == "STORY"
        assert (connect_mariadb, connect_mongodb) in ((True, False), (False, True))
        return runtime_database

    adapter = FileRuntimeAdapter(
        database_factory=database_factory,
        identifier_coordinator_factory=lambda _database: identifier_coordinator,
    )
    adapter._run_analyzer = lambda _source, _metadata: {
        "status": "SUCCESS",
        "analyzer_module": "document_analyzer",
        "analyzer_method": "extract_document_text",
        "text": "검증용 상세 Document 본문",
    }
    return adapter, common_database, identifier_coordinator


def test_execute_persists_index_execution_link_and_document_in_order(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "source.txt"
    source_file.write_text("source", encoding="utf-8")
    runtime_database = _RuntimeDatabase()
    adapter, common_database, identifier_coordinator = _build_adapter(
        runtime_database
    )

    result = adapter.execute(
        str(source_file),
        requested_by="tester",
        client_ip="127.0.0.1",
    )

    assert result["status"] == "SUCCESS"
    assert runtime_database.events == [
        "begin",
        "mariadb_index",
        "execution_link",
        "mongodb_document",
        "mariadb_finalize",
        "commit",
    ]
    assert [
        request["object_code"]
        for request in identifier_coordinator.prepare_requests
    ] == [
        "EXECUTION_HISTORY",
        "DOCUMENT",
        "MDD",
    ]
    assert all(
        request["created_by"] == "tester"
        and request["updated_by"] == "tester"
        and request["client_ip"] == "127.0.0.1"
        for request in identifier_coordinator.prepare_requests
    )
    assert identifier_coordinator.acquired == [
        "EXECUTION_HISTORY",
        "DOCUMENT",
        "MDD",
    ]
    assert identifier_coordinator.resolved == [
        "EXECUTION_HISTORY",
        "DOCUMENT",
        "MDD",
    ]
    assert identifier_coordinator.released == [
        "MDD",
        "DOCUMENT",
        "EXECUTION_HISTORY",
    ]
    assert result["identifier_sequence_result"] == {
        "prepared_object_codes": ["EXECUTION_HISTORY", "DOCUMENT", "MDD"],
        "rule_resolutions": {
            object_code: {
                "rule_id": "RULE_OBJECT_LEVEL",
                "rule_code": "RL_OBJECT_LEVEL_CLASSIFICATION",
                "rule_action_id": "ACTION_OBJECT_LEVEL",
                "rule_action_type_code": "OBJECT_LEVEL_CLASSIFICATION",
                "object_level": 3,
                "resolution_source": "EXPLICIT_RULE",
            }
            for object_code in ("EXECUTION_HISTORY", "DOCUMENT", "MDD")
        },
        "status": "SUCCESS",
    }

    document = runtime_database.mongodb_documents[0]
    assert document["execution_history_id"] == "EH_20260802_00001"
    assert document["mongodb_database_id"] == "OBJECT_MDB"
    assert document["mongodb_collection_id"] == "OBJECT_MCO"
    assert document["mongodb_document_master_id"] == "OBJECT_MCM"
    assert document["mongodb_document_details_id"] == "MDD_20260802_00001"
    assert document["content"] == "검증용 상세 Document 본문"

    link_sql, link_params = next(
        item
        for item in runtime_database.executed
        if "INSERT INTO sp_object_execution_link" in item[0]
    )
    assert "object_attempt_id" in link_sql
    assert link_params[:7] == (
        "EH_20260802_00001",
        "OBJECT_EXECUTION_HISTORY",
        "OBJECT_MCM",
        "MONGODB",
        "OBJECT_MDB",
        "OBJECT_MCO",
        "OBJECT_MCM",
    )
    assert common_database.closed is True
    assert runtime_database.closed is True


def test_execute_does_not_write_mongodb_when_execution_link_write_fails(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "source.txt"
    source_file.write_text("source", encoding="utf-8")
    runtime_database = _RuntimeDatabase(fail_execution_link=True)
    adapter, common_database, _ = _build_adapter(runtime_database)

    with pytest.raises(RuntimeError, match="execution link write failed"):
        adapter.execute(
            str(source_file),
            requested_by="tester",
            client_ip="127.0.0.1",
        )

    assert "rollback" in runtime_database.events
    assert runtime_database.deleted_filters == []
    assert runtime_database.mongodb_documents == []
    assert common_database.closed is True
    assert runtime_database.closed is True


def test_execute_uses_index_table_name_from_storage_contract(tmp_path: Path) -> None:
    source_file = tmp_path / "source.txt"
    source_file.write_text("source", encoding="utf-8")
    runtime_database = _RuntimeDatabase()
    adapter, common_database, _ = _build_adapter(runtime_database)
    contract = json.loads(common_database.contract_rows[0]["common_code_json"])
    contract["source_table_name"] = "runtime_execution_index"
    common_database.contract_rows[0]["common_code_json"] = json.dumps(contract)

    adapter.execute(
        str(source_file),
        requested_by="tester",
        client_ip="127.0.0.1",
    )

    executed_sql = [sql for sql, _ in runtime_database.executed]
    assert any("INSERT INTO runtime_execution_index" in sql for sql in executed_sql)
    assert any("UPDATE runtime_execution_index" in sql for sql in executed_sql)
