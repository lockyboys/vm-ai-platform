"""이메일 연결을 실제 LangGraph로 검증하며 LLM/외부 I/O는 대역으로 격리합니다."""
import asyncio
import importlib
import sys
import types
from typing import TypedDict
from unittest.mock import Mock
import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command

@pytest.fixture
def setup_agent(monkeypatch):
    from langchain_google_genai import ChatGoogleGenerativeAI
    model = Mock()
    monkeypatch.setattr("langchain_google_genai.ChatGoogleGenerativeAI", lambda **kwargs: model)
    name = "FastAPI.LangGraph.sps_main_orchestrator"
    sys.modules.pop(name, None)
    main = importlib.import_module(name)
    # 이메일 모듈은 네트워크/SMTP 호출 없이 기존 노드 계약을 재현합니다.
    class State(TypedDict):
        email_content: str
        sender_email: str
        email_id: str
        classification: dict
        search_results: list
        customer_history: dict
        draft_response: str
        messages: list
    fake = types.ModuleType("FastAPI.LangGraph.Agent_Import_RAGs.LangGraph_email_RAG_Agent")
    fake.EmailAgentState = State
    fake.classify_intent = Mock(return_value=Command(update={
        "classification": {"intent": "question", "urgency": "low", "topic": "coverage"}
    }, goto="search_router"))
    fake.search_router = Mock(return_value={"search_mode": "tavily"})
    fake.tavily_search_node = Mock(return_value={"search_results": [
        "고정 예시", "[출처: https://fss.or.kr/test] 확인된 근거"]})
    fake.draft_response = Mock(return_value=Command(update={"draft_response": "근거 있는 초안"}, goto="send_reply"))
    fake.send_reply = Mock(side_effect=AssertionError("SMTP must not run"))
    package = importlib.import_module("FastAPI.LangGraph.Agent_Import_RAGs")
    monkeypatch.setattr(package, "LangGraph_email_RAG_Agent", fake, raising=False)
    monkeypatch.setitem(sys.modules, fake.__name__, fake)
    yield main, fake, model
    sys.modules.pop(name, None)

def test_email_draft_and_no_send(setup_agent):
    main, fake, model = setup_agent
    result = asyncio.run(main.run_email_rag_tool.ainvoke({"email_content": "보험 웹 문의"}))
    assert result["draft_response"] == "근거 있는 초안"
    assert result["email_sent"] is False
    assert result["sources"] == ["[출처: https://fss.or.kr/test] 확인된 근거"]
    fake.send_reply.assert_not_called()

def test_internal_rag_is_not_faked(setup_agent):
    main, fake, _ = setup_agent
    fake.search_router.return_value = {"search_mode": "rag_search"}
    result = asyncio.run(main.run_email_rag_tool.ainvoke({"email_content": "보험 약관 문의"}))
    assert result["retrieval_status"] == "internal_rag_not_implemented"
    assert result["status"] == "review_required"
    assert result["sources"] == []
    fake.draft_response.assert_not_called()

def test_empty_input_rejected(setup_agent):
    main, fake, _ = setup_agent
    with pytest.raises(ValueError):
        asyncio.run(main.run_email_rag_tool.ainvoke({"email_content": "  "}))
    fake.classify_intent.assert_not_called()

def test_graph_dispatch_and_existing_tools(setup_agent):
    main, fake, model = setup_agent
    calls = []
    async def answer(messages):
        calls.append(messages)
        if len(calls) == 1:
            return AIMessage(content="", tool_calls=[{
                "name": "run_email_rag_tool", "args": {"email_content": "웹 보험 문의"}, "id": "email-1"}])
        return AIMessage(content="초안 결과")
    model.bind_tools.return_value = model
    model.ainvoke = answer
    graph = main.create_agent_graph()
    names = {t.name for t in model.bind_tools.call_args.args[0]}
    assert names == {"run_crawler_tool", "search_public_documents", "run_email_rag_tool"}
    result = asyncio.run(graph.ainvoke({"messages": [HumanMessage(content="문의 초안")]}))
    assert result["messages"][-1].content == "초안 결과"
    assert any(getattr(m, "tool_call_id", None) == "email-1" for m in result["messages"])
    fake.draft_response.assert_called_once()
    fake.send_reply.assert_not_called()

def test_search_failure_does_not_make_draft(setup_agent):
    main, fake, _ = setup_agent
    fake.tavily_search_node.return_value = {"search_results": ["검색 실패"], "tavily_status": "failed"}
    result = asyncio.run(main.run_email_rag_tool.ainvoke({"email_content": "웹 문의"}))
    assert result["status"] == "review_required"
    fake.draft_response.assert_not_called()

def test_real_email_module_import_and_graph_build(monkeypatch):
    # 실제 모듈 의존성과 StateGraph 스키마를 확인하되 LLM 호출은 하지 않습니다.
    monkeypatch.setattr("langchain_google_genai.ChatGoogleGenerativeAI", lambda **kwargs: Mock())
    name = "FastAPI.LangGraph.sps_main_orchestrator"
    sys.modules.pop(name, None)
    try:
        main = importlib.import_module(name)
        graph = main.create_email_rag_graph()
        assert {"classify", "retrieve", "draft"} <= set(graph.get_graph().nodes)
    finally:
        sys.modules.pop(name, None)
