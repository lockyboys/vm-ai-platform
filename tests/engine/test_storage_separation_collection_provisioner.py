"""Storage separation collection provisioning unit tests."""

from __future__ import annotations

from typing import Any

from engine.storage.storage_separation_collection_provisioner import (
    StorageSeparationCollectionProvisioner,
    StorageSeparationContractRepository,
)


class FakeCollection:
    def __init__(self) -> None:
        self.indexes: list[dict[str, Any]] = []

    def create_index(
        self,
        keys: list[tuple[str, int]],
        *,
        name: str,
        unique: bool = False,
    ) -> str:
        self.indexes.append(
            {
                "keys": keys,
                "name": name,
                "unique": unique,
            }
        )
        return name


class FakeMongoDatabase:
    def __init__(self, database_name: str, collection_by_name: dict[str, FakeCollection]) -> None:
        self.name = database_name
        self.collection_by_name = collection_by_name

    def create_collection(self, collection_name: str) -> None:
        self.collection_by_name.setdefault(collection_name, FakeCollection())


class FakeCommonDatabase:
    def __init__(self, role: str, contracts: list[dict[str, Any]] | None = None) -> None:
        self.role = role
        self.contracts = contracts or []
        self.collection_by_name: dict[str, FakeCollection] = {}
        self.mongodb_database = FakeMongoDatabase(
            f"{role.lower()}_mongodb",
            self.collection_by_name,
        )

    def fetch_all(self, sql: str, params: tuple[str]) -> list[dict[str, Any]]:
        assert params == ("STORAGE_SEPARATION_TARGET",)
        return self.contracts

    def get_mongodb_database(self) -> FakeMongoDatabase:
        return self.mongodb_database

    def list_collection_names(self) -> list[str]:
        return sorted(self.collection_by_name)

    def get_collection(self, collection_name: str) -> FakeCollection:
        return self.collection_by_name.setdefault(collection_name, FakeCollection())

    def close(self) -> None:
        return None


def test_contract_repository_parses_metadata_driven_storage_contract() -> None:
    database = FakeCommonDatabase(
        "COMMON",
        contracts=[
            {
                "code": "HEALTH_REPORT_CONTENT",
                "code_name": "Health Report Content",
                "common_code_json": (
                    '{"source_database_role":"COMMON",'
                    '"source_table_name":"health_report",'
                    '"source_identifier_column_name":"health_report_id",'
                    '"mongodb_collection_name":"health_report_document"}'
                ),
            }
        ],
    )

    contracts = StorageSeparationContractRepository(
        database,
        group_code="STORAGE_SEPARATION_TARGET",
    ).load_active_contracts()

    assert contracts == [
        {
            "contract_code": "HEALTH_REPORT_CONTENT",
            "contract_name": "Health Report Content",
            "source_database_role": "COMMON",
            "source_table_name": "health_report",
            "source_identifier_column_name": "health_report_id",
            "mongodb_collection_name": "health_report_document",
        }
    ]


def test_collection_provisioner_creates_contract_collections_and_indexes() -> None:
    database_by_role: dict[str, FakeCommonDatabase] = {}

    def database_factory(role: str) -> FakeCommonDatabase:
        return database_by_role.setdefault(role, FakeCommonDatabase(role))

    results = StorageSeparationCollectionProvisioner(database_factory).provision(
        [
            {
                "contract_code": "RUNTIME_EXECUTION_PAYLOAD",
                "source_database_role": "STORY",
                "source_identifier_column_name": "execution_history_id",
                "mongodb_collection_name": "runtime_execution_payload",
            },
            {
                "contract_code": "HEALTH_REPORT_CONTENT",
                "source_database_role": "COMMON",
                "source_identifier_column_name": "health_report_id",
                "mongodb_collection_name": "health_report_document",
            },
        ]
    )

    assert [result["collection_name"] for result in results] == [
        "runtime_execution_payload",
        "health_report_document",
    ]
    assert database_by_role["STORY"].collection_by_name[
        "runtime_execution_payload"
    ].indexes == [
        {
            "keys": [("execution_history_id", 1)],
            "name": "uq_execution_history_id",
            "unique": True,
        },
        {
            "keys": [("created_dt", -1)],
            "name": "ix_created_dt",
            "unique": False,
        },
    ]
