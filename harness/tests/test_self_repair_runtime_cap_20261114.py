"""자기 수리 job 수명 상한 36,000초 적용 테스트 (2026-11-14, LuckyBoys 선택 A: 자기 수리만 36,000초).

재현: config.SELF_REPAIR['job_timeout_seconds']=36000 인데 self_repair_run 명령은 RuntimeMaxSec=3600 이었다.
      multi_persona_tools._systemd_command 가 모든 유닛을 SPS_GENERAL_UNIT_RUNTIME_SECONDS(3600)로 잘랐기 때문
      (메리츠 job c87a1169… 는 3214초에 끝나 상한에 거의 닿았다).
수정: _systemd_command 에 선택 인자 runtime_cap 추가(기본 None = 기존 3600 상한 그대로, 다른 작업 영향 없음).
      self_repair_run 만 runtime_cap=SELF_REPAIR['job_timeout_seconds'] 를 넘긴다.
systemd·LLM 을 실행하지 않는다(dry_run 계획만 확인).
"""
import asyncio

import pytest

import config as project_config
from harness.mcp.agents import self_repair_engine as engine
from harness.mcp.tools import multi_persona_tools as tools

# self_repair_run 이 계획을 만들 수 있는 최소 스펙(이미 검증된 모양을 흉내, 실행하지 않음)
_SPEC = {"name": "t", "command": {"module": "a.b"}, "args_template": [], "params": []}


def test_self_repair_run_plan_uses_self_repair_job_timeout(monkeypatch):
    # 재현: 수정 전에는 RuntimeMaxSec=3600
    monkeypatch.setattr(engine, "get_target", lambda name: dict(_SPEC))
    plan = asyncio.run(engine.self_repair_run("t", "{}", dry_run=True))
    expected = int(project_config.SELF_REPAIR["job_timeout_seconds"])
    assert f"RuntimeMaxSec={expected}" in plan["command"]
    assert plan["timeout_seconds"] == expected


def test_default_cap_is_unchanged_for_other_jobs():
    # 다른 작업(리뷰·오케스트레이터)은 기존처럼 일반 유닛 상한으로 잘린다
    _, command = tools._systemd_command(["-m", "x"], 36000, "review")
    assert f"RuntimeMaxSec={int(project_config.SPS_GENERAL_UNIT_RUNTIME_SECONDS)}" in command


def test_runtime_cap_raises_limit_only_when_given():
    _, command = tools._systemd_command(["-m", "x"], 36000, "self-repair", runtime_cap=36000)
    assert "RuntimeMaxSec=36000" in command
    _, smaller = tools._systemd_command(["-m", "x"], 100, "self-repair", runtime_cap=36000)
    assert "RuntimeMaxSec=100" in smaller          # 요청 시간이 더 짧으면 그 값(상한일 뿐 늘리지 않음)


@pytest.mark.parametrize("bad", [0, -1, True, "36000", 1.5])
def test_runtime_cap_rejects_bad_values(bad):
    # 잘못된 입력: 양의 정수가 아니면 명령을 만들지 않는다
    with pytest.raises(ValueError):
        tools._systemd_command(["-m", "x"], 100, "self-repair", runtime_cap=bad)
