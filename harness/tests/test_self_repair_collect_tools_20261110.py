"""self_repair_collect 도구 테스트 (2026-11-10 LuckyBoys: "건수가 부족해도 스스로 고치는 수집 도구", 결정 B + 목표 건수 (가) 직접 입력).

검증 범위 (네트워크·브라우저·systemd 없이 함수 주입만 사용)
  a) 수집 건수 < 목표 → NEEDS_NEW_RULE / category=shortfall 보고서 (메리츠 10건 < 1000 재현)
  b) 수집 건수 >= 목표 → None (수리 불필요)
  c) 잘못된 입력(음수·0·bool·문자열 목표, success 없음, 잘못된 이름·회사명) → ValueError
  d) collect_and_check 를 기존 auto_with_repair 에 넣으면: 부족 → 수리(partner) 호출 → 재수집 성공 흐름
  e) dry_run 계획: 프로세스 미실행, 32자리 hex job_id, --wait/--pipe 없음
  f) 잘못된 job_id 거부(경로 조작 차단)
"""
from __future__ import annotations

import asyncio
import json
import re

import pytest

from harness.mcp.tools import self_repair_collect_tools as tool
from harness.mcp.agents import autodiscover_self_repair as repair


# ---------------------------------------------------------------------------
# a) b) c) check_shortfall
# ---------------------------------------------------------------------------
def test_shortfall_when_collected_below_target():
    """메리츠 사례 재현: 10건 수집, 목표 1000건 → 수리가 필요하다는 보고서."""
    report = tool.check_shortfall({"success": 10, "targets": 10, "failed": 0}, 1000, "status.json")
    assert report["result"] == "NEEDS_NEW_RULE"
    assert report["failure"]["category"] == "shortfall"
    assert "10" in report["failure"]["error"] and "1000" in report["failure"]["error"]
    assert report["failure"]["evidence"] == "status.json"


def test_no_shortfall_when_target_met():
    """목표 이상이면 수리하지 않는다(None)."""
    assert tool.check_shortfall({"success": 1000}, 1000) is None
    assert tool.check_shortfall({"success": 1500}, 1000) is None


@pytest.mark.parametrize("expected", [0, -1, True, "1000", 1.5, None])
def test_shortfall_rejects_bad_target(expected):
    """목표 건수는 1 이상 정수만(bool 은 int 의 하위형이라 별도로 거부)."""
    with pytest.raises(ValueError):
        tool.check_shortfall({"success": 10}, expected)


@pytest.mark.parametrize("status", [{}, {"success": "10"}, {"success": True}, None, []])
def test_shortfall_rejects_bad_status(status):
    """status.json 에 정수 success 가 없으면 판정할 수 없다 → ValueError(성공으로 숨기지 않음)."""
    with pytest.raises(ValueError):
        tool.check_shortfall(status, 10)


@pytest.mark.parametrize("request_value", [
    {"name": "Meritz", "company_name": "메리츠화재", "expected_min_count": 10},     # 대문자 이름
    {"name": "meritz", "company_name": "", "expected_min_count": 10},              # 빈 회사명
    {"name": "meritz", "company_name": "a\nb", "expected_min_count": 10},          # 여러 줄 회사명
    {"name": "meritz", "company_name": "메리츠화재", "expected_min_count": 0},      # 목표 0
    {"name": "meritz", "company_name": "메리츠화재", "expected_min_count": True},   # bool 목표
    {"name": "meritz", "company_name": "메리츠화재", "expected_min_count": 10, "document_keyword": ""},
    "not a dict",
])
def test_validate_request_rejects_bad_input(request_value):
    with pytest.raises(ValueError):
        tool.validate_request(request_value)


def test_validate_request_defaults_keyword():
    """document_keyword 를 주지 않으면 '약관'."""
    value = tool.validate_request({"name": "meritz", "company_name": " 메리츠화재 ", "expected_min_count": 1000})
    assert value == {"name": "meritz", "company_name": "메리츠화재", "expected_min_count": 1000,
                     "document_keyword": "약관"}


# ---------------------------------------------------------------------------
# d) 기존 수리 루프와의 연결
# ---------------------------------------------------------------------------
def test_collect_and_check_uses_injected_collector():
    """수집기 실행 함수를 주입하면 그 결과 status 로 판정한다."""
    request = {"name": "meritz", "company_name": "메리츠화재", "expected_min_count": 100}
    short = tool.collect_and_check(request, run_collector=lambda r: ({"success": 10}, "s.json"))
    assert short["result"] == "NEEDS_NEW_RULE"
    ok = tool.collect_and_check(request, run_collector=lambda r: ({"success": 100}, "s.json"))
    assert ok["result"].startswith("DISCOVERED")          # 기존 heal_succeeded 기준과 맞춘다
    assert ok["success"] == 100


def test_auto_with_repair_repairs_shortfall_then_succeeds(tmp_path, monkeypatch):
    """부족(10건) → PARTNER 수리 1회(주입) → 재수집 1000건 → 최종 성공."""
    monkeypatch.setattr(repair, "_work_dir", lambda name: tmp_path)    # 증빙 파일은 임시 폴더로
    statuses = iter([({"success": 10}, "s.json"), ({"success": 1000}, "s.json")])
    request = {"name": "meritz", "company_name": "메리츠화재", "expected_min_count": 1000}
    calls = []

    def partner(task, round_no):
        calls.append(task)
        change = {"change_set_id": "cs1", "success": True, "dry_run": False,
                  "staged_groups": {"source": ["FastAPI/LangGraph/Agent_Import_PFDs/public_document_catalog_collector.py"]}}
        return {"verdict": "PASS", "tool_evidence": [{"content": json.dumps(change)}], "steps": []}

    out = repair.auto_with_repair(
        request,
        auto_fn=lambda req: tool.collect_and_check(req, run_collector=lambda r: next(statuses)),
        partner_fn=partner, backup_fn=lambda paths: {}, restore_fn=lambda backups: None)
    assert out["first_result"] == "NEEDS_NEW_RULE"
    assert len(calls) == 1 and "shortfall" in calls[0]       # 수리 작업문에 부족 사유가 들어간다
    assert out["result"].startswith("DISCOVERED")
    assert out["repairs"][0]["after_result"].startswith("DISCOVERED")


# ---------------------------------------------------------------------------
# e) f) MCP 도구(백그라운드 job)
# ---------------------------------------------------------------------------
def test_dry_run_plan_does_not_execute(monkeypatch):
    """dry_run=True(기본)는 계획만 돌려주고 프로세스를 띄우지 않는다."""
    async def forbidden(*args, **kwargs):
        raise AssertionError("dry-run must not start a process")
    monkeypatch.setattr(asyncio, "create_subprocess_exec", forbidden)
    plan = asyncio.run(tool.self_repair_collect("meritz", "메리츠화재", 1000))
    assert plan["dry_run"] is True and plan["executed"] is False
    assert re.fullmatch(r"[0-9a-f]{32}", plan["job_id"])
    assert "--wait" not in plan["command"] and "--pipe" not in plan["command"]
    assert plan["command"][-2:] == ["--job-worker", plan["job_id"]]


def test_dry_run_rejects_bad_input():
    with pytest.raises(ValueError):
        asyncio.run(tool.self_repair_collect("meritz", "메리츠화재", 0))


@pytest.mark.parametrize("job_id", ["../etc", "ABC", "1234", "g" * 32])
def test_bad_job_id_rejected(job_id):
    with pytest.raises(ValueError):
        asyncio.run(tool.self_repair_collect("meritz", "메리츠화재", 1000, job_id=job_id))
