"""이메일 흐름을 단일 진입점으로 정리한 뒤 발송 없는 실행 계약을 검증합니다."""
import asyncio
import importlib
import sys
from unittest.mock import AsyncMock, Mock

import pytest
from langgraph.types import Command


@pytest.fixture
def modules(monkeypatch):
    """실제 그래프 구조는 사용하되 LLM·웹·SMTP 외부 I/O를 격리합니다."""
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    model = Mock()
    model.bind_tools.return_value = model
    monkeypatch.setattr(
        "langchain_google_genai.ChatGoogleGenerativeAI",
        lambda **kwargs: model,
    )
    email_name = "FastAPI.LangGraph.Agent_Import_RAGs.LangGraph_email_RAG_Agent"
    main_name = "FastAPI.LangGraph.sps_main_orchestrator"
    sys.modules.pop(main_name, None)
    sys.modules.pop(email_name, None)
    email_agent = importlib.import_module(email_name)
    main = importlib.import_module(main_name)
    yield email_agent, main
    sys.modules.pop(main_name, None)
    sys.modules.pop(email_name, None)


def _stub_email_nodes(monkeypatch, email_agent, *, mode="tavily", sources=None):
    """분류·검색·초안 노드를 고정해 라우팅 결과만 검증합니다."""
    monkeypatch.setattr(
        email_agent,
        "classify_intent",
        Mock(return_value=Command(
            update={"classification": {
                "intent": "question",
                "urgency": "low",
                "topic": "coverage",
            }},
            goto="search_router",
        )),
    )
    monkeypatch.setattr(
        email_agent,
        "search_router",
        Mock(return_value={"search_mode": mode}),
    )
    monkeypatch.setattr(
        email_agent,
        "tavily_search_node",
        Mock(return_value={"search_results": sources or []}),
    )
    monkeypatch.setattr(
        email_agent,
        "draft_response",
        Mock(return_value=Command(
            update={"draft_response": "근거 있는 초안"},
            goto="send_reply",
        )),
    )
    monkeypatch.setattr(
        email_agent,
        "send_reply",
        Mock(side_effect=AssertionError("SMTP must not run")),
    )


def test_process_email_query_uses_verified_sources_only(modules, monkeypatch):
    email_agent, _ = modules
    _stub_email_nodes(
        monkeypatch,
        email_agent,
        sources=["고정 예시", "[출처: https://fss.or.kr/test] 확인된 근거"],
    )
    result = asyncio.run(email_agent.process_email_query(
        "보험 웹 문의",
        sender_email="customer@example.com",
        email_id="mail-1",
    ))
    assert result["status"] == "draft_ready"
    assert result["source_count"] == 1
    assert result["sources"] == ["[출처: https://fss.or.kr/test] 확인된 근거"]
    assert result["email_id"] == "mail-1"
    assert result["email_sent"] is False
    email_agent.send_reply.assert_not_called()


def test_internal_rag_gap_is_reported_without_fake_draft(modules, monkeypatch):
    email_agent, _ = modules
    _stub_email_nodes(monkeypatch, email_agent, mode="rag_search")
    result = asyncio.run(email_agent.process_email_query("보험 약관 문의"))
    assert result["status"] == "review_required"
    assert result["retrieval_status"] == "internal_rag_not_implemented"
    assert result["sources"] == []
    email_agent.draft_response.assert_not_called()
    email_agent.send_reply.assert_not_called()


def test_empty_email_is_rejected_before_graph(modules, monkeypatch):
    email_agent, _ = modules
    classify = Mock()
    monkeypatch.setattr(email_agent, "classify_intent", classify)
    with pytest.raises(ValueError):
        asyncio.run(email_agent.process_email_query("   "))
    classify.assert_not_called()


def test_orchestrator_delegates_to_one_email_entrypoint(modules, monkeypatch):
    email_agent, main = modules
    expected = {
        "status": "review_required",
        "retrieval_status": "no_verified_sources",
        "email_sent": False,
    }
    handler = AsyncMock(return_value=expected)
    monkeypatch.setattr(email_agent, "process_email_query", handler)
    result = asyncio.run(main.run_email_rag_tool.ainvoke({
        "email_content": "문의",
        "sender_email": "a@example.com",
        "email_id": "mail-2",
    }))
    assert result == expected
    handler.assert_awaited_once_with(
        email_content="문의",
        sender_email="a@example.com",
        email_id="mail-2",
    )


def test_orchestrator_registers_all_three_tools(modules):
    _, main = modules
    bound_tools = main.sps_graph.get_graph().nodes["tools"].data.tools_by_name
    assert set(bound_tools) == {
        "run_crawler_tool",
        "search_public_documents",
        "run_email_rag_tool",
    }


def test_query_graph_has_linear_safe_flow(modules):
    email_agent, _ = modules
    graph = email_agent.email_query_app.get_graph()
    assert {"classify", "retrieve", "draft"} <= set(graph.nodes)
    assert "send_reply" not in graph.nodes
    assert "human_review" not in graph.nodes
    assert "ingest_insurance_pdfs" not in graph.nodes
    assert email_agent.app is email_agent.email_query_app
    assert email_agent.full_workflow_app is not email_agent.app
