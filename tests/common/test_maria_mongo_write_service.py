"""MariaMongoWriteService 공통 입력·보상 처리 단위 테스트."""

from __future__ import annotations

import runpy
from types import SimpleNamespace

import common.database as database_module
database_module = SimpleNamespace(**runpy.run_path(database_module.__file__))
import pytest


class FakeDatabase:
    """CommonDatabase 쓰기 계약을 재현하는 메모리 기반 테스트 대역."""

    def __init__(self, *, fail_commit: bool = False) -> None:
        self.fail_commit = fail_commit
        self.begin_count = 0
        self.commit_count = 0
        self.rollback_count = 0
        self.execute_calls: list[tuple[str, tuple[object, ...]]] = []
        self.documents: list[dict[str, object]] = []
        self.deleted_filters: list[dict[str, object]] = []
        self.close_count = 0

    def ping_mariadb(self) -> bool:
        return True

    def ping_mongodb(self) -> bool:
        return True

    def begin(self) -> None:
        self.begin_count += 1

    def commit(self) -> None:
        self.commit_count += 1
        if self.fail_commit:
            raise RuntimeError("MariaDB commit failed")

    def rollback(self) -> None:
        self.rollback_count += 1

    def execute(self, sql_text: str, parameters: tuple[object, ...]) -> int:
        self.execute_calls.append((sql_text, parameters))
        return 1

    def insert_one(
        self,
        collection_name: str,
        document: dict[str, object],
    ) -> SimpleNamespace:
        stored_document = {"_id": f"document-{len(self.documents) + 1}", **document}
        self.documents.append(stored_document)
        return SimpleNamespace(inserted_id=stored_document["_id"])

    def delete_one(
        self,
        collection_name: str,
        filter_document: dict[str, object],
    ) -> None:
        self.deleted_filters.append(filter_document)
        self.documents = [
            document
            for document in self.documents
            if not all(document.get(key) == value for key, value in filter_document.items())
        ]

    def close(self) -> None:
        self.close_count += 1


def test_writer_commits_mariadb_and_preserves_mongodb_document() -> None:
    mariadb_database = FakeDatabase()
    mongodb_database = FakeDatabase()

    with database_module.MariaMongoWriteService(
        mariadb_database,
        mongodb_database,
    ) as writer:
        assert writer.execute_verified_mariadb(
            "INSERT INTO registered_table (source_id) VALUES (%s)",
            ("source-1",),
            expected_affected_rows=1,
        ) == 1
        document_id = writer.insert_mongodb_document(
            collection_name="runtime_execution_payload",
            document={"_sps": {"execution_history_id": "execution-1"}},
        )

    assert document_id == "document-1"
    assert mariadb_database.begin_count == 1
    assert mariadb_database.commit_count == 1
    assert mariadb_database.rollback_count == 0
    assert mongodb_database.documents == [
        {
            "_id": "document-1",
            "_sps": {"execution_history_id": "execution-1"},
        }
    ]
    assert mongodb_database.deleted_filters == []


def test_writer_compensates_mongodb_when_mariadb_commit_fails() -> None:
    mariadb_database = FakeDatabase(fail_commit=True)
    mongodb_database = FakeDatabase()

    with pytest.raises(RuntimeError, match="MariaDB commit failed"):
        with database_module.MariaMongoWriteService(
            mariadb_database,
            mongodb_database,
        ) as writer:
            writer.insert_mongodb_document(
                collection_name="runtime_execution_payload",
                document={"_sps": {"execution_history_id": "execution-2"}},
            )

    assert mariadb_database.begin_count == 1
    assert mariadb_database.commit_count == 1
    assert mariadb_database.rollback_count == 1
    assert mongodb_database.documents == []
    assert mongodb_database.deleted_filters == [{"_id": "document-1"}]


def test_writer_rejects_writes_outside_active_context() -> None:
    writer = database_module.MariaMongoWriteService(FakeDatabase(), FakeDatabase())

    with pytest.raises(RuntimeError, match="active MariaMongoWriteService context"):
        writer.execute_verified_mariadb("UPDATE registered_table SET active_yn = %s", ("Y",))

    with pytest.raises(RuntimeError, match="active MariaMongoWriteService context"):
        writer.insert_mongodb_document(
            collection_name="runtime_execution_payload",
            document={"_sps": {"execution_history_id": "execution-3"}},
        )
