"""Explicit real MongoDB test; synthetic identity, offline LLM, exact-record cleanup."""
import importlib
import sys
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

agent = importlib.import_module("FastAPI.LangGraph.langgraph_long_term_memory_agent")
pytestmark = pytest.mark.skipif(
    not any("test_agent_context_db_live_20260910.py" in a for a in sys.argv[1:]),
    reason="Explicit live DB invocation required",
)

def test_context_persistence_replay_conflict_and_isolation(monkeypatch):
    subject = "context-db-verification-" + uuid4().hex
    calls = []
    class Graph:
        async def ainvoke(self, state, config):
            calls.append(state)
            return {"verified_response": "synthetic calendar and mail answer", "token_usage": {}}
    monkeypatch.setattr(agent, "get_agent_graph", lambda: Graph())
    payload = {"query": "synthetic context", "thread_id": "test", "request_id": "one",
               "calendar_results": [{"event_id": "cal-test"}],
               "gmail_results": [{"message_id": "mail-test"}]}
    memory = agent.PersistentMemory()
    token = agent.get_auth().issue_access_token(subject)
    headers = {"Authorization": "Bearer " + token}
    try:
        with TestClient(agent.app) as client:
            assert client.post("/api/agent/context", json=payload).status_code == 401
            first = client.post("/api/agent/context", json=payload, headers=headers)
            assert first.status_code == 200, first.text
            assert first.json()["memory_saved"] is True
            other = agent.PersistentMemory()
            try:
                row = other.completed(subject, "test", "one")
                assert row["source_context"]["calendar_results"] == payload["calendar_results"]
                assert row["source_context"]["gmail_results"] == payload["gmail_results"]
                assert row["created_by"] == subject
                assert other.completed(subject + "-other", "test", "one") is None
                assert "synthetic calendar" in other.recall(subject, "next", "synthetic")
            finally:
                other.close()
            second = client.post("/api/agent/context", json=payload, headers=headers)
            assert second.status_code == 200
            assert len(calls) == 1
            changed = dict(payload, gmail_results=[{"message_id": "changed"}])
            assert client.post("/api/agent/context", json=changed, headers=headers).status_code == 409
            assert len(calls) == 1
            assert calls[0]["calendar_results"] == payload["calendar_results"]
            assert calls[0]["gmail_results"] == payload["gmail_results"]
    finally:
        memory.database.delete_one(memory.collection, memory.request_filter(subject, "test", "one"))
        memory.close()
