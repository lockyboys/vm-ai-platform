"""자율 수리 엔진을 haness/source_repair.py 하나로 통일한 것을 검증한다(2026-10-25 LuckyBoys:
"git add까지만 하게 바꾸고, source_repair.py 하나로 통일").

검증 항목 (실제 LLM·git·네트워크 없이 가짜 repair 모듈 주입)
1. 설정: AUTODISCOVER_SELF_REPAIR.allowed_paths ⊆ SPS_SOURCE_REPAIR_ALLOWED_PATHS (엔진 허용 목록과 어긋나지 않게)
2. PARTNER 수정 도구(source_repair_tool_call):
   - 허용 밖 경로·잘못된 도구 이름·인자 누락은 엔진을 호출하지 않고 JSON 오류로 거부
   - dry_run은 항상 False로 고정(모델이 바꿀 수 없음)
   - PreCommitRequired → error_code PRE_COMMIT_REQUIRED, 그 밖 ValueError → error_code INVALID_REQUEST (예외를 던지지 않음)
3. staged_change_sets: source_repair 적용 보고서(applied·staged)를 변경 세트로 인정,
   dry-run·미적용·stage 실패는 제외. 예전 change_set 형식도 계속 인정.
"""
from __future__ import annotations

import json

import pytest

import config
from haness.mcp.agents import autodiscover_self_repair as loop
from haness.mcp.agents import persona_repair_chain as chain

ALLOWED = list(config.AUTODISCOVER_SELF_REPAIR["allowed_paths"])


class FakeRepair:
    """haness.source_repair 대역: 호출 인자를 기록하고 정해진 결과/예외를 돌려준다."""

    class PreCommitRequired(ValueError):
        pass

    def __init__(self, result=None, error=None):
        self.calls, self.result, self.error = [], result, error

    def read_repair_source(self, file_path):
        self.calls.append(("read", file_path))
        if self.error:
            raise self.error
        return {"path": file_path, "sha256": "a" * 64, "source": "x = 1\n"}

    def repair_source(self, file_path, old_code, new_code, regression_test, expected_sha256, dry_run=True):
        self.calls.append(("repair", file_path, dry_run))
        if self.error:
            raise self.error
        return self.result or {"success": True, "applied": True, "dry_run": dry_run, "path": file_path}


REPAIR_ARGS = {"old_code": "a-b", "new_code": "a+b", "regression_test": "import unittest", "expected_sha256": "a" * 64}


def test_autodiscover_allowed_paths_are_subset_of_engine_allow_list():
    assert set(ALLOWED) <= set(config.SPS_SOURCE_REPAIR_ALLOWED_PATHS)


@pytest.mark.parametrize("path", ["config.py", "../x.py", "", "haness/source_repair.py"])
def test_tool_rejects_path_outside_allowed_without_calling_engine(path):
    fake = FakeRepair()
    out = json.loads(chain.source_repair_tool_call("repair_source", {"file_path": path, **REPAIR_ARGS}, repair=fake))
    assert out["success"] is False and out["error_code"] == "PATH_NOT_ALLOWED"
    assert fake.calls == []


def test_tool_rejects_unknown_tool_and_missing_arguments():
    fake = FakeRepair()
    unknown = json.loads(chain.source_repair_tool_call("execute_change_set", {"file_path": ALLOWED[0]}, repair=fake))
    missing = json.loads(chain.source_repair_tool_call("repair_source", {"file_path": ALLOWED[0]}, repair=fake))
    assert unknown["error_code"] == "UNKNOWN_TOOL"
    assert missing["error_code"] == "INVALID_REQUEST"
    assert fake.calls == []


def test_tool_forces_dry_run_false_even_if_model_passes_true():
    fake = FakeRepair()
    out = json.loads(chain.source_repair_tool_call(
        "repair_source", {"file_path": ALLOWED[0], **REPAIR_ARGS, "dry_run": True}, repair=fake))
    assert fake.calls == [("repair", ALLOWED[0], False)]
    assert out["applied"] is True


def test_tool_maps_pre_commit_required_and_value_error_to_json():
    pre = FakeRepair(error=FakeRepair.PreCommitRequired("미커밋 변경"))
    bad = FakeRepair(error=ValueError("수정 위치는 정확히 한 곳이어야 합니다"))
    out_pre = json.loads(chain.source_repair_tool_call("read_repair_source", {"file_path": ALLOWED[0]}, repair=pre))
    out_bad = json.loads(chain.source_repair_tool_call("repair_source", {"file_path": ALLOWED[0], **REPAIR_ARGS},
                                                       repair=bad))
    assert out_pre == {"success": False, "error_code": "PRE_COMMIT_REQUIRED", "error": "미커밋 변경"}
    assert out_bad["error_code"] == "INVALID_REQUEST" and "한 곳" in out_bad["error"]


def _evidence(value) -> dict:
    return {"tool_evidence": [{"tool_call_id": "t1", "content": json.dumps(value)}]}


def test_staged_change_sets_accepts_applied_and_staged_source_repair_report():
    report = {"success": True, "applied": True, "dry_run": False, "path": ALLOWED[0],
              "after_sha256": "b" * 64, "git_stage": {"staged": True}}
    sets = loop.staged_change_sets(_evidence(report))
    assert len(sets) == 1
    assert loop.changed_paths(sets) == [ALLOWED[0]]
    assert sets[0]["change_set_id"].startswith("source_repair:")


@pytest.mark.parametrize("report", [
    {"success": True, "applied": False, "dry_run": True, "path": "p.py", "git_stage": {"staged": True}},
    {"success": False, "applied": False, "dry_run": False, "path": "p.py"},
    {"success": True, "applied": True, "dry_run": False, "path": "p.py", "git_stage": {"staged": False}},
    {"success": True, "applied": True, "dry_run": False, "git_stage": {"staged": True}},
])
def test_staged_change_sets_rejects_dry_run_unapplied_or_unstaged(report):
    assert loop.staged_change_sets(_evidence(report)) == []


def test_staged_change_sets_still_accepts_legacy_change_set():
    legacy = {"change_set_id": "cs1", "success": True, "dry_run": False, "staged_groups": {"source": ["a.py"]}}
    assert loop.staged_change_sets(_evidence(legacy)) == [legacy]
