"""스스로 고치는 리뷰 앱의 LLM 선택(provider) 테스트 (2026-11-10).

검증: 기본 provider는 gemini / ollama 선택 시 Ollama CLI 사용 / 워커도 같은 CLI 사용 /
      등록되지 않은 provider·잘못된 타입은 시작 전 거부.
LLM·systemd는 실행하지 않는다(dry-run과 subprocess.run 대역).
"""
import asyncio
import hashlib
import json
from types import SimpleNamespace

import pytest

from harness.mcp.tools import multi_persona_tools as review

TARGET = "FastAPI/LangGraph/multi_persona/review_contract.py"


def test_default_provider_is_gemini():
    plan = asyncio.run(review.review_python_source(TARGET))
    assert plan["provider"] == review.project_config.MULTI_PERSONA_REVIEW_DEFAULT_PROVIDER == "gemini"
    assert plan["review_command"][2].endswith("multi_persona_agent_gemini.py")
    # 2026-11-10: 공용 CLI는 --provider로 LLM을 고른다.
    assert plan["review_command"][3:5] == ["--provider", "gemini"]


def test_ollama_provider_uses_shared_cli_with_tuning():
    """2026-11-10 경로 통일: ollama도 공용 CLI + --provider ollama(llm_provider의 11-01 튜닝 사용)."""
    plan = asyncio.run(review.review_python_source(TARGET, provider="ollama"))
    assert plan["provider"] == "ollama"
    assert plan["review_command"][2].endswith("multi_persona_agent_gemini.py")
    assert plan["review_command"][3:5] == ["--provider", "ollama"]


def test_ollama_gemma_keeps_dedicated_cli():
    plan = asyncio.run(review.review_python_source(TARGET, provider="ollama_gemma"))
    assert plan["review_command"][2].endswith("multi_persona_agent_Ollama_Gemma4_e4b.py")
    assert "--output-dir" in plan["review_command"]  # 같은 출력 계약
    assert "--provider" not in plan["review_command"]  # 전용 CLI는 추가 인자 없음


@pytest.mark.parametrize("name", ["openai", "claude"])
def test_openai_and_claude_share_generic_cli(name):
    """ChatGPT·Claude는 같은 공용 CLI를 쓰고 --provider만 다르다(키·패키지는 실행 시점에 확인)."""
    plan = asyncio.run(review.review_python_source(TARGET, provider=name))
    assert plan["review_command"][2].endswith("multi_persona_agent_gemini.py")
    assert plan["review_command"][3:5] == ["--provider", name]


@pytest.mark.parametrize("bad", ["chatgpt", "", 1, "GEMINI", None.__class__.__name__])
def test_unknown_provider_rejected(bad):
    """잘못된 입력: 미등록 이름, 빈 문자열, 숫자, 대소문자 다름."""
    with pytest.raises(ValueError):
        asyncio.run(review.review_python_source(TARGET, provider=bad))


def test_worker_uses_saved_provider(tmp_path, monkeypatch):
    """워커는 request.json에 저장된 provider의 CLI로 실행한다."""
    monkeypatch.setattr(review, "PROJECT_ROOT", tmp_path)
    source = tmp_path / "sample.py"
    source.write_text("X = 1\n", encoding="utf-8")
    job_id = "d" * 32
    request_path, _ = review._job_files(job_id)
    request_path.parent.mkdir(parents=True)
    request_path.write_text(json.dumps({
        "source_path": "sample.py", "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "timeout_seconds": 60, "output_limit": 100, "error_path": None,
        # 2026-11-10: 전용 CLI 이름이 ollama_gemma로 바뀜(ollama는 공용 CLI로 통일)
        "auto_apply": False, "test_paths": [], "provider": "ollama_gemma"}), encoding="utf-8")
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")
    monkeypatch.setattr(review.subprocess, "run", run)
    review._run_review_job(job_id)
    assert calls[0][2].endswith("multi_persona_agent_Ollama_Gemma4_e4b.py")
