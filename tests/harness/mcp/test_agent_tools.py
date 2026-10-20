"""Regression tests for the authenticated SPS Gemini Agent MCP tool."""

from __future__ import annotations

import pytest

from harness.mcp.tools import agent_tools


def test_agent_tool_rejects_empty_prompt_without_network(monkeypatch):
    monkeypatch.setenv("SPS_AUTH_JWT_SECRET_KEY", "unit-test-signing-key")
    monkeypatch.setenv("SPS_AUTH_JWT_EXPIRE_SECONDS", "900")
    monkeypatch.setenv("SPS_AUTH_REFRESH_TOKEN_EXPIRE_SECONDS", "3600")
    monkeypatch.setenv("SPS_MCP_COMMON_AUTH_ALLOWED_SUBJECTS", "jeaje")

    with pytest.raises(ValueError, match="must not be empty"):
        import asyncio
        asyncio.run(agent_tools.sps_gemini_agent_chat("  "))


def test_agent_url_rejects_public_hosts(monkeypatch):
    monkeypatch.setenv("SPS_GEMINI_AGENT_URL", "https://example.com")

    with pytest.raises(RuntimeError, match="loopback HTTP URL"):
        agent_tools._agent_endpoint()


def test_agent_chat_posts_payload_with_short_lived_common_auth(monkeypatch):
    import asyncio

    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"result": "오늘 메일 2건을 확인했습니다."}

    class FakeClient:
        def __init__(self, *, timeout, trust_env):
            captured["timeout"] = timeout
            captured["trust_env"] = trust_env

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def post(self, endpoint, *, json, headers):
            captured.update(endpoint=endpoint, payload=json, headers=headers)
            return FakeResponse()

    monkeypatch.setattr(agent_tools.httpx, "AsyncClient", FakeClient)
    monkeypatch.setenv("SPS_AUTH_JWT_SECRET_KEY", "unit-test-signing-key")
    monkeypatch.setenv("SPS_AUTH_JWT_EXPIRE_SECONDS", "900")
    monkeypatch.setenv("SPS_AUTH_REFRESH_TOKEN_EXPIRE_SECONDS", "3600")
    monkeypatch.setenv("SPS_MCP_COMMON_AUTH_ALLOWED_SUBJECTS", "jeaje")

    result = asyncio.run(agent_tools.sps_gemini_agent_chat("오늘 메일을 읽어줘"))

    assert result == "오늘 메일 2건을 확인했습니다."
    assert captured["endpoint"] == "http://127.0.0.1:8012/agent/chat"
    assert captured["payload"] == {"user_input": "오늘 메일을 읽어줘"}
    assert captured["headers"]["Authorization"].startswith("Bearer ")
    assert captured["trust_env"] is False


def test_agent_chat_refuses_ambiguous_service_identity(monkeypatch):
    monkeypatch.setenv("SPS_MCP_COMMON_AUTH_ALLOWED_SUBJECTS", "jeaje,other")
    monkeypatch.delenv("SPS_MCP_AGENT_SUBJECT_ID", raising=False)

    with pytest.raises(RuntimeError, match="exactly one"):
        agent_tools._service_subject()
