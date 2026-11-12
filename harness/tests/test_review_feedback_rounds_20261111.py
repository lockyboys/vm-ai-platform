"""review_python_source 실패 피드백 재시도 테스트 (2026-11-11, LuckyBoys 결정).

재현 상황: 1차 수정안이 테스트에 실패해 되돌려지면, 실패 내용을 feedback.txt로 만들어
같은 AI에게 직전 수정안과 함께 다시 리뷰시키고(2차), 2차 수정안이 통과하면 반영해야 한다.
LLM·systemd는 실행하지 않는다(subprocess.run 대역: 리뷰 CLI 호출은 제안 파일 생성, pytest 호출은
현재 원본 내용으로 통과 여부를 결정).
"""
import hashlib
import json
from types import SimpleNamespace

import pytest

from harness.mcp.tools import multi_persona_tools as review

ORIGINAL = "def keep():\n    return 1\n"
FIRST = "def keep():\n    return 2\n"   # 1차 수정안(테스트 실패)
GOOD = "def keep():\n    return 3\n"    # 2차 수정안(테스트 통과)
VERIFIED = "[출력 검증] 오류=[], 보고서=x\n[최종 검증된 답변]:\n본문\n"


@pytest.fixture
def job(tmp_path, monkeypatch):
    """임시 저장소에 원본·테스트·request.json을 만든다."""
    monkeypatch.setattr(review, "PROJECT_ROOT", tmp_path)
    source = tmp_path / "sample.py"
    source.write_text(ORIGINAL, encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    job_id = "d" * 32
    request_path, _ = review._job_files(job_id)
    request_path.parent.mkdir(parents=True)
    request_path.write_text(json.dumps({
        "source_path": "sample.py", "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "timeout_seconds": 600, "output_limit": 1000, "error_path": None,
        "auto_apply": True, "test_paths": ["tests/test_sample.py"]}), encoding="utf-8")
    return source, job_id


def fake_run(source, proposals, verified=(True, True)):
    """리뷰 CLI는 proposals를 차례로 내고, pytest는 원본이 GOOD일 때만 통과(junit xml도 씀)."""
    calls = {"review": [], "pytest": 0}

    def run(command, **_kwargs):
        if "pytest" in command:
            calls["pytest"] += 1
            ok = source.read_text(encoding="utf-8") == GOOD
            xml = next(arg for arg in command if arg.startswith("--junitxml=")).split("=", 1)[1]
            body = "" if ok else '<failure message="keep() -&gt; 2, 기대 3"/>'
            review.Path(xml).write_text(f'<testsuite><testcase classname="t" name="test_ok">{body}</testcase></testsuite>',
                                        encoding="utf-8")
            return SimpleNamespace(returncode=0 if ok else 1, stdout=b"pytest", stderr=b"")
        number = len(calls["review"])
        calls["review"].append(command)
        out_dir = review.Path(command[command.index("--output-dir") + 1])
        if verified[number]:
            (out_dir / "proposed.py").write_text(proposals[number], encoding="utf-8")
        text = VERIFIED if verified[number] else "[검증 미완료 - 초안 대체 답변]:\n"
        return SimpleNamespace(returncode=0, stdout=text.encode(), stderr=b"")

    run.calls = calls
    return run


def result(job_id):
    return json.loads(review._job_files(job_id)[1].read_text(encoding="utf-8"))


def test_second_round_fixes_and_applies(job, monkeypatch):
    """재현: 1차 실패 → 피드백 → 2차 통과 → 반영."""
    source, job_id = job
    run = fake_run(source, [FIRST, GOOD])
    monkeypatch.setattr(review.subprocess, "run", run)
    monkeypatch.setattr(review.auto_apply.subprocess, "run", run)
    review._run_review_job(job_id)
    data = result(job_id)
    assert source.read_text(encoding="utf-8") == GOOD
    assert data["auto_apply_result"]["applied"] is True
    assert [r["round"] for r in data["auto_apply_rounds"]] == [1, 2]
    round_dir = review._job_files(job_id)[0].parent / "round2"
    # 2차 입력은 1차 수정안이고, 피드백에는 실패 메시지가 들어간다.
    assert (round_dir / "sample.py").read_text(encoding="utf-8") == FIRST
    feedback = (round_dir / "feedback.txt").read_text(encoding="utf-8")
    assert "keep() -> 2, 기대 3" in feedback
    second = run.calls["review"][1]
    assert second[second.index("--error-path") + 1] == str(round_dir / "feedback.txt")
    assert data["final_proposed_path"].endswith("round2/proposed.py")


def test_unverified_second_round_keeps_original(job, monkeypatch):
    """2차 리뷰가 검증되지 않으면 멈추고 원본을 그대로 둔다."""
    source, job_id = job
    run = fake_run(source, [FIRST, GOOD], verified=(True, False))
    monkeypatch.setattr(review.subprocess, "run", run)
    monkeypatch.setattr(review.auto_apply.subprocess, "run", run)
    review._run_review_job(job_id)
    data = result(job_id)
    assert source.read_text(encoding="utf-8") == ORIGINAL
    assert data["auto_apply_rounds"][-1]["verified"] is False


def test_not_enough_time_skips_retry(job, monkeypatch):
    """남은 시간이 최소값보다 적으면 2차를 건너뛴다(AI 추가 호출 없음)."""
    source, job_id = job
    monkeypatch.setattr(review.project_config, "MULTI_PERSONA_AUTO_APPLY_RETRY_MIN_SECONDS", 10**6)
    run = fake_run(source, [FIRST, GOOD])
    monkeypatch.setattr(review.subprocess, "run", run)
    monkeypatch.setattr(review.auto_apply.subprocess, "run", run)
    review._run_review_job(job_id)
    data = result(job_id)
    assert len(run.calls["review"]) == 1
    assert data["auto_apply_rounds"][-1]["skipped"] == "not enough time left"
    assert source.read_text(encoding="utf-8") == ORIGINAL


@pytest.mark.parametrize("bad_rounds", [1, 0, -3])
def test_max_rounds_one_or_invalid_means_no_retry(job, monkeypatch, bad_rounds):
    """잘못된 입력·1회 설정: 최대 라운드가 1 이하이면 재시도하지 않는다."""
    source, job_id = job
    monkeypatch.setattr(review.project_config, "MULTI_PERSONA_AUTO_APPLY_MAX_ROUNDS", bad_rounds)
    run = fake_run(source, [FIRST, GOOD])
    monkeypatch.setattr(review.subprocess, "run", run)
    monkeypatch.setattr(review.auto_apply.subprocess, "run", run)
    review._run_review_job(job_id)
    assert len(run.calls["review"]) == 1
    assert source.read_text(encoding="utf-8") == ORIGINAL


def test_success_on_first_round_does_not_retry(job, monkeypatch):
    """1차에서 전부 통과하면 2차는 돌지 않는다."""
    source, job_id = job
    run = fake_run(source, [GOOD, GOOD])
    monkeypatch.setattr(review.subprocess, "run", run)
    monkeypatch.setattr(review.auto_apply.subprocess, "run", run)
    review._run_review_job(job_id)
    assert len(run.calls["review"]) == 1
    assert result(job_id)["auto_apply_rounds"] == [
        {"round": 1, "verified": True, **review._round_view(result(job_id)["auto_apply_result"])}]


def test_junit_failures_handles_missing_file(tmp_path):
    """잘못된 입력: 결과 파일이 없거나 깨져도 예외 없이 빈 목록."""
    assert review._junit_failures(tmp_path / "missing.xml", 5) == []
    broken = tmp_path / "broken.xml"
    broken.write_text("<testsuite>", encoding="utf-8")
    assert review._junit_failures(broken, 5) == []
