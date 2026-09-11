"""실제 FastAPI 모듈의 장기기억 연결을 검증한다. AI 호출만 대체한다."""
import importlib
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient

agent = importlib.import_module("FastAPI.LangGraph.langgraph_long_term_memory_agent")
memory_module = importlib.import_module("FastAPI.LangGraph.agent_memory")


class DatabaseDouble:
    def __init__(self):
        self.rows = {}
        self.fail = False
    def close(self):
        pass
    def find_one(self, collection, selector, projection=None):
        if self.fail:
            raise OSError("storage unavailable")
        return next((deepcopy(row) for row in self.rows.values()
                     if all(row.get(k) == v for k, v in selector.items())), None)
    def update_one(self, collection, selector, update, upsert=False):
        if self.fail:
            raise OSError("storage unavailable")
        self.rows.setdefault(selector["_id"], deepcopy(update["$setOnInsert"]))
        return SimpleNamespace(acknowledged=True)
    def find(self, collection, selector, projection=None, limit=None, sort=None):
        import re
        def matches(row, clause):
            for k, v in clause.items():
                if k == "$or":
                    if not any(matches(row, child) for child in v):
                        return False
                elif isinstance(v, dict):
                    if "$ne" in v and row.get(k) == v["$ne"]:
                        return False
                    if "$regex" in v and not re.search(v["$regex"], row.get(k, ""), re.I):
                        return False
                elif row.get(k) != v:
                    return False
            return True
        rows = [deepcopy(row) for row in self.rows.values() if matches(row, selector)]
        rows.sort(key=lambda row: (row["created_dt"], row["_id"]), reverse=True)
        return rows[:limit]


@pytest.fixture
def api(monkeypatch):
    database = DatabaseDouble()
    memory = memory_module.PersistentMemory(database=database)
    graph = AsyncMock()
    graph.ainvoke.return_value = {"verified_response": "테스트 응답", "token_usage": {}}
    monkeypatch.setattr(agent, "get_agent_graph", lambda: graph)
    agent.app.dependency_overrides[agent.get_subject] = lambda: "subject-a"
    agent.app.dependency_overrides[agent.get_memory] = lambda: memory
    with TestClient(agent.app) as client:
        yield client, graph, memory, database
    agent.app.dependency_overrides.clear()


@pytest.mark.parametrize("path", ["/api/memory/chat", "/api/insurance/claim"])
def test_chat_routes_forward_query_and_thread(api, path):
    client, graph, memory, database = api
    response = client.post(path, json={"query": "기억 확인", "thread_id": "one", "request_id": "r1"})
    assert response.status_code == 200
    assert response.json()["memory_saved"] is True
    assert memory.history("subject-a", "one") == [("user", "기억 확인"), ("assistant", "테스트 응답")]
    graph.ainvoke.assert_awaited_once()


def test_missing_query_rejected_before_graph(api):
    client, graph, _, _ = api
    assert client.post("/api/memory/chat", json={"thread_id": "one"}).status_code == 422
    graph.ainvoke.assert_not_awaited()


def test_openapi_exposes_memory_route_and_title(api):
    schema = api[0].get("/openapi.json").json()
    assert schema["info"]["title"] == "LangGraph Long-term Memory Agent"
    assert "post" in schema["paths"]["/api/memory/chat"]


def test_new_instance_restores_history_and_cross_thread_recall(api):
    client, graph, memory, database = api
    client.post("/api/memory/chat", json={"query": "내 이름은 Luckyboys", "thread_id": "old"})
    restored = memory_module.PersistentMemory(database=database)
    agent.app.dependency_overrides[agent.get_memory] = lambda: restored
    assert restored.history("subject-a", "old")[0][1] == "내 이름은 Luckyboys"
    response = client.post("/api/memory/chat", json={"query": "내 이름은?", "thread_id": "new"})
    assert response.status_code == 200
    state = graph.ainvoke.call_args.args[0]
    assert "Luckyboys" in state["memory_context"]


def test_subject_and_domain_isolation(api):
    _, _, memory, database = api
    memory.save("subject-a", "old", "r1", "private", {"response": "private"}, "test")
    assert memory.history("subject-b", "old") == []
    assert memory.recall("subject-b", "new", "private") == "[]"
    other = memory_module.PersistentMemory(settings={**memory.settings, "domain_code": "other"}, database=database)
    assert other.history("subject-a", "old") == []


def test_retry_is_idempotent_and_conflicting_query_rejected(api):
    client, graph, _, database = api
    body = {"query": "기억해", "thread_id": "one", "request_id": "same"}
    first = client.post("/api/memory/chat", json=body)
    assert client.post("/api/memory/chat", json=body).json() == first.json()
    assert len(database.rows) == 1
    graph.ainvoke.assert_awaited_once()
    assert client.post("/api/memory/chat", json={**body, "query": "다른 질문"}).status_code == 409


def test_storage_failure_does_not_report_success(api):
    client, graph, _, database = api
    database.fail = True
    assert client.post("/api/memory/chat", json={"query": "test", "thread_id": "one"}).status_code == 503
    graph.ainvoke.assert_not_awaited()


def test_no_access_token_is_rejected(api):
    client, graph, _, _ = api
    del agent.app.dependency_overrides[agent.get_subject]
    assert client.post("/api/memory/chat", json={"query": "test", "thread_id": "one"}).status_code == 401
    graph.ainvoke.assert_not_awaited()
