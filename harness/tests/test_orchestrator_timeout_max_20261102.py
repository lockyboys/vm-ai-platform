"""2026-11-02 LuckyBoys 요청: run_sps_orchestrator 실행 시간 상한 → 최대(3600초).

설계 변경(2026-11-02): MCP 호출이 180초에서 끊기므로 3600초는 백그라운드 job(job_submit)에 적용하고,
동기 경로는 기존 값(config.SPS_MAIN_ORCHESTRATOR_TIMEOUT_SECONDS)을 유지한다.
성공 기준:
  1) 공용 유닛 상한 config.SPS_GENERAL_UNIT_RUNTIME_SECONDS == 3600
  2) job_submit dry-run 계획의 timeout_seconds와 systemd RuntimeMaxSec가 3600이다.
  3) 잘못된 값(0, 음수, 공용 유닛 상한 초과)은 실행 전에 ValueError로 거부된다.
워커·Gemini·크롤러는 실행하지 않는다(dry-run 또는 프로세스 생성 차단).
"""
import asyncio
import json
from unittest.mock import AsyncMock

import pytest

import config
from harness.mcp.tools import orchestrator_tools as module


@pytest.fixture
def no_process(monkeypatch):
    # 실제 sudo/systemd-run 실행을 막는다(단위 테스트 격리).
    start = AsyncMock()
    monkeypatch.setattr(module.asyncio, "create_subprocess_exec", start)
    return start


def test_default_timeout_is_general_unit_max():
    assert config.SPS_GENERAL_UNIT_RUNTIME_SECONDS == 3600


def test_dry_run_plan_uses_3600_seconds(no_process):
    query = json.dumps({"mode": "job_submit", "query": "흥국생명 약관"}, ensure_ascii=False)
    plan = asyncio.run(module.run_sps_orchestrator(query, dry_run=True))
    assert plan["timeout_seconds"] == 3600
    assert "RuntimeMaxSec=3600" in plan["command"]
    no_process.assert_not_awaited()


@pytest.mark.parametrize("bad", [0, -1, 3601])
def test_invalid_timeout_rejected_before_launch(monkeypatch, no_process, bad):
    # 잘못된 설정값은 워커를 띄우기 전에 거부한다.
    monkeypatch.setattr(config, "SPS_MAIN_ORCHESTRATOR_TIMEOUT_SECONDS", bad)
    with pytest.raises(ValueError):
        asyncio.run(module.run_sps_orchestrator("task", dry_run=True))
    no_process.assert_not_awaited()
