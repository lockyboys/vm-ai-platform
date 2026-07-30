"""OAuth 2.1 authorization server and JWT verifier for SPS Harness MCP."""

from __future__ import annotations

import asyncio
import base64
import fcntl
import hashlib
import json
import logging
import os
import secrets
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Awaitable, Callable
from urllib.parse import urlencode, urlparse

import anyio
import httpx
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import id_token as google_id_token

from common.auth import AuthenticationError, CommonAuth
from mcp.server.auth.provider import (
    AccessToken,
    AuthorizeError,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    TokenError,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

GoogleClaimsVerifier = Callable[[str, str], Awaitable[dict[str, Any]]]

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class HarnessOAuthSettings:
    """Validated OAuth settings loaded from environment variables."""

    issuer_url: str
    resource_url: str
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str
    allowed_emails: frozenset[str]
    jwt_secret_key: str
    access_token_expire_seconds: int
    refresh_token_expire_seconds: int
    authorization_code_expire_seconds: int
    login_state_expire_seconds: int
    scopes: tuple[str, ...]
    client_registry_path: str

    @classmethod
    def from_environment(cls) -> "HarnessOAuthSettings":
        issuer_url = cls._required("SPS_MCP_OAUTH_ISSUER_URL").rstrip("/")
        resource_url = os.getenv(
            "SPS_MCP_OAUTH_RESOURCE_URL",
            f"{issuer_url}/mcp",
        ).strip().rstrip("/")
        google_redirect_uri = os.getenv(
            "SPS_MCP_GOOGLE_REDIRECT_URI",
            f"{issuer_url}/oauth/google/callback",
        ).strip()
        allowed_emails = frozenset(
            email.strip().lower()
            for email in cls._required("SPS_MCP_OAUTH_ALLOWED_EMAILS").split(",")
            if email.strip()
        )
        scopes = tuple(
            scope.strip()
            for scope in os.getenv("SPS_MCP_OAUTH_SCOPES", "mcp:tools").split(",")
            if scope.strip()
        )
        jwt_secret_key = cls._required("SPS_AUTH_JWT_SECRET_KEY")
        client_registry_path = cls._required("SPS_MCP_OAUTH_CLIENT_REGISTRY_PATH")

        cls._require_https_url("SPS_MCP_OAUTH_ISSUER_URL", issuer_url)
        cls._require_https_url("SPS_MCP_OAUTH_RESOURCE_URL", resource_url)
        cls._require_https_url("SPS_MCP_GOOGLE_REDIRECT_URI", google_redirect_uri)
        if not allowed_emails:
            raise RuntimeError("SPS_MCP_OAUTH_ALLOWED_EMAILS must contain at least one email address.")
        if not scopes:
            raise RuntimeError("SPS_MCP_OAUTH_SCOPES must contain at least one scope.")
        if len(jwt_secret_key.encode("utf-8")) < 32:
            raise RuntimeError("SPS_AUTH_JWT_SECRET_KEY must contain at least 32 bytes.")

        return cls(
            issuer_url=issuer_url,
            resource_url=resource_url,
            google_client_id=cls._required("SPS_MCP_GOOGLE_CLIENT_ID"),
            google_client_secret=cls._required("SPS_MCP_GOOGLE_CLIENT_SECRET"),
            google_redirect_uri=google_redirect_uri,
            allowed_emails=allowed_emails,
            jwt_secret_key=jwt_secret_key,
            access_token_expire_seconds=cls._positive_integer(
                "SPS_AUTH_JWT_EXPIRE_SECONDS",
                3600,
            ),
            refresh_token_expire_seconds=cls._positive_integer(
                "SPS_AUTH_REFRESH_TOKEN_EXPIRE_SECONDS",
                2592000,
            ),
            authorization_code_expire_seconds=cls._positive_integer(
                "SPS_MCP_OAUTH_CODE_EXPIRE_SECONDS",
                300,
            ),
            login_state_expire_seconds=cls._positive_integer(
                "SPS_MCP_OAUTH_LOGIN_STATE_EXPIRE_SECONDS",
                600,
            ),
            scopes=scopes,
            client_registry_path=client_registry_path,
        )

    @staticmethod
    def _required(name: str) -> str:
        value = os.getenv(name, "").strip()
        if not value:
            raise RuntimeError(f"{name} environment variable is required.")
        return value

    @classmethod
    def _positive_integer(cls, name: str, default: int) -> int:
        value = os.getenv(name, str(default)).strip()
        try:
            result = int(value)
        except ValueError as error:
            raise RuntimeError(f"{name} must be an integer.") from error
        if result <= 0:
            raise RuntimeError(f"{name} must be positive.")
        return result

    @staticmethod
    def _require_https_url(name: str, value: str) -> None:
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise RuntimeError(f"{name} must be an absolute HTTPS URL without user information.")


@dataclass(frozen=True)
class PendingGoogleLogin:
    client_id: str
    params: AuthorizationParams
    nonce: str
    expires_at: int


class HarnessOAuthProvider(
    OAuthAuthorizationServerProvider[AuthorizationCode, RefreshToken, AccessToken]
):
    """Google-backed OAuth provider that issues audience-bound SPS JWTs."""

    GOOGLE_AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

    def __init__(
        self,
        settings: HarnessOAuthSettings,
        *,
        google_claims_verifier: GoogleClaimsVerifier | None = None,
    ) -> None:
        self.settings = settings
        self._auth = CommonAuth(
            secret_key=settings.jwt_secret_key,
            jwt_expire_seconds=settings.access_token_expire_seconds,
            refresh_token_expire_seconds=settings.refresh_token_expire_seconds,
        )
        self._clients: dict[str, OAuthClientInformationFull] = {}
        self._clients_loaded = False
        self._authorization_codes: dict[str, AuthorizationCode] = {}
        self._pending_google_logins: dict[str, PendingGoogleLogin] = {}
        self._revoked_jti: dict[str, int] = {}
        self._lock = asyncio.Lock()
        self._google_claims_verifier = google_claims_verifier or self._verify_google_id_token
        LOGGER.info(
            "SPS OAuth authorization-code store initialized. pid=%s store_path=%s",
            os.getpid(),
            self._authorization_code_store_path,
        )

    @property
    def _authorization_code_store_path(self) -> str:
        """Return the private process-shared authorization-code store path."""

        return f"{self.settings.client_registry_path}.authorization_codes.json"

    @contextmanager
    def _locked_authorization_code_store(self) -> Any:
        """Yield the shared authorization-code map under an exclusive process lock."""

        store_path = self._authorization_code_store_path
        lock_path = f"{store_path}.lock"
        os.makedirs(os.path.dirname(store_path), mode=0o700, exist_ok=True)
        descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            try:
                with open(store_path, encoding="utf-8") as store_file:
                    stored_codes = json.load(store_file)
            except FileNotFoundError:
                stored_codes = {}
            if not isinstance(stored_codes, dict):
                raise RuntimeError("SPS OAuth authorization-code store has an invalid format.")
            now = time.time()
            stored_codes = {
                code: value
                for code, value in stored_codes.items()
                if isinstance(value, dict) and float(value.get("expires_at", 0)) > now
            }
            yield stored_codes
            temporary_path = f"{store_path}.{secrets.token_hex(8)}.tmp"
            try:
                file_descriptor = os.open(
                    temporary_path,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                )
                with os.fdopen(file_descriptor, "w", encoding="utf-8") as store_file:
                    json.dump(stored_codes, store_file, ensure_ascii=False, sort_keys=True)
                    store_file.flush()
                    os.fsync(store_file.fileno())
                os.replace(temporary_path, store_path)
            finally:
                if os.path.exists(temporary_path):
                    os.unlink(temporary_path)
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    @staticmethod
    def _authorization_code_log_id(code: str) -> str:
        """Return a non-secret code correlation value for operational diagnostics."""

        return hashlib.sha256(code.encode("utf-8")).hexdigest()[:12]

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        await self._ensure_registered_clients_loaded()
        async with self._lock:
            client = self._clients.get(client_id)
        if client is None:
            LOGGER.warning("SPS OAuth client was not found. client_id=%s", client_id)
        return client

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        client_id = str(client_info.client_id or "").strip()
        if not client_id:
            raise ValueError("Registered OAuth clients require a client_id.")
        await self._ensure_registered_clients_loaded()
        async with self._lock:
            self._clients[client_id] = client_info
            self._persist_registered_clients_locked()
        LOGGER.info("SPS OAuth client registered. client_id=%s", client_id)

    async def _ensure_registered_clients_loaded(self) -> None:
        async with self._lock:
            if self._clients_loaded:
                return

            registry_path = self.settings.client_registry_path
            try:
                with open(registry_path, encoding="utf-8") as registry_file:
                    payload = json.load(registry_file)
            except FileNotFoundError:
                payload = []
            except (OSError, json.JSONDecodeError) as error:
                raise RuntimeError(
                    f"Unable to load SPS OAuth client registry: {registry_path}"
                ) from error

            if not isinstance(payload, list):
                raise RuntimeError("SPS OAuth client registry must contain a JSON array.")

            clients: dict[str, OAuthClientInformationFull] = {}
            for client_payload in payload:
                client = OAuthClientInformationFull.model_validate(client_payload)
                client_id = str(client.client_id or "").strip()
                if not client_id:
                    raise RuntimeError("SPS OAuth client registry contains an empty client_id.")
                clients[client_id] = client

            self._clients = clients
            self._clients_loaded = True
        LOGGER.info("SPS OAuth client registry loaded. client_count=%s", len(clients))

    def _persist_registered_clients_locked(self) -> None:
        registry_path = self.settings.client_registry_path
        registry_directory = os.path.dirname(registry_path)
        if not registry_directory:
            raise RuntimeError("SPS OAuth client registry path must include a directory.")

        os.makedirs(registry_directory, mode=0o700, exist_ok=True)
        temporary_path = f"{registry_path}.{secrets.token_hex(8)}.tmp"
        payload = [
            self._clients[client_id].model_dump(mode="json")
            for client_id in sorted(self._clients)
        ]
        try:
            file_descriptor = os.open(
                temporary_path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as registry_file:
                json.dump(payload, registry_file, ensure_ascii=False, sort_keys=True)
                registry_file.flush()
                os.fsync(registry_file.fileno())
            os.replace(temporary_path, registry_path)
        finally:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)

    async def authorize(
        self,
        client: OAuthClientInformationFull,
        params: AuthorizationParams,
    ) -> str:
        client_id = str(client.client_id or "").strip()
        if not client_id:
            raise AuthorizeError("unauthorized_client", "OAuth client_id is required.")
        if params.resource and params.resource.rstrip("/") != self.settings.resource_url:
            raise AuthorizeError(
                "invalid_request",
                "OAuth resource does not match the SPS Harness MCP resource.",
            )
        requested_scopes = list(params.scopes or self.settings.scopes)
        if not set(requested_scopes).issubset(self.settings.scopes):
            raise AuthorizeError("invalid_scope", "Requested OAuth scope is not supported.")

        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        pending = PendingGoogleLogin(
            client_id=client_id,
            params=params,
            nonce=nonce,
            expires_at=int(time.time()) + self.settings.login_state_expire_seconds,
        )
        async with self._lock:
            self._prune_expired_locked()
            self._pending_google_logins[state] = pending

        query = urlencode(
            {
                "client_id": self.settings.google_client_id,
                "redirect_uri": self.settings.google_redirect_uri,
                "response_type": "code",
                "scope": "openid email profile",
                "state": state,
                "nonce": nonce,
                "prompt": "select_account",
            }
        )
        return f"{self.GOOGLE_AUTHORIZATION_ENDPOINT}?{query}"

    async def complete_google_authorization(
        self,
        *,
        state: str,
        google_code: str,
    ) -> str:
        async with self._lock:
            pending = self._pending_google_logins.pop(state, None)
        if pending is None or pending.expires_at <= int(time.time()):
            raise ValueError("Google OAuth state is invalid or expired.")

        claims = await self._exchange_and_verify_google_code(google_code)
        if claims.get("nonce") != pending.nonce:
            raise ValueError("Google ID token nonce does not match the login request.")
        email = str(claims.get("email") or "").strip().lower()
        if claims.get("email_verified") is not True:
            raise PermissionError("Google account email is not verified.")
        if email not in self.settings.allowed_emails:
            raise PermissionError("Google account is not allowed to access SPS Harness MCP.")

        authorization_code_value = secrets.token_urlsafe(32)
        params = pending.params
        authorization_code = AuthorizationCode(
            code=authorization_code_value,
            scopes=list(params.scopes or self.settings.scopes),
            expires_at=time.time() + self.settings.authorization_code_expire_seconds,
            client_id=pending.client_id,
            code_challenge=params.code_challenge,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            resource=self.settings.resource_url,
            subject=email,
        )
        async with self._lock:
            self._authorization_codes[authorization_code_value] = authorization_code
        with self._locked_authorization_code_store() as authorization_codes:
            authorization_codes[authorization_code_value] = authorization_code.model_dump(
                mode="json"
            )
        LOGGER.info(
            "SPS OAuth authorization code saved. pid=%s code_id=%s store_path=%s",
            os.getpid(),
            self._authorization_code_log_id(authorization_code_value),
            self._authorization_code_store_path,
        )

        return construct_redirect_uri(
            str(params.redirect_uri),
            code=authorization_code_value,
            state=params.state,
        )

    async def google_error_redirect(self, *, state: str, error_description: str) -> str:
        async with self._lock:
            pending = self._pending_google_logins.pop(state, None)
        if pending is None or pending.expires_at <= int(time.time()):
            raise ValueError("Google OAuth state is invalid or expired.")
        return construct_redirect_uri(
            str(pending.params.redirect_uri),
            error="access_denied",
            error_description=error_description,
            state=pending.params.state,
        )

    async def load_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: str,
    ) -> AuthorizationCode | None:
        with self._locked_authorization_code_store() as authorization_codes:
            stored_payload = authorization_codes.get(authorization_code)
        if not isinstance(stored_payload, dict):
            LOGGER.warning(
                "SPS OAuth authorization code was not found during token exchange. "
                "pid=%s code_id=%s store_path=%s",
                os.getpid(),
                self._authorization_code_log_id(authorization_code),
                self._authorization_code_store_path,
            )
            return None
        try:
            stored = AuthorizationCode.model_validate(stored_payload)
        except ValueError:
            LOGGER.warning("SPS OAuth authorization-code store contains an invalid record.")
            return None
        if stored is None:
            LOGGER.warning("SPS OAuth authorization code was not found during token exchange.")
            return None
        if stored.expires_at <= time.time():
            LOGGER.warning("SPS OAuth authorization code expired before token exchange.")
            return None
        if stored.client_id != client.client_id:
            LOGGER.warning(
                "SPS OAuth authorization code client binding did not match during token exchange."
            )
            return None
        return stored

    async def exchange_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: AuthorizationCode,
    ) -> OAuthToken:
        with self._locked_authorization_code_store() as authorization_codes:
            stored_payload = authorization_codes.pop(authorization_code.code, None)
        try:
            stored = (
                AuthorizationCode.model_validate(stored_payload)
                if isinstance(stored_payload, dict)
                else None
            )
        except ValueError:
            stored = None
        if (
            stored is None
            or stored.expires_at <= time.time()
            or stored.client_id != client.client_id
            or not stored.subject
        ):
            raise TokenError("invalid_grant", "Authorization code is invalid or expired.")
        return self._issue_token_pair(
            subject=stored.subject,
            client_id=stored.client_id,
            scopes=stored.scopes,
        )

    async def load_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: str,
    ) -> RefreshToken | None:
        claims = self._decode_jwt(refresh_token, expected_token_use="refresh")
        if claims is None or claims.get("client_id") != client.client_id:
            return None
        return RefreshToken(
            token=refresh_token,
            client_id=str(claims["client_id"]),
            scopes=self._claim_scopes(claims),
            expires_at=int(claims["exp"]),
            subject=str(claims["sub"]),
        )

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        requested_scopes = scopes or refresh_token.scopes
        if not set(requested_scopes).issubset(refresh_token.scopes):
            raise TokenError("invalid_scope", "Requested scope exceeds the refresh token scope.")
        await self.revoke_token(refresh_token)
        return self._issue_token_pair(
            subject=str(refresh_token.subject),
            client_id=str(client.client_id),
            scopes=requested_scopes,
        )

    async def load_access_token(self, token: str) -> AccessToken | None:
        claims = self._decode_jwt(token, expected_token_use="access")
        if claims is None:
            return None
        scopes = self._claim_scopes(claims)
        if not set(self.settings.scopes).issubset(scopes):
            return None
        return AccessToken(
            token=token,
            client_id=str(claims["client_id"]),
            scopes=scopes,
            expires_at=int(claims["exp"]),
            resource=self.settings.resource_url,
            subject=str(claims["sub"]),
            claims={
                "iss": claims["iss"],
                "aud": claims["aud"],
                "jti": claims["jti"],
                "token_use": claims["token_use"],
            },
        )

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        claims = self._decode_jwt(
            token.token,
            expected_token_use="access" if isinstance(token, AccessToken) else "refresh",
            allow_revoked=True,
        )
        if claims is None:
            return
        async with self._lock:
            self._revoked_jti[str(claims["jti"])] = int(claims["exp"])
            self._prune_expired_locked()

    def _issue_token_pair(self, *, subject: str, client_id: str, scopes: list[str]) -> OAuthToken:
        now = int(time.time())
        access_token = self._encode_jwt(
            subject=subject,
            client_id=client_id,
            scopes=scopes,
            token_use="access",
            issued_at=now,
            expires_at=now + self.settings.access_token_expire_seconds,
        )
        refresh_token = self._encode_jwt(
            subject=subject,
            client_id=client_id,
            scopes=scopes,
            token_use="refresh",
            issued_at=now,
            expires_at=now + self.settings.refresh_token_expire_seconds,
        )
        return OAuthToken(
            access_token=access_token,
            token_type="Bearer",
            expires_in=self.settings.access_token_expire_seconds,
            scope=" ".join(scopes),
            refresh_token=refresh_token,
        )

    def _encode_jwt(
        self,
        *,
        subject: str,
        client_id: str,
        scopes: list[str],
        token_use: str,
        issued_at: int,
        expires_at: int,
    ) -> str:
        return self._auth.issue_token(
            subject,
            token_type=f"mcp_${token_use}",
            expires_in=expires_at - issued_at,
            issued_at=issued_at,
            additional_claims={
                "iss": self.settings.issuer_url,
                "aud": self.settings.resource_url,
                "client_id": client_id,
                "scope": " ".join(scopes),
                "token_use": token_use,
                "nbf": issued_at,
            },
        )

    def _decode_jwt(
        self,
        token: str,
        *,
        expected_token_use: str,
        allow_revoked: bool = False,
    ) -> dict[str, Any] | None:
        try:
            claims = self._auth.verify_token(
                token,
                expected_type=f"mcp_${expected_token_use}",
                leeway_seconds=30,
            )
        except AuthenticationError:
            return None
        required_claims = {
            "iss",
            "aud",
            "sub",
            "client_id",
            "scope",
            "token_use",
            "iat",
            "nbf",
            "exp",
            "jti",
        }
        if (
            not required_claims.issubset(claims)
            or claims.get("iss") != self.settings.issuer_url
            or claims.get("aud") != self.settings.resource_url
            or claims.get("token_use") != expected_token_use
            or not isinstance(claims.get("client_id"), str)
            or not isinstance(claims.get("scope"), str)
            or not isinstance(claims.get("jti"), str)
        ):
            return None
        if not allow_revoked and str(claims["jti"]) in self._revoked_jti:
            return None
        return claims

    @staticmethod
    def _claim_scopes(claims: dict[str, Any]) -> list[str]:
        scope = claims.get("scope")
        return scope.split() if isinstance(scope, str) else []

    async def _exchange_and_verify_google_code(self, google_code: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                self.GOOGLE_TOKEN_ENDPOINT,
                data={
                    "code": google_code,
                    "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret,
                    "redirect_uri": self.settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            response.raise_for_status()
            token_response = response.json()
        id_token_value = str(token_response.get("id_token") or "")
        if not id_token_value:
            raise ValueError("Google token response did not include an ID token.")
        return await self._google_claims_verifier(
            id_token_value,
            self.settings.google_client_id,
        )

    @staticmethod
    async def _verify_google_id_token(id_token_value: str, client_id: str) -> dict[str, Any]:
        def verify() -> dict[str, Any]:
            claims = google_id_token.verify_oauth2_token(
                id_token_value,
                GoogleAuthRequest(),
                client_id,
            )
            return dict(claims)

        return await anyio.to_thread.run_sync(verify)

    def _prune_expired_locked(self) -> None:
        now = int(time.time())
        self._pending_google_logins = {
            key: value
            for key, value in self._pending_google_logins.items()
            if value.expires_at > now
        }
        self._authorization_codes = {
            key: value
            for key, value in self._authorization_codes.items()
            if value.expires_at > now
        }
        self._revoked_jti = {
            key: expires_at
            for key, expires_at in self._revoked_jti.items()
            if expires_at > now
        }


def pkce_s256(verifier: str) -> str:
    """Return an RFC 7636 S256 challenge; used by tests and operational probes."""

    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
