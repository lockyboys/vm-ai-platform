"""review_python_source 완전 자동 수정(auto_apply) 테스트 (2026-11-10, LuckyBoys 선택: 완전 자동).

동작 계약
  - 검증된 리뷰(model_verified)만 원본에 자동 적용한다.
  - 적용 전 원본을 job 폴더 original.py로 백업한다.
  - 적용 후 문법 컴파일 + (지정 시) pytest를 돌리고, 하나라도 실패하면 원본으로 자동 되돌린다.
  - 리뷰 중 원본이 바뀌었거나 리뷰가 검증되지 않으면 적용하지 않는다.
  - test_paths는 설정된 테스트 폴더 안만 허용한다(잘못된 입력은 제출 단계에서 거부).
LLM·systemd는 실행하지 않는다(subprocess.run 대역 사용).
"""
import asyncio
import hashlib
import json
from types import SimpleNamespace

import pytest

from harness.mcp.tools import multi_persona_tools as review

ORIGINAL = "def keep():\n    return 1\n"
PROPOSED = "def keep():\n    return 2\n"
VERIFIED_OUTPUT = "[출력 검증] 오류=[], 보고서=x\n[최종 검증된 답변]:\n본문\n"


@pytest.fixture
def job(tmp_path, monkeypatch):
    """임시 저장소에 원본·테스트 파일·request.json을 만들고 job_id를 돌려준다."""
    monkeypatch.setattr(review, "PROJECT_ROOT", tmp_path)
    source = tmp_path / "sample.py"
    source.write_text(ORIGINAL, encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    def make(auto_apply=True, test_paths=("tests/test_sample.py",)):
        job_id = "c" * 32
        request_path, _ = review._job_files(job_id)
        request_path.parent.mkdir(parents=True, exist_ok=True)
        request_path.write_text(json.dumps({
            "source_path": "sample.py", "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "timeout_seconds": 600, "output_limit": 1000, "error_path": None,
            "auto_apply": auto_apply, "test_paths": list(test_paths)}), encoding="utf-8")
        return job_id
    return source, make


def _fake_run(test_returncode=0, verified=True, proposed=PROPOSED, mutate_source=None):
    """리뷰 CLI 호출이면 제안 파일을 만들고, pytest 호출이면 지정한 종료 코드를 돌려준다."""
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        if "pytest" in command:
            return SimpleNamespace(returncode=test_returncode, stdout=b"1 passed" if test_returncode == 0 else b"1 failed",
                                   stderr=b"")
        out_dir = review.Path(command[command.index("--output-dir") + 1])
        if verified:
            (out_dir / "proposed.py").write_text(proposed, encoding="utf-8")
        if mutate_source is not None:
            mutate_source()  # 리뷰 도중 다른 작업이 원본을 바꾼 상황
        text = VERIFIED_OUTPUT if verified else "[검증 미완료 - 초안 대체 답변]:\n"
        return SimpleNamespace(returncode=0, stdout=text.encode(), stderr=b"")
    run.calls = calls
    return run


def _result(job_id):
    return json.loads(review._job_files(job_id)[1].read_text(encoding="utf-8"))


def test_verified_proposal_is_applied_when_tests_pass(job, monkeypatch):
    source, make = job
    job_id = make()
    monkeypatch.setattr(review.subprocess, "run", _fake_run(test_returncode=0))
    review._run_review_job(job_id)
    auto = _result(job_id)["auto_apply_result"]
    assert auto["applied"] is True and auto["rolled_back"] is False
    assert source.read_text(encoding="utf-8") == PROPOSED
    # 원본 백업이 job 폴더에 남는다(일반 지침 7)
    assert (review._job_files(job_id)[0].parent / "original.py").read_text(encoding="utf-8") == ORIGINAL


def test_failed_tests_roll_back_to_original(job, monkeypatch):
    source, make = job
    job_id = make()
    monkeypatch.setattr(review.subprocess, "run", _fake_run(test_returncode=1))
    review._run_review_job(job_id)
    auto = _result(job_id)["auto_apply_result"]
    assert auto["applied"] is False and auto["rolled_back"] is True
    assert auto["test_returncode"] == 1
    assert source.read_text(encoding="utf-8") == ORIGINAL


def test_uncompilable_proposal_rolls_back(job, monkeypatch):
    source, make = job
    job_id = make(test_paths=())
    monkeypatch.setattr(review.subprocess, "run", _fake_run(proposed="def broken(:\n"))
    review._run_review_job(job_id)
    auto = _result(job_id)["auto_apply_result"]
    assert auto["rolled_back"] is True
    assert source.read_text(encoding="utf-8") == ORIGINAL


def test_unverified_review_is_never_applied(job, monkeypatch):
    source, make = job
    job_id = make()
    run = _fake_run(verified=False)
    monkeypatch.setattr(review.subprocess, "run", run)
    review._run_review_job(job_id)
    auto = _result(job_id)["auto_apply_result"]
    assert auto["applied"] is False and auto["rolled_back"] is False
    assert source.read_text(encoding="utf-8") == ORIGINAL
    # 검증 안 된 리뷰는 '적용 검증' 테스트를 돌리지 않는다.
    # 2026-11-21 (LuckyBoys 승인 '실패 테스트 집중'): 리뷰 전에 원본으로 한 번 돌리는 읽기 전용 테스트(junit_focus.xml)는 예외.
    apply_runs = [c for c in run.calls if "pytest" in c
                  and not any(str(arg).endswith("junit_focus.xml") for arg in c)]
    assert not apply_runs


def test_source_changed_during_review_is_not_overwritten(job, monkeypatch):
    source, make = job
    job_id = make()
    other = "def keep():\n    return 99\n"
    monkeypatch.setattr(review.subprocess, "run",
                        _fake_run(mutate_source=lambda: source.write_text(other, encoding="utf-8")))
    review._run_review_job(job_id)
    auto = _result(job_id)["auto_apply_result"]
    assert auto["applied"] is False
    assert source.read_text(encoding="utf-8") == other  # 다른 작업의 변경을 덮어쓰지 않음


def test_auto_apply_off_keeps_proposal_only(job, monkeypatch):
    source, make = job
    job_id = make(auto_apply=False)
    monkeypatch.setattr(review.subprocess, "run", _fake_run())
    review._run_review_job(job_id)
    assert _result(job_id)["auto_apply_result"]["auto_apply"] is False
    assert source.read_text(encoding="utf-8") == ORIGINAL


@pytest.mark.parametrize("bad", [["config.py"], ["../escape.py"], "tests/x.py", [1], ["tests/missing_20261110.py"]])
def test_invalid_test_paths_rejected_before_launch(bad):
    """잘못된 입력: 테스트 폴더 밖·경로 탈출·문자열·숫자·없는 파일은 제출 단계에서 거부."""
    with pytest.raises((ValueError, FileNotFoundError)):
        asyncio.run(review.review_python_source("FastAPI/LangGraph/multi_persona/review_contract.py",
                                                test_paths=bad))


def test_dry_run_plan_shows_auto_apply_settings():
    # 2026-11-10: tests/test_review_output_contract.py → harness/tests/로 이동(LuckyBoys 지시)
    plan = asyncio.run(review.review_python_source("FastAPI/LangGraph/multi_persona/review_contract.py",
                                                   test_paths=["harness/tests/test_review_output_contract.py"]))
    assert plan["executed"] is False
    assert plan["test_paths"] == ["harness/tests/test_review_output_contract.py"]
    assert plan["auto_apply"] is review.project_config.MULTI_PERSONA_REVIEW_AUTO_APPLY
