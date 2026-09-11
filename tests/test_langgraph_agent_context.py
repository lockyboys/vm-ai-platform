import importlib

from fastapi.testclient import TestClient

agent = importlib.import_module("FastAPI.LangGraph.langgraph_long_term_memory_agent")


class FakeGraph:
    def __init__(self):
        self.payload = None

    async def ainvoke(self, payload, config):
        self.payload = payload
        return {
            "verified_response": "통합 컨텍스트 확인",
            "token_usage": {"rag_tavily": {"total_tokens": 0}},
        }


def test_agent_context_injects_calendar_and_gmail(monkeypatch):
    fake_graph = FakeGraph()
    monkeypatch.setattr(agent, "get_agent_graph", lambda: fake_graph)
    calendar_results = [{"event_id": "CAL001", "summary": "정형외과 예약"}]
    gmail_results = [{"message_id": f"MSG{i}"} for i in range(1, 7)]

    with TestClient(agent.app) as client:
        response = client.post(
            "/api/agent/context",
            json={
                "query": "최근 보험 관련 일정과 메일 확인",
                "thread_id": "context-test",
                "calendar_results": calendar_results,
                "gmail_results": gmail_results,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["calendar_count"] == 1
    assert body["gmail_count"] == 6
    assert fake_graph.payload["calendar_results"] == calendar_results
    assert fake_graph.payload["gmail_results"] == gmail_results
