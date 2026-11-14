from __future__ import annotations

import asyncio
import os
import time

import httpx
import pytest
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import AnyHttpUrl

from common.auth import CommonAuth
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


def test_common_auth_token_replacement_and_mcp_http_calls(monkeypatch, tmp_path) -> None:
    """테스트 키로 발급→환경변수 교체→HTTP 초기화·도구 조회까지 검증합니다."""
    async def scenario() -> None:
        settings = HarnessOAuthSettings(
            issuer_url="https://auth.example.test",
            resource_url="https://auth.example.test/mcp",
            google_client_id="test-client",
            google_client_secret="test-secret",
            google_redirect_uri="https://auth.example.test/oauth/google/callback",
            allowed_emails=frozenset({"allowed@example.test"}),
            jwt_secret_key="test-only-secret-key-with-at-least-32-bytes",
            access_token_expire_seconds=60,
            refresh_token_expire_seconds=120,
            authorization_code_expire_seconds=30,
            login_state_expire_seconds=60,
            scopes=("mcp:tools",),
            client_registry_path=str(tmp_path / "clients.json"),
            common_auth_allowed_subjects=frozenset({"local-user"}),
        )
        provider = HarnessOAuthProvider(settings)
        auth = CommonAuth(
            secret_key=settings.jwt_secret_key,
            jwt_expire_seconds=settings.access_token_expire_seconds,
            refresh_token_expire_seconds=settings.refresh_token_expire_seconds,
        )
        server = FastMCP(
            "CommonAuth HTTP verification",
            auth_server_provider=provider,
            stateless_http=True,
            json_response=True,
            transport_security=TransportSecuritySettings(
                enable_dns_rebinding_protection=True,
                allowed_hosts=["auth.example.test"],
                allowed_origins=[settings.issuer_url],
            ),
            auth=AuthSettings(
                issuer_url=AnyHttpUrl(settings.issuer_url),
                resource_server_url=AnyHttpUrl(settings.resource_url),
                required_scopes=list(settings.scopes),
            ),
        )

        @server.tool()
        def connection_probe() -> str:
            """Read-only in-process test probe; never accesses production data."""
            return "connection-ok"

        app = server.streamable_http_app()
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=settings.issuer_url) as client:
                async def request(token: str, method: str, params: dict | None = None):
                    return await client.post(
                        "/mcp",
                        headers={"Authorization": f"Bearer {token}", "Accept": "application/json, text/event-stream"},
                        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
                    )

                invalid = "x" * 24
                monkeypatch.setenv("SPS_MCP_BEARER_TOKEN", invalid)
                assert (await request(os.environ["SPS_MCP_BEARER_TOKEN"], "tools/list")).status_code == 401
                monkeypatch.setenv("SPS_MCP_BEARER_TOKEN", auth.issue_access_token("local-user"))
                token = os.environ["SPS_MCP_BEARER_TOKEN"]
                initialized = await request(token, "initialize", {
                    "protocolVersion": "2025-06-18", "capabilities": {},
                    "clientInfo": {"name": "common-auth-probe", "version": "1"},
                })
                assert initialized.status_code == 200
                assert "result" in initialized.json()
                listed = await request(token, "tools/list")
                assert listed.status_code == 200
                assert "connection_probe" in {tool["name"] for tool in listed.json()["result"]["tools"]}
                called = await request(token, "tools/call", {"name": "connection_probe", "arguments": {}})
                assert called.status_code == 200
                assert called.json()["result"]["content"][0]["text"] == "connection-ok"
                for denied_token in (
                    auth.issue_access_token("other-user"),
                    auth.issue_refresh_token("local-user"),
                    auth.issue_token("local-user", token_type="access", expires_in=1, issued_at=int(time.time()) - 5),
                ):
                    assert (await request(denied_token, "tools/list")).status_code == 401
                access = await provider.load_access_token(token)
                assert access is not None
                await provider.revoke_token(access)
                assert (await request(token, "tools/list")).status_code == 401

    asyncio.run(scenario())


def load_gemini_agent_for_test(monkeypatch):
    """운영 .env를 읽지 않고 테스트 자격증명만 주입합니다."""
    import importlib
    import dotenv

    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: False)
    monkeypatch.setenv("SPS_AUTH_JWT_SECRET_KEY", "test-only-common-auth-key-at-least-32-bytes")
    monkeypatch.setenv("SPS_AUTH_JWT_EXPIRE_SECONDS", "60")
    monkeypatch.setenv("SPS_AUTH_REFRESH_TOKEN_EXPIRE_SECONDS", "120")
    monkeypatch.setenv("SPS_MCP_URL", "https://auth.example.test/mcp")
    monkeypatch.setenv("SPS_MCP_BEARER_TOKEN", "x" * 24)
    agent = importlib.import_module("FastAPI.LangGraph.gemini.sps_gemini_agent")
    monkeypatch.setattr(agent, "BEARER_TOKEN", "x" * 24)
    return agent


def test_gemini_check_issues_and_replaces_token_without_printing_it(monkeypatch, capsys) -> None:
    import sys

    agent = load_gemini_agent_for_test(monkeypatch)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    class TestClient:
        def __init__(self, connections):
            headers = connections["sps_harness"]["headers"]
            issued_token = os.environ["SPS_MCP_BEARER_TOKEN"]
            assert headers["Authorization"] == f"Bearer {issued_token}"
            assert CommonAuth().verify_token(issued_token, expected_type="access")["sub"] == "local-user"

        async def get_tools(self):
            return [object()]

    def unexpected_gemini_call():
        pytest.fail("--check-mcp must not call Gemini")

    monkeypatch.setattr(agent, "MultiServerMCPClient", TestClient)
    monkeypatch.setattr(agent, "create_gemini_model", unexpected_gemini_call)
    monkeypatch.setattr(sys, "argv", ["sps_gemini_agent.py", "--common-auth-user", "local-user", "--check-mcp"])
    asyncio.run(agent.main())
    output = capsys.readouterr()
    assert "MCP_OK tools=1" in output.out
    assert os.environ["SPS_MCP_BEARER_TOKEN"] not in output.out + output.err


def test_gemini_common_token_requires_signing_configuration(monkeypatch) -> None:
    agent = load_gemini_agent_for_test(monkeypatch)
    monkeypatch.delenv("SPS_AUTH_JWT_SECRET_KEY")
    with pytest.raises(RuntimeError, match="SPS_AUTH_JWT_SECRET_KEY"):
        agent.issue_common_auth_token("local-user")
    assert os.environ["SPS_MCP_BEARER_TOKEN"] == "x" * 24


def test_gemini_rejects_single_part_placeholder_before_connecting(monkeypatch) -> None:
    agent = load_gemini_agent_for_test(monkeypatch)
    with pytest.raises(RuntimeError, match="JWT"):
        agent.validate_environment(require_gemini=False)


def test_gemini_check_reports_http_status_without_exception_secrets(monkeypatch, capsys) -> None:
    import sys

    agent = load_gemini_agent_for_test(monkeypatch)
    monkeypatch.setattr(agent, "BEARER_TOKEN", "header.payload.signature")

    class DeniedClient:
        async def get_tools(self):
            request = httpx.Request("POST", "https://auth.example.test/mcp")
            response = httpx.Response(401, request=request)
            raise ExceptionGroup("private-group", [
                httpx.HTTPStatusError("do-not-log-token", request=request, response=response)
            ])

    monkeypatch.setattr(agent, "create_mcp_client", DeniedClient)
    monkeypatch.setattr(sys, "argv", ["sps_gemini_agent.py", "--check-mcp"])
    with pytest.raises(SystemExit) as exited:
        asyncio.run(agent.main())
    assert exited.value.code == 1
    output = capsys.readouterr()
    assert "HTTP 401" in output.err
    assert "do-not-log-token" not in output.out + output.err
    assert "private-group" not in output.out + output.err


def test_gemini_cli_runs_memory_graph_with_thread_id(monkeypatch, capsys) -> None:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    agent = load_gemini_agent_for_test(monkeypatch)
    monkeypatch.setattr(agent, "BEARER_TOKEN", "header.payload.signature")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

    class EmptyClient:
        async def get_tools(self):
            return []

    class TestModel:
        def bind_tools(self, tools):
            return self

        async def ainvoke(self, messages):
            assert isinstance(messages[0], SystemMessage)
            assert any(isinstance(message, HumanMessage) and message.content == "test-query" for message in messages)
            return AIMessage(content="graph-complete")

    monkeypatch.setattr(agent, "create_mcp_client", EmptyClient)
    monkeypatch.setattr(agent, "create_gemini_model", TestModel)
    asyncio.run(agent.run_agent("test-query", thread_id="test-thread"))
    assert "graph-complete" in capsys.readouterr().out
