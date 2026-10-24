"""source_audit 래퍼가 호출 클라이언트 이름(clientInfo.name)을 로그로 남기는지 검증한다.

목적: AI별 user_id 설계 전에, 각 앱(Claude/ChatGPT/Codex/Gemini)이 보내는 clientInfo 값을
      서버 로그에서 수집하기 위한 최소 변경의 회귀 테스트(2026-10-24 LuckyBoys 승인).
주의: 실제 MCP 서버·DB·Verified SQL은 쓰지 않는다(_record를 가짜로 교체).
"""
from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

from harness.mcp import source_audit


def _fake_source_read(path: str) -> dict:
    """감사 대상 이름(source_read)을 가진 가짜 도구."""
    return {"path": path}


_fake_source_read.__name__ = "source_read"


@pytest.fixture
def wrapped(monkeypatch):
    # 기록 단계는 이 테스트 범위가 아니므로 아무것도 하지 않게 바꾼다.
    monkeypatch.setattr(source_audit, "_record", lambda *args, **kwargs: None)
    return source_audit.source_audit_recorded(_fake_source_read)


def _set_request_context(monkeypatch, client_info):
    """mcp 요청 컨텍스트(ContextVar)를 가짜 세션으로 채운다."""
    from mcp.server.lowlevel import server as lowlevel_server

    session = SimpleNamespace(client_params=SimpleNamespace(clientInfo=client_info))
    token = lowlevel_server.request_ctx.set(SimpleNamespace(session=session))
    return lowlevel_server.request_ctx, token


def test_logs_client_name_and_version(monkeypatch, wrapped, caplog):
    ctx_var, token = _set_request_context(monkeypatch, SimpleNamespace(name="claude-ai", version="0.1.0"))
    try:
        with caplog.at_level(logging.INFO, logger=source_audit.LOGGER.name):
            assert wrapped("a.py") == {"path": "a.py"}  # 원래 결과는 그대로
    finally:
        ctx_var.reset(token)
    assert "client_name=claude-ai" in caplog.text
    assert "client_version=0.1.0" in caplog.text
    assert "tool=source_read" in caplog.text


def test_missing_context_does_not_break_tool(wrapped, caplog):
    # 요청 컨텍스트가 없어도(테스트·내부 호출) 도구 결과는 정상이고 unknown으로만 남긴다.
    with caplog.at_level(logging.INFO, logger=source_audit.LOGGER.name):
        assert wrapped("b.py") == {"path": "b.py"}
    assert "client_name=unknown" in caplog.text


def test_missing_client_info_does_not_break_tool(monkeypatch, wrapped, caplog):
    # 초기화 정보에 clientInfo가 없어도 실패하지 않는다(잘못된 입력 방어).
    ctx_var, token = _set_request_context(monkeypatch, None)
    try:
        with caplog.at_level(logging.INFO, logger=source_audit.LOGGER.name):
            assert wrapped("c.py") == {"path": "c.py"}
    finally:
        ctx_var.reset(token)
    assert "client_name=unknown" in caplog.text
