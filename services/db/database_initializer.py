# =============================================================================
# File Name   : services/db/database_initializer.py
# Purpose     : SPDF Database Schema Initializer
# Author      : PARK HEAKYU
# Created     : 2026-07-26
# Description : CommonDatabase를 통해 초기 Database Schema를 생성한다.
# =============================================================================
# CHANGE HISTORY
# =============================================================================
# 20260726 | OpenAI | db_service의 Schema 초기화 책임을 전용 Service로 분리했음
# =============================================================================

from __future__ import annotations

from common.database import CommonDatabase


INIT_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    email       VARCHAR(255) UNIQUE NOT NULL     COMMENT '이메일 (로그인 ID)',
    password    VARCHAR(255) NOT NULL             COMMENT 'SHA-256 암호화 비밀번호',
    plan        VARCHAR(50)  DEFAULT 'free'       COMMENT '플랜: free/pro/enterprise',
    is_active   TINYINT(1)   DEFAULT 1            COMMENT '활성 여부 (1=활성, 0=비활성)',
    last_login  TIMESTAMP    NULL                 COMMENT '마지막 로그인 시각',
    created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP COMMENT '가입일'
);

CREATE TABLE IF NOT EXISTS pipeline_results (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    user_id       VARCHAR(100)                    COMMENT '사용자 ID',
    file_name     VARCHAR(255)                    COMMENT '분석한 파일명',
    task_type     VARCHAR(50)                     COMMENT '태스크 유형 (classification/regression)',
    learning_type VARCHAR(50)                     COMMENT '학습 방식',
    accuracy      FLOAT                           COMMENT '정확도 (0~1)',
    data_json     MEDIUMTEXT                      COMMENT '전체 결과 JSON',
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS uploaded_files (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     VARCHAR(100)                     COMMENT '업로드한 사용자 ID',
    file_name   VARCHAR(255)                     COMMENT '파일명',
    file_hash   VARCHAR(64) UNIQUE               COMMENT 'MD5 해시 (중복 감지)',
    save_path   VARCHAR(500)                     COMMENT '실제 저장 경로',
    row_count   INT                              COMMENT '행 수',
    col_count   INT                              COMMENT '열 수',
    col_info    TEXT                             COMMENT '컬럼 정보 JSON',
    plan        VARCHAR(50)                      COMMENT '업로드 시 플랜',
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_hash (file_hash)
);

CREATE TABLE IF NOT EXISTS model_history (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    user_id       VARCHAR(100)                   COMMENT '학습한 사용자 ID',
    model_name    VARCHAR(100)                   COMMENT '모델 이름',
    task_type     VARCHAR(50)                    COMMENT '태스크 유형',
    learning_type VARCHAR(50)                    COMMENT '학습 방식',
    accuracy      FLOAT                          COMMENT '정확도',
    features      TEXT                           COMMENT '사용된 특성 목록 (JSON)',
    target_col    VARCHAR(100)                   COMMENT '타겟 열 이름',
    plan          VARCHAR(50)                    COMMENT '학습 시 플랜',
    trained_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cron_logs (
    id       INT AUTO_INCREMENT PRIMARY KEY,
    job_name VARCHAR(100)                        COMMENT 'Cron 작업 이름',
    status   VARCHAR(50)                         COMMENT '실행 결과 (완료/실패/스킵)',
    message  TEXT                                COMMENT '상세 메시지',
    ran_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


class DatabaseInitializer:
    """Database Schema 초기화 책임을 제공한다."""

    def __init__(self, database_role: str = "STORY") -> None:
        self.database_role = database_role

    def initialize_schema(self) -> None:
        """등록된 초기 DDL을 하나의 Transaction으로 실행한다."""
        database = CommonDatabase(database_role=self.database_role)

        try:
            database.begin()
            for statement in self._split_statements(INIT_SQL):
                database.execute(statement)
            database.commit()
        except Exception:
            database.rollback()
            raise
        finally:
            database.close()

    @staticmethod
    def _split_statements(sql_text: str) -> list[str]:
        """세미콜론 단위의 초기 DDL을 실행 가능한 문장으로 분리한다."""
        return [
            statement.strip()
            for statement in sql_text.strip().split(";")
            if statement.strip()
        ]
