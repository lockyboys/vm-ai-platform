# ==========================================================
# 파일명: ai_job_service.py
# 업무분류: AI
# 목적: AI 작업 비즈니스 로직 처리
# 관련 Repository: AIJobRepository
# ==========================================================

from src.AI.repositories.ai_job_repository import AIJobRepository
from config import AI_JOB_DEFAULT_LIMIT, AI_JOB_MAX_LIMIT


class AIJobService:
    """
    AI 작업 Service

    목적:
        Controller와 Repository 사이에서 AI 작업 업무 로직을 처리한다.

    주의:
        트랜잭션이 필요한 작업은 Service에서 관리한다.
    """

    def __init__(self):
        self.repository = AIJobRepository()

    def get_ai_jobs(self, limit: int = AI_JOB_DEFAULT_LIMIT) -> list:
        """
        AI 작업 목록 조회

        입력:
            limit: 조회할 최대 건수

        반환:
            AI 작업 목록
        """
        if limit <= 0:
            limit = AI_JOB_DEFAULT_LIMIT

        if limit > AI_JOB_MAX_LIMIT:
            limit = AI_JOB_MAX_LIMIT

        return self.repository.find_ai_jobs(limit)
