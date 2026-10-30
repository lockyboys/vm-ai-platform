"""블라인드 리뷰 실행기 완료 판정 결함 재현·회귀 테스트 (2026-10-30, LuckyBoys 보고서 대책 반영).

재현 대상 (sps_blind_review_comprehensive_report.docx 3장·5장):
- 0/82 결과인데 status=completed 로 기록됨 → 82건 완료 게이트 필요
- blocked_after_3_consecutive_failures 가 completed 로 집계됨
- pid 가 없는 오래된 request.json 이 영원히 running 으로 보임 (os.kill(0, 0) 은 자기 그룹이라 성공)
- summary 가 현재 실행분만 세어 개별 파일 수와 불일치 → 고유 결과 파일 기준 재생성
- 실패한 결과 파일이 존재만 하면 재시도 없이 건너뜀 → attempt 누적 보존 후 재실행
잘못된 입력 테스트: job_id 형식, provider 값
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from haness.mcp.tools import blind_review_jobs_v2 as jobs

# 워커는 패키지가 아니므로 파일 경로로 로드한다 (main() 은 실행되지 않음)
WORKER_PATH = Path("/data/vm_project/haness/apps/blind_review_20261027/blind_worker.py")
_spec = importlib.util.spec_from_file_location("blind_worker_under_test", WORKER_PATH)
worker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(worker)

# 존재하지 않는 PID (Linux pid_max 기본 4194304 초과) → 프로세스 종료 상태를 흉내 낸다
DEAD_PID = 99_999_999
JOB_ID = "0" * 31 + "1"


def _make_job(tmp_path, monkeypatch, final: dict | None, pid=DEAD_PID, rc: str | None = None):
    """임시 JOB_ROOT 에 request/result(/return_code) 파일을 만든다."""
    monkeypatch.setattr(jobs, "JOB_ROOT", tmp_path)
    d = tmp_path / JOB_ID
    d.mkdir()
    req = {"job_id": JOB_ID, "provider": "ollama", "state": "running",
           "result_path": str(d / "result.json")}
    if pid is not None:
        req["pid"] = pid
    (d / "request.json").write_text(json.dumps(req), encoding="utf-8")
    (d / "result.json").write_text("" if final is None else json.dumps(final) + "\n", encoding="utf-8")
    if rc is not None:
        (d / "return_code").write_text(rc, encoding="utf-8")
    return d


# ---------- 잘못된 입력 ----------
@pytest.mark.parametrize("bad", ["", "abc", "G" * 32, "../" + "0" * 29, "0" * 33])
def test_invalid_job_id_rejected(bad):
    with pytest.raises(ValueError):
        jobs._paths(bad)


def test_invalid_provider_rejected():
    with pytest.raises(ValueError):
        jobs.submit("openai")


# ---------- 완료 게이트 (보고서 5장 재현) ----------
def test_zero_of_82_is_not_completed(tmp_path, monkeypatch):
    _make_job(tmp_path, monkeypatch, {"status": "completed", "completed": 0, "total": 82})
    assert jobs.status(JOB_ID)["state"] == "incomplete"


def test_blocked_is_not_completed(tmp_path, monkeypatch):
    _make_job(tmp_path, monkeypatch,
              {"status": "blocked_after_3_consecutive_failures", "completed": 3, "total": 82})
    assert jobs.status(JOB_ID)["state"] == "failed"


def test_full_82_is_completed_and_persisted(tmp_path, monkeypatch):
    d = _make_job(tmp_path, monkeypatch,
                  {"status": "completed", "completed": 82, "total": 82, "unique_ids": 82}, rc="0")
    res = jobs.status(JOB_ID)
    assert res["state"] == "completed" and res["return_code"] == 0
    # 종료 상태가 request.json 에도 반영되어 running 고착이 없어야 한다
    assert json.loads((d / "request.json").read_text())["state"] == "completed"


def test_nonzero_return_code_is_failed(tmp_path, monkeypatch):
    _make_job(tmp_path, monkeypatch,
              {"status": "completed", "completed": 82, "total": 82, "unique_ids": 82}, rc="1")
    assert jobs.status(JOB_ID)["state"] == "failed"


def test_missing_pid_is_not_running(tmp_path, monkeypatch):
    _make_job(tmp_path, monkeypatch, None, pid=None)
    assert jobs.status(JOB_ID)["state"] == "failed"


# ---------- summary 재생성 / attempt 누적 (워커) ----------
def _write_result(out: Path, item_id: str, success: bool):
    (out / f"{item_id}.json").write_text(json.dumps(
        {"id": item_id, "success": success, "started_at": "s", "finished_at": "f",
         "elapsed_seconds": 1.0}), encoding="utf-8")


def test_summary_rebuilt_from_unique_files(tmp_path):
    inputs = [{"id": f"c{i}"} for i in range(3)]
    for i in range(3):
        _write_result(tmp_path, f"c{i}", True)
    s = worker.finalize_summary({"status": "running", "runs": [], "completed": 0}, tmp_path, inputs)
    assert (s["completed"], s["total"], s["unique_ids"], s["status"]) == (3, 3, 3, "completed")


def test_summary_incomplete_when_failure_or_missing(tmp_path):
    inputs = [{"id": f"c{i}"} for i in range(3)]
    _write_result(tmp_path, "c0", True)
    _write_result(tmp_path, "c1", False)          # c2 는 결과 파일 없음
    s = worker.finalize_summary({"status": "running", "runs": []}, tmp_path, inputs)
    assert s["completed"] == 1 and s["status"] == "incomplete"


def test_summary_zero_inputs_not_completed(tmp_path):
    s = worker.finalize_summary({"status": "running", "runs": []}, tmp_path, [])
    assert s["status"] == "incomplete"


def test_failed_result_is_archived_not_skipped(tmp_path):
    _write_result(tmp_path, "c0", False)
    assert worker.reusable_result(tmp_path / "c0.json") is None      # 재실행 대상
    assert (tmp_path / "c0.attempt1.json").exists()                  # 이전 시도는 보존
    _write_result(tmp_path, "c0", True)
    assert worker.reusable_result(tmp_path / "c0.json")["success"] is True
