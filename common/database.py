# =============================================================================
# File Name   : database.py
# Purpose     : Common Database Connection
# Author      : PARK HEAKYU
# Created     : 2026-06-27
# Updated     : 2026-06-27
# Description : SPS Framework에서 MariaDB 연결을 공통으로 관리한다.
# =============================================================================
# CHANGE HISTORY
# =============================================================================
# 20260627 | SYSTEM | CommonDatabase를 생성했고, MariaDB 연결과 조회 기능을 지원했음
# =============================================================================

import pymysql


class CommonDatabase:
    # -------------------------------------------------------------------------
    # Story : MariaDB 연결 객체를 생성한다.
    # Input : config(dict)
    # Output: CommonDatabase instance
    # -------------------------------------------------------------------------
    def __init__(self, config: dict):
        self.database_name = config["database"]
        self.config = config
        self.connection = pymysql.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            database=config["database"],
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
        )

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
    # Story : INSERT/UPDATE/DELETE SQL을 실행하고 영향 행 수를 반환한다.
    # Input : sql(str), params(tuple | list | dict | None)
    # Output: int
    # -------------------------------------------------------------------------
    def execute(self, sql: str, params=None) -> int:
        with self.connection.cursor() as cursor:
            return cursor.execute(sql, params)

    # -------------------------------------------------------------------------
    # Story : DB 연결을 종료한다.
    # Input : 없음
    # Output: 없음
    # -------------------------------------------------------------------------
    def close(self):
        self.connection.close()