# ==========================================================
# 파일명: ai_job_log_service.py
# 업무분류: AI
# 목적: AI 작업 로그 비즈니스 로직을 처리한다.
# 관련 Repository: AIJobLogRepository
#
# 변경이력
# [v7.21] 2026-06-19
# - AI_JOB_LOGS Service 신규 생성
# ==========================================================

from src.AI.repositories.ai_job_log_repository import AIJobLogRepository


class AIJobLogService:
    """
    AI 작업 로그 Service

    목적:
        로그 저장 전 검증과 기본값 처리를 담당한다.
    """

    def __init__(self):
        self.repository = AIJobLogRepository()

    def add_log(self, job_id: int, log_level: str,
                log_message: str, log_json: dict | None = None) -> int:
        """
        AI 작업 로그 추가

        입력:
            job_id: AI 작업 ID
            log_level: 로그 레벨
            log_message: 로그 메시지
            log_json: 상세 JSON 데이터

        반환:
            생성된 job_log_id
        """
        if not job_id:
            raise ValueError("job_id는 필수입니다.")

        if not log_level:
            log_level = "INFO"

        if not log_message:
            log_message = "AI 작업 로그"

        return self.repository.insert_log(
            job_id=job_id,
            log_level=log_level,
            log_message=log_message,
            log_json=log_json
        )

    def get_logs(self, job_id: int, limit: int = 100) -> list:
        """
        AI 작업 로그 목록 조회
        """
        if limit <= 0:
            limit = 100

        if limit > 500:
            limit = 500

        return self.repository.find_logs_by_job_id(job_id, limit)
