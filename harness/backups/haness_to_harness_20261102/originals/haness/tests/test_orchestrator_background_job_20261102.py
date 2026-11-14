"""2026-11-02 LuckyBoys 요청: run_sps_orchestrator를 백그라운드 job + 상태 조회 방식으로 (상한 3600초).

배경: MCP 도구 호출 자체가 180초에서 끊겨, 동기 실행 상한만 늘려서는 긴 작업을 할 수 없다.
성공 기준:
  1) {"mode":"job_submit","query":...} dry-run → job_id, RuntimeMaxSec=3600, --wait/--pipe 없음, 프로세스 미실행.
  2) 실제 제출 → request.json(0600, query 포함) 저장 후 state=running 즉시 반환.
  3) {"mode":"job_status","job_id":...} → result.json이 있으면 그 내용, 없으면 유닛 상태로 판정.
  4) 워커 → 실행 결과를 result.json(state=completed)으로 저장, 예외도 failed로 저장.
  5) 잘못된 입력(빈 query, 비문자열, job 안의 job, 잘못된 job_id)은 실행 전에 거부.
  6) 기존 동기 경로(일반 query)의 계획은 바뀌지 않는다(회귀 방지).
실제 sudo/systemd/Gemini/크롤러는 실행하지 않는다.
"""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import config
from haness.mcp.tools import orchestrator_tools as module


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    # job 파일은 임시 폴더에, 프로세스 생성은 가짜로 대체한다.
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    start = AsyncMock()
    monkeypatch.setattr(module.asyncio, "create_subprocess_exec", start)
    return start


def _submit(query, dry_run=True):
    payload = json.dumps({"mode": "job_submit", "query": query}, ensure_ascii=False)
    return asyncio.run(module.run_sps_orchestrator(payload, dry_run=dry_run))


def test_job_submit_dry_run_plan(isolated):
    plan = _submit("흥국생명 약관 수집")
    assert plan["dry_run"] and not plan["executed"]
    assert len(plan["job_id"]) == 32
    assert plan["timeout_seconds"] == config.SPS_GENERAL_UNIT_RUNTIME_SECONDS == 3600
    assert "RuntimeMaxSec=3600" in plan["command"]
    assert "--wait" not in plan["command"] and "--pipe" not in plan["command"]
    assert "흥국생명 약관 수집" not in plan["command"]  # query는 인자에 노출되지 않는다
    isolated.assert_not_awaited()


def test_job_submit_executes_detached_and_returns_running(isolated):
    isolated.return_value = SimpleNamespace(returncode=0, communicate=AsyncMock(return_value=(b"", b"")),
                                            kill=lambda: None, wait=AsyncMock())
    result = _submit("흥국생명 약관 수집", dry_run=False)
    assert result["state"] == "running" and result["executed"]
    request_path, _ = module._orchestrator_job_files(result["job_id"])
    saved = json.loads(request_path.read_text(encoding="utf-8"))
    assert saved["query"] == "흥국생명 약관 수집"
    assert oct(request_path.stat().st_mode & 0o777) == "0o600"


def test_job_status_returns_saved_result(isolated):
    job_id = "a" * 32
    request_path, result_path = module._orchestrator_job_files(job_id)
    request_path.parent.mkdir(parents=True)
    request_path.write_text(json.dumps({"unit": "u", "started_at": 0, "query": "q"}), encoding="utf-8")
    result_path.write_text(json.dumps({"state": "completed", "success": True}), encoding="utf-8")
    payload = json.dumps({"mode": "job_status", "job_id": job_id})
    assert asyncio.run(module.run_sps_orchestrator(payload))["state"] == "completed"


def test_job_status_failed_unit_without_result(isolated):
    job_id = "b" * 32
    request_path, _ = module._orchestrator_job_files(job_id)
    request_path.parent.mkdir(parents=True)
    request_path.write_text(json.dumps({"unit": "u", "started_at": 0, "query": "secret q"}), encoding="utf-8")
    isolated.return_value = SimpleNamespace(
        returncode=0, communicate=AsyncMock(return_value=(b"LoadState=not-found\nActiveState=inactive\n", b"")))
    status = asyncio.run(module.run_sps_orchestrator(json.dumps({"mode": "job_status", "job_id": job_id})))
    assert status["state"] == "failed" and status["success"] is False
    assert "query" not in status  # 상태 응답에 원문 요청을 싣지 않는다


def test_job_worker_saves_completed_and_failed(isolated, monkeypatch):
    cases = (("c" * 32, AsyncMock(return_value={"success": True, "response": "ok"}), "completed"),
             ("d" * 32, AsyncMock(side_effect=RuntimeError("boom")), "failed"))
    for job_id, inline, expected in cases:
        monkeypatch.setattr(module, "_run_query_inline", inline)
        request_path, result_path = module._orchestrator_job_files(job_id)
        request_path.parent.mkdir(parents=True)
        request_path.write_text(json.dumps({"query": "q", "timeout_seconds": 3600, "unit": "u",
                                            "started_at": 0}), encoding="utf-8")
        module._run_orchestrator_job(job_id)
        result = json.loads(result_path.read_text(encoding="utf-8"))
        assert result["state"] == expected
        assert "query" not in result


@pytest.mark.parametrize("bad_query", ["", "   ", None, 123,
                                       json.dumps({"mode": "job_submit", "query": "x"}),
                                       json.dumps({"mode": "job_status", "job_id": "a" * 32})])
def test_invalid_job_submit_rejected(isolated, bad_query):
    with pytest.raises(ValueError):
        _submit(bad_query, dry_run=False)
    isolated.assert_not_awaited()


@pytest.mark.parametrize("bad_id", ["", "../../etc", "A" * 32, "a" * 31, None])
def test_invalid_job_id_rejected(isolated, bad_id):
    with pytest.raises(ValueError):
        asyncio.run(module.run_sps_orchestrator(json.dumps({"mode": "job_status", "job_id": bad_id})))


def test_sync_path_plan_unchanged(isolated):
    # 회귀 방지: 일반 query의 동기 계획은 기존 config 값을 그대로 쓴다.
    plan = asyncio.run(module.run_sps_orchestrator("어떤 도구가 있니?"))
    assert plan["timeout_seconds"] == config.SPS_MAIN_ORCHESTRATOR_TIMEOUT_SECONDS
    assert "--wait" in plan["command"]
