"""자가 수정 라운드가 멈춘 이유(stop_reason)를 항상 남기는지 테스트 (2026-11-18, LuckyBoys 승인).

사고(job 5fa104be, Ollama gemma4:12b, 메모리 에이전트)
- 2라운드가 출력 형식 검사에서 2번(본 시도 + 같은 라운드 재시도 1회) 떨어지자 반복이 끝나 3라운드가 돌지 않았다.
- 그런데 결과(auto_apply_rounds)에는 '왜 멈췄는지'가 없어, 보고 때 '시간 한도 때문'이라고 잘못 추측했다.
기대
- 반복을 끝내는 모든 경로에서 마지막 기록에 stop_reason(한국어 한 문장)을 남긴다.
- 멈추는 조건·재시도 횟수 같은 동작은 바꾸지 않는다(기존 test_review_feedback_rounds 그대로 통과).
LLM·systemd는 실행하지 않는다(test_review_feedback_rounds 의 subprocess.run 대역 재사용).
"""
from types import SimpleNamespace

from harness.mcp.tools import multi_persona_tools as review
# 같은 대역·픽스처를 그대로 쓴다(job 픽스처는 import 하면 pytest가 찾는다)
from harness.tests.test_review_feedback_rounds import FIRST, GOOD, ORIGINAL, fake_run, job, result  # noqa: F401


def _patch(monkeypatch, run):
    """리뷰 CLI·pytest 호출을 대역으로 바꾼다."""
    monkeypatch.setattr(review.subprocess, "run", run)
    monkeypatch.setattr(review.auto_apply.subprocess, "run", run)


def test_reproduce_format_retries_exhausted_has_stop_reason(job, monkeypatch):
    """재현: 형식 거부가 같은 라운드 재시도 한도를 넘으면 그 사실을 남기고,
    2026-11-21(대응표 '고쳐질 때까지 반복')부터는 다음 라운드로 간다. 끝까지 안 되면 제자리걸음으로 멈춘다."""
    source, job_id = job
    monkeypatch.setattr(review.project_config, "MULTI_PERSONA_AUTO_APPLY_MAX_ROUNDS", 3)
    monkeypatch.setattr(review.project_config, "MULTI_PERSONA_AUTO_APPLY_UNVERIFIED_RETRIES", 1)
    run = fake_run(source, [FIRST, GOOD, GOOD, GOOD, GOOD], verified=(True, False, False, False, False))
    _patch(monkeypatch, run)
    review._run_review_job(job_id)
    rounds = result(job_id)["auto_apply_rounds"]
    assert len(run.calls["review"]) == 5                      # 1차 + 2라운드(본 시도+재시도) + 3라운드(본 시도+재시도)
    exhausted = [r for r in rounds if "next_action" in r]
    assert exhausted and all("재시도 한도(1회) 소진" in r["next_action"] for r in exhausted)
    assert "stop_reason" in rounds[-1]                         # 끝에는 멈춘 이유가 반드시 남는다
    assert source.read_text(encoding="utf-8") == ORIGINAL


def test_max_rounds_used_up_has_stop_reason(job, monkeypatch):
    """최대 라운드를 다 써도 여전히 실패면 '최대 라운드 소진'을 남긴다."""
    source, job_id = job
    monkeypatch.setattr(review.project_config, "MULTI_PERSONA_AUTO_APPLY_MAX_ROUNDS", 2)
    run = fake_run(source, [FIRST, FIRST])
    _patch(monkeypatch, run)
    review._run_review_job(job_id)
    assert "최대 라운드(2)" in result(job_id)["auto_apply_rounds"][-1]["stop_reason"]


def test_not_enough_time_has_stop_reason(job, monkeypatch):
    """남은 시간 부족으로 건너뛸 때도 같은 이름(stop_reason)으로 남는다(기존 skipped 값은 그대로)."""
    source, job_id = job
    monkeypatch.setattr(review.project_config, "MULTI_PERSONA_AUTO_APPLY_RETRY_MIN_SECONDS", 10**6)
    _patch(monkeypatch, fake_run(source, [FIRST, GOOD]))
    review._run_review_job(job_id)
    last = result(job_id)["auto_apply_rounds"][-1]
    assert last["skipped"] == "not enough time left" and "남은 시간" in last["stop_reason"]


def test_cli_error_has_stop_reason(job, monkeypatch):
    """리뷰 CLI가 비정상 종료(returncode != 0)하면 그 코드를 이유에 남긴다."""
    source, job_id = job
    base = fake_run(source, [FIRST, GOOD])

    def run(command, **kwargs):
        # 피드백 라운드(2라운드)만 비정상 종료. 2026-11-21: 1라운드도 실패 테스트(focus.txt)를 --error-path로
        # 받게 되어, 라운드 구분은 출력 폴더 이름(round2)으로 한다.
        if "--output-dir" in command and "round" in command[command.index("--output-dir") + 1]:
            return SimpleNamespace(returncode=2, stdout=b"", stderr=b"boom")
        return base(command, **kwargs)

    _patch(monkeypatch, run)
    review._run_review_job(job_id)
    assert "returncode=2" in result(job_id)["auto_apply_rounds"][-1]["stop_reason"]


def test_invalid_retry_setting_still_has_stop_reason(job, monkeypatch):
    """잘못된 입력: 재시도 설정이 음수여도 예외 없이 같은 라운드 재시도는 하지 않고(한도 0회로 적음),
    다음 라운드로 가다가 제자리걸음에서 멈춘다(2026-11-21 대응표)."""
    source, job_id = job
    monkeypatch.setattr(review.project_config, "MULTI_PERSONA_AUTO_APPLY_UNVERIFIED_RETRIES", -5)
    run = fake_run(source, [FIRST, GOOD, GOOD], verified=(True, False, False))
    _patch(monkeypatch, run)
    review._run_review_job(job_id)
    rounds = result(job_id)["auto_apply_rounds"]
    assert len(run.calls["review"]) == 3                      # 같은 라운드 재시도 없이 라운드마다 1번씩
    assert "0회" in rounds[1]["next_action"] and "stop_reason" in rounds[-1]


def test_success_on_first_round_has_no_stop_reason(job, monkeypatch):
    """1차에서 다 통과하면 멈춘 게 아니라 끝난 것이라 stop_reason을 붙이지 않는다."""
    source, job_id = job
    _patch(monkeypatch, fake_run(source, [GOOD, GOOD]))
    review._run_review_job(job_id)
    assert "stop_reason" not in result(job_id)["auto_apply_rounds"][-1]
