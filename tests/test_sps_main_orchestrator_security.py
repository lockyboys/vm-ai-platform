"""sps_main_orchestrator.py의 P0 보강(SSRF 방어, API 키 인증) 회귀 테스트.

검증 의도:
- run_crawler_tool이 내부망·루프백·메타데이터 주소로는 크롤러를 실행하지 않는지 확인한다.
- /api/gemini/chat이 올바른 Bearer 토큰 없이는 통과하지 못하는지 확인한다.
기대 결과: 잘못된 입력(내부 주소, 키 누락/불일치)은 모두 예외로 막히고,
정상 입력(공인 주소, 올바른 키)만 통과한다.
"""

import asyncio
import importlib.util
import os
from pathlib import Path

import pytest
from fastapi import HTTPException
from langchain_core.messages import AIMessage, HumanMessage

# 모듈 import 시 ChatGoogleGenerativeAI가 생성되므로, 실제 네트워크 호출 없이
# 객체만 만들 수 있도록 오프라인 플레이스홀더 키를 미리 넣어둔다.
os.environ.setdefault("GOOGLE_API_KEY", "offline-test-placeholder")
os.environ.setdefault("GEMINI_API_KEY", "offline-test-placeholder")

SOURCE_PATH = (
    Path(__file__).resolve().parents[1]
    / "FastAPI"
    / "LangGraph"
    / "sps_main_orchestrator.py"
)
SPEC = importlib.util.spec_from_file_location("sps_main_orchestrator_under_test", SOURCE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


# ------------------------------------------------------------------------------
# SSRF 방어 테스트
# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "target_url",
    [
        "http://127.0.0.1/",            # 루프백
        "http://localhost/",            # 차단 호스트명
        "http://169.254.169.254/",      # 클라우드 메타데이터 주소
        "http://10.0.0.5/",             # 사설망(RFC1918)
        "http://192.168.1.1/",          # 사설망(RFC1918)
    ],
)
def test_crawl_target_blocks_internal_addresses(target_url):
    """내부망·루프백·메타데이터 주소는 모두 안전하지 않다고 판정해야 한다."""
    assert MODULE._is_crawl_target_safe(target_url) is False


def test_crawl_target_allows_public_address(monkeypatch):
    """DNS가 공인 주소만 반환하면 안전하다고 판정해야 한다."""
    # 실제 DNS 조회 대신 고정된 공인 IP를 반환하도록 치환한다.
    monkeypatch.setattr(
        MODULE.socket,
        "getaddrinfo",
        lambda host, port: [(None, None, None, None, ("8.8.8.8", 0))],
    )
    assert MODULE._is_crawl_target_safe("https://example.com/terms") is True


def test_crawl_target_blocks_when_any_resolved_ip_is_internal(monkeypatch):
    """DNS 재바인딩 대비: 여러 주소 중 하나라도 내부망이면 차단해야 한다."""
    monkeypatch.setattr(
        MODULE.socket,
        "getaddrinfo",
        lambda host, port: [
            (None, None, None, None, ("8.8.8.8", 0)),
            (None, None, None, None, ("10.0.0.1", 0)),
        ],
    )
    assert MODULE._is_crawl_target_safe("https://example.com/") is False


# ------------------------------------------------------------------------------
# API 키 인증 테스트
# ------------------------------------------------------------------------------
def test_require_valid_api_key_rejects_when_unset(monkeypatch):
    """서버 키가 비어 있으면(기본값 거부) 503으로 막아야 한다."""
    monkeypatch.setattr(MODULE.config, "SPS_MAIN_ORCHESTRATOR_API_KEY", "")
    with pytest.raises(HTTPException) as exc_info:
        MODULE._require_valid_api_key("Bearer anything")
    assert exc_info.value.status_code == 503


def test_require_valid_api_key_rejects_wrong_token(monkeypatch):
    """키가 설정되어 있어도 값이 다르면 401로 막아야 한다."""
    monkeypatch.setattr(MODULE.config, "SPS_MAIN_ORCHESTRATOR_API_KEY", "correct-secret")
    with pytest.raises(HTTPException) as exc_info:
        MODULE._require_valid_api_key("Bearer wrong-secret")
    assert exc_info.value.status_code == 401


def test_require_valid_api_key_rejects_missing_header(monkeypatch):
    """Authorization 헤더 자체가 없으면 401로 막아야 한다."""
    monkeypatch.setattr(MODULE.config, "SPS_MAIN_ORCHESTRATOR_API_KEY", "correct-secret")
    with pytest.raises(HTTPException) as exc_info:
        MODULE._require_valid_api_key(None)
    assert exc_info.value.status_code == 401


def test_require_valid_api_key_accepts_matching_token(monkeypatch):
    """올바른 Bearer 토큰이면 예외 없이 통과해야 한다."""
    monkeypatch.setattr(MODULE.config, "SPS_MAIN_ORCHESTRATOR_API_KEY", "correct-secret")
    MODULE._require_valid_api_key("Bearer correct-secret")  # 예외가 없으면 통과


def test_graph_preserves_direct_answer_when_no_tool_was_called(monkeypatch):
    """도구 결과가 없으면 verifier가 정상 답변을 도구 보고서로 덮어쓰지 않아야 한다."""
    created_models = []

    class FakeModel:
        def __init__(self, *args, **kwargs):
            self.verifier_calls = 0
            created_models.append(self)

        def bind_tools(self, tools):
            class BoundModel:
                async def ainvoke(self, messages):
                    return AIMessage(content="SYSTEMD_RUN_OK")

            return BoundModel()

        async def ainvoke(self, messages):
            self.verifier_calls += 1
            return AIMessage(content="잘못 재작성된 도구 결과 보고")

    monkeypatch.setattr(MODULE, "ChatGoogleGenerativeAI", FakeModel)
    graph = MODULE.create_agent_graph()
    result = asyncio.run(
        graph.ainvoke({"messages": [HumanMessage(content="도구 호출 없이 상태 확인")]})
    )

    assert result["messages"][-1].content == "SYSTEMD_RUN_OK"
    assert created_models[0].verifier_calls == 0
