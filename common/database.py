# =============================================================================
# File Name   : common/database.py
# Purpose     : Common Database Connection
# Author      : PARK HEAKYU
# Created     : 2026-06-27
# Updated     : 2026-07-07
# Description : SPS Framework에서 MariaDB 연결과 Transaction을 공통으로 관리한다.
# =============================================================================
# CHANGE HISTORY
# =============================================================================
# 20260627 | SYSTEM | CommonDatabase를 생성했고, MariaDB 연결과 조회 기능을 지원했음
# 20260707 | SYSTEM | database_role 기반 연결과 Transaction 기능을 추가했음
# =============================================================================

import os
import pymysql
from dotenv import load_dotenv


class CommonDatabase:
    # -------------------------------------------------------------------------
    # Story : database_role 기반으로 MariaDB 연결 객체를 생성한다.
    # Input : database_role(str)
    # Output: CommonDatabase instance
    # -------------------------------------------------------------------------
    def __init__(self, database_role: str = "STORY_PLATFORM"):
        load_dotenv()

        self.database_role = database_role
        self.config = self._load_config(database_role)
        self.database_name = self.config["database"]

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

    # -------------------------------------------------------------------------
    # Story : database_role에 맞는 환경설정을 조회한다.
    # Input : database_role(str)
    # Output: dict
    # -------------------------------------------------------------------------
    def _load_config(self, database_role: str) -> dict:
        prefix_map = {
            "COMMON": "COMMON_MARIADB",
            "AI_PLATFORM": "AI_PLATFORM_MARIADB",
            "HEALTH_COMPANION": "HEALTH_COMPANION_MARIADB",
            "STORY_PLATFORM": "STORY_PLATFORM_MARIADB",
        }

        if database_role not in prefix_map:
            raise ValueError(f"Unknown database_role: {database_role}")

        prefix = prefix_map[database_role]

        config = {
            "host": os.getenv(f"{prefix}_HOST", "127.0.0.1"),
            "port": os.getenv(f"{prefix}_PORT", "3306"),
            "user": os.getenv(f"{prefix}_USER"),
            "password": os.getenv(f"{prefix}_PASSWORD"),
            "database": os.getenv(f"{prefix}_DATABASE"),
        }

        missing = [
            key for key, value in config.items()
            if value is None or value == ""
        ]

        if missing:
            raise ValueError(
                f"Missing database config for {database_role}: {missing}"
            )

        return config

    # -------------------------------------------------------------------------
    # Story : Transaction을 시작한다.
    # Input : 없음
    # Output: 없음
    # -------------------------------------------------------------------------
    def begin(self):
        self.connection.begin()

    # -------------------------------------------------------------------------
    # Story : Transaction을 Commit한다.
    # Input : 없음
    # Output: 없음
    # -------------------------------------------------------------------------
    def commit(self):
        self.connection.commit()

    # -------------------------------------------------------------------------
    # Story : Transaction을 Rollback한다.
    # Input : 없음
    # Output: 없음
    # -------------------------------------------------------------------------
    def rollback(self):
        self.connection.rollback()

    # -------------------------------------------------------------------------
    # Story : SELECT SQL을 실행하고 결과 목록을 반환한다.
    # Input : sql(str), params(tuple | list | dict | None)
    # Output: list[dict]
    # -------------------------------------------------------------------------
    def fetch_all(self, sql: str, params=None):
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()

    # -------------------------------------------------------------------------
    # Story : SELECT SQL을 실행하고 단일 결과를 반환한다.
    # Input : sql(str), params(tuple | list | dict | None)
    # Output: dict | None
    # -------------------------------------------------------------------------
    def fetch_one(self, sql: str, params=None):
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()

    # -------------------------------------------------------------------------
    # Story : INSERT/UPDATE/DELETE SQL을 실행하고 영향 행 수를 반환한다.
    # Input : sql(str), params(tuple | list | dict | None)
    # Output: int
    # -------------------------------------------------------------------------
    def execute(self, sql: str, params=None) -> int:
        with self.connection.cursor() as cursor:
            return cursor.execute(sql, params)

    # -------------------------------------------------------------------------
    # Story : 마지막 INSERT ID를 반환한다.
    # Input : 없음
    # Output: int
    # -------------------------------------------------------------------------
    def last_insert_id(self):
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT LAST_INSERT_ID() AS last_insert_id")
            row = cursor.fetchone()
            return row["last_insert_id"]

    # -------------------------------------------------------------------------
    # Story : DB 연결을 종료한다.
    # Input : 없음
    # Output: 없음
    # -------------------------------------------------------------------------
    def close(self):
        self.connection.close()