# services/history_service.py ★ 7.16.4
# ⭐ 이력 JSON 파일 저장 서비스
# 🆕 모든 이력은 무조건 JSON 파일로 저장!
#    DB 연결 없어도 항상 기록이 남아요.
#
# 초등학생 설명:
#   일어난 일을 일기장(JSON 파일)에 기록해요.
#   DB가 없어도 파일은 항상 남아요!
#
# 저장 구조:
#   logs/
#   ├── history/
#   │   ├── pipeline/        ← AI 분석 실행 이력
#   │   │   └── 20260616.json
#   │   ├── model/           ← 모델 학습 이력
#   │   │   └── 20260616.json
#   │   ├── cron/            ← Cron 자동 실행 이력
#   │   │   └── 20260616.json
#   │   ├── upload/          ← 파일 업로드 이력
#   │   │   └── 20260616.json
#   │   ├── login/           ← 로그인 이력
#   │   │   └── 20260616.json
#   │   └── deploy/          ← 배포 이력
#   │       └── 20260616.json
#
# [버전 이력]
#   7.16.4 (2026-06-16): 최초 생성 — 모든 이력 JSON 파일로 통합

import os, json, glob
from datetime import datetime
from typing import Any
from config import LOG_PATH

# 이력 저장 기본 경로
HISTORY_PATH = os.path.join(LOG_PATH, "history")


# ─────────────────────────────────────────────────────
# 📝 핵심 함수: 이력 저장
# ─────────────────────────────────────────────────────

def save_history(category: str, data: dict) -> str:
    """
    이력을 날짜별 JSON 파일에 저장
    초등학생 설명: "오늘 이런 일 있었어요"를 날짜별 파일에 기록해요.

    Args:
        category : 이력 종류 (pipeline/model/cron/upload/login/deploy)
        data     : 저장할 데이터 딕셔너리

    Returns:
        저장된 파일 경로

    사용 예시:
        save_history("pipeline", {"user": "jeaje", "accuracy": 0.87})
        save_history("model",    {"model": "RandomForest", "accuracy": 0.91})
        save_history("cron",     {"job": "daily_retrain", "status": "완료"})
    """
    # 폴더 생성
    folder = os.path.join(HISTORY_PATH, category)
    os.makedirs(folder, exist_ok=True)

    # 날짜별 파일명 (하루치를 한 파일에 모음)
    today    = datetime.now().strftime("%Y%m%d")
    filepath = os.path.join(folder, f"{today}.json")

    # 타임스탬프 자동 추가
    data["recorded_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data["category"]    = category

    # 기존 파일 읽기 (없으면 빈 리스트)
    records = _load_json_safe(filepath, default=[])

    # 새 이력 추가
    records.append(data)

    # 저장
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2, default=str)

    return filepath


def load_history(category: str, days: int = 7, limit: int = 100) -> list:
    """
    최근 N일치 이력 조회
    초등학생 설명: 최근 일기 몇 권을 꺼내서 보는 거예요.

    Args:
        category : 이력 종류
        days     : 최근 며칠치 (기본 7일)
        limit    : 최대 개수 (기본 100개)

    Returns:
        이력 리스트 (최신순)
    """
    folder = os.path.join(HISTORY_PATH, category)
    if not os.path.exists(folder):
        return []

    # 날짜 내림차순으로 파일 정렬
    files   = sorted(glob.glob(os.path.join(folder, "*.json")), reverse=True)[:days]
    records = []

    for fpath in files:
        data = _load_json_safe(fpath, default=[])
        if isinstance(data, list):
            records.extend(data)

    # 최신순 정렬 후 limit 개수만 반환
    records.sort(key=lambda x: x.get("recorded_at",""), reverse=True)
    return records[:limit]


def load_all_history(days: int = 7) -> dict:
    """
    전체 카테고리 이력 한번에 조회
    초등학생 설명: 모든 종류의 일기를 한꺼번에 꺼내줘요.

    Returns:
        {카테고리: 이력리스트} 딕셔너리
    """
    categories = ["pipeline", "model", "cron", "upload", "login", "deploy"]
    return {cat: load_history(cat, days=days) for cat in categories}


# ─────────────────────────────────────────────────────
# 📋 카테고리별 편의 함수
# ─────────────────────────────────────────────────────

def save_pipeline_history(user_id: str, file_name: str, task_type: str,
                          learning_type: str, accuracy: float,
                          elapsed: float, result: dict = None) -> str:
    """
    AI 파이프라인 실행 이력 저장
    초등학생 설명: AI가 분석을 할 때마다 "언제, 누가, 얼마나 잘했는지" 기록해요.
    """
    return save_history("pipeline", {
        "user_id":       user_id,
        "file_name":     file_name,
        "task_type":     task_type,
        "learning_type": learning_type,
        "accuracy":      round(float(accuracy), 4) if accuracy else 0,
        "elapsed_sec":   round(float(elapsed), 2),
        "타겟열":        result.get("타겟_열","") if result else "",
        "모델":          result.get("ML결과",{}).get("모델명","") if result else "",
        "등급":          result.get("점수",{}).get("종합_등급","") if result else "",
    })


def save_model_history(model_name: str, task_type: str, learning_type: str,
                       accuracy: float, features: list, target_col: str,
                       user_id: str = "system") -> str:
    """
    모델 학습 이력 저장 — 시간이 지날수록 정확도 향상 추이 확인 가능
    초등학생 설명: AI가 공부할 때마다 "몇 점 받았는지" 성적표를 기록해요.
    """
    return save_history("model", {
        "model_name":    model_name,
        "task_type":     task_type,
        "learning_type": learning_type,
        "accuracy":      round(float(accuracy), 4) if accuracy else 0,
        "features":      features if isinstance(features, list) else [],
        "target_col":    target_col,
        "user_id":       user_id,
    })


def save_cron_history(job_name: str, status: str, message: str = "") -> str:
    """
    Cron 자동 실행 이력 저장
    초등학생 설명: 알람시계가 울렸을 때 "언제 울렸고 결과가 어땠는지" 기록해요.
    """
    return save_history("cron", {
        "job_name": job_name,
        "status":   status,
        "message":  str(message)[:500],
    })


def save_upload_history(user_id: str, file_name: str, file_hash: str,
                        row_count: int, col_count: int) -> str:
    """
    파일 업로드 이력 저장
    초등학생 설명: 어떤 파일을 언제 올렸는지 기록해요.
    """
    return save_history("upload", {
        "user_id":   user_id,
        "file_name": file_name,
        "file_hash": file_hash[:8] + "...",   # 해시 앞 8자리만
        "row_count": row_count,
        "col_count": col_count,
    })


def save_login_history(email: str, plan: str, success: bool,
                       reason: str = "") -> str:
    """
    로그인 이력 저장
    초등학생 설명: 누가 언제 로그인했는지(성공/실패) 기록해요.
    """
    return save_history("login", {
        "email":   email,
        "plan":    plan,
        "success": success,
        "reason":  reason,
    })


def save_deploy_history(version: str, status: str,
                        message: str = "", user: str = "admin") -> str:
    """
    배포 이력 저장
    초등학생 설명: 새 버전을 올릴 때마다 "언제 어떤 버전으로 바꿨는지" 기록해요.
    """
    return save_history("deploy", {
        "version": version,
        "status":  status,
        "message": message,
        "user":    user,
    })


# ─────────────────────────────────────────────────────
# 📊 통계 함수
# ─────────────────────────────────────────────────────

def get_stats(days: int = 7) -> dict:
    """
    전체 이력 통계 요약
    초등학생 설명: "이번 주에 총 몇 번 분석했고, 평균 점수는 몇 점이야?" 알려줘요.
    """
    pipeline = load_history("pipeline", days=days)
    model    = load_history("model",    days=days)
    cron     = load_history("cron",     days=days)
    upload   = load_history("upload",   days=days)
    login    = load_history("login",    days=days)
    deploy   = load_history("deploy",   days=days)

    # 평균 정확도
    accs    = [r.get("accuracy",0) for r in model if r.get("accuracy",0) > 0]
    avg_acc = round(sum(accs)/len(accs)*100, 1) if accs else 0

    return {
        "분석_횟수":    len(pipeline),
        "학습_횟수":    len(model),
        "평균_정확도":  f"{avg_acc}%",
        "cron_실행":    len(cron),
        "업로드_횟수":  len(upload),
        "로그인_횟수":  len(login),
        "배포_횟수":    len(deploy),
        "최고_정확도":  f"{max(accs)*100:.1f}%" if accs else "-",
        "조회_기간":    f"최근 {days}일",
    }


# ─────────────────────────────────────────────────────
# 🔧 내부 유틸
# ─────────────────────────────────────────────────────

def _load_json_safe(path: str, default: Any = None) -> Any:
    """
    JSON 파일 안전하게 읽기 — 파일 없거나 깨져도 기본값 반환
    초등학생 설명: 일기장이 없거나 찢어져도 빈 일기장을 새로 줘요.
    """
    if not os.path.exists(path):
        return default if default is not None else {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return default if default is not None else {}
