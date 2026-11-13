"""PARTNER 모델 공급자에 openai·claude 추가 테스트 (2026-11-12, LuckyBoys: Gemini 402 크레딧 소진 → openai/claude 먼저).

재현: 수정 전 _build_model 은 gemini / ollama 만 받아 'openai'·'claude' 는 ValueError 였다
      (메리츠 자기 수리 job da702ac6… 의 수리 2라운드가 Gemini 402 로 실패해도 다른 공급자로 바꿀 수 없었다).
수정: openai·claude 는 공용 팩토리 common.llm_provider.create_chat_model(provider, temperature=0) 로 만든다
      (키·모델 이름은 환경변수에서만 읽고 추측하지 않는다 — 공용 모듈 규칙 그대로).
네트워크·실제 키를 쓰지 않는다(팩토리를 가짜로 바꿔치기).
"""
import pytest

from common import llm_provider
from harness.mcp.agents import source_partner_agent as agent


@pytest.mark.parametrize("provider", ["openai", "claude"])
def test_build_model_uses_common_factory_for_openai_and_claude(provider, monkeypatch):
    calls = []
    monkeypatch.setattr(agent.project_config, "SPS_SOURCE_PARTNER_MODEL_PROVIDER", provider)
    monkeypatch.setattr(llm_provider, "create_chat_model",
                        lambda name, temperature=0.2, max_retries=2: calls.append((name, temperature)) or f"model:{name}")
    assert agent._build_model() == f"model:{provider}"
    assert calls == [(provider, 0)]          # PARTNER 는 기존과 같이 temperature 0 을 요청한다


@pytest.mark.parametrize("provider", ["", "gpt", "anthropic", "OPENAI ", None])
def test_build_model_rejects_unknown_provider(provider, monkeypatch):
    # 잘못된 입력: 등록되지 않은 이름은 조용히 다른 모델로 대체하지 않고 ValueError
    monkeypatch.setattr(agent.project_config, "SPS_SOURCE_PARTNER_MODEL_PROVIDER", provider)
    with pytest.raises(ValueError, match="gemini.*ollama.*openai.*claude"):
        agent._build_model()


def test_build_model_reports_missing_key_clearly(monkeypatch):
    # 팩토리의 명확한 오류(키 없음)를 그대로 전달한다(키 값은 메시지에 없음)
    monkeypatch.setattr(agent.project_config, "SPS_SOURCE_PARTNER_MODEL_PROVIDER", "claude")

    def fail(name, temperature=0.2, max_retries=2):
        raise ValueError("claude: none of ANTHROPIC_API_KEY is set")

    monkeypatch.setattr(llm_provider, "create_chat_model", fail)
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        agent._build_model()
