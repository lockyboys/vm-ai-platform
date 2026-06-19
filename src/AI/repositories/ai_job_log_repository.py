# ==========================================================
# 파일명: ai_job_log_repository.py
# 업무분류: AI
# 목적: AI_JOB_LOGS 테이블에 작업 로그를 저장하고 조회한다.
# 관련 테이블: AI_JOB_LOGS
#
# 변경이력
# [v7.21] 2026-06-19
# - AI_JOB_LOGS Repository 신규 생성
# ==========================================================

import json
import mysql.connector
from config import MYSQL_CONFIG


class AIJobLogRepository:
    """
    AI 작업 로그 Repository

    목적:
        AI 작업 실행 과정에서 발생한 로그를 DB에 저장한다.

    주의:
        SQL 실행만 담당한다.
        트랜잭션 전체 흐름은 Service에서 관리한다.
    """

    def insert_log(self, job_id: int, log_level: str,
                   log_message: str, log_json: dict | None = None) -> int:
        """
        AI 작업 로그 저장

        입력:
            job_id: AI 작업 ID
            log_level: 로그 레벨
            log_message: 로그 메시지
            log_json: 상세 JSON 데이터

        반환:
            생성된 job_log_id

        관련 테이블:
            AI_JOB_LOGS
        """
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO AI_JOB_LOGS
                (
                    job_id,
                    log_level,
                    log_message,
                    log_json
                )
                VALUES
                (
                    %s, %s, %s, %s
                )
                """,
                (
                    job_id,
                    log_level,
                    log_message,
                    json.dumps(log_json, ensure_ascii=False) if log_json else None
                )
            )

            conn.commit()
            return cursor.lastrowid

        finally:
            cursor.close()
            conn.close()

    def find_logs_by_job_id(self, job_id: int, limit: int = 100) -> list:
        """
        AI 작업 로그 조회

        목적:
            특정 AI 작업의 처리 로그를 조회한다.

        입력:
            job_id: AI 작업 ID
            limit: 조회 건수

        반환:
            작업 로그 목록

        관련 테이블:
            AI_JOB_LOGS

        실행 SQL:
            SELECT
                job_log_id,
                job_id,
                log_level,
                log_message,
                log_json,
                created_at
            FROM AI_JOB_LOGS
            WHERE job_id = %s
            ORDER BY job_log_id DESC
            LIMIT %s
        """
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute(
                """
                SELECT
                    job_log_id,
                    job_id,
                    log_level,
                    log_message,
                    log_json,
                    created_at
                FROM AI_JOB_LOGS
                WHERE job_id = %s
                ORDER BY job_log_id DESC
                LIMIT %s
                """,
                (job_id, limit)
            )
            return cursor.fetchall()

        finally:
            cursor.close()
            conn.close()
