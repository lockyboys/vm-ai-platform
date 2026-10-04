"""멀티 페르소나 순차 실행과 Tavily 공통 호출 예산의 회귀 테스트."""

import importlib.util
import os
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage

# 테스트 중에는 모델을 생성만 하며 외부 API를 호출하지 않습니다.
os.environ.setdefault("GEMINI_API_KEY", "offline-test-placeholder")
SOURCE_PATH = Path(__file__).with_name("multi_persona_agent_gemini.py")
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

    result = MODULE.planner_node({"messages": [HumanMessage(content="코드를 검토해줘")]})

    assert result["persona_plan"] == ["ARCHITECT", "TESTER", "TUTOR"]
    assert result["llm_call_count"] == 1


def test_personas_run_sequentially_with_shared_tavily_budget(monkeypatch):
    """복수 페르소나를 호출하고 Tavily는 요청 전체 상한까지만 실행해야 합니다."""
    tavily = FakeTavily()
    tool_request = AIMessage(
        content="",
        tool_calls=[
            {"name": tavily.name, "args": {"query": "첫 검색"}, "id": "call-1", "type": "tool_call"},
            {"name": tavily.name, "args": {"query": "두 번째 검색"}, "id": "call-2", "type": "tool_call"},
        ],
    )
    fake_llm = FakeLLM([
        tool_request,
        AIMessage(content="아키텍트 분석"),
        AIMessage(content="테스터 분석"),
    ])
    monkeypatch.setattr(MODULE, "agent_llm", fake_llm)
    monkeypatch.setattr(MODULE, "tavily_tool", tavily)
    monkeypatch.setattr(MODULE, "agent_tools", [tavily])
    monkeypatch.setattr(MODULE, "MAX_PERSONAS_PER_PLAN", 2)
    monkeypatch.setattr(MODULE, "MAX_PERSONA_CALLS", 6)
    monkeypatch.setattr(MODULE, "MAX_TAVILY_CALLS", 1)
    monkeypatch.setattr(MODULE, "MAX_TOTAL_LLM_CALLS", 12)

    result = MODULE.agent_node({
        "messages": [HumanMessage(content="구현을 검토하고 테스트해줘")],
        "persona_plan": ["ARCHITECT", "TESTER"],
        "persona_outputs": [],
        "persona_call_count": 0,
        "tavily_call_count": 0,
        "llm_call_count": 1,
    })

    assert [args["query"] for args in tavily.calls] == ["첫 검색"]
    assert "### ARCHITECT" in result["draft_response"]
    assert "### TESTER" in result["draft_response"]
    assert result["persona_call_count"] == 3
    assert result["tavily_call_count"] == 1
    assert result["llm_call_count"] == 4
    assert not fake_llm.responses
