"""스스로 고치는 앱의 Ollama 사전 점검 + '모델 없음(404)' 즉시 정지 테스트 (2026-11-21, LuckyBoys 선택 1안).

사고(2026-11-16~18, 메모리 에이전트 Ollama 시험)
- 노트북 터널이 끊긴 채 시작하자 자동 선택이 개발 서버 CPU Ollama(127.0.0.1:11434)로 붙어 8번 호출이 모두
  시간 초과 → 40분 낭비(job 86dcf050).
- AI 서버 IP가 바뀔 때마다 같은 일이 생길 수 있고, 12b 모델은 노트북에 없어 '모델 없음'이 날 수 있다.
기대
- Ollama 공급자는 1라운드 리뷰 전·각 피드백 라운드 전에 '연결 주소·모델'을 점검하고, 문제가 있으면 AI를 부르지 않고
  바로 멈춘 뒤 이유(터널/IP/모델 확인 안내)를 provider_fatal_error·stop_reason으로 남긴다.
- Ollama 404 'model ... not found, try pulling it first'는 치명 오류로 바로 멈춘다.
- 다른 공급자(gemini 등)는 점검하지 않는다(네트워크 호출 없음).
LLM·네트워크는 실행하지 않는다(대역 함수).
"""
import pytest

from common import common_function as cf
from harness.mcp.tools import multi_persona_tools as review
from harness.tests.test_review_feedback_rounds import FIRST, GOOD, fake_run, result
from harness.tests.test_selffix_focus_salvage_timeout import _make_job, _patch

GPU = "http://127.0.0.1:11435"          # AI 서버 터널(정상 경로)
CPU = "http://127.0.0.1:11434"          # 개발 서버 CPU Ollama(리뷰에 쓰면 시간 초과)


def _env(monkeypatch, chosen=GPU, models=("gemma4:12b-it-q4_K_M",), model="gemma4:12b-it-q4_K_M"):
    """주소 자동 선택·모델 목록 조회를 대역으로 바꾼다. chosen이 예외면 '후보 전부 응답 없음'."""
    monkeypatch.setenv("OLLAMA_MODEL", model)

    def resolve(*_args, **_kwargs):
        if isinstance(chosen, Exception):
            raise chosen
        return {"base_url": chosen, "mode": "auto", "tried": []}

    def tags(url, _timeout):
        if isinstance(models, Exception):
            raise models
        return list(models)

    monkeypatch.setattr(review, "resolve_ollama_base_url", resolve)
    monkeypatch.setattr(review, "list_ollama_models", tags)


def test_non_ollama_provider_is_not_checked(monkeypatch):
    """gemini 등은 점검하지 않는다(대역이 불리면 실패)."""
    def boom(*_a, **_k):
        raise AssertionError("network check must not run for gemini")
    monkeypatch.setattr(review, "resolve_ollama_base_url", boom)
    assert review._ollama_preflight("gemini") is None
    assert review._ollama_preflight(None) is None            # 기본 공급자(gemini)


def test_reproduce_cpu_fallback_is_rejected(monkeypatch):
    """재현: 터널이 끊겨 개발 서버 CPU Ollama로만 붙으면 바로 멈추고 터널·IP 확인을 안내한다."""
    _env(monkeypatch, chosen=CPU)
    reason = review._ollama_preflight("ollama")
    assert reason.startswith("[환경 점검 실패]") and "터널" in reason and "IP" in reason


def test_no_candidate_responds(monkeypatch):
    """후보 주소가 하나도 응답하지 않으면(AI 서버 꺼짐 등) 멈춘다."""
    _env(monkeypatch, chosen=RuntimeError("no ollama candidate responded"))
    assert "응답하지" in review._ollama_preflight("ollama")


def test_reproduce_missing_model_is_rejected(monkeypatch):
    """재현: 연결된 Ollama에 설정한 모델이 없으면(노트북에 12b 없음) pull 안내와 함께 멈춘다."""
    _env(monkeypatch, models=("gemma4:e4b",))
    reason = review._ollama_preflight("ollama")
    assert "gemma4:12b-it-q4_K_M" in reason and "ollama pull" in reason


@pytest.mark.parametrize("model, models", [("gemma4:12b-it-q4_K_M", ["gemma4:12b-it-q4_K_M"]),
                                           ("gemma4", ["gemma4:latest"])])
def test_ready_environment_passes(monkeypatch, model, models):
    """GPU 경로 + 모델 있음이면 통과(태그 없는 이름은 ':latest'로도 찾는다)."""
    _env(monkeypatch, models=models, model=model)
    assert review._ollama_preflight("ollama") is None


def test_tags_query_error_is_reported(monkeypatch):
    """모델 목록 조회가 실패해도 예외로 죽지 않고 이유를 돌려준다."""
    _env(monkeypatch, models=OSError("refused"))
    assert "/api/tags" in review._ollama_preflight("ollama")


def test_reproduce_worker_skips_review_when_environment_not_ready(tmp_path, monkeypatch):
    """재현: 점검에 실패하면 1라운드 리뷰 CLI를 부르지 않고(시간 초과 40분 방지) 이유를 결과에 남긴다."""
    source, job_id = _make_job(tmp_path, monkeypatch, FIRST)
    _set_provider(job_id, "ollama")
    monkeypatch.setattr(review, "_ollama_preflight", lambda _p: "[환경 점검 실패] 테스트")
    run = fake_run(source, [GOOD])
    _patch(monkeypatch, run)
    review._run_review_job(job_id)
    data = result(job_id)
    assert run.calls["review"] == [] and data["provider_fatal_error"] == "[환경 점검 실패] 테스트"
    assert data["success"] is False


def test_feedback_round_stops_when_environment_breaks(tmp_path, monkeypatch):
    """1라운드 뒤 터널이 끊기면 다음 라운드를 부르지 않고 그 이유로 멈춘다(대응표의 provider_fatal = stop)."""
    source, job_id = _make_job(tmp_path, monkeypatch, "def keep():\n    return 1\n")
    _set_provider(job_id, "ollama")
    answers = iter([None, "[환경 점검 실패] 터널 끊김"])
    monkeypatch.setattr(review, "_ollama_preflight", lambda _p: next(answers))
    run = fake_run(source, [FIRST, GOOD])
    _patch(monkeypatch, run)
    review._run_review_job(job_id)
    data = result(job_id)
    last = data["auto_apply_rounds"][-1]
    assert len(run.calls["review"]) == 1
    assert last["situation"] == "provider_fatal" and "터널 끊김" in last["stop_reason"]
    assert data["provider_fatal_error"] == "[환경 점검 실패] 터널 끊김"


def _set_provider(job_id, provider):
    """_make_job이 만든 request.json에 provider만 넣는다(나머지는 그대로)."""
    import json
    path = review._job_files(job_id)[0]
    data = json.loads(path.read_text(encoding="utf-8"))
    data["provider"] = provider
    path.write_text(json.dumps(data), encoding="utf-8")


# ---------------------------------------------------------------- 공용 함수·치명 오류 목록
@pytest.mark.parametrize("url, timeout", [("ftp://x", 3), ("", 3), (GPU, 0), (GPU, True), (GPU, "3")])
def test_list_ollama_models_bad_input(url, timeout):
    """잘못된 입력: 주소 형식·대기 시간이 틀리면 네트워크를 건드리기 전에 ValueError."""
    with pytest.raises(ValueError):
        cf.list_ollama_models(url, timeout)


def test_reproduce_model_not_found_is_fatal():
    """재현: Ollama 404 '모델 없음'은 다시 불러도 같으므로 치명 오류로 바로 멈춘다."""
    text = 'model "gemma4:12b-it-q4_K_M" not found, try pulling it first (status code: 404)'
    assert "모델 없음" in cf.fatal_provider_error_reason(text)
