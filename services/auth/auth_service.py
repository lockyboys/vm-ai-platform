"""Web authentication compatibility facade backed by common.auth.CommonAuth."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from functools import wraps
from typing import Any, Dict, List, Optional

from flask import g, jsonify, request

from common.auth import AuthenticationError, CommonAuth

_PASSWORD_ITERATIONS = 600_000
_ALLOWED_PLANS = ("free", "pro", "enterprise")

PLAN_PERMISSIONS: Dict[str, List[str]] = {
    "free": ["기본분석", "CSV업로드", "결과조회", "AI분석", "지도학습_분류"],
    "pro": [
        "기본분석", "CSV업로드", "결과조회", "AI분석", "지도학습_분류",
        "지도학습_회귀", "비지도학습", "SHAP", "PDF다운로드",
        "파일다운로드", "배치처리", "Cron조회",
    ],
    "enterprise": [
        "기본분석", "CSV업로드", "결과조회", "AI분석", "지도학습_분류",
        "지도학습_회귀", "비지도학습", "준지도학습", "강화학습", "SHAP",
        "PDF다운로드", "파일다운로드", "배치처리", "AutoML", "API접근",
        "Cron조회", "Cron관리",
    ],
}

PARTIAL_PERMISSIONS = {
    "free": {
        "AI분석": "분류(Classification)만 가능 / 회귀(Regression)는 Pro부터",
        "지도학습_분류": "분류만 허용",
    },
    "pro": {"Cron조회": "조회만 가능 / 관리는 Enterprise부터"},
}

ENTERPRISE_HIGHLIGHTS = {
    "준지도학습": {
        "title": "업계 희귀 기능",
        "desc": "일부 라벨을 활용해 나머지 데이터를 학습합니다.",
        "badge": "Enterprise 전용",
    },
    "강화학습": {
        "title": "자동 최적화",
        "desc": "보상 기반으로 정책을 개선합니다.",
        "badge": "Enterprise 전용",
    },
    "Cron관리": {
        "title": "완전 자동화",
        "desc": "예약 작업의 등록·수정·삭제를 지원합니다.",
        "badge": "Enterprise 전용",
    },
}

LEARNING_PERMISSION_MAP = {
    "supervised_classification": "지도학습_분류",
    "supervised_regression": "지도학습_회귀",
    "unsupervised": "비지도학습",
    "semi_supervised": "준지도학습",
    "reinforcement": "강화학습",
}


def _auth(secret_key: Optional[str] = None) -> CommonAuth:
    """Build the sole JWT implementation; configuration fails closed."""
    return CommonAuth(
        secret_key=secret_key,
        jwt_expire_seconds=(
            int(os.environ["SPS_AUTH_JWT_EXPIRE_SECONDS"])
            if secret_key is None else 3600
        ),
        refresh_token_expire_seconds=(
            int(os.environ["SPS_AUTH_REFRESH_TOKEN_EXPIRE_SECONDS"])
            if secret_key is None else 86400
        ),
    )


def _admin_emails() -> set[str]:
    return {
        value.strip().lower()
        for value in os.getenv("SPS_ADMIN_EMAILS", "").split(",")
        if value.strip()
    }


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str) -> str:
    """Create a salted PBKDF2-HMAC-SHA256 password hash."""
    if not password:
        raise ValueError("password is required")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PASSWORD_ITERATIONS
    )
    return (
        f"pbkdf2_sha256${_PASSWORD_ITERATIONS}$"
        f"{_b64encode(salt)}${_b64encode(digest)}"
    )


def verify_password(password: str, password_hash: str) -> bool:
    """Verify only the current salted password contract."""
    try:
        algorithm, iterations, salt_text, digest_text = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            _b64decode(salt_text),
            int(iterations),
        )
        return hmac.compare_digest(actual, _b64decode(digest_text))
    except (AttributeError, TypeError, ValueError):
        return False


class AuthService:
    """JWT issue/verification adapter retaining the legacy web response shape."""

    def __init__(self, secret_key: Optional[str] = None, algorithm: str = "HS256"):
        if algorithm != CommonAuth.ALGORITHM:
            raise ValueError("Only HS256 is supported by the SPS token contract.")
        self._common_auth = _auth(secret_key)

    def generate_token(
        self,
        user_id: str,
        email: str,
        plan: str = "free",
        expires_in_hours: Optional[int] = None,
    ) -> str:
        normalized_plan = plan.lower()
        if normalized_plan not in PLAN_PERMISSIONS:
            raise ValueError("Unsupported plan.")
        expires_in = (
            expires_in_hours * 3600
            if expires_in_hours is not None
            else self._common_auth.get_jwt_expire_seconds()
        )
        return self._common_auth.issue_token(
            user_id,
            token_type="access",
            expires_in=expires_in,
            additional_claims={
                "email": email.strip().lower(),
                "plan": normalized_plan,
                "is_admin": email.strip().lower() in _admin_emails(),
            },
        )

    def verify_token(self, token: Optional[str]) -> Dict[str, Any]:
        if not token:
            return {"valid": False, "reason": "Token missing"}
        if token.startswith("Bearer "):
            token = token[7:].strip()
        try:
            payload = self._common_auth.verify_token(token, expected_type="access")
            plan = str(payload.get("plan", "")).lower()
            email = str(payload.get("email", "")).strip().lower()
            if plan not in PLAN_PERMISSIONS or not email:
                raise AuthenticationError("Required signed claims are missing.")
            return {
                "valid": True,
                "user_id": payload["sub"],
                "email": email,
                "plan": plan,
                "is_admin": bool(payload.get("is_admin", False)),
                "roles": payload.get("roles", []),
                "exp": payload["exp"],
            }
        except (AuthenticationError, TypeError, ValueError):
            return {"valid": False, "reason": "Invalid or expired token"}


def create_token(user_id: str, email: str, plan: str = "free") -> Dict[str, Any]:
    service = AuthService()
    token = service.generate_token(user_id, email, plan)
    verified = service.verify_token(token)
    return {
        "token": token,
        "expire": verified["exp"],
        "user_id": user_id,
        "plan": plan.lower(),
        "is_admin": verified["is_admin"],
    }


def verify_token(token: Optional[str]) -> Dict[str, Any]:
    return AuthService().verify_token(token)


def check_permission(plan: str, feature: Optional[str] = None):
    """Check a plan feature, or act as a legacy authentication decorator."""
    if feature is not None:
        return feature in PLAN_PERMISSIONS.get(plan.lower(), [])

    required_role = plan

    def decorator(function):
        @wraps(function)
        def decorated_function(*args, **kwargs):
            result = verify_token(request.headers.get("Authorization"))
            if not result["valid"]:
                return jsonify({"success": False, "message": "Unauthorized"}), 401
            roles = set(result.get("roles", []))
            if required_role not in {"user", result["plan"]} and required_role not in roles:
                return jsonify({"success": False, "message": "Forbidden"}), 403
            g.user_id = result["user_id"]
            g.plan = result["plan"]
            return function(*args, **kwargs)

        return decorated_function

    return decorator


def check_learning_permission(
    plan: str, learning_type: str, task_type: str = "classification"
) -> tuple[bool, str, str]:
    if learning_type == "supervised":
        permission = (
            "지도학습_분류" if task_type == "classification" else "지도학습_회귀"
        )
    else:
        permission = LEARNING_PERMISSION_MAP.get(learning_type, learning_type)
    allowed = bool(check_permission(plan, permission))
    message = (
        f"[{plan}] {permission} 허용"
        if allowed
        else f"[{plan}] {permission} 불가"
    )
    return allowed, permission, message


def get_all_permissions(plan: Optional[str] = None) -> List[str]:
    return list(PLAN_PERMISSIONS.get((plan or "free").lower(), []))


def get_permission_summary() -> Dict[str, Any]:
    return {
        plan: {
            "permissions": list(permissions),
            "count": len(permissions),
            "partials": PARTIAL_PERMISSIONS.get(plan, {}),
        }
        for plan, permissions in PLAN_PERMISSIONS.items()
    }


def get_upgrade_info(plan: Optional[str] = None, feature: Optional[str] = None) -> Dict[str, Any]:
    current_plan = (plan or "free").lower()
    available = [
        candidate
        for candidate in _ALLOWED_PLANS
        if candidate != current_plan
        and (feature is None or feature in PLAN_PERMISSIONS[candidate])
    ]
    return {
        "current_plan": current_plan,
        "feature": feature,
        "eligible_for_upgrade": bool(available),
        "available_plans": available,
        "highlights": ENTERPRISE_HIGHLIGHTS,
    }
