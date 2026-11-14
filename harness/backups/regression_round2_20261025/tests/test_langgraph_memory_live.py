"""Live MongoDB and provider checks. Run explicitly; only uniquely scoped test records are removed."""
import importlib
import json
import subprocess
import sys
import pytest
from pathlib import Path
from uuid import uuid4

agent = importlib.import_module("FastAPI.LangGraph.langgraph_long_term_memory_agent")
memory_module = importlib.import_module("FastAPI.LangGraph.agent_memory")
ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(
    not any("test_langgraph_memory_live.py" in arg for arg in sys.argv[1:]),
    reason="Live checks require an explicit test-file invocation",
)


def test_mongodb_memory_survives_new_process():
    subject = "memory-verification-" + uuid4().hex
    memory = memory_module.PersistentMemory()
    selector = memory.request_filter(subject, "old", "persist")
    try:
        memory.save(subject, "old", "persist", "내 별명은 Luckyboys", {"response": "기억했습니다"}, "127.0.0.1")
        memory.close()
        code = """
import sys
from FastAPI.LangGraph import langgraph_long_term_memory_agent
from FastAPI.LangGraph.agent_memory import PersistentMemory
memory = PersistentMemory()
try:
    assert memory.history(sys.argv[1], "old")[0][1] == "내 별명은 Luckyboys"
    assert "Luckyboys" in memory.recall(sys.argv[1], "new", "별명")
    assert memory.history(sys.argv[1] + "-other", "old") == []
    print("PERSISTENCE_VERIFIED")
finally:
    memory.close()
"""
        child = subprocess.run([sys.executable, "-c", code, subject], cwd=ROOT,
                               capture_output=True, text=True, timeout=30)
        assert child.returncode == 0, "Fresh-process MongoDB read failed (output withheld)"
        assert "PERSISTENCE_VERIFIED" in child.stdout
    finally:
        memory.database.delete_one(memory.collection, selector)
        memory.close()


def test_live_gemini_recalls_memory_in_new_process():
    from fastapi.testclient import TestClient
    from common.auth import CommonAuth
    subject = "memory-ai-verification-" + uuid4().hex
    marker = "MEMORY" + uuid4().hex[:10]
    memory = memory_module.PersistentMemory()
    # A short-lived synthetic test subject; no real user's identity is used.
    token = agent.get_auth().issue_access_token(subject)
    try:
        with TestClient(agent.app) as client:
            first = client.post("/api/memory/chat",
                headers={"Authorization": "Bearer " + token},
                json={"query": "내 테스트 암호는 " + marker + " 입니다. 기억했다고 짧게 답하세요. 검색하지 마세요.",
                      "thread_id": "first", "request_id": "first"})
            assert first.status_code == 200, "Live agent first request failed"
            assert first.json()["memory_saved"] is True
        code = """
import sys
from fastapi.testclient import TestClient
from common.auth import CommonAuth
from FastAPI.LangGraph.langgraph_long_term_memory_agent import app, get_auth
# Tokens stay inside the process and never appear on the command line or stdout.
token = get_auth().issue_access_token(sys.argv[1])
with TestClient(app) as client:
    response = client.post("/api/memory/chat", headers={"Authorization": "Bearer " + token},
        json={"query": "이전 대화에서 알려준 내 테스트 암호만 답하세요. 검색하지 마세요.",
              "thread_id": "second", "request_id": "second"})
    assert response.status_code == 200
    assert sys.argv[2] in response.json()["response"]
    assert response.json()["memory_saved"] is True
print("LIVE_MEMORY_VERIFIED")
"""
        child = subprocess.run([sys.executable, "-c", code, subject, marker], cwd=ROOT,
                               capture_output=True, text=True, timeout=90)
        assert child.returncode == 0, "Fresh-process AI recall failed (output withheld)"
        assert "LIVE_MEMORY_VERIFIED" in child.stdout
    finally:
        for thread in ("first", "second"):
            memory.database.delete_one(memory.collection, memory.request_filter(subject, thread, thread))
        memory.close()
