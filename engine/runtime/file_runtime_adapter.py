"""Repository-driven file runtime persistence adapter.

File Story:
    파일 분석 결과를 Storage Separation 계약에 따라 MariaDB 실행 Index,
    MongoDB 상세 Document, sp_object_execution_link 순서로 저장한다.

Change History:
    20260802 | Codex | File Runtime의 MariaDB Index, MongoDB Document, Execution Link 저장을
    Storage Separation Repository 계약과 보상 트랜잭션으로 연결했음.
    20260802 | Codex | 등록된 Repository Object의 Identifier Sequence 준비·발급 책임을
    IdentifierCoordinator로 이관하여 Object 재등록 없이 처리하도록 보완했음.
"""

from __future__ import annotations

import importlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from common.common_function import normalize_required_text
from common.database import CommonDatabase
from core.transaction.sps_distributed_transaction import SpsDistributedTransaction
from engine.identifier import IdentifierCoordinator
from engine.runtime.object_runtime_engine import ObjectRuntimeEngine
from engine.storage.storage_separation_collection_provisioner import (
    StorageSeparationContractRepository,
)


DOCUMENT_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt",
    ".txt", ".csv", ".md", ".rtf", ".hwp", ".hwpx",
}

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp", ".heic",
}

VIDEO_EXTENSIONS = {
    ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm",
}

AUDIO_EXTENSIONS = {
    ".mp3", ".wav", ".flac", ".ogg", ".wma", ".m4a", ".aac",
}


class FileRuntimeAdapter:
    """File 입력을 Storage Separation Runtime으로 연결한다."""

    _STORAGE_SEPARATION_GROUP_CODE = "STORAGE_SEPARATION_TARGET"
    _RUNTIME_EXECUTION_CONTRACT_CODE = "RUNTIME_EXECUTION_PAYLOAD"
    _MONGODB_RUNTIME_OBJECT_DEFINITION_GROUP_CODE = (
        "MONGODB_RUNTIME_OBJECT_DEFINITION"
    )

    def __init__(
        self,
        *,
        database_factory: Callable[..., CommonDatabase] | None = None,
        identifier_coordinator_factory: (
            Callable[[CommonDatabase], IdentifierCoordinator] | None
        ) = None,
    ) -> None:
        self._database_factory = database_factory or CommonDatabase
        self._identifier_coordinator_factory = (
            identifier_coordinator_factory or IdentifierCoordinator
        )

    def execute(
        self,
        file_path: str,
        *,
        requested_by: str,
        client_ip: str,
    ) -> dict[str, Any]:
        """파일을 분석하고 Index, Document, Execution Link를 한 단위로 저장한다."""
        actor_id = normalize_required_text(requested_by, "requested_by")
        normalized_client_ip = normalize_required_text(client_ip, "client_ip")
        source_file = Path(file_path).expanduser().resolve()

        if not source_file.exists() or not source_file.is_file():
            raise FileNotFoundError(f"File not found: {source_file}")

        file_metadata = self._build_file_metadata(source_file)
        analyzer_result = self._run_analyzer(source_file, file_metadata)

        common_database = self._database_factory(database_role="COMMON")
        mariadb_database: CommonDatabase | None = None
        mongodb_database: CommonDatabase | None = None
        try:
            storage_contract = self._load_runtime_execution_contract(common_database)
            mariadb_database_role = normalize_required_text(
                storage_contract.get("source_database_role"),
                "source_database_role",
            ).upper()
            mongodb_database_role = normalize_required_text(
                storage_contract.get("mongodb_database_role"),
                "mongodb_database_role",
            ).upper()
            mariadb_database = self._database_factory(
                database_role=mariadb_database_role,
                connect_mongodb=False,
            )
            mongodb_database = self._database_factory(
                database_role=mongodb_database_role,
                connect_mariadb=False,
                connect_mongodb=True,
            )

            collection_name = normalize_required_text(
                storage_contract.get("mongodb_collection_name"),
                "mongodb_collection_name",
            )
            self._assert_collection_provisioned(mongodb_database, collection_name)
            index_table_name = self._normalize_sql_identifier(
                storage_contract.get("source_table_name"),
                "source_table_name",
            )

            identifier_coordinator = self._identifier_coordinator_factory(
                mariadb_database
            )
            index_object = self._load_active_object(
                mariadb_database,
                normalize_required_text(
                    storage_contract.get("source_object_code"),
                    "source_object_code",
                ),
            )
            source_object = self._load_active_object(
                mariadb_database,
                normalize_required_text(
                    file_metadata.get("object_code"),
                    "object_code",
                ),
            )
            mongodb_objects = self._load_mongodb_runtime_objects(
                common_database,
                mariadb_database,
            )
            identifier_contexts = self._prepare_registered_identifier_contexts(
                identifier_coordinator=identifier_coordinator,
                objects=(
                    index_object,
                    source_object,
                    mongodb_objects["document_detail"],
                ),
                requested_by=actor_id,
                client_ip=normalized_client_ip,
            )
            now = datetime.now(timezone.utc)

            acquired_identifier_preparations: list[dict[str, Any]] = []
            try:
                for _request, prepared in identifier_contexts:
                    identifier_coordinator.acquire(prepared)
                    acquired_identifier_preparations.append(prepared)
                with SpsDistributedTransaction(
                    mariadb_database,
                    mongodb_database,
                ) as transaction:
                    identifier_resolutions = {
                        request["object_code"]: identifier_coordinator.resolve(
                            request=request,
                            prepared=prepared,
                        )
                        for request, prepared in identifier_contexts
                    }
                    execution_history_id = identifier_resolutions[
                        index_object["object_code"]
                    ].identifier
                    source_identifier = identifier_resolutions[
                        source_object["object_code"]
                    ].identifier
                    document_detail_id = identifier_resolutions[
                        mongodb_objects["document_detail"]["object_code"]
                    ].identifier

                    self._insert_execution_history_index(
                        database=mariadb_database,
                        index_table_name=index_table_name,
                        execution_history_id=execution_history_id,
                        source_object=source_object,
                        source_identifier=source_identifier,
                        actor_id=actor_id,
                        client_ip=normalized_client_ip,
                    )
                    mongodb_document = self._build_mongodb_document(
                        storage_contract=storage_contract,
                        execution_history_id=execution_history_id,
                        source_object=source_object,
                        source_identifier=source_identifier,
                        mongodb_objects=mongodb_objects,
                        document_detail_id=document_detail_id,
                        file_metadata=file_metadata,
                        analyzer_result=analyzer_result,
                        actor_id=actor_id,
                        client_ip=normalized_client_ip,
                        created_dt=now,
                    )
                    inserted_id = transaction.insert_mongodb_document(
                        collection_name=collection_name,
                        document=mongodb_document,
                        compensation_filter={
                            mongodb_objects["document_detail"][
                                "target_identifier_field"
                            ]: document_detail_id,
                        },
                    )
                    self._insert_execution_link(
                        database=mariadb_database,
                        storage_contract=storage_contract,
                        execution_history_id=execution_history_id,
                        index_object=index_object,
                        mongodb_objects=mongodb_objects,
                        actor_id=actor_id,
                        client_ip=normalized_client_ip,
                    )
                    self._finalize_execution_history_index(
                        database=mariadb_database,
                        index_table_name=index_table_name,
                        execution_history_id=execution_history_id,
                        actor_id=actor_id,
                        client_ip=normalized_client_ip,
                    )

                return {
                    "status": "SUCCESS",
                    "file_metadata": file_metadata,
                    "analyzer_result": analyzer_result,
                    "mariadb_index_result": {
                        "execution_history_id": execution_history_id,
                        "object_id": source_object["object_id"],
                        "object_code": source_object["object_code"],
                        "generated_identifier": source_identifier,
                        "status": "SUCCESS",
                    },
                    "mongodb_document_result": {
                        "collection_name": collection_name,
                        "mongodb_document_details_id": document_detail_id,
                        "inserted_id": inserted_id,
                        "status": "SUCCESS",
                    },
                    "execution_link_result": {
                        "object_attempt_id": execution_history_id,
                        "object_id": index_object["object_id"],
                        "target_object_id": mongodb_objects["document_master"][
                            "object_id"
                        ],
                        "status": "SUCCESS",
                    },
                    "identifier_sequence_result": {
                        "prepared_object_codes": [
                            request["object_code"]
                            for request, _prepared in identifier_contexts
                        ],
                        "rule_resolutions": {
                            object_code: {
                                "rule_id": resolution.rule_id,
                                "rule_code": resolution.rule_code,
                                "rule_action_id": resolution.rule_action_id,
                                "rule_action_type_code": (
                                    resolution.rule_action_type_code
                                ),
                                "object_level": resolution.object_level,
                                "resolution_source": resolution.resolution_source,
                            }
                            for object_code, resolution in identifier_resolutions.items()
                        },
                        "status": "SUCCESS",
                    },
                    "mongodb_collection_generator_result": {
                        "collection_name": collection_name,
                        "created_yn": "N",
                        "status": "SUCCESS",
                    },
                }
            finally:
                for prepared in reversed(acquired_identifier_preparations):
                    identifier_coordinator.release(prepared)
        finally:
            if mariadb_database is not None:
                mariadb_database.close()
            if mongodb_database is not None:
                mongodb_database.close()
            common_database.close()

    def _load_runtime_execution_contract(
        self,
        common_database: CommonDatabase,
    ) -> dict[str, Any]:
        contracts = StorageSeparationContractRepository(
            common_database,
            group_code=self._STORAGE_SEPARATION_GROUP_CODE,
        ).load_active_contracts()
        matches = [
            contract
            for contract in contracts
            if contract.get("contract_code") == self._RUNTIME_EXECUTION_CONTRACT_CODE
        ]
        if len(matches) != 1:
            raise ValueError(
                "Runtime execution storage contract must resolve to exactly one row. "
                f"contract_code={self._RUNTIME_EXECUTION_CONTRACT_CODE}, "
                f"count={len(matches)}"
            )

        contract = matches[0]
        required_fields = (
            "source_database_role",
            "source_table_name",
            "source_object_code",
            "source_identifier_column_name",
            "mongodb_collection_name",
            "execution_link_required_yn",
            "execution_link_type_code",
        )
        for field_name in required_fields:
            normalize_required_text(contract.get(field_name), field_name)

        if str(contract["execution_link_required_yn"]).upper() != "Y":
            raise ValueError(
                "Runtime execution storage contract must require an execution link. "
                f"contract_code={contract['contract_code']}"
            )
        return contract

    def _load_mongodb_runtime_objects(
        self,
        common_database: CommonDatabase,
        runtime_database: CommonDatabase,
    ) -> dict[str, dict[str, Any]]:
        rows = common_database.fetch_all(
            """
            SELECT
                code,
                common_code_json
            FROM cm_common_code
            WHERE group_code = %s
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
            ORDER BY sort_no, code
            """,
            (self._MONGODB_RUNTIME_OBJECT_DEFINITION_GROUP_CODE,),
        )
        definitions = [
            self._parse_mongodb_runtime_definition(row)
            for row in rows
        ]
        if not definitions:
            raise ValueError(
                "MongoDB Runtime Object definitions are not registered. "
                f"group_code={self._MONGODB_RUNTIME_OBJECT_DEFINITION_GROUP_CODE}"
            )

        database_definition = self._select_single_definition(
            definitions,
            "MongoDB Database",
            lambda definition: str(
                definition.get("object_type_code")
            ).upper() == "DATABASE",
        )
        collection_definition = self._select_single_definition(
            definitions,
            "MongoDB Collection",
            lambda definition: (
                int(definition.get("object_level", -1)) == 2
                and str(definition.get("mongodb_internal_yn")).upper() != "Y"
            ),
        )
        document_master_definition = self._select_single_definition(
            definitions,
            "MongoDB Document Master",
            lambda definition: (
                int(definition.get("object_level", -1)) == 3
                and str(definition.get("mongodb_internal_yn")).upper() != "Y"
            ),
        )
        document_detail_definition = self._select_single_definition(
            definitions,
            "MongoDB Document Detail",
            lambda definition: str(
                definition.get("mongodb_internal_yn")
            ).upper() == "Y",
        )

        return {
            "database": self._load_active_object(
                runtime_database,
                database_definition["object_code"],
            ),
            "collection": self._load_active_object(
                runtime_database,
                collection_definition["object_code"],
            ),
            "document_master": self._load_active_object(
                runtime_database,
                document_master_definition["object_code"],
            ),
            "document_detail": self._load_active_object(
                runtime_database,
                document_detail_definition["object_code"],
            ),
        }

    @staticmethod
    def _parse_mongodb_runtime_definition(
        row: Mapping[str, Any],
    ) -> dict[str, Any]:
        try:
            definition = json.loads(
                normalize_required_text(
                    row.get("common_code_json"),
                    "common_code_json",
                )
            )
        except json.JSONDecodeError as error:
            raise ValueError(
                "MongoDB Runtime Object definition must contain valid JSON. "
                f"code={row.get('code')}"
            ) from error
        if not isinstance(definition, dict):
            raise ValueError(
                "MongoDB Runtime Object definition must be a JSON object. "
                f"code={row.get('code')}"
            )

        code = normalize_required_text(row.get("code"), "code")
        object_code = normalize_required_text(
            definition.get("object_code"),
            "object_code",
        )
        if code != object_code:
            raise ValueError(
                "MongoDB Runtime Object definition code mismatch. "
                f"code={code}, object_code={object_code}"
            )

        required_fields = (
            "object_level",
            "object_type_code",
            "target_identifier_field",
            "identifier_target_code",
            "mongodb_internal_yn",
        )
        for field_name in required_fields:
            normalize_required_text(definition.get(field_name), field_name)
        return definition

    @staticmethod
    def _select_single_definition(
        definitions: list[dict[str, Any]],
        definition_name: str,
        predicate: Callable[[dict[str, Any]], bool],
    ) -> dict[str, Any]:
        matches = [
            definition
            for definition in definitions
            if predicate(definition)
        ]
        if len(matches) != 1:
            raise ValueError(
                "MongoDB Runtime Object definition must resolve to exactly one "
                f"target. definition_name={definition_name}, count={len(matches)}"
            )
        return matches[0]

    @staticmethod
    def _load_active_object(
        database: CommonDatabase,
        object_code: str,
    ) -> dict[str, Any]:
        row = database.fetch_one(
            """
            SELECT
                object_id,
                object_code,
                object_name,
                object_description,
                business_code,
                domain_code,
                object_type_code,
                object_level,
                target_identifier_field,
                identifier_target_code,
                sequence_scope_code,
                sequence_length,
                status_code,
                active_yn
            FROM sp_object
            WHERE object_code = %s
              AND active_yn = 'Y'
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
            ORDER BY sort_no, object_code
            LIMIT 1
            """,
            (object_code,),
        )
        if not row:
            raise ValueError(
                "Active Repository Object metadata not found. "
                f"object_code={object_code}"
            )
        return dict(row)

    def _prepare_registered_identifier_contexts(
        self,
        *,
        identifier_coordinator: IdentifierCoordinator,
        objects: tuple[Mapping[str, Any], ...],
        requested_by: str,
        client_ip: str,
    ) -> tuple[tuple[dict[str, Any], dict[str, Any]], ...]:
        """Prepare Identifier allocation for active Objects without re-registering them."""
        contexts: list[tuple[dict[str, Any], dict[str, Any]]] = []
        prepared_object_codes: set[str] = set()

        for object_metadata in objects:
            object_code = normalize_required_text(
                object_metadata.get("object_code"),
                "object_code",
            )
            if object_code in prepared_object_codes:
                continue

            request, prepared = identifier_coordinator.prepare_registered_object(
                object_metadata=object_metadata,
                created_by=requested_by,
                updated_by=requested_by,
                client_ip=client_ip,
                program_id=self._program_id(),
            )
            contexts.append((request, prepared))
            prepared_object_codes.add(object_code)

        return tuple(contexts)

    @staticmethod
    def _assert_collection_provisioned(
        database: CommonDatabase,
        collection_name: str,
    ) -> None:
        if collection_name not in database.list_collection_names():
            raise RuntimeError(
                "MongoDB collection is not provisioned from the Storage Separation "
                f"contract. collection_name={collection_name}"
            )

    def _insert_execution_history_index(
        self,
        *,
        database: CommonDatabase,
        index_table_name: str,
        execution_history_id: str,
        source_object: Mapping[str, Any],
        source_identifier: str,
        actor_id: str,
        client_ip: str,
    ) -> None:
        affected_rows = database.execute(
            f"""
            INSERT INTO {index_table_name}
            (
                execution_history_id,
                trace_id,
                engine_code,
                object_code,
                object_id,
                generated_identifier,
                repository_status_code,
                mongodb_status_code,
                execution_status_code,
                history_status_code,
                created_by,
                updated_by,
                program_id,
                client_ip
            )
            VALUES
            (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s
            )
            """,
            (
                execution_history_id,
                execution_history_id,
                self._runtime_engine_code(),
                source_object["object_code"],
                source_object["object_id"],
                source_identifier,
                "READY",
                "READY",
                "RUNNING",
                "READY",
                actor_id,
                actor_id,
                self._program_id(),
                client_ip,
            ),
        )
        if affected_rows != 1:
            raise RuntimeError(
                "MariaDB execution-history index insert did not affect one row. "
                f"execution_history_id={execution_history_id}, "
                f"affected_rows={affected_rows}"
            )

    def _insert_execution_link(
        self,
        *,
        database: CommonDatabase,
        storage_contract: Mapping[str, Any],
        execution_history_id: str,
        index_object: Mapping[str, Any],
        mongodb_objects: Mapping[str, Mapping[str, Any]],
        actor_id: str,
        client_ip: str,
    ) -> None:
        document_master = mongodb_objects["document_master"]
        affected_rows = database.execute(
            """
            INSERT INTO sp_object_execution_link
            (
                object_attempt_id,
                object_id,
                target_object_id,
                execution_link_type_code,
                mongodb_database_id,
                mongodb_collection_id,
                mongodb_document_master_id,
                created_by,
                updated_by,
                client_ip,
                program_id
            )
            VALUES
            (
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s
            )
            """,
            (
                execution_history_id,
                index_object["object_id"],
                document_master["object_id"],
                storage_contract["execution_link_type_code"],
                mongodb_objects["database"]["object_id"],
                mongodb_objects["collection"]["object_id"],
                document_master["object_id"],
                actor_id,
                actor_id,
                client_ip,
                self._program_id(),
            ),
        )
        if affected_rows != 1:
            raise RuntimeError(
                "Execution-link insert did not affect one row. "
                f"object_attempt_id={execution_history_id}, "
                f"affected_rows={affected_rows}"
            )

    def _finalize_execution_history_index(
        self,
        *,
        database: CommonDatabase,
        index_table_name: str,
        execution_history_id: str,
        actor_id: str,
        client_ip: str,
    ) -> None:
        affected_rows = database.execute(
            f"""
            UPDATE {index_table_name}
            SET
                repository_status_code = %s,
                mongodb_status_code = %s,
                execution_status_code = %s,
                history_status_code = %s,
                updated_by = %s,
                updated_dt = CURRENT_TIMESTAMP,
                program_id = %s,
                client_ip = %s
            WHERE execution_history_id = %s
              AND deleted_dt IS NULL
            """,
            (
                "SUCCESS",
                "SUCCESS",
                "SUCCESS",
                "SAVED",
                actor_id,
                self._program_id(),
                client_ip,
                execution_history_id,
            ),
        )
        if affected_rows != 1:
            raise RuntimeError(
                "MariaDB execution-history index finalize did not affect one row. "
                f"execution_history_id={execution_history_id}, "
                f"affected_rows={affected_rows}"
            )

    def _build_mongodb_document(
        self,
        *,
        storage_contract: Mapping[str, Any],
        execution_history_id: str,
        source_object: Mapping[str, Any],
        source_identifier: str,
        mongodb_objects: Mapping[str, Mapping[str, Any]],
        document_detail_id: str,
        file_metadata: Mapping[str, Any],
        analyzer_result: Mapping[str, Any],
        actor_id: str,
        client_ip: str,
        created_dt: datetime,
    ) -> dict[str, Any]:
        document_detail_field = normalize_required_text(
            mongodb_objects["document_detail"].get(
                "target_identifier_field"
            ),
            "mongodb_document_detail_target_identifier_field",
        )
        source_identifier_field = normalize_required_text(
            storage_contract.get("source_identifier_column_name"),
            "source_identifier_column_name",
        )
        return {
            source_identifier_field: execution_history_id,
            "source_object_id": source_object["object_id"],
            "source_object_code": source_object["object_code"],
            "source_identifier": source_identifier,
            "storage_contract_code": storage_contract["contract_code"],
            "mongodb_database_id": mongodb_objects["database"]["object_id"],
            "mongodb_collection_id": mongodb_objects["collection"]["object_id"],
            "mongodb_document_master_id": mongodb_objects["document_master"][
                "object_id"
            ],
            document_detail_field: document_detail_id,
            "content": str(analyzer_result.get("text") or ""),
            "file_metadata": dict(file_metadata),
            "analyzer_result": dict(analyzer_result),
            "created_by": actor_id,
            "client_ip": client_ip,
            "program_id": self._program_id(),
            "created_dt": created_dt.isoformat(timespec="seconds"),
        }

    @staticmethod
    def _runtime_engine_code() -> str:
        runtime_name = ObjectRuntimeEngine.__name__.removesuffix("Engine")
        return re.sub(r"(?<!^)(?=[A-Z])", "_", runtime_name).upper()

    @staticmethod
    def _normalize_sql_identifier(value: Any, field_name: str) -> str:
        identifier = normalize_required_text(value, field_name)
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", identifier):
            raise ValueError(
                "Repository storage contract SQL identifier is invalid. "
                f"field_name={field_name}, value={identifier}"
            )
        return identifier

    def _program_id(self) -> str:
        return f"{self.__class__.__module__}.{self.__class__.__name__}"

    @staticmethod
    def _build_file_metadata(source_file: Path) -> dict[str, Any]:
        extension = source_file.suffix.lower()

        if extension in DOCUMENT_EXTENSIONS:
            object_code = "DOCUMENT"
            analyzer_module = "document_analyzer"
            analyzer_method = "extract_document_text"
        elif extension in IMAGE_EXTENSIONS:
            object_code = "IMAGE"
            analyzer_module = "image_analyzer"
            analyzer_method = "extract_text_from_image"
        elif extension in VIDEO_EXTENSIONS:
            object_code = "VIDEO"
            analyzer_module = "video_analyzer"
            analyzer_method = "extract_text_from_video"
        elif extension in AUDIO_EXTENSIONS:
            object_code = "AUDIO"
            analyzer_module = "audio_analyzer"
            analyzer_method = "transcribe_audio_to_text"
        else:
            object_code = "FILE"
            analyzer_module = None
            analyzer_method = None

        return {
            "file_path": str(source_file),
            "file_name": source_file.name,
            "file_stem": source_file.stem,
            "extension": extension,
            "file_size": source_file.stat().st_size,
            "object_code": object_code,
            "analyzer_module": analyzer_module,
            "analyzer_method": analyzer_method,
        }

    @staticmethod
    def _run_analyzer(
        source_file: Path,
        file_metadata: Mapping[str, Any],
    ) -> dict[str, Any]:
        analyzer_module = file_metadata.get("analyzer_module")
        analyzer_method = file_metadata.get("analyzer_method")

        if not analyzer_module or not analyzer_method:
            return {
                "status": "SKIPPED",
                "reason": "Analyzer not defined",
                "text": "",
            }

        module = importlib.import_module(str(analyzer_module))
        method = getattr(module, str(analyzer_method))
        text = method(source_file)

        return {
            "status": "SUCCESS",
            "analyzer_module": analyzer_module,
            "analyzer_method": analyzer_method,
            "text": text or "",
        }


if __name__ == "__main__":
    file_path = input("File Path : ").strip().strip('"')
    requested_by = input("Requested By : ").strip()
    client_ip = input("Client IP : ").strip()
    result = FileRuntimeAdapter().execute(
        file_path,
        requested_by=requested_by,
        client_ip=client_ip,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
