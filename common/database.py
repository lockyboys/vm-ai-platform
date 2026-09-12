# =============================================================================
# File Name   : common/database.py
# Purpose     : SPDF Common Database Framework
# Author      : PARK HEAKYU
# Created     : 2026-06-27
# Updated     : 2026-07-26
# Description : MariaDB와 MongoDB 연결, Transaction, CRUD를 공통으로 관리한다.
# =============================================================================
# CHANGE HISTORY
# =============================================================================
# 20260627 | SYSTEM | CommonDatabase를 생성했고, MariaDB 연결과 조회 기능을 지원했음
# 20260707 | SYSTEM | database_role 기반 연결과 Transaction 기능을 추가했음
# 20260726 | OpenAI | MongoDB 연결과 CRUD를 통합해 SPDF Database Framework로 승격했음
# 20260830 | CODEX | MariaMongoWriteService commit 실패 시 MongoDB 보상 rollback을 보장했음
# 20260830 | OpenAI | STORY 역할이 SPS_REPOSITORY_* 공통 연결정보를 후순위로 재사용하도록 보완했음
# =============================================================================

from __future__ import annotations

import os
from urllib.parse import quote_plus
from typing import Any, Iterable, Mapping, Sequence

import pymysql
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database as MongoDatabase
from common.common_function import normalize_required_text
from core.database.database_manager import DatabaseManager
from pymongo.results import (
    DeleteResult,
    InsertManyResult,
    InsertOneResult,
    UpdateResult,
)


class CommonDatabase:
    """MariaDB와 MongoDB의 공통 접근 지점을 제공한다."""

    _ROLE_PREFIX_MAP = {
        "COMMON": "COMMON",
        "STORY": "STORY_PLATFORM",
        "STORY_PLATFORM": "STORY_PLATFORM",
        "AI": "AI_PLATFORM",
        "AI_PLATFORM": "AI_PLATFORM",
        "HEALTH": "HEALTH_COMPANION",
        "HEALTH_COMPANION": "HEALTH_COMPANION",
        "BUSAN": "BUSAN_CARE",
        "BUSAN_CARE": "BUSAN_CARE",
        "KDT": "KDT_CARE",
        "KDT_CARE": "KDT_CARE",
    }

    def __init__(
        self,
        database_role: str = "STORY_PLATFORM",
        *,
        connect_mariadb: bool = True,
        connect_mongodb: bool = False,
    ) -> None:
        load_dotenv()

        self.database_role = self._normalize_database_role(database_role)
        self._environment_prefix = self._ROLE_PREFIX_MAP[self.database_role]

        self.config = self._load_mariadb_config() if connect_mariadb else {}
        self.database_name = self.config.get("database")
        self.connection = None

        self._mongodb_config: dict[str, Any] | None = None
        self._mongodb_client: MongoClient | None = None
        self._mongodb_database: MongoDatabase | None = None

        if connect_mariadb:
            self.connect_mariadb()
        if connect_mongodb:
            self.connect_mongodb()

    # -------------------------------------------------------------------------
    # Story : database_role을 공식 Role 이름으로 정규화한다.
    # -------------------------------------------------------------------------
    @classmethod
    def _normalize_database_role(cls, database_role: str) -> str:
        normalized_role = database_role.strip().upper()
        if normalized_role not in cls._ROLE_PREFIX_MAP:
            raise ValueError(f"Unknown database_role: {database_role}")
        return normalized_role

    # -------------------------------------------------------------------------
    # Story : MariaDB 환경설정을 조회하고 필수값을 검증한다.
    # -------------------------------------------------------------------------
    def _load_mariadb_config(self) -> dict[str, Any]:
        prefix = f"{self._environment_prefix}_MARIADB"
        repository_fallback_yn = self.database_role in {
            "STORY",
            "STORY_PLATFORM",
        }

        def resolve(role_key: str, repository_key: str) -> str | None:
            role_value = os.getenv(f"{prefix}_{role_key}")
            if role_value or not repository_fallback_yn:
                return role_value
            return os.getenv(repository_key)

        def resolve_database() -> str | None:
            role_database = os.getenv(f"{prefix}_DATABASE")
            if role_database or not repository_fallback_yn:
                return role_database
            return DatabaseManager().get_database_name(self.database_role)

        config = {
            "host": resolve("HOST", "SPS_REPOSITORY_HOST") or "127.0.0.1",
            "port": resolve("PORT", "SPS_REPOSITORY_PORT") or "3306",
            "user": resolve("USER", "SPS_REPOSITORY_USER"),
            "password": resolve("PASSWORD", "SPS_REPOSITORY_PASSWORD"),
            "database": resolve_database(),
        }
        self._validate_required_config(config, f"MariaDB/{self.database_role}")
        return config

    # -------------------------------------------------------------------------
    # Story : MongoDB 환경설정을 Role별 설정 우선순위로 조회한다.
    # -------------------------------------------------------------------------
    def _load_mongodb_config(self) -> dict[str, Any]:
        if self._mongodb_config is not None:
            return self._mongodb_config

        prefix = f"{self._environment_prefix}_MONGODB"

        def resolve(config_key: str) -> str | None:
            return os.getenv(f"{prefix}_{config_key}") or os.getenv(
                f"MONGODB_{config_key}"
            )

        mongodb_uri = resolve("URI")
        if not mongodb_uri:
            host = resolve("HOST")
            port = resolve("PORT") or "27017"
            user = resolve("USER")
            password = resolve("PASSWORD")
            if host and user and password:
                mongodb_uri = (
                    f"mongodb://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/"
                )

        config = {
            "uri": mongodb_uri,
            "database": (
                os.getenv(f"{prefix}_DATABASE")
                or os.getenv("MONGODB_DATABASE")
            ),
            "server_selection_timeout_ms": int(
                os.getenv(
                    f"{prefix}_SERVER_SELECTION_TIMEOUT_MS",
                    os.getenv("MONGODB_SERVER_SELECTION_TIMEOUT_MS", "5000"),
                )
            ),
        }
        self._validate_required_config(
            {"uri": config["uri"], "database": config["database"]},
            f"MongoDB/{self.database_role}",
        )
        self._mongodb_config = config
        return config

    @staticmethod
    def _validate_required_config(config: Mapping[str, Any], config_name: str) -> None:
        missing = [key for key, value in config.items() if value is None or value == ""]
        if missing:
            raise ValueError(f"Missing database config for {config_name}: {missing}")

    # -------------------------------------------------------------------------
    # Story : MariaDB 연결을 생성하거나 기존 연결을 반환한다.
    # -------------------------------------------------------------------------
    def connect_mariadb(self):
        if self.connection is not None and getattr(self.connection, "open", False):
            return self.connection

        self.connection = pymysql.connect(
            host=self.config["host"],
            port=int(self.config["port"]),
            user=self.config["user"],
            password=self.config["password"],
            database=self.config["database"],
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
        )
        return self.connection

    # -------------------------------------------------------------------------
    # Story : MongoDB Client와 Database를 지연 생성한다.
    # -------------------------------------------------------------------------
    def connect_mongodb(self) -> MongoDatabase:
        if self._mongodb_client is not None and self._mongodb_database is not None:
            return self._mongodb_database

        config = self._load_mongodb_config()
        self._mongodb_client = MongoClient(
            config["uri"],
            serverSelectionTimeoutMS=config["server_selection_timeout_ms"],
        )
        self._mongodb_database = self._mongodb_client[config["database"]]
        return self._mongodb_database

    # -------------------------------------------------------------------------
    # MariaDB Transaction
    # -------------------------------------------------------------------------
    def begin(self) -> None:
        self.connect_mariadb().begin()

    def commit(self) -> None:
        self.connect_mariadb().commit()

    def rollback(self) -> None:
        self.connect_mariadb().rollback()

    # -------------------------------------------------------------------------
    # MariaDB Query
    # -------------------------------------------------------------------------
    def fetch_all(self, sql: str, params=None) -> list[dict[str, Any]]:
        with self.connect_mariadb().cursor() as cursor:
            cursor.execute(sql, params)
            return list(cursor.fetchall())

    def fetch_one(self, sql: str, params=None) -> dict[str, Any] | None:
        with self.connect_mariadb().cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()

    def execute(self, sql: str, params=None) -> int:
        with self.connect_mariadb().cursor() as cursor:
            return cursor.execute(sql, params)

    def execute_many(self, sql: str, params: Sequence[Any]) -> int:
        with self.connect_mariadb().cursor() as cursor:
            return cursor.executemany(sql, params)

    def last_insert_id(self) -> int:
        row = self.fetch_one("SELECT LAST_INSERT_ID() AS last_insert_id")
        if not row:
            raise RuntimeError("LAST_INSERT_ID() did not return a row.")
        return int(row["last_insert_id"])

    # -------------------------------------------------------------------------
    # MongoDB Access
    # -------------------------------------------------------------------------
    def get_mongodb_database(self) -> MongoDatabase:
        return self.connect_mongodb()

    def get_collection(self, collection_name: str) -> Collection:
        normalized_name = self._validate_collection_name(collection_name)
        return self.connect_mongodb()[normalized_name]

    @staticmethod
    def _validate_collection_name(collection_name: str) -> str:
        normalized_name = collection_name.strip()
        if not normalized_name:
            raise ValueError("collection_name is required.")
        if "\x00" in normalized_name or normalized_name.startswith("system."):
            raise ValueError("collection_name is not allowed.")
        return normalized_name

    # -------------------------------------------------------------------------
    # MongoDB CRUD
    # -------------------------------------------------------------------------
    def list_collection_names(self) -> list[str]:
        return sorted(self.connect_mongodb().list_collection_names())

    def insert_one(
        self,
        collection_name: str,
        document: Mapping[str, Any],
    ) -> InsertOneResult:
        return self.get_collection(collection_name).insert_one(dict(document))

    def insert_many(
        self,
        collection_name: str,
        documents: Iterable[Mapping[str, Any]],
        *,
        ordered: bool = True,
    ) -> InsertManyResult:
        normalized_documents = [dict(document) for document in documents]
        if not normalized_documents:
            raise ValueError("documents must contain at least one document.")
        return self.get_collection(collection_name).insert_many(
            normalized_documents,
            ordered=ordered,
        )

    def find_one(
        self,
        collection_name: str,
        filter_document: Mapping[str, Any] | None = None,
        projection: Mapping[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        return self.get_collection(collection_name).find_one(
            dict(filter_document or {}),
            projection,
        )

    def find(
        self,
        collection_name: str,
        filter_document: Mapping[str, Any] | None = None,
        projection: Mapping[str, Any] | None = None,
        *,
        limit: int | None = None,
        sort: Sequence[tuple[str, int]] | None = None,
    ) -> list[dict[str, Any]]:
        cursor = self.get_collection(collection_name).find(
            dict(filter_document or {}),
            projection,
        )
        if sort:
            cursor = cursor.sort(list(sort))
        if limit is not None:
            if limit <= 0:
                raise ValueError("limit must be positive.")
            cursor = cursor.limit(limit)
        return list(cursor)

    def update_one(
        self,
        collection_name: str,
        filter_document: Mapping[str, Any],
        update_document: Mapping[str, Any],
        *,
        upsert: bool = False,
    ) -> UpdateResult:
        return self.get_collection(collection_name).update_one(
            dict(filter_document),
            dict(update_document),
            upsert=upsert,
        )

    def delete_one(
        self,
        collection_name: str,
        filter_document: Mapping[str, Any],
    ) -> DeleteResult:
        return self.get_collection(collection_name).delete_one(dict(filter_document))

    def aggregate(
        self,
        collection_name: str,
        pipeline: Iterable[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        normalized_pipeline = [dict(stage) for stage in pipeline]
        return list(self.get_collection(collection_name).aggregate(normalized_pipeline))

    def count_documents(
        self,
        collection_name: str,
        filter_document: Mapping[str, Any] | None = None,
    ) -> int:
        return self.get_collection(collection_name).count_documents(
            dict(filter_document or {})
        )

    # -------------------------------------------------------------------------
    # Health Check
    # -------------------------------------------------------------------------
    def ping_mariadb(self) -> bool:
        self.connect_mariadb().ping(reconnect=True)
        return True

    def ping_mongodb(self) -> bool:
        self.connect_mongodb().command("ping")
        return True

    # -------------------------------------------------------------------------
    # Story : 모든 Database 연결을 종료한다.
    # -------------------------------------------------------------------------
    def close_mariadb(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def close_mongodb(self) -> None:
        if self._mongodb_client is not None:
            self._mongodb_client.close()
            self._mongodb_client = None
            self._mongodb_database = None

    def close(self) -> None:
        self.close_mariadb()
        self.close_mongodb()

    def __enter__(self) -> "CommonDatabase":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if exc_type is not None and self.connection is not None:
            self.rollback()
        self.close()


class MariaMongoWriteService:
    """Coordinate MariaDB with compensating MongoDB deletes."""

    def __init__(self, mariadb_database: CommonDatabase, mongodb_database: CommonDatabase) -> None:
        self.mariadb_database = mariadb_database
        self.mongodb_database = mongodb_database
        self._active = False
        self._inserted_mongodb_documents: list[tuple[str, dict[str, Any]]] = []

    def __enter__(self) -> "MariaMongoWriteService":
        self.mariadb_database.begin()
        self._active = True
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        try:
            if exc_type is not None:
                self.mariadb_database.rollback()
                self._compensate_mongodb()
                return
            try:
                self.mariadb_database.commit()
            except Exception:
                self.mariadb_database.rollback()
                self._compensate_mongodb()
                raise
        finally:
            self._active = False

    def _require_active(self) -> None:
        if not self._active:
            raise RuntimeError("active MariaMongoWriteService context is required")

    def execute_verified_mariadb(
        self, sql_text: str, parameters: tuple[Any, ...] = (),
        *, expected_affected_rows: int | None = None,
    ) -> int:
        self._require_active()
        affected_rows = self.mariadb_database.execute(sql_text, parameters)
        if expected_affected_rows is not None and affected_rows != expected_affected_rows:
            raise RuntimeError(
                f"MariaDB affected row count mismatch: expected={expected_affected_rows}, actual={affected_rows}"
            )
        return affected_rows

    def insert_mongodb_document(
        self,
        *,
        collection_name: str,
        document: Mapping[str, Any],
        compensation_filter: Mapping[str, Any] | None = None,
    ) -> Any:
        self._require_active()
        result = self.mongodb_database.insert_one(collection_name, document)
        inserted_id = result.inserted_id
        delete_filter = (
            dict(compensation_filter)
            if compensation_filter is not None
            else {"_id": inserted_id}
        )
        self._inserted_mongodb_documents.append((collection_name, delete_filter))
        return inserted_id

    def _compensate_mongodb(self) -> None:
        for collection_name, delete_filter in reversed(self._inserted_mongodb_documents):
            self.mongodb_database.delete_one(collection_name, delete_filter)
        self._inserted_mongodb_documents.clear()
