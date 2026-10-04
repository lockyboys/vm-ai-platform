"""멀티 페르소나 순차 실행과 Tavily 공통 호출 예산의 회귀 테스트."""

import importlib.util
import os
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

# 테스트 중에는 모델을 생성만 하며 외부 API를 호출하지 않습니다.
os.environ.setdefault("GEMINI_API_KEY", "offline-test-placeholder")
SOURCE_PATH = (
    Path(__file__).resolve().parents[1]
    / "FastAPI"
    / "LangGraph"
    / "multi_persona"
    / "multi_persona_agent_gemini.py"
)
SPEC = importlib.util.spec_from_file_location("multi_persona_agent_under_test", SOURCE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FakeTavily:
    """실제 네트워크 대신 호출 수와 검색 입력을 기록합니다."""

    name = "tavily_search"

    def __init__(self):
        self.calls = []

    def invoke(self, args):
        self.calls.append(args)
        return [{"title": "offline result", "url": "https://example.invalid"}]


class FakeLLM:
    """미리 정한 tool call 및 persona 답변을 순서대로 반환합니다."""

    def __init__(self, responses):
        self.responses = list(responses)

    def invoke(self, messages):
        assert self.responses, "예상보다 많은 모델 호출이 발생했습니다."
        return self.responses.pop(0)


def test_planner_selects_multiple_allowed_personas(monkeypatch):
    """계획기는 중복 제거 후 호출 상한 안에서 여러 역할을 반환해야 합니다."""
    monkeypatch.setattr(MODULE, "MAX_PERSONAS_PER_PLAN", 3)
    monkeypatch.setattr(
        MODULE,
        "router_llm",
        FakeLLM([AIMessage(content='{"personas":["ARCHITECT","TESTER","ARCHITECT","TUTOR"]}')]),
    )

    result = MODULE.router_node({"messages": [HumanMessage(content="코드를 검토해줘")]})

    assert result["persona_plan"] == ["ARCHITECT", "TESTER", "TUTOR"]
    assert result["llm_call_count"] == 1



def test_graph_runs_personas_and_verifier_through_langgraph_edges(monkeypatch):
    """실제 compiled graph가 페르소나를 순차 실행하고 최종 검증해야 합니다."""
    monkeypatch.setattr(MODULE, "MAX_PERSONAS_PER_PLAN", 2)
    monkeypatch.setattr(
        MODULE,
        "router_llm",
        FakeLLM([AIMessage(content='{"personas":["ARCHITECT","TESTER"]}')]),
    )
    fake_agent = FakeLLM([
        AIMessage(content="아키텍트 분석"),
        AIMessage(content="테스터 분석"),
    ])
    monkeypatch.setattr(MODULE, "agent_llm", fake_agent)
    monkeypatch.setattr(MODULE, "verifier_llm", FakeLLM([
        AIMessage(content="## 1. 전문가적 견해 및 종합 평가\\n검증 완료")
    ]))
    monkeypatch.setattr(MODULE, "MAX_PERSONA_CALLS", 6)
    monkeypatch.setattr(MODULE, "MAX_TOTAL_LLM_CALLS", 12)
    monkeypatch.setattr(MODULE, "MAX_VERIFIER_CALLS", 3)
    monkeypatch.setattr(MODULE, "MAX_VERIFIER_RETRIES", 1)

    result = MODULE.graph.invoke(
        {"messages": [HumanMessage(content="구현을 검토하고 테스트해줘")]},
        config={"configurable": {"thread_id": "multi-persona-graph-test"}},
    )

    assert result["persona_outputs"][0].endswith("아키텍트 분석")
    assert result["persona_outputs"][1].endswith("테스터 분석")
    assert result["verification_succeeded"] is True
    assert "검증 완료" in result["final_response"]
    assert result["persona_call_count"] == 2
    assert result["llm_call_count"] == 4
    graph_nodes = MODULE.graph.get_graph().nodes
    assert "router" in graph_nodes
    assert "agent" in graph_nodes
    assert "persona_complete" in graph_nodes
    assert "verifier" in graph_nodes
    assert "retry_persona" in graph_nodes

class FakeToolRunner:
    """외부 검색 없이 ToolNode 래퍼 경로를 검증합니다."""

    def invoke(self, state):
        return {"messages": [ToolMessage(content="mock search result", tool_call_id="tavily-1")]}


def test_router_conditional_routes_search_to_toolnode(monkeypatch):
    """router의 tool call은 ToolNode로 분기되고 사용량에 반영되어야 합니다."""
    monkeypatch.setattr(MODULE, "tool_node", FakeToolRunner())
    monkeypatch.setattr(MODULE, "tavily_tool", FakeTavily())
    monkeypatch.setattr(MODULE, "MAX_TAVILY_CALLS", 1)
    request = AIMessage(content="", tool_calls=[{
        "name": "tavily_search", "args": {"query": "test"},
        "id": "tavily-1", "type": "tool_call",
    }])
    state = {"messages": [request], "tavily_call_count": 0}

    assert MODULE.route_router(state) == "tools"
    result = MODULE.counted_tool_node(state)
    assert result["tavily_call_count"] == 1
    assert result["messages"][0].content == "mock search result"

def test_final_text_handles_empty_messages_without_index_error():
    """빈 messages와 final_response에서도 오류 대신 초안/안내를 반환해야 합니다."""
    assert MODULE.resolve_final_text({"messages": [], "final_response": "", "draft_response": "초안"}) == "초안"
    assert MODULE.resolve_final_text({"messages": [], "final_response": ""}) == "[출력 오류] 최종 답변과 초안이 모두 비어 있습니다."
