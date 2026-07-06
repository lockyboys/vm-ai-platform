from typing import Any, Callable, Dict, List, Optional

from pymongo import MongoClient
from urllib.parse import quote_plus

class SpsDistributedTransaction:
    """
    SPS Distributed Transaction v0.1

    목적:
    - MariaDB Transaction과 MongoDB 보상 작업을 하나의 SPS 실행 단위로 관리한다.
    - 진짜 2PC가 아니라 Saga / Compensation 방식이다.

    원칙:
    - MariaDB는 실제 Transaction으로 보호한다.
    - MongoDB 작업은 성공 후 보상 작업을 등록한다.
    - 중간 실패 시 MongoDB 보상 작업을 역순으로 실행한다.
    - MariaDB는 rollback 한다.
    """

    def __init__(self, mariadb_connection, mongodb_client: MongoClient):
        self.mariadb_connection = mariadb_connection
        self.mongodb_client = mongodb_client
        self.compensation_actions: List[Callable[[], None]] = []
        self.started = False
        self.completed = False

    def __enter__(self):
        self.begin()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.commit()
            return False

        self.rollback()
        return False

    def begin(self) -> None:
        if self.started:
            raise RuntimeError("Transaction already started.")

        self.mariadb_connection.begin()
        self.started = True
        print("MariaDB transaction started")

    def commit(self) -> None:
        if not self.started:
            raise RuntimeError("Transaction has not started.")

        if self.completed:
            raise RuntimeError("Transaction already completed.")

        self.mariadb_connection.commit()
        self.completed = True
        self.compensation_actions.clear()
        print("MariaDB commit completed")

    def rollback(self) -> None:
        if not self.started:
            return

        if self.completed:
            return

        self._run_compensations()
        self.mariadb_connection.rollback()
        self.completed = True
        print("MariaDB rollback completed")

    def register_compensation(self, action: Callable[[], None]) -> None:
        self.compensation_actions.append(action)

    def insert_mongodb_document(
        self,
        database_name: str,
        collection_name: str,
        document: Dict[str, Any],
        compensation_filter: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        MongoDB document insert + compensation 등록.

        실패 시 compensation_filter 기준으로 삭제한다.
        """

        collection = self.mongodb_client[database_name][collection_name]
        result = collection.insert_one(document)

        print("MongoDB document inserted")

        if compensation_filter is None:
            compensation_filter = {"_id": result.inserted_id}

        def compensation():
            collection.delete_one(compensation_filter)
            print("MongoDB compensation completed")

        self.register_compensation(compensation)

        return result.inserted_id

    def _run_compensations(self) -> None:
        for action in reversed(self.compensation_actions):
            try:
                action()
            except Exception as exc:
                print(f"Compensation failed: {exc}")