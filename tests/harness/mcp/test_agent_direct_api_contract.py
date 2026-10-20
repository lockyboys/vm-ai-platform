"""Verify the direct Agent HTTP contract without starting Gemini or Gmail."""
import ast
from pathlib import Path

import pytest
import yaml
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
AGENT = ROOT / "FastAPI/LangGraph/gemini/sps_gemini_agent.py"


def _request_model():
    # Compile the real request model only; provider SDK imports must not make network calls.
    tree = ast.parse(AGENT.read_text(encoding="utf-8"))
    model = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ChatRequest")
    namespace = {"BaseModel": BaseModel, "Field": Field}
    exec(compile(ast.Module(body=[model], type_ignores=[]), str(AGENT), "exec"), namespace)
    return namespace["ChatRequest"]


def _client():
    # Exercise the actual request model at the HTTP boundary with an isolated handler.
    app = FastAPI()
    model = _request_model()

    @app.post("/agent/chat")
    def chat(req: model):
        return {"result": req.user_input}

    return TestClient(app)


@pytest.mark.parametrize("payload", [{}, {"message": "hello"}, {"user_input": ""}, {"user_input": "  \n "}, {"user_input": "x" * 20001}, {"user_input": 3}])
def test_direct_http_rejects_invalid_commands(payload):
    # Missing, malformed, whitespace-only and oversized input must fail before an LLM runs.
    assert _client().post("/agent/chat", json=payload).status_code == 422


def test_direct_http_accepts_command():
    # Preserve the existing request and response names expected by API clients.
    response = _client().post("/agent/chat", json={"user_input": "연결 확인"})
    assert response.status_code == 200
    assert response.json() == {"result": "연결 확인"}


def test_gateway_declares_direct_agent_contract():
    # API registration must expose the actual required field and preserve bearer forwarding.
    spec = yaml.safe_load((ROOT / "openapi-spec.yaml").read_text(encoding="utf-8"))
    operation = spec["paths"]["/agent/chat"]["post"]
    assert operation["operationId"] == "chatWithSpsAgent"
    assert operation["x-google-backend"]["disable_auth"] is True
    body = next(p for p in operation["parameters"] if p["in"] == "body")
    assert body["required"] is True
    assert body["schema"]["required"] == ["user_input"]
    field = body["schema"]["properties"]["user_input"]
    assert field["type"] == "string"
    assert field["minLength"] == 1 and field["maxLength"] == 20000
    assert field["pattern"] == r"\S"
    assert operation["responses"][200]["schema"]["properties"]["result"]["type"] == "string"


def test_agent_chat_is_not_registered_as_mcp_tool():
    # The old wrapper may remain archived in source, but must not be exposed as an MCP tool.
    source = (ROOT / "harness/mcp/sps_harness_server.py").read_text(encoding="utf-8")
    assert "mcp.tool()(sps_gemini_agent_chat)" not in source
    assert 'path == "/agent/chat"' in source
