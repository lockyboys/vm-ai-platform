# services/auth/auth_service.py ★ 7.16.4
# ⭐ JWT 기반 인증 + 플랜별 세분화 권한 관리
# 초등학생 설명: 학교 출입증처럼 "이 사람이 누구인지, 뭘 할 수 있는지" 확인해요!
# 🆕 free = 분류만 / pro = 배치처리 포함 / enterprise = 전부

import hashlib, time, json
from utils import logger
from config import SECRET_KEY, TOKEN_EXPIRE_HOURS

# ─────────────────────────────────────────────────────────
# 플랜별 허용 기능 목록
# ─────────────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────────
# 🎨 UI 표시 규칙 (색깔/뱃지 기준)
# ──────────────────────────────────────────────────────────────────
# ✅ 녹색 뱃지  = 해당 플랜에서 완전 허용
# 🔶 주황 뱃지  = Free에서 일부만 허용 (분류만, 회귀 불가)
# ❌ 회색 취소선 = 해당 플랜에서 사용 불가
# ──────────────────────────────────────────────────────────────────

# UI에서 "일부 허용" 표시할 기능 목록 (Free 한정)
# → 색깔을 녹색이 아닌 주황으로 표시하고 "(분류만)" 라벨 추가
PARTIAL_PERMISSIONS = {
    # 🔶 일부 허용 — UI에서 주황 뱃지로 표시
    "free": {
        "AI분석":        "분류(Classification)만 가능 / 회귀(Regression)는 Pro부터",
        "지도학습_분류": "분류만 허용 / 회귀·비지도·강화학습은 Pro·Enterprise부터",
    },
    # 🔶 Pro의 Cron은 조회만
    "pro": {
        "Cron조회": "Cron 실행 이력 조회만 가능 / 등록·수정·삭제는 Enterprise부터",
    },
}

# 🌟 Enterprise 차별 마케팅 포인트
ENTERPRISE_HIGHLIGHTS = {
    "준지도학습": {
        "title":   "🌟 업계 희귀 기능",
        "desc":    "라벨이 일부만 있어도 AI가 나머지를 스스로 유추해요! "
                   "데이터 라벨링 비용을 최대 70% 절감할 수 있어요.",
        "badge":   "🌟 Enterprise 전용",
        "example": "100개 중 30개만 답을 알려줘도 나머지 70개를 AI가 맞춰요!",
    },
    "강화학습": {
        "title":   "🎮 자동 최적화",
        "desc":    "보상/벌칙 방식으로 AI가 스스로 최적 파라미터를 찾아요!",
        "badge":   "🌟 Enterprise 전용",
        "example": "게임처럼 점수를 올리면서 AI가 스스로 더 똑똑해져요!",
    },
    "Cron관리": {
        "title":   "⏰ 완전 자동화",
        "desc":    "매일 새벽 자동 재학습으로 시간이 지날수록 정확도가 올라가요!",
        "badge":   "🌟 Enterprise 전용",
        "example": "자는 동안 AI가 공부해서 다음 날 더 똑똑해져요!",
    },
}

PLAN_PERMISSIONS = {

    # ┌─────────────────────────────────────────────────────────────┐
    # │  🟢 FREE 플랜 — 무료                                        │
    # │  AI분석 일부 개방: 분류(classification)만 허용              │
    # │  🔶 주황색으로 표시 → "일부 제한" 안내 뱃지 붙임            │
    # │                                                             │
    # │  ✅ 허용: 기본분석 / CSV업로드 / 결과조회                   │
    # │  🔶 일부: AI분석(분류만) / 지도학습_분류                    │
    # │  ❌ 불가: 회귀 / 비지도 / SHAP / PDF / 강화학습 / AutoML   │
    # └─────────────────────────────────────────────────────────────┘
    "free": [
        "기본분석",           # ✅ 완전 허용
        "CSV업로드",          # ✅ 완전 허용
        "결과조회",           # ✅ 완전 허용
        "AI분석",             # 🔶 일부 허용 — 분류만! (PARTIAL_PERMISSIONS 참고)
        "지도학습_분류",      # 🔶 일부 허용 — classification만, regression ❌
        #                     ↑ UI에서 주황색 뱃지 + "(분류만)" 라벨로 표시
        # ──── 아래는 전부 ❌ 불가 ────────────────────────────────
        # "지도학습_회귀",    # ❌ Pro부터 → 집값예측·수치예측 등
        # "비지도학습",       # ❌ Pro부터 → 클러스터링
        # "SHAP",             # ❌ Pro부터 → AI 설명 그래프
        # "PDF다운로드",      # ❌ Pro부터 → 리포트 다운로드
        # "배치처리",         # ❌ Pro부터 → 여러 파일 한번에
        # "준지도학습",       # ❌ Enterprise부터
        # "강화학습",         # ❌ Enterprise부터
        # "AutoML",           # ❌ Enterprise부터
        # "Cron관리",         # ❌ Enterprise부터
    ],

    # 🟡 Pro — 월 5,000원 (분류+회귀+비지도+SHAP+PDF+배치처리)
    # 초등학생 설명: 돈 내는 회원이라 집값 예측(회귀)도 되고 배치처리도 돼요!
    # 🟡 Pro — 월 5,000원
    # 🆕 7.16.4: Cron 제한적 제공 (조회만, 등록/수정/삭제는 Enterprise)
    "pro": [
        "기본분석",           # ✅ 완전허용
        "CSV업로드",          # ✅ 완전허용
        "결과조회",           # ✅ 완전허용
        "AI분석",             # ✅ 완전허용
        "지도학습_분류",      # ✅ classification 허용
        "지도학습_회귀",      # ✅ regression 허용 (free엔 없음)
        "비지도학습",         # ✅ 클러스터링 허용
        "SHAP",               # ✅ AI 설명 그래프
        "PDF다운로드",        # ✅ 리포트 다운로드
        "파일다운로드",       # ✅ 파일 다운로드
        "배치처리",           # ✅ 여러 파일 한번에
        "Cron조회",           # 🆕 7.16.4: Cron 실행 이력 조회만 허용
        #                       ↑ 등록/수정/삭제는 Enterprise만!
    ],

    # 🟣 Enterprise — 월 10,000원 (전부 + 준지도/강화/AutoML/Cron/API)
    # 초등학생 설명: 기업 회원이라 모든 기능을 다 쓸 수 있어요!
    "enterprise": [
        "기본분석",
        "CSV업로드",
        "결과조회",
        "지도학습_분류",
        "지도학습_회귀",
        "비지도학습",
        "준지도학습",
        "강화학습",
        "AI분석",
        "SHAP",
        "PDF다운로드",
        "파일다운로드",
        "배치처리",
        "AutoML",
        "API접근",
        "Cron조회",           # ✅ Pro 기능 포함
        "Cron관리",           # ⏰ 등록·수정·삭제 전용
    ],
}

# 학습방식 → 필요 권한 매핑
# 초등학생 설명: "강화학습 하고 싶어요" 하면 어떤 권한이 필요한지 알려줘요.
LEARNING_PERMISSION_MAP = {
    "supervised_classification": "지도학습_분류",
    "supervised_regression":     "지도학습_회귀",
    "unsupervised":              "비지도학습",
    "semi_supervised":           "준지도학습",
    "reinforcement":             "강화학습",
}


# ─────────────────────────────────────────────────────────
# 함수들
# ─────────────────────────────────────────────────────────

def hash_password(pw: str) -> str:
    """비밀번호 SHA-256 암호화 — 원본은 절대 저장 안 해요"""
    return hashlib.sha256((pw + SECRET_KEY).encode()).hexdigest()


# 관리자 이메일 목록
ADMIN_EMAILS = {"admin@test.com"}

def create_token(user_id: str, email: str, plan: str = "free") -> dict:
    """
    JWT 스타일 토큰 발급
    초등학생 설명: 로그인하면 도장 찍힌 입장권을 줘요!
    """
    is_admin = email in ADMIN_EMAILS
    expire   = time.time() + TOKEN_EXPIRE_HOURS * 3600
    payload  = json.dumps({"user_id": user_id, "email": email,
                            "plan": plan, "is_admin": is_admin, "exp": expire})
    token    = hashlib.sha256((payload + SECRET_KEY).encode()).hexdigest()
    logger.info(f"🔐 토큰 발급: {email} [{plan}] {'👑관리자' if is_admin else ''}")
    return {"token": token, "expire": expire,
            "user_id": user_id, "plan": plan, "is_admin": is_admin}


def verify_token(token: str) -> dict:
    """토큰 검증 — 실서비스에서는 DB 조회 추가 권장"""
    return {"valid": True, "plan": "enterprise"}  # 데모용


def check_permission(plan: str, feature: str) -> bool:
    """
    플랜별 기능 권한 확인
    초등학생 설명: "이 회원이 이 기능을 쓸 수 있나요?" 확인해요.
    """
    allowed = PLAN_PERMISSIONS.get(plan, [])
    ok = feature in allowed
    if not ok:
        logger.warning(f"🚫 권한 없음: [{plan}] → '{feature}'")
    return ok


def check_learning_permission(plan: str, learning_type: str,
                               task_type: str = "classification") -> tuple:
    """
    학습방식 + 태스크 유형 조합으로 권한 확인
    초등학생 설명: "지도학습인데 분류야? 회귀야?" 구분해서 권한 확인해요.

    Returns:
        (허용여부: bool, 필요권한: str, 안내메시지: str)
    """
    # 지도학습은 분류/회귀 구분
    if learning_type == "supervised":
        if task_type == "classification":
            perm = "지도학습_분류"
        else:
            perm = "지도학습_회귀"
    else:
        perm = LEARNING_PERMISSION_MAP.get(learning_type, learning_type)

    ok = check_permission(plan, perm)

    if ok:
        msg = f"✅ [{plan}] {perm} 허용"
    else:
        # 업그레이드 안내
        upgrade = _suggest_upgrade(plan, perm)
        msg = f"❌ [{plan}] {perm} 불가 → {upgrade} 플랜으로 업그레이드 필요"

    return ok, perm, msg


def _suggest_upgrade(plan: str, feature: str) -> str:
    """어떤 플랜으로 올려야 하는지 안내"""
    for p in ["pro", "enterprise"]:
        if feature in PLAN_PERMISSIONS.get(p, []):
            return p
    return "enterprise"


def get_all_permissions(plan: str) -> list:
    """플랜의 전체 권한 목록 반환"""
    return PLAN_PERMISSIONS.get(plan, [])


def get_permission_summary() -> dict:
    """전체 플랜 권한 요약 반환 (UI 표시용)"""
    return {
        plan: {
            "permissions": perms,
            "count": len(perms)
        }
        for plan, perms in PLAN_PERMISSIONS.items()
    }


def get_upgrade_info(plan: str, feature: str) -> dict:
    """
    권한 없을 때 업그레이드 안내 정보 반환
    초등학생 설명: "이 기능 쓰려면 어떤 플랜으로 바꾸면 돼요?" 알려줘요!

    Args:
        plan    : 현재 플랜 (free/pro/enterprise)
        feature : 사용하려는 기능

    Returns:
        {
            "current_plan":  현재 플랜,
            "required_plan": 필요한 플랜,
            "upgrade_price": 업그레이드 비용,
            "feature_desc":  기능 설명,
            "cta":           행동 유도 문구
        }
    """
    # 어떤 플랜이 필요한지 찾기
    required = _suggest_upgrade(plan, feature)

    # Enterprise 차별 기능이면 마케팅 문구 추가
    highlight = ENTERPRISE_HIGHLIGHTS.get(feature, {})

    price_map = {
        "free":       0,
        "pro":        5000,
        "enterprise": 10000,
    }
    current_price  = price_map.get(plan, 0)
    required_price = price_map.get(required, 0)
    diff_price     = required_price - current_price

    return {
        "current_plan":  plan,
        "required_plan": required,
        "upgrade_price": diff_price,
        "feature":       feature,
        "highlight":     highlight,
        "cta":           f"월 {diff_price:,}원 추가로 '{feature}' 기능을 사용해보세요! 🚀",
        "upgrade_url":   f"/register?plan={required}",   # 업그레이드 링크
    }
