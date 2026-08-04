"""MariaDB와 MongoDB를 함께 저장하는 SPS 보상 트랜잭션."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from common.common_function import normalize_required_text
from common.database import CommonDatabase


class SpsDistributedTransaction:
    """MariaDB transaction과 MongoDB 보상 작업을 한 실행 단위로 관리한다.

    MariaDB와 MongoDB는 하나의 물리 2PC transaction을 공유하지 않는다.
    따라서 MariaDB 작업은 transaction으로 보호하고 MongoDB 저장 직후
    역순 보상 작업을 등록하여, 업무 실패 시 두 저장소의 결과를 함께 제거한다.
    """

    def __init__(
        self,
        mariadb_database: CommonDatabase,
        mongodb_database: CommonDatabase | None = None,
    ) -> None:
        """MariaDB 트랜잭션 연결과 MongoDB 저장 연결을 분리해 받는다.

        mongodb_database를 생략한 기존 호출은 같은 연결을 사용한다.
        """
        self.mariadb_database = mariadb_database
        self.mongodb_database = mongodb_database or mariadb_database
        self.compensation_actions: list[Callable[[], None]] = []
        self.started = False
        self.completed = False

    def __enter__(self) -> "SpsDistributedTransaction":
        self.begin()
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> bool:
        if exc_type is not None:
            self.rollback()
            return False

        try:
            self.commit()
        except Exception:
            self.rollback()
            raise
        return False

    def begin(self) -> None:
        """MariaDB transaction을 시작하고 MongoDB 연결을 사전 검증한다."""
        if self.started:
            raise RuntimeError("Distributed transaction already started.")

        self.mariadb_database.ping_mariadb()
        self.mongodb_database.ping_mongodb()
        self.mariadb_database.begin()
        self.started = True

    def commit(self) -> None:
        """MariaDB를 commit하고 보상 작업을 해제한다."""
        if not self.started:
            raise RuntimeError("Distributed transaction has not started.")
        if self.completed:
            raise RuntimeError("Distributed transaction already completed.")

        self.mariadb_database.commit()
        self.completed = True
        self.compensation_actions.clear()

    def rollback(self) -> None:
        """MariaDB rollback과 MongoDB 보상 작업을 함께 수행한다."""
        if not self.started or self.completed:
            return

        compensation_error: Exception | None = None
        try:
            self.mariadb_database.rollback()
        finally:
            for action in reversed(self.compensation_actions):
                try:
                    action()
                except Exception as error:
                    compensation_error = error
            self.compensation_actions.clear()
            self.completed = True

        if compensation_error is not None:
            raise RuntimeError(
                "MariaDB rollback completed but MongoDB compensation failed."
            ) from compensation_error

    def register_compensation(self, action: Callable[[], None]) -> None:
        """실행 완료된 MongoDB 변경을 되돌릴 보상 작업을 등록한다."""
        if not self.started or self.completed:
            raise RuntimeError("Cannot register compensation outside an active transaction.")
        self.compensation_actions.append(action)

    def insert_mongodb_document(
        self,
        *,
        collection_name: str,
        document: Mapping[str, Any],
        compensation_filter: Mapping[str, Any] | None = None,
    ) -> str:
        """MongoDB document를 저장하고 실패 시 삭제할 보상을 등록한다."""
        if not self.started or self.completed:
            raise RuntimeError("MongoDB insert requires an active transaction.")

        resolved_collection_name = normalize_required_text(
            collection_name,
            "collection_name",
        )
        result = self.mongodb_database.insert_one(resolved_collection_name, document)
        resolved_filter = dict(compensation_filter or {"_id": result.inserted_id})

        def compensation() -> None:
            self.mongodb_database.delete_one(resolved_collection_name, resolved_filter)

        self.register_compensation(compensation)
        return str(result.inserted_id)
