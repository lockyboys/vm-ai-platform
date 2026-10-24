"""모델 호출 없이 실제 팩토리의 컨텍스트·출력 예산과 CLI 연결을 검증합니다."""
import ast
import os
from pathlib import Path
from types import SimpleNamespace
import pytest
BASE = Path(__file__).resolve().parents[1] / "FastAPI/LangGraph/multi_persona"
AGENT = BASE / "multi_persona_agent_Ollama_Gemma4_e4b.py"

def factory(config_model=None):
    tree = ast.parse(AGENT.read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "initialize_llm")
    fake = lambda **kwargs: kwargs
    settings = {"MULTI_PERSONA_OLLAMA_CONTEXT": 65536, "MULTI_PERSONA_OLLAMA_OUTPUT": 32768}
    if config_model is not None:
        settings["MULTI_PERSONA_OLLAMA_MODEL"] = config_model
    scope = {"os": os, "Optional": __import__("typing").Optional, "ChatOllama": fake, "project_config": SimpleNamespace(**settings)}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(AGENT), "exec"), scope)
    return scope["initialize_llm"]

def test_request_explicit_context_and_output_budget(monkeypatch):
    for name in ("OLLAMA_CONTEXT_LENGTH", "OLLAMA_NUM_PREDICT", "OLLAMA_TIMEOUT"):
        monkeypatch.delenv(name, raising=False)
    result = factory()()
    assert result["num_ctx"] == 65536
    assert result["num_predict"] == 32768
    assert result["client_kwargs"]["timeout"] == 3000

def test_plan_budget_and_default_reasoning(monkeypatch):
    # 짧은 단계의 출력 상한과 dev의 기존 추론 모드 설정을 확인합니다.
    monkeypatch.delenv("OLLAMA_NUM_PREDICT", raising=False)
    factory_fn = factory()
    assert factory_fn(output_limit=512)["num_predict"] == 512
    assert factory_fn(output_limit=2048)["num_predict"] == 2048
    assert factory_fn()["reasoning"] is None

def test_invalid_context_is_rejected(monkeypatch):
    monkeypatch.setenv("OLLAMA_CONTEXT_LENGTH", "invalid")
    with pytest.raises(ValueError):
        factory()()

def test_run_override_is_preserved(monkeypatch):
    monkeypatch.setenv("OLLAMA_CONTEXT_LENGTH", "98304")
    assert factory()()["num_ctx"] == 98304

def test_host_config_selects_model_without_changing_dev_default(monkeypatch):
    # PC/dev는 기존 기본값, AI 서버는 자체 config.py 모델명을 사용합니다.
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    assert factory()()["model"] == "gemma4:e4b"
    assert factory("gemma4:12b-it-q4_K_M")()["model"] == "gemma4:12b-it-q4_K_M"

def test_explicit_model_environment_has_priority(monkeypatch):
    # 실행자가 환경 변수를 주면 호스트 설정과 무관하게 해당 모델을 사용합니다.
    monkeypatch.setenv("OLLAMA_MODEL", "gemma4:e4b")
    assert factory("gemma4:12b-it-q4_K_M")()["model"] == "gemma4:e4b"

def test_invalid_host_model_does_not_silently_fallback(monkeypatch):
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    with pytest.raises(AttributeError):
        factory(123)()

@pytest.mark.parametrize("name", ["multi_persona_agent_gemini.py", AGENT.name])
def test_cli_uses_contract_and_keeps_error_input(name):
    tree = ast.parse((BASE / name).read_text())
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
    assert any(n.func.id == "build_review_query" and isinstance(n.args[2], ast.Name) and n.args[2].id == "previous_error" for n in calls)
    assert any(n.func.id == "normalize_plan" for n in calls)
    assert any(n.func.id == "validate_review" for n in calls)
