"""LLM 크레딧 부족(402)·키 오류(401)가 나면 바로 멈추고 보고하는지 확인하는 재현 테스트 (2026-11-14, LuckyBoys 요청).

사고(fresh20 Gemini 실행 중)
- Gemini가 "402 RESOURCE_EXHAUSTED ... Your prepayment credits are depleted."를 돌려줬는데
  리뷰 CLI(safe_invoke_llm)는 "할당량 초과, 잠시 후 다시 시도" 경고 메시지를 답처럼 돌려주고
  다른 페르소나 노드를 계속 불렀다(job 하나에 402 호출 8번).
- 앱(_run_feedback_rounds)은 이 실패를 '출력 검사 거부'로 보고 같은 라운드를 다시 시도했다.
기대
- 공통 판정(common_function.fatal_provider_error_reason): 402·크레딧 소진·401 키 오류는 '치명적'으로 판정,
  429 같은 일시 오류와 일반 문장은 치명적이 아님. 문자열이 아닌 입력은 ValueError.
- CLI 정지(common_function.stop_on_fatal_provider_error): 치명적이면 표시 줄을 출력하고 SystemExit(설정 종료 코드).
- 앱: 리뷰 출력에 표시 줄이 있으면 provider_fatal_error로 보고하고, 재시도·다음 라운드를 하지 않는다.
LLM·systemd는 실행하지 않는다(subprocess.run 대역).
"""
import hashlib
import json
from types import SimpleNamespace

import pytest

import config as project_config
from common import common_function as cf
from harness.mcp.tools import multi_persona_tools as review

# 실제 로그에서 가져온 오류 문장(비밀값 없음)
CREDIT_402 = ("Error calling model 'gemini-3.8-flash' (RESOURCE_EXHAUSTED): 402 RESOURCE_EXHAUSTED. "
              "{'error': {'code': 402, 'message': 'Your prepayment credits are depleted.'}}")
KEY_401 = "Error code: 401 - {'error': {'code': 'invalid_api_key', 'message': 'Incorrect API key provided'}}"
RATE_429 = "429 Too Many Requests: rate limit, retry after 10s"


# ------------------------------------------------------------------ 1) 공통 판정 함수
def test_reproduce_credit_402_is_fatal():
    """재현: 크레딧 소진 402는 치명적 오류로 판정되어야 한다(사고 때는 '잠시 후 다시 시도'로 처리)."""
    assert "402" in cf.fatal_provider_error_reason(CREDIT_402)


def test_invalid_api_key_401_is_fatal():
    """키 오류도 다시 불러 봐야 소용없으므로 치명적."""
    assert "401" in cf.fatal_provider_error_reason(KEY_401)


@pytest.mark.parametrize("text", [RATE_429, "", "정상 답변 402줄 중 1줄 수정"])
def test_transient_or_normal_text_is_not_fatal(text):
    """일시 오류(429)와 일반 문장(숫자 402가 섞여도)은 치명적이 아님 → None."""
    assert cf.fatal_provider_error_reason(text) is None


@pytest.mark.parametrize("bad", [None, 402, b"402 RESOURCE_EXHAUSTED"])
def test_bad_input_type_raises(bad):
    """잘못된 입력: 문자열이 아니면 ValueError(조용히 넘어가지 않음)."""
    with pytest.raises(ValueError):
        cf.fatal_provider_error_reason(bad)


def test_stop_on_fatal_prints_marker_and_exits(capsys):
    """CLI 정지: 표시 줄을 출력하고 설정된 종료 코드로 끝난다."""
    with pytest.raises(SystemExit) as stopped:
        cf.stop_on_fatal_provider_error(CREDIT_402, "router")
    assert stopped.value.code == project_config.MULTI_PERSONA_FATAL_PROVIDER_EXIT_CODE
    out = capsys.readouterr().out
    assert out.startswith(project_config.MULTI_PERSONA_FATAL_PROVIDER_MARKER)
    assert "router" in out and "402" in out


def test_stop_on_non_fatal_returns_none():
    """일시 오류는 멈추지 않고 None(기존 처리 그대로)."""
    assert cf.stop_on_fatal_provider_error(RATE_429, "router") is None


# ------------------------------------------------------------------ 2) 앱(_run_review_job / 재시도 라운드)
ORIGINAL = "def keep():\n    return 1\n"
FIRST = "def keep():\n    return 2\n"
VERIFIED = "[출력 검증] 오류=[], 보고서=x\n[최종 검증된 답변]:\n본문\n"
MARKER_LINE = (project_config.MULTI_PERSONA_FATAL_PROVIDER_MARKER
               + " LLM 크레딧 부족(402) — 리뷰를 멈춥니다. 노드=router\n")


@pytest.fixture
def job(tmp_path, monkeypatch):
    """임시 저장소에 원본·테스트·request.json을 만든다."""
    monkeypatch.setattr(review, "PROJECT_ROOT", tmp_path)
    source = tmp_path / "sample.py"
    source.write_text(ORIGINAL, encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    job_id = "f" * 32
    request_path, _ = review._job_files(job_id)
    request_path.parent.mkdir(parents=True)
    request_path.write_text(json.dumps({
        "source_path": "sample.py", "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "timeout_seconds": 600, "output_limit": 1000, "error_path": None,
        "auto_apply": True, "test_paths": ["tests/test_sample.py"]}), encoding="utf-8")
    return source, job_id


def fake_run(fatal_at):
    """리뷰 CLI 호출 번호 fatal_at에서 치명적 오류(표시 줄 + 종료 코드)를 낸다. pytest는 항상 실패(재시도 유도)."""
    calls = {"review": []}

    def run(command, **_kwargs):
        if "pytest" in command:
            xml = next(arg for arg in command if arg.startswith("--junitxml=")).split("=", 1)[1]
            review.Path(xml).write_text('<testsuite><testcase classname="t" name="test_ok">'
                                        '<failure message="keep() -&gt; 2"/></testcase></testsuite>',
                                        encoding="utf-8")
            return SimpleNamespace(returncode=1, stdout=b"pytest", stderr=b"")
        number = len(calls["review"])
        calls["review"].append(command)
        if number == fatal_at:
            return SimpleNamespace(returncode=project_config.MULTI_PERSONA_FATAL_PROVIDER_EXIT_CODE,
                                   stdout=MARKER_LINE.encode(), stderr=b"")
        out_dir = review.Path(command[command.index("--output-dir") + 1])
        (out_dir / "proposed.py").write_text(FIRST, encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout=VERIFIED.encode(), stderr=b"")

    run.calls = calls
    return run


def _run(job, monkeypatch, fatal_at):
    _source, job_id = job
    run = fake_run(fatal_at)
    monkeypatch.setattr(review.subprocess, "run", run)
    monkeypatch.setattr(review.auto_apply.subprocess, "run", run)
    monkeypatch.setattr(review.project_config, "MULTI_PERSONA_AUTO_APPLY_UNVERIFIED_RETRIES", 1)
    review._run_review_job(job_id)
    return run, json.loads(review._job_files(job_id)[1].read_text(encoding="utf-8"))


def test_reproduce_fatal_in_first_review_is_reported(job, monkeypatch):
    """재현: 1차 리뷰에서 크레딧 부족 → 결과에 provider_fatal_error로 보고, 재시도 없음, 원본 그대로."""
    run, data = _run(job, monkeypatch, fatal_at=0)
    source, _ = job
    assert len(run.calls["review"]) == 1
    assert "402" in data["provider_fatal_error"]
    assert data["success"] is False and data["auto_apply_rounds"] is None
    assert data["auto_apply_result"]["reason"] == data["provider_fatal_error"]
    assert source.read_text(encoding="utf-8") == ORIGINAL


def test_reproduce_fatal_in_retry_round_stops_without_same_round_retry(job, monkeypatch):
    """재현: 2차 라운드에서 크레딧 부족 → 같은 라운드 재시도·3차 없이 멈추고 그 라운드에 이유를 남긴다."""
    run, data = _run(job, monkeypatch, fatal_at=1)
    assert len(run.calls["review"]) == 2
    last = data["auto_apply_rounds"][-1]
    assert last["round"] == 2 and "402" in last["provider_fatal_error"]
    assert "402" in data["provider_fatal_error"]


def test_no_fatal_keeps_old_behavior(job, monkeypatch):
    """치명적 오류가 없으면 예전처럼 라운드를 진행하고 provider_fatal_error는 None."""
    run, data = _run(job, monkeypatch, fatal_at=-1)
    assert len(run.calls["review"]) == project_config.MULTI_PERSONA_AUTO_APPLY_MAX_ROUNDS
    assert data["provider_fatal_error"] is None


# ------------------------------------------------------------------ 3) LangGraph 안에서도 그래프 전체가 멈추는지
GRAPH_CHILD = r'''
import sys
sys.path.insert(0, ROOT)
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from common.common_function import stop_on_fatal_provider_error
class S(TypedDict, total=False):
    a: int
    b: int
def credit_node(state):
    try:
        raise RuntimeError("402 RESOURCE_EXHAUSTED. Your prepayment credits are depleted.")
    except Exception as e:  # safe_invoke_llm과 같은 모양: 일반 except 안에서 정지 함수 호출
        stop_on_fatal_provider_error(str(e), "credit_node")
        return {"a": 1}
def after(state):
    print("after 실행됨")
    return {}
g = StateGraph(S)
g.add_node("credit_node", credit_node)
g.add_node("other_node", lambda state: {"b": 1})
g.add_node("after", after)
g.add_edge(START, "credit_node")
g.add_edge(START, "other_node")
g.add_edge(["credit_node", "other_node"], "after")
g.add_edge("after", END)
try:
    g.compile().invoke({})
except Exception as e:  # CLI main처럼 일반 예외를 잡아도 SystemExit는 빠져나가야 한다
    print("일반 예외로 잡힘(실패)", type(e).__name__)
print("그래프가 끝까지 실행됨(실패)")
'''


def test_fatal_stop_ends_whole_langgraph_process():
    """병렬 노드 중 하나가 402로 멈추면 다음 노드 없이 프로세스가 설정 종료 코드로 끝나야 한다(실제 LLM 없음)."""
    import subprocess, sys
    root = str(review.Path(project_config.__file__).resolve().parent)
    done = subprocess.run([sys.executable, "-c", f"ROOT = {root!r}\n" + GRAPH_CHILD],
                          capture_output=True, text=True, timeout=120)
    assert done.returncode == project_config.MULTI_PERSONA_FATAL_PROVIDER_EXIT_CODE, done.stderr[-500:]
    assert done.stdout.startswith(project_config.MULTI_PERSONA_FATAL_PROVIDER_MARKER)
    assert "after 실행됨" not in done.stdout and "(실패)" not in done.stdout
