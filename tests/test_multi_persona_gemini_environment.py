"""Gemini 키 경계 회귀 테스트: 보호 파일은 에이전트가 읽지 않아야 한다."""
import ast
import os
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "FastAPI/LangGraph/multi_persona/multi_persona_agent_gemini.py"


def _initialize():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "initialize_llm")
    namespace = {
        "os": os,
        "SecretStr": lambda value: value,
        "ChatGoogleGenerativeAI": lambda **kwargs: kwargs,
    }
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(SOURCE), "exec"), namespace)
    return namespace["initialize_llm"]


@pytest.mark.parametrize("values", [{}, {"GEMINI_API_KEY": " ", "GOOGLE_API_KEY": " "}])
def test_missing_or_blank_key_rejected(values):
    # 키가 없으면 모델 생성 전에 명확히 실패해야 한다.
    with patch.dict(os.environ, values, clear=True):
        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            _initialize()()


@pytest.mark.parametrize("name", ["GEMINI_API_KEY", "GOOGLE_API_KEY"])
def test_injected_runtime_key_accepted(name):
    # systemd EnvironmentFile/실행 환경이 주입한 키만 사용하며 외부 호출은 하지 않는다.
    with patch.dict(os.environ, {name: "test-placeholder"}, clear=True):
        result = _initialize()(temp=0.1)
        assert result["api_key"] == "test-placeholder"


def test_agent_source_does_not_reference_protected_secret_path():
    # AI 에이전트 소스가 보호 파일 경로·dotenv_values·Path.open을 참조하지 않는지 확인한다.
    source = SOURCE.read_text(encoding="utf-8")
    assert "/etc/sps-harness/secrets.env" not in source
    assert "dotenv_values" not in source
    assert "secret_path.open" not in source
