# ==========================================================
# 파일명: ai_job_repository.py
# 업무분류: AI
# 목적: AI_JOBS / AI_AUTOML_RESULTS 조회 SQL 전담
# 관련 테이블: AI_JOBS, AI_AUTOML_RESULTS
# ==========================================================

import mysql.connector
from config import MYSQL_CONFIG


class AIJobRepository:
    """
    AI 작업 Repository

    목적:
        AI 작업 관련 SQL을 전담한다.

    주의:
        비즈니스 로직은 작성하지 않는다.
        SQL 실행만 담당한다.
    """

    def find_ai_jobs(self, limit: int = 100) -> list:
        """
        AI 작업 목록 조회

        입력:
            limit: 조회할 최대 건수

        반환:
            AI 작업 목록

        관련 테이블:
            AI_JOBS
            AI_AUTOML_RESULTS
        """
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute(
                """
                SELECT
                    j.job_id,
                    j.job_name,
                    j.job_type_code,
                    j.status_code,
                    j.created_by,
                    j.started_at,
                    j.ended_at,
                    j.created_at,
                    ar.automl_result_id,
                    ar.best_algorithm_name,
                    ar.best_score
                FROM AI_JOBS j
                LEFT JOIN AI_AUTOML_RESULTS ar
                    ON ar.job_id = j.job_id
                ORDER BY j.job_id DESC
                LIMIT %s
                """,
                (limit,)
            )
            return cursor.fetchall()

        finally:
            cursor.close()
            conn.close()


    def insert_job_log(self, job_id: int, log_level: str, log_message: str, log_json=None) -> int:
        """
        AI 작업 로그 저장

        목적:
            AI 작업의 상태 변화나 처리 이력을 AI_JOB_LOGS에 저장한다.

        관련 테이블:
            AI_JOB_LOGS
        """
        import json

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
