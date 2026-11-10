"""CommonAuth bearer boundary tests for the public agent chat route."""
from importlib import import_module
from unittest.mock import AsyncMock

import dotenv
from fastapi.testclient import TestClient


def test_agent_chat_rejects_missing_malformed_and_invalid_bearer_before_tools(monkeypatch) -> None:
    # Keep these tests isolated from the real service environment and signing key.
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: False)
    monkeypatch.setenv("SPS_AUTH_JWT_SECRET_KEY", "test-only-common-auth-signing-key-32-bytes")
    monkeypatch.setenv("SPS_AUTH_JWT_EXPIRE_SECONDS", "60")
    monkeypatch.setenv("SPS_AUTH_REFRESH_TOKEN_EXPIRE_SECONDS", "120")

    agent = import_module("FastAPI.LangGraph.gemini.sps_gemini_agent")
    agent_work = AsyncMock()
    monkeypatch.setattr(agent, "get_or_create_agent", agent_work)
    cases = [
        {},  # Missing credentials must fail closed.
        {"Authorization": "Basic not-a-bearer"},  # Wrong scheme must fail closed.
        {"Authorization": "Bearer malformed"},  # Invalid CommonAuth JWT must fail closed.
    ]

    with TestClient(agent.app) as client:
        for headers in cases:
            response = client.post("/agent/chat", json={"user_input": "test"}, headers=headers)
            assert response.status_code == 401
            assert response.headers["www-authenticate"] == "Bearer"

    # No unauthenticated request may initialize or invoke the agent tools.
    agent_work.assert_not_awaited()
