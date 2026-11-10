"""공용 LLM 팩토리 common/llm_provider.py 테스트 (2026-11-10).

네트워크·실제 LLM 호출은 하지 않는다(모델 객체 생성만, 키는 가짜 값).
"""
import pytest

from common import llm_provider


def test_registered_providers():
    assert llm_provider.available_providers() == ["claude", "gemini", "ollama", "openai"]


def test_gemini_model_is_created_with_key(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "fake-key-for-test")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    model = llm_provider.create_chat_model("gemini", temperature=0.1)
    assert type(model).__name__ == "ChatGoogleGenerativeAI"


def test_openai_requires_model_name(monkeypatch):
    """모델 이름을 추측하지 않는다: OPENAI_MODEL이 없으면 거부."""
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-test")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    with pytest.raises(ValueError, match="OPENAI_MODEL"):
        llm_provider.create_chat_model("openai")


def test_openai_model_is_created(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-test")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    assert type(llm_provider.create_chat_model("openai")).__name__ == "ChatOpenAI"


def test_missing_key_is_reported_without_value(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        llm_provider.create_chat_model("openai")


def test_claude_reports_missing_package_or_key(monkeypatch):
    """langchain_anthropic 미설치·키 없음 상태에서는 명확한 오류로 즉시 실패한다."""
    monkeypatch.setenv("ANTHROPIC_MODEL", "test-model")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValueError):
        llm_provider.create_chat_model("claude")


def test_ollama_uses_shared_base_url(monkeypatch):
    """2026-11-10: 실제 함수 계약(고정 주소, 후보, 대기초 → {"base_url"})대로 불리는지 확인한다."""
    monkeypatch.setenv("OLLAMA_MODEL", "test-model")
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    import common.common_function as common_function
    seen = {}

    def fake(pinned, candidates, timeout_seconds):
        seen.update(pinned=pinned, candidates=candidates, timeout=timeout_seconds)
        return {"base_url": "http://gpu:11434"}
    monkeypatch.setattr(common_function, "resolve_ollama_base_url", fake)
    model = llm_provider.create_chat_model("ollama")
    assert type(model).__name__ == "ChatOllama"
    assert model.base_url == "http://gpu:11434"
    assert seen["candidates"] == llm_provider.project_config.SPS_SOURCE_PARTNER_OLLAMA_CANDIDATES
    # 2026-11-01 튜닝 반영: 응답 대기 시간
    assert model.client_kwargs["timeout"] == float(llm_provider.project_config.SPS_SOURCE_PARTNER_OLLAMA_TIMEOUT_SECONDS)


def test_ollama_default_model_and_context_env(monkeypatch):
    """OLLAMA_MODEL이 없으면 튜닝 모델(SPS_SOURCE_PARTNER_OLLAMA_MODEL), OLLAMA_CONTEXT_LENGTH가 있으면 그 값."""
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.setenv("OLLAMA_CONTEXT_LENGTH", "4096")
    import common.common_function as common_function
    monkeypatch.setattr(common_function, "resolve_ollama_base_url", lambda *a: {"base_url": "http://x:11434"})
    model = llm_provider.create_chat_model("ollama")
    assert model.model == llm_provider.project_config.SPS_SOURCE_PARTNER_OLLAMA_MODEL
    assert model.num_ctx == 4096


@pytest.mark.parametrize("bad", ["chatgpt", "", None, 3])
def test_unknown_provider_rejected(bad):
    with pytest.raises(ValueError):
        llm_provider.create_chat_model(bad)
