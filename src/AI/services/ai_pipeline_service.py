# ==========================================================
# 파일명: ai_pipeline_service.py
# 업무분류: AI
# 목적: AI 분석 결과 저장 및 작업 로그 자동 기록
# 관련 테이블: AI_JOBS, AI_AUTOML_RESULTS, AI_JOB_LOGS
#
# 변경이력
# [v7.21] 2026-06-19
# - save_pipeline_result 기능을 db_service.py에서 AI Service로 분리
# - AI_JOB_LOGS 자동 기록 추가
# ==========================================================

import json
import mysql.connector

from config import MYSQL_CONFIG
from src.AI.services.ai_job_log_service import AIJobLogService


class AIPipelineService:
    """
    AI Pipeline Service

    목적:
        AI 분석 결과를 신규 표준 테이블에 저장한다.

    트랜잭션:
        AI_JOBS 저장과 AI_AUTOML_RESULTS 저장은 하나의 작업이다.
        둘 다 성공하면 COMMIT.
        하나라도 실패하면 ROLLBACK.
    """

    def save_pipeline_result(self, user_id, file_name, task_type,
                             learning_type, accuracy, data) -> bool:
        """
        AI 분석 결과 저장

        입력:
            user_id: 사용자 ID
            file_name: 분석 파일명
            task_type: 분석 유형
            learning_type: 학습 방식
            accuracy: 정확도
            data: 분석 결과 JSON

        반환:
            성공 여부

        관련 테이블:
            AI_JOBS
            AI_AUTOML_RESULTS
            AI_JOB_LOGS

        실행 SQL:
            INSERT INTO AI_JOBS (...)
            INSERT INTO AI_AUTOML_RESULTS (...)
        """
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        conn.start_transaction()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO AI_JOBS
                (
                    job_name,
                    job_type_code,
                    status_code,
                    created_by,
                    started_at,
                    ended_at
                )
                VALUES
                (
                    %s,
                    %s,
                    'SUCCESS',
                    %s,
                    NOW(),
                    NOW()
                )
                """,
                (
                    file_name,
                    learning_type.upper() if learning_type else "AUTOML",
                    user_id
                )
            )

            job_id = cursor.lastrowid

            cursor.execute(
                """
                INSERT INTO AI_AUTOML_RESULTS
                (
                    job_id,
                    best_algorithm_name,
                    best_score,
                    result_json
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    job_id,
                    task_type,
                    accuracy,
                    json.dumps(data, ensure_ascii=False)
                )
            )

            conn.commit()

            AIJobLogService().add_log(
                job_id=job_id,
                log_level="INFO",
                log_message="AI 분석 결과 저장 완료",
                log_json={
                    "file_name": file_name,
                    "task_type": task_type,
                    "learning_type": learning_type,
                    "accuracy": accuracy
                }
            )

            return True

        except Exception as e:
            conn.rollback()
            raise e

        finally:
            cursor.close()
            conn.close()
