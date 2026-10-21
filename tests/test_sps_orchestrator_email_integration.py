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
    monkeypatch.setattr(
        email_agent,
        "rag_search_node",
        Mock(return_value={"search_results": [], "rag_status": "empty"}),
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
    assert result["retrieval_status"] == "internal_rag_empty"
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


def test_orchestrator_registers_all_email_and_document_tools(modules):
    _, main = modules
    bound_tools = main.sps_graph.get_graph().nodes["tools"].data.tools_by_name
    assert set(bound_tools) == {
        "run_crawler_tool",
        "search_public_documents",
        "run_email_rag_tool",
        "collect_and_process_mailboxes",
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


def test_mailbox_config_supports_gmail_outlook_and_custom(modules, monkeypatch):
    email_agent, _ = modules
    monkeypatch.setenv("GMAIL_SECRET", "gmail-token")
    monkeypatch.setenv("OUTLOOK_SECRET", "outlook-token")
    monkeypatch.setenv("CUSTOM_SECRET", "custom-password")
    raw = """[
      {"name":"g","provider":"gmail","username":"g@example.com","token_env":"GMAIL_SECRET","auth":"xoauth2"},
      {"name":"o","provider":"outlook","username":"o@example.com","token_env":"OUTLOOK_SECRET","auth":"xoauth2"},
      {"name":"c","provider":"imap","host":"mail.example.com","username":"c@example.com","password_env":"CUSTOM_SECRET"}
    ]"""
    accounts = email_agent.load_mailbox_accounts(raw)
    assert [item["host"] for item in accounts] == [
        "imap.gmail.com",
        "outlook.office365.com",
        "mail.example.com",
    ]
    assert [item["auth"] for item in accounts] == ["xoauth2", "xoauth2", "password"]


def test_mailbox_collection_deduplicates_and_isolates_failures(modules):
    email_agent, _ = modules

    class FakeAdapter:
        def __init__(self, account):
            self.account = account

        def fetch_messages(self, limit):
            if self.account["name"] == "broken":
                raise RuntimeError("offline")
            return [{
                "mailbox": self.account["name"],
                "provider": "imap",
                "email_id": self.account["name"] + ":1",
                "message_id": "<same@example.com>",
                "sender_email": "a@example.com",
                "subject": "보험 문의",
                "received_at": "today",
                "email_content": "보장 내용을 알려 주세요.",
            }]

    result = email_agent.collect_mailbox_messages(
        accounts=[{"name": "one"}, {"name": "two"}, {"name": "broken"}],
        limit_per_account=5,
        adapter_factory=FakeAdapter,
    )
    assert result["configured_mailboxes"] == 3
    assert result["successful_mailboxes"] == 2
    assert result["message_count"] == 1
    assert result["errors"][0]["mailbox"] == "broken"


def test_internal_rag_ranks_real_mongodb_chunks(modules, monkeypatch):
    email_agent, _ = modules
    monkeypatch.setattr(email_agent, "_create_embeddings", lambda texts: [[1.0, 0.0]])

    class Cursor(list):
        def limit(self, count):
            return Cursor(self[:count])

    class Collection:
        def find(self, query, projection):
            return Cursor([
                {"source_file": "low.pdf", "chunk_index": 1,
                 "payload": {"embedding": [0.0, 1.0], "normalized_text": "낮은 관련성"}},
                {"source_file": "high.pdf", "chunk_index": 2,
                 "payload": {"embedding": [1.0, 0.0], "normalized_text": "높은 관련성"}},
            ])

    class Client:
        def __init__(self, *args, **kwargs):
            self.collection = Collection()
            self.closed = False

        def __getitem__(self, name):
            return self.collection if name == "insurance_policy_terms_payload" else self

        def close(self):
            self.closed = True

    monkeypatch.setattr(email_agent, "MongoClient", Client)
    monkeypatch.setenv("RAG_MIN_SCORE", "0.5")
    results = email_agent.retrieve_internal_policy_documents("보장 문의", top_k=1)
    assert len(results) == 1
    assert "internal://high.pdf#chunk-2" in results[0]
    assert "score=1.0000" in results[0]


def test_process_configured_mailboxes_runs_common_flow(modules, monkeypatch):
    email_agent, _ = modules
    monkeypatch.setattr(email_agent, "collect_mailbox_messages", Mock(return_value={
        "configured_mailboxes": 2,
        "successful_mailboxes": 2,
        "message_count": 1,
        "errors": [],
        "messages": [{
            "mailbox": "gmail",
            "provider": "gmail",
            "email_id": "gmail:1",
            "sender_email": "customer@example.com",
            "subject": "실손 문의",
            "email_content": "보장 범위가 궁금합니다.",
        }],
    }))
    handler = AsyncMock(return_value={
        "status": "draft_ready",
        "classification": {},
        "draft_response": "초안",
        "sources": ["source"],
        "source_count": 1,
        "retrieval_status": "internal_rag_sources",
        "email_id": "gmail:1",
        "email_sent": False,
    })
    monkeypatch.setattr(email_agent, "process_email_query", handler)
    result = asyncio.run(email_agent.process_configured_mailboxes(5))
    assert result["processed_messages"] == 1
    assert result["results"][0]["mailbox"] == "gmail"
    handler.assert_awaited_once()


def test_mailbox_limit_validation(modules):
    email_agent, _ = modules
    with pytest.raises(ValueError):
        email_agent.collect_mailbox_messages(accounts=[], limit_per_account=0)


def test_imap_adapter_parses_message_without_marking_read(modules, monkeypatch):
    email_agent, _ = modules
    raw = (
        b"From: customer@example.com\r\n"
        b"Subject: Insurance question\r\n"
        b"Message-ID: <mail-1@example.com>\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n\r\n"
        b"Please explain coverage."
    )

    class FakeImap:
        def __init__(self):
            self.readonly = None

        def login(self, username, secret):
            assert username == "user@example.com"
            assert secret == "secret"

        def select(self, mailbox, readonly=False):
            self.readonly = readonly
            return "OK", [b"1"]

        def uid(self, command, *args):
            if command == "search":
                return "OK", [b"7"]
            return "OK", [(b"7 (RFC822)", raw)]

        def logout(self):
            return "BYE", []

    client = FakeImap()
    account = {
        "name": "primary",
        "provider": "imap",
        "host": "mail.example.com",
        "port": 993,
        "username": "user@example.com",
        "secret": "secret",
        "auth": "password",
        "mailbox": "INBOX",
        "search": "UNSEEN",
        "ssl": True,
    }
    adapter = email_agent.ImapMailboxAdapter(account)
    monkeypatch.setattr(adapter, "_connect", lambda: client)
    messages = adapter.fetch_messages(10)
    assert client.readonly is True
    assert messages[0]["email_id"] == "primary:7"
    assert messages[0]["email_content"] == "Please explain coverage."
