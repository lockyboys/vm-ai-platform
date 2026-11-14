"""PARTNER 수리 범위 사전 차단 테스트(2026-10-25 LuckyBoys: 사후 원복이 아니라 적용 전에 막는다).

execute_change_set에 allowed_source_paths가 있으면 run_change_set 전에 다음을 거부해야 한다.
- 허용 소스 밖 파일 patch / 기존 테스트 덮어쓰기 / haness/tests 밖 새 파일 / 범위 밖 stage
거부된 변경은 run_change_set까지 가지 않는다(= 원본 파일이 바뀌지 않는다).
"""
from __future__ import annotations

import json

import pytest

from haness.mcp.agents import source_partner_agent as agent

ALLOWED = "FastAPI/LangGraph/Agent_Import_PFDs/profile_autodiscover.py"


def _patch(path: str) -> str:
    return f"--- a/{path}\n+++ b/{path}\n@@ -1 +1 @@\n-a\n+b\n"


def _payload(**overrides) -> dict:
    base = {"change_set_id": "fix1", "patch_text": _patch(ALLOWED), "writes": [],
            "test_paths": ["haness/tests/test_new_fix.py"],
            "stage_groups": {"source": [ALLOWED], "tests": []}, "commit": {"requested": False}}
    base.update(overrides)
    return base


@pytest.fixture()
def execute(monkeypatch, tmp_path):
    """범위가 고정된 execute_change_set 도구와 run_change_set 호출 기록을 돌려준다."""
    calls = []
    monkeypatch.setattr(agent, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(agent, "run_change_set", lambda payload, dry_run: calls.append(payload) or {"ok": True})
    (tmp_path / "haness/tests").mkdir(parents=True)
    (tmp_path / "haness/tests/test_existing.py").write_text("x", encoding="utf-8")
    tools = agent.build_partner_tools(dry_run=False, source_write_confirmed=True, commit_confirmed=False,
                                      allowed_source_paths=[ALLOWED])
    tool = next(t for t in tools if t.name == "execute_change_set")
    return (lambda payload: tool.invoke({"change_set_json": json.dumps(payload)})), calls


@pytest.mark.parametrize("payload", [
    _payload(patch_text=_patch("config.py"), stage_groups={"source": ["config.py"]}),          # 허용 밖 patch
    _payload(patch_text=_patch(ALLOWED) + _patch("haness/tests/test_existing.py")),          # 기존 테스트 patch
    _payload(writes=[{"path": "haness/tests/test_existing.py", "content": "y"}]),            # 기존 테스트 덮어쓰기
    _payload(writes=[{"path": "haness/tests/test_new.py", "content": "y", "overwrite": True}]),
    _payload(writes=[{"path": "tests/test_new.py", "content": "y"}]),                        # haness/tests 밖
    _payload(writes=[{"path": "haness/tests/../x.py", "content": "y"}]),                     # 경로 이탈
    _payload(stage_groups={"source": [ALLOWED, "common/database.py"]}),                       # 범위 밖 stage
])
def test_out_of_scope_change_is_rejected_before_apply(execute, payload):
    run, calls = execute
    with pytest.raises(Exception, match="change scope"):
        run(payload)
    assert calls == []


def test_allowed_change_reaches_change_set(execute):
    run, calls = execute
    payload = _payload(writes=[{"path": "haness/tests/test_new_fix.py", "content": "def test_x(): pass\n"}],
                       stage_groups={"source": [ALLOWED], "tests": ["haness/tests/test_new_fix.py"]})
    run(payload)
    assert len(calls) == 1


def test_without_scope_old_behavior_is_kept(monkeypatch):
    calls = []
    monkeypatch.setattr(agent, "run_change_set", lambda payload, dry_run: calls.append(payload) or {"ok": True})
    tools = agent.build_partner_tools(dry_run=True, source_write_confirmed=False, commit_confirmed=False)
    tool = next(t for t in tools if t.name == "execute_change_set")
    tool.invoke({"change_set_json": json.dumps(_payload(patch_text=_patch("config.py")))})
    assert len(calls) == 1
