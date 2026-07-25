"""SPDF Authentication Framework: JWT, security cookies, current user and CSRF."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping


class AuthenticationError(ValueError):
    """Access 또는 Refresh Token이 없거나 유효하지 않다."""


class CsrfValidationError(ValueError):
    """인증된 브라우저 요청의 CSRF 검증이 실패했다."""


@dataclass(frozen=True)
class AuthenticatedUser:
    """검증된 JWT에서 얻은 현재 사용자."""

    user_id: str


class CommonAuth:
    """SPDF Access/Refresh JWT와 HttpOnly 보안 쿠키를 일관되게 관리한다."""

    ACCESS_TOKEN_COOKIE_NAME = "spdf_access_token"
    REFRESH_TOKEN_COOKIE_NAME = "spdf_refresh_token"
    ALGORITHM = "HS256"
    SAME_SITE = "Lax"
    COOKIE_PATH = "/"

    def __init__(
        self,
        *,
        secret_key: str | None = None,
        jwt_expire_seconds: int | None = None,
        refresh_token_expire_seconds: int | None = None,
    ) -> None:
        self._secret_key = secret_key or self._required_setting("SPS_AUTH_JWT_SECRET_KEY")
        self._jwt_expire_seconds = jwt_expire_seconds or self._positive_integer_setting(
            "SPS_AUTH_JWT_EXPIRE_SECONDS"
        )
        self._refresh_token_expire_seconds = refresh_token_expire_seconds or self._positive_integer_setting(
            "SPS_AUTH_REFRESH_TOKEN_EXPIRE_SECONDS"
        )

    @staticmethod
    def _required_setting(name: str) -> str:
        value = os.getenv(name, "").strip()
        if not value:
            raise RuntimeError(f"{name} environment variable is required.")
        return value

    @classmethod
    def _positive_integer_setting(cls, name: str) -> int:
        value = cls._required_setting(name)
        try:
            seconds = int(value)
        except ValueError as error:
            raise RuntimeError(f"{name} must be an integer.") from error
        if seconds <= 0:
            raise RuntimeError(f"{name} must be positive.")
        return seconds

    @staticmethod
    def _base64url_encode(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")

    @staticmethod
    def _base64url_decode(value: str) -> bytes:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

    @staticmethod
    def _user_id(user: str | Mapping[str, Any]) -> str:
        if isinstance(user, str):
            user_id = user.strip()
        else:
            user_id = str(user.get("user_id") or user.get("id") or user.get("sub") or "").strip()
        if not user_id:
            raise ValueError("A non-empty user identifier is required.")
        return user_id

    def _signature(self, signing_input: str) -> str:
        return self._base64url_encode(
            hmac.new(self._secret_key.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
        )

    def _issue_token(self, user: str | Mapping[str, Any], *, token_type: str, expires_in: int) -> str:
        now = int(time.time())
        header = self._base64url_encode(
            json.dumps({"alg": self.ALGORITHM, "typ": "JWT"}, separators=(",", ":")).encode("utf-8")
        )
        payload = self._base64url_encode(
            json.dumps(
                {
                    "sub": self._user_id(user),
                    "iat": now,
                    "exp": now + expires_in,
                    "jti": secrets.token_urlsafe(24),
                    "token_type": token_type,
                },
                separators=(",", ":"),
            ).encode("utf-8")
        )
        signing_input = f"{header}.{payload}"
        return f"{signing_input}.{self._signature(signing_input)}"

    def _verify_token(self, token: str | None, *, expected_type: str) -> tuple[AuthenticatedUser, int]:
        if not token:
            raise AuthenticationError("Authentication token is required.")
        try:
            header_segment, payload_segment, signature = token.split(".")
            header = json.loads(self._base64url_decode(header_segment))
            payload = json.loads(self._base64url_decode(payload_segment))
            signing_input = f"{header_segment}.{payload_segment}"
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AuthenticationError("Malformed authentication token.") from error
        if header != {"alg": self.ALGORITHM, "typ": "JWT"}:
            raise AuthenticationError("Unsupported authentication token.")
        if not hmac.compare_digest(signature, self._signature(signing_input)):
            raise AuthenticationError("Invalid authentication token signature.")
        user_id = payload.get("sub")
        expires_at = payload.get("exp")
        if (
            not isinstance(user_id, str)
            or not user_id
            or not isinstance(expires_at, int)
            or expires_at <= int(time.time())
            or payload.get("token_type") != expected_type
        ):
            raise AuthenticationError("Expired or invalid authentication token.")
        return AuthenticatedUser(user_id=user_id), expires_at

    @staticmethod
    def _cookie_value(request: Any, cookie_name: str) -> str | None:
        return getattr(request, "cookies", {}).get(cookie_name)

    def get_jwt_expire_seconds(self) -> int:
        """Framework Access Token 만료 시간(초)을 반환한다."""
        return self._jwt_expire_seconds

    def issue_access_token(self, user: str | Mapping[str, Any]) -> str:
        """현재 사용자의 짧은 수명 Access Token을 발급한다."""
        return self._issue_token(user, token_type="access", expires_in=self.get_jwt_expire_seconds())

    def verify_access_token(self, request: Any) -> AuthenticatedUser:
        """요청 Cookie의 Access Token을 검증한다."""
        user, _ = self._verify_token(
            self._cookie_value(request, self.ACCESS_TOKEN_COOKIE_NAME),
            expected_type="access",
        )
        return user

    def issue_refresh_token(self, user: str | Mapping[str, Any]) -> str:
        """Access Token 재발급용 Refresh Token을 발급한다."""
        return self._issue_token(user, token_type="refresh", expires_in=self._refresh_token_expire_seconds)

    def verify_refresh_token(self, request: Any) -> AuthenticatedUser:
        """요청 Cookie의 Refresh Token을 검증한다."""
        user, _ = self._verify_token(
            self._cookie_value(request, self.REFRESH_TOKEN_COOKIE_NAME),
            expected_type="refresh",
        )
        return user

    def get_current_user(self, request: Any) -> AuthenticatedUser | None:
        """유효한 Access Token이 있으면 현재 사용자를, 없으면 None을 반환한다."""
        try:
            return self.verify_access_token(request)
        except AuthenticationError:
            return None

    def require_login(self, request: Any) -> AuthenticatedUser:
        """유효한 Access Token이 없으면 실패하고, 있으면 현재 사용자를 반환한다."""
        return self.verify_access_token(request)

    def generate_csrf_token(self, request: Any) -> str:
        """현재 Access Token에 결속된 CSRF 토큰을 생성한다."""
        token = self._cookie_value(request, self.ACCESS_TOKEN_COOKIE_NAME)
        self._verify_token(token, expected_type="access")
        return hmac.new(
            self._secret_key.encode("utf-8"),
            f"csrf:{token}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def verify_csrf_token(self, request: Any) -> None:
        """폼의 CSRF 토큰이 현재 Access Token에 결속됐는지 검증한다."""
        supplied_token = str(getattr(request, "form", {}).get("csrf_token", ""))
        try:
            expected_token = self.generate_csrf_token(request)
        except AuthenticationError as error:
            raise CsrfValidationError("Authenticated CSRF validation requires a valid Access Token.") from error
        if not hmac.compare_digest(supplied_token, expected_token):
            raise CsrfValidationError("Invalid CSRF token.")

    def _token_expiration(self, token: str, *, token_type: str) -> int:
        _, expires_at = self._verify_token(token, expected_type=token_type)
        return expires_at

    def set_cookie(self, *, response: Any, token: str, token_type: str = "access") -> None:
        """JWT를 HttpOnly·Secure·SameSite=Lax·Expires 쿠키로 응답에 설정한다."""
        if token_type not in {"access", "refresh"}:
            raise ValueError("token_type must be 'access' or 'refresh'.")
        expires_at = self._token_expiration(token, token_type=token_type)
        cookie_name = self.ACCESS_TOKEN_COOKIE_NAME if token_type == "access" else self.REFRESH_TOKEN_COOKIE_NAME
        response.set_cookie(
            cookie_name,
            token,
            max_age=max(expires_at - int(time.time()), 0),
            expires=datetime.fromtimestamp(expires_at, tz=timezone.utc),
            httponly=True,
            secure=True,
            samesite=self.SAME_SITE,
            path=self.COOKIE_PATH,
        )

    def clear_cookie(self, *, response: Any) -> None:
        """Access/Refresh 보안 쿠키를 모두 제거한다."""
        for cookie_name in (self.ACCESS_TOKEN_COOKIE_NAME, self.REFRESH_TOKEN_COOKIE_NAME):
            response.delete_cookie(
                cookie_name,
                path=self.COOKIE_PATH,
                secure=True,
                httponly=True,
                samesite=self.SAME_SITE,
            )
