"""LangGraph_MariaDB_Memory_Agent.py 공용 테스트 묶음 (2026-11-15, LuckyBoys 요청: 이 소스로 ChatGPT·Claude·Ollama 자가 수정 시험).

왜 이렇게 만드나
- 대상 소스는 import 순간 Gemini LLM 생성·Tavily 도구 생성·MariaDB 연결·PDF 로드를 바로 한다.
  테스트가 실제 네트워크·DB·과금 API를 부르면 안 되므로, import 전에 sys.modules에 가짜 모듈을 넣는다.
- 원본 파일과 AI별 복사본(selffix_demo/memory_agent/<ai>/)에 같은 테스트를 돌리기 위해,
  각 test_*.py 파일은 TARGET 경로만 정하고 이 모듈의 테스트를 가져다 쓴다(load_cases).
- 실제 결함을 드러내는 재현 테스트 1개 포함: 도구 호출 뒤 agent_node가 '사용자 질문'이 아니라
  마지막 도구 결과 문장으로 약관(RAG)을 검색한다(test_reproduce_rag_query_uses_latest_user_question).
LLM·DB·네트워크는 실행하지 않는다.
"""
from __future__ import annotations

import importlib.util
import sys
import types
from itertools import count
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool

_SEQ = count()
# CommonDatabase 가짜가 연결을 허락할 역할(None이면 모두 ValueError). 테스트마다 바꾼다.
ALLOWED_DB_ROLE = {"role": None}


class FakeLLM:
    """ChatGoogleGenerativeAI 대역: 생성 인자를 기록하고, invoke는 정해진 답을 돌려준다."""

    created: list[dict] = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.calls = []
        FakeLLM.created.append(kwargs)

    def bind_tools(self, tools):
        """도구 바인딩 흉내(자기 자신 반환)."""
        self.tools = tools
        return self

    def invoke(self, messages):
        """받은 메시지를 기록하고 고정 답(도구 호출 없음)을 돌려준다."""
        self.calls.append(messages)
        return AIMessage(content="가짜 답변", usage_metadata={"input_tokens": 3, "output_tokens": 2, "total_tokens": 5})


class FakeDatabase:
    """CommonDatabase 대역: ALLOWED_DB_ROLE에 맞는 역할만 연결 성공, 나머지는 ValueError."""

    def __init__(self, database_role, connect_mariadb=True, connect_mongodb=False):
        if database_role != ALLOWED_DB_ROLE["role"]:
            raise ValueError(f"unknown role {database_role}")
        self.role = database_role

    def ping_mariadb(self):
        return True

    def close(self):
        pass


def _install_fakes(monkeypatch):
    """대상 소스가 import하는 외부 모듈을 가짜로 바꾼다(실제 API·DB·PDF 사용 금지)."""
    genai = types.ModuleType("langchain_google_genai")
    genai.ChatGoogleGenerativeAI = FakeLLM
    genai.GoogleGenerativeAIEmbeddings = lambda **kw: object()
    monkeypatch.setitem(sys.modules, "langchain_google_genai", genai)

    tavily = types.ModuleType("langchain_tavily")

    def tavily_search_factory(max_results=3):
        @tool
        def tavily_search(query: str) -> str:
            """가짜 웹 검색."""
            return f"web:{query}"
        return tavily_search
    tavily.TavilySearch = tavily_search_factory
    monkeypatch.setitem(sys.modules, "langchain_tavily", tavily)

    for name in ("langchain_community", "langchain_community.document_loaders", "langchain_community.vectorstores"):
        monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    sys.modules["langchain_community.document_loaders"].PyMuPDFLoader = lambda path: types.SimpleNamespace(load=lambda: [])
    sys.modules["langchain_community.vectorstores"].FAISS = types.SimpleNamespace(from_documents=lambda *a, **k: None)

    splitters = types.ModuleType("langchain_text_splitters")
    splitters.RecursiveCharacterTextSplitter = lambda **kw: types.SimpleNamespace(split_documents=lambda docs: docs)
    monkeypatch.setitem(sys.modules, "langchain_text_splitters", splitters)

    database = types.ModuleType("common.database")
    database.CommonDatabase = FakeDatabase
    monkeypatch.setitem(sys.modules, "common.database", database)


def load_agent(target: Path, monkeypatch):
    """가짜 모듈을 넣은 뒤 target 소스를 새 모듈 이름으로 불러온다(테스트끼리 상태가 섞이지 않게)."""
    _install_fakes(monkeypatch)
    FakeLLM.created = []
    name = f"memory_agent_under_test_{next(_SEQ)}"
    spec = importlib.util.spec_from_file_location(name, target)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


# ----------------------------------------------------------------------------- 테스트 본문
def case_import_without_db_uses_memory_checkpointer(target, monkeypatch):
    """DB 역할이 모두 실패하면 db=None이고 그래프는 인메모리 체크포인터로 컴파일된다."""
    ALLOWED_DB_ROLE["role"] = None
    agent = load_agent(target, monkeypatch)
    assert agent.db is None and agent.graph is not None


def case_db_role_fallback_picks_first_working_role(target, monkeypatch):
    """앞 역할이 ValueError여도 다음 후보 역할로 연결한다."""
    ALLOWED_DB_ROLE["role"] = "COMMON"
    agent = load_agent(target, monkeypatch)
    assert agent.db is not None and agent.db.role == "COMMON"


@pytest.mark.parametrize("message, expected", [
    (types.SimpleNamespace(text="t", content="c"), "t"),
    (types.SimpleNamespace(content="plain"), "plain"),
    (types.SimpleNamespace(content=[{"type": "text", "text": "a"}, {"type": "image"}, "x", {"type": "text", "text": "b"}]), "a\nb"),
    (types.SimpleNamespace(content=None), "None"),
])
def case_get_message_text(target, monkeypatch, message, expected):
    """str·블록 목록·.text 속성 모두에서 글자만 뽑는다(잘못된 블록은 건너뜀)."""
    agent = load_agent(target, monkeypatch)
    assert agent.get_message_text(message) == expected


@pytest.mark.parametrize("result", [
    types.SimpleNamespace(usage_metadata={"input_tokens": 1, "output_tokens": 2, "total_tokens": 3}),
    types.SimpleNamespace(usage_metadata=None, response_metadata={"token_usage": {"prompt_tokens": 1}}),
    types.SimpleNamespace(usage_metadata=None, response_metadata={}),
    object(),
])
def case_print_token_usage_never_raises(target, monkeypatch, result):
    """잘못된 입력·사용량 없음에도 예외 없이 끝나야 한다."""
    agent = load_agent(target, monkeypatch)
    agent.print_token_usage(result, "node")


def case_gmail_without_credentials_returns_guide(target, monkeypatch):
    """인증 정보가 없으면 안내(시뮬레이션) 문장을 돌려주고 질의어를 포함한다."""
    agent = load_agent(target, monkeypatch)
    monkeypatch.setattr(agent, "_get_google_credentials", lambda: None)
    text = agent.search_gmail_messages.invoke({"query": "발목"})
    assert "Gmail 연동 안내" in text and "발목" in text


def case_calendar_without_credentials_returns_guide(target, monkeypatch):
    """캘린더도 인증 정보가 없으면 안내 문장을 돌려준다."""
    agent = load_agent(target, monkeypatch)
    monkeypatch.setattr(agent, "_get_google_credentials", lambda: None)
    text = agent.search_google_calendar.invoke({"query": "병원"})
    assert "Google Calendar 연동 안내" in text and "병원" in text


def _fake_google_build(gmail_messages=None, calendar_items=None, error=None):
    """googleapiclient.discovery.build 대역(메서드 체인만 흉내)."""
    def build(service_name, version, credentials=None):
        if error:
            raise error
        ns = types.SimpleNamespace
        execute = lambda value: ns(execute=lambda: value)
        if service_name == "gmail":
            messages = ns(list=lambda **kw: execute({"messages": gmail_messages or []}),
                          get=lambda **kw: execute({"payload": {"headers": [{"name": "Subject", "value": "제목A"}]},
                                                    "snippet": "요약A"}))
            return ns(users=lambda: ns(messages=lambda: messages))
        return ns(events=lambda: ns(list=lambda **kw: execute({"items": calendar_items or []})))
    return build


def _install_google_build(monkeypatch, **kwargs):
    discovery = types.ModuleType("googleapiclient.discovery")
    discovery.build = _fake_google_build(**kwargs)
    monkeypatch.setitem(sys.modules, "googleapiclient", types.ModuleType("googleapiclient"))
    monkeypatch.setitem(sys.modules, "googleapiclient.discovery", discovery)


def case_gmail_no_match_and_match(target, monkeypatch):
    """검색 결과 0건이면 '없음' 안내, 1건이면 제목·요약을 담아 돌려준다."""
    agent = load_agent(target, monkeypatch)
    monkeypatch.setattr(agent, "_get_google_credentials", lambda: object())
    _install_google_build(monkeypatch, gmail_messages=[])
    assert "일치하는 수신 메일이 없습니다" in agent.search_gmail_messages.invoke({"query": "x"})
    _install_google_build(monkeypatch, gmail_messages=[{"id": "1"}])
    found = agent.search_gmail_messages.invoke({"query": "x"})
    assert "제목A" in found and "요약A" in found and "(1건)" in found


def case_gmail_api_error_is_reported_not_raised(target, monkeypatch):
    """API 오류는 예외 대신 '조회 실패' 문장으로 보고한다."""
    agent = load_agent(target, monkeypatch)
    monkeypatch.setattr(agent, "_get_google_credentials", lambda: object())
    _install_google_build(monkeypatch, error=RuntimeError("boom"))
    assert "Gmail 조회 실패" in agent.search_gmail_messages.invoke({"query": "x"})


def case_calendar_event_formatting(target, monkeypatch):
    """일정이 있으면 일정명·일시·장소를 담고, 장소가 없으면 '장소 미기재'로 채운다."""
    agent = load_agent(target, monkeypatch)
    monkeypatch.setattr(agent, "_get_google_credentials", lambda: object())
    _install_google_build(monkeypatch, calendar_items=[{"summary": "진료", "start": {"date": "2026-11-15"}}])
    text = agent.search_google_calendar.invoke({"query": "진료"})
    assert "진료" in text and "2026-11-15" in text and "장소 미기재" in text


def case_agent_node_without_retriever(target, monkeypatch):
    """약관 검색기가 없으면 rag_context는 빈 문자열이고 LLM 답을 초안으로 남긴다."""
    agent = load_agent(target, monkeypatch)
    agent.retriever = None
    out = agent.agent_node({"messages": [HumanMessage(content="질문")]})
    assert out["rag_context"] == "" and out["draft_response"] == "가짜 답변"


def case_reproduce_rag_query_uses_latest_user_question(target, monkeypatch):
    """재현: 도구 호출 뒤 다시 agent_node에 오면 마지막 메시지는 도구 결과다.
    약관(RAG) 검색어는 도구 결과 문장이 아니라 가장 최근의 사용자 질문이어야 한다."""
    agent = load_agent(target, monkeypatch)
    seen = []
    agent.retriever = types.SimpleNamespace(invoke=lambda q: seen.append(q) or [])
    state = {"messages": [
        HumanMessage(content="발목 골절 보험금 청구 서류"),
        AIMessage(content="", tool_calls=[{"name": "search_gmail_messages", "args": {"query": "골절"}, "id": "c1"}]),
        ToolMessage(content="[Gmail 연동 안내] 메일 결과 문장", tool_call_id="c1"),
    ]}
    agent.agent_node(state)
    assert seen == ["발목 골절 보험금 청구 서류"]


def case_verifier_uses_draft(target, monkeypatch):
    """검증 노드는 초안을 사람 메시지로 넘기고 결과를 verified_response에 담는다."""
    agent = load_agent(target, monkeypatch)
    out = agent.verifier_node({"messages": [], "draft_response": "초안"})
    sent = agent.verifier_llm.calls[-1]
    assert sent[-1].content == "초안" and out["verified_response"] == "가짜 답변"


CASES = {name[len("case_"):]: fn for name, fn in dict(globals()).items() if name.startswith("case_")}


def load_cases(namespace: dict, target: Path) -> None:
    """test 파일의 전역 이름공간에 test_<이름> 함수를 만든다(대상 경로만 다르고 내용은 같음)."""
    for name, fn in CASES.items():
        marks = getattr(fn, "pytestmark", [])
        params = [m for m in marks if m.name == "parametrize"]

        def make(fn=fn):
            def test(monkeypatch, **kwargs):
                fn(target, monkeypatch, **kwargs)
            return test
        test = make()
        if params:
            argnames = params[0].args[0]
            names = [a.strip() for a in argnames.split(",")]
            # pytest가 인자 이름을 알 수 있게 시그니처를 맞춘 래퍼를 만든다
            code = f"def test(monkeypatch, {', '.join(names)}):\n    fn(target, monkeypatch, {', '.join(n + '=' + n for n in names)})\n"
            scope = {"fn": fn, "target": target}
            exec(code, scope)  # noqa: S102 - 테스트 래퍼 생성 전용(외부 입력 없음)
            test = pytest.mark.parametrize(*params[0].args, **params[0].kwargs)(scope["test"])
        test.__name__ = f"test_{name}"
        namespace[test.__name__] = test
