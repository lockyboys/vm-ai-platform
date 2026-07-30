from __future__ import annotations

import asyncio

import httpx
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import AnyHttpUrl

from harness.mcp.oauth_provider import HarnessOAuthProvider, HarnessOAuthSettings


def test_oauth_metadata_and_protected_mcp_http_boundary() -> None:
    async def scenario() -> None:
        settings = HarnessOAuthSettings(
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
            client_registry_path="/tmp/sps_harness_oauth_http_test_clients.json",
        )
        server = FastMCP(
            "SPS Harness OAuth Test",
            auth_server_provider=HarnessOAuthProvider(settings),
            transport_security=TransportSecuritySettings(
                enable_dns_rebinding_protection=True,
                allowed_hosts=["auth.example.test"],
                allowed_origins=[settings.issuer_url],
            ),
            auth=AuthSettings(
                issuer_url=AnyHttpUrl(settings.issuer_url),
                resource_server_url=AnyHttpUrl(settings.resource_url),
                client_registration_options=ClientRegistrationOptions(
                    enabled=True,
                    valid_scopes=list(settings.scopes),
                    default_scopes=list(settings.scopes),
                ),
                required_scopes=list(settings.scopes),
            ),
        )
        app = server.streamable_http_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url=settings.issuer_url,
        ) as client:
            protected_metadata = await client.get(
                "/.well-known/oauth-protected-resource/mcp"
            )
            assert protected_metadata.status_code == 200
            assert protected_metadata.json()["resource"] == settings.resource_url
            assert protected_metadata.json()["authorization_servers"] == [
                f"{settings.issuer_url}/"
            ]

            authorization_metadata = await client.get(
                "/.well-known/oauth-authorization-server"
            )
            assert authorization_metadata.status_code == 200
            assert authorization_metadata.json()["issuer"] == f"{settings.issuer_url}/"
            assert authorization_metadata.json()["code_challenge_methods_supported"] == [
                "S256"
            ]

            denied = await client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {},
                        "clientInfo": {"name": "probe", "version": "1"},
                    },
                },
            )
            assert denied.status_code == 401
            challenge = denied.headers["www-authenticate"]
            assert challenge.startswith("Bearer ")
            assert "resource_metadata=" in challenge

    asyncio.run(scenario())
