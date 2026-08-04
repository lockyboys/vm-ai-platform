"""SPS MariaDB-MongoDB 보상 트랜잭션 단위 테스트."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from core.transaction.sps_distributed_transaction import SpsDistributedTransaction


class FakeCommonDatabase:
    """CommonDatabase 계약을 검증하는 in-memory test double."""

    def __init__(self, *, fail_commit: bool = False) -> None:
        self.fail_commit = fail_commit
        self.begin_count = 0
        self.commit_count = 0
        self.rollback_count = 0
        self.documents: list[dict[str, object]] = []
        self.deleted_filters: list[dict[str, object]] = []

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


def test_distributed_transaction_commits_mariadb_and_preserves_mongodb_document() -> None:
    database = FakeCommonDatabase()

    with SpsDistributedTransaction(database) as transaction:
        document_id = transaction.insert_mongodb_document(
            collection_name="runtime_execution_payload",
            document={"execution_history_id": "execution-1"},
        )

    assert document_id == "document-1"
    assert database.begin_count == 1
    assert database.commit_count == 1
    assert database.rollback_count == 0
    assert len(database.documents) == 1
    assert database.deleted_filters == []


def test_distributed_transaction_rolls_back_mariadb_and_compensates_mongodb_document() -> None:
    database = FakeCommonDatabase()

    with pytest.raises(RuntimeError, match="forced failure"):
        with SpsDistributedTransaction(database) as transaction:
            transaction.insert_mongodb_document(
                collection_name="runtime_execution_payload",
                document={"execution_history_id": "execution-2"},
            )
            raise RuntimeError("forced failure")

    assert database.begin_count == 1
    assert database.commit_count == 0
    assert database.rollback_count == 1
    assert database.documents == []
    assert database.deleted_filters == [{"_id": "document-1"}]


def test_distributed_transaction_compensates_mongodb_when_mariadb_commit_fails() -> None:
    database = FakeCommonDatabase(fail_commit=True)

    with pytest.raises(RuntimeError, match="MariaDB commit failed"):
        with SpsDistributedTransaction(database) as transaction:
            transaction.insert_mongodb_document(
                collection_name="runtime_execution_payload",
                document={"execution_history_id": "execution-3"},
            )

    assert database.begin_count == 1
    assert database.commit_count == 1
    assert database.rollback_count == 1
    assert database.documents == []
    assert database.deleted_filters == [{"_id": "document-1"}]
