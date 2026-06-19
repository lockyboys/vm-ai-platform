# ==========================================================
# 파일명: ai_job_controller.py
# 업무분류: AI
# 목적: AI 작업 관련 API Controller
# 관련 Service: AIJobService, AIJobLogService
#
# 변경이력
# [v7.21] 2026-06-19
# - /api/ai-jobs API를 web/app.py에서 분리
# - /api/ai-jobs/<job_id>/logs API를 web/app.py에서 분리
# ==========================================================

from flask import Blueprint, jsonify, request

from config import AI_JOB_DEFAULT_LIMIT
from src.AI.services.ai_job_service import AIJobService
from src.AI.services.ai_job_log_service import AIJobLogService


ai_job_bp = Blueprint("ai_job", __name__)


@ai_job_bp.route("/api/ai-jobs", methods=["GET"])
def api_ai_jobs():
    """
    AI 작업 목록 조회 API

    목적:
        AI_JOBS에 저장된 분석 작업 목록을 조회한다.

    관련 테이블:
        AI_JOBS
        AI_AUTOML_RESULTS
    """
    try:
        limit = request.args.get("limit", AI_JOB_DEFAULT_LIMIT, type=int)

        rows = AIJobService().get_ai_jobs(limit)

        return jsonify({
            "success": True,
            "message": "AI job list",
            "count": len(rows),
            "data": rows
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "AI job list failed",
            "error": str(e)
        }), 500


@ai_job_bp.route("/api/ai-jobs/<int:job_id>/logs", methods=["GET"])
def api_ai_job_logs(job_id):
    """
    AI 작업 로그 조회 API

    목적:
        특정 AI 작업의 처리 이력을 조회한다.

    관련 테이블:
        AI_JOB_LOGS
    """
    try:
        limit = request.args.get("limit", AI_JOB_DEFAULT_LIMIT, type=int)

        rows = AIJobLogService().get_logs(job_id, limit)

        return jsonify({
            "success": True,
            "message": "AI job logs",
            "job_id": job_id,
            "count": len(rows),
            "data": rows
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "AI job logs failed",
            "error": str(e)
        }), 500
