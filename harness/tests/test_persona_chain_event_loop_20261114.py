"""페르소나 수리 체인 'Event loop is closed' 재현·수정 테스트 (2026-11-14, LuckyBoys: 재현 테스트 → 최소 수정).

재현(메리츠 job 5acd70ce…, 공급자 openai):
    run_step 은 단계마다 asyncio.run() 을 따로 불러 매번 새 이벤트 루프를 만들고 닫았다.
    langchain-openai 는 비동기 HTTP 클라이언트를 프로세스 전체에서 재사용(캐시)하므로,
    첫 단계는 성공하고 두 번째 단계에서 '이미 닫힌 첫 루프'에 묶인 연결을 쓰다 RuntimeError: Event loop is closed.
수정: run_step 의 비동기 실행을 프로세스 안에서 유지되는 이벤트 루프 하나(_run_async)로 통일.
네트워크·LLM 을 쓰지 않는다(가짜 모델·그래프·도구 로더로 대체).
"""
import asyncio

import pytest
from langchain_core.messages import AIMessage

from harness.mcp.agents import persona_repair_chain as chain
from harness.mcp.agents import source_partner_agent as agent


class _LoopBoundClient:
    """처음 쓰인 이벤트 루프에 묶이는 클라이언트(httpx 연결 풀과 같은 성질)를 흉내 낸다."""

    def __init__(self):
        self.loop = None

    async def call(self):
        if self.loop is None:
            self.loop = asyncio.get_running_loop()          # 첫 호출 루프에 묶임
        future = asyncio.get_running_loop().create_future()
        # 묶인 루프로 콜백을 보낸다. 그 루프가 닫혔으면 여기서 'Event loop is closed'
        self.loop.call_soon_threadsafe(lambda: None)
        future.set_result("ok")
        return await future


@pytest.fixture
def fake_runtime(monkeypatch):
    """LLM·MCP 없이 run_step 을 돌리기 위한 가짜 부품. 공유 클라이언트는 프로세스 캐시처럼 하나만 쓴다."""
    shared = _LoopBoundClient()

    class _Graph:
        async def ainvoke(self, state, config=None):
            await shared.call()
            return {"messages": [AIMessage(content="ok")]}

    async def _no_tools(*, source_write_confirmed):
        return []

    monkeypatch.setattr(agent, "_build_model", lambda: object())
    monkeypatch.setattr(agent, "_load_sps_mcp_tools", _no_tools)
    monkeypatch.setattr(agent, "build_source_partner_graph", lambda **kwargs: _Graph())
    return shared


def test_two_steps_reuse_loop_bound_client_without_closed_loop_error(fake_runtime):
    # 재현: 수정 전에는 두 번째 단계에서 RuntimeError: Event loop is closed
    first = chain.run_step("ARCHITECT", "sys", "task", "none")
    second = chain.run_step("REVIEWER", "sys", "task", "none")
    assert first["output"] == "ok" and second["output"] == "ok"


def test_run_async_keeps_one_loop_across_calls():
    # 같은 프로세스 안에서는 같은 루프를 계속 쓴다(캐시된 클라이언트가 안전)
    async def current_loop():
        return asyncio.get_running_loop()

    assert chain._run_async(current_loop()) is chain._run_async(current_loop())


@pytest.mark.parametrize("bad", [None, 123, "coro", lambda: None])
def test_run_async_rejects_non_coroutine(bad):
    # 잘못된 입력: 코루틴이 아니면 실행하지 않고 즉시 오류
    with pytest.raises((TypeError, ValueError)):
        chain._run_async(bad)
