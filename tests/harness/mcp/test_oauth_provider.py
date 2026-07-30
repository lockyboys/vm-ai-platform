from __future__ import annotations

import asyncio
from urllib.parse import parse_qs, urlparse

import pytest
from mcp.server.auth.provider import AuthorizationParams
from mcp.shared.auth import OAuthClientInformationFull

from harness.mcp.oauth_provider import (
    HarnessOAuthProvider,
    HarnessOAuthSettings,
    pkce_s256,
)


def make_settings() -> HarnessOAuthSettings:
    return HarnessOAuthSettings(
        issuer_url="https://auth.example.test",
        resource_url="https://auth.example.test/mcp",
        google_client_id="google-client",
        google_client_secret="google-secret",
        google_redirect_uri="https://auth.example.test/oauth/google/callback",
        allowed_emails=frozenset({"allowed@example.test"}),
        jwt_secret_key="test-only-secret-key-with-at-least-32-bytes",
        access_token_expire_seconds=3600,
        refresh_token_expire_seconds=7200,
        authorization_code_expire_seconds=300,
        login_state_expire_seconds=600,
        scopes=("mcp:tools",),
        client_registry_path="/tmp/sps_harness_oauth_provider_test_clients.json",
    )


def make_client() -> OAuthClientInformationFull:
    return OAuthClientInformationFull(
        client_id="public-test-client",
        redirect_uris=["http://127.0.0.1:9876/callback"],
        token_endpoint_auth_method="none",
        scope="mcp:tools",
    )


def make_authorization_params() -> AuthorizationParams:
    return AuthorizationParams(
        state="client-state",
        scopes=["mcp:tools"],
        code_challenge=pkce_s256("a" * 64),
        redirect_uri="http://127.0.0.1:9876/callback",
        redirect_uri_provided_explicitly=True,
        resource="https://auth.example.test/mcp",
    )


def test_pkce_s256_matches_rfc_7636_example() -> None:
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    assert pkce_s256(verifier) == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"


def test_environment_settings_require_https_and_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPS_MCP_OAUTH_ISSUER_URL", "http://auth.example.test")
    monkeypatch.setenv("SPS_MCP_OAUTH_ALLOWED_EMAILS", "allowed@example.test")
    monkeypatch.setenv("SPS_AUTH_JWT_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("SPS_MCP_GOOGLE_CLIENT_ID", "client")
    monkeypatch.setenv("SPS_MCP_GOOGLE_CLIENT_SECRET", "secret")
    monkeypatch.setenv("SPS_MCP_OAUTH_CLIENT_REGISTRY_PATH", "/tmp/sps_oauth_test_clients.json")

    with pytest.raises(RuntimeError, match="absolute HTTPS URL"):
        HarnessOAuthSettings.from_environment()


def test_google_login_issues_and_verifies_audience_bound_jwt() -> None:
    async def scenario() -> None:
        settings = make_settings()
        provider = HarnessOAuthProvider(settings)
        client = make_client()
        await provider.register_client(client)

        google_redirect = await provider.authorize(client, make_authorization_params())
        query = parse_qs(urlparse(google_redirect).query)
        state = query["state"][0]
        assert query["client_id"] == [settings.google_client_id]
        assert query["redirect_uri"] == [settings.google_redirect_uri]
        assert query["scope"] == ["openid email profile"]

        nonce = provider._pending_google_logins[state].nonce

        async def verified_google_claims(_: str) -> dict[str, object]:
            return {
                "sub": "google-subject",
                "email": "Allowed@Example.Test",
                "email_verified": True,
                "nonce": nonce,
            }

        provider._exchange_and_verify_google_code = verified_google_claims  # type: ignore[method-assign]
        client_redirect = await provider.complete_google_authorization(
            state=state,
            google_code="google-authorization-code",
        )
        callback_query = parse_qs(urlparse(client_redirect).query)
        assert callback_query["state"] == ["client-state"]

        authorization_code = await provider.load_authorization_code(
            client,
            callback_query["code"][0],
        )
        assert authorization_code is not None
        token_pair = await provider.exchange_authorization_code(client, authorization_code)

        access = await provider.load_access_token(token_pair.access_token)
        assert access is not None
        assert access.subject == "allowed@example.test"
        assert access.client_id == client.client_id
        assert access.resource == settings.resource_url
        assert access.scopes == ["mcp:tools"]

        tampered = token_pair.access_token[:-1] + (
            "A" if token_pair.access_token[-1] != "A" else "B"
        )
        assert await provider.load_access_token(tampered) is None

        refresh = await provider.load_refresh_token(client, str(token_pair.refresh_token))
        assert refresh is not None
        rotated = await provider.exchange_refresh_token(client, refresh, ["mcp:tools"])
        assert await provider.load_access_token(rotated.access_token) is not None
        assert await provider.load_refresh_token(client, str(token_pair.refresh_token)) is None

        await provider.revoke_token(access)
        assert await provider.load_access_token(token_pair.access_token) is None

    asyncio.run(scenario())


def test_unlisted_google_account_is_denied() -> None:
    async def scenario() -> None:
        provider = HarnessOAuthProvider(make_settings())
        client = make_client()
        google_redirect = await provider.authorize(client, make_authorization_params())
        state = parse_qs(urlparse(google_redirect).query)["state"][0]
        nonce = provider._pending_google_logins[state].nonce

        async def unlisted_google_claims(_: str) -> dict[str, object]:
            return {
                "email": "other@example.test",
                "email_verified": True,
                "nonce": nonce,
            }

        provider._exchange_and_verify_google_code = unlisted_google_claims  # type: ignore[method-assign]
        with pytest.raises(PermissionError, match="not allowed"):
            await provider.complete_google_authorization(
                state=state,
                google_code="google-authorization-code",
            )

    asyncio.run(scenario())
