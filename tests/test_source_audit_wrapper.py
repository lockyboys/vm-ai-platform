"""harness/mcp/source_audit.py 자동 감사 기록 래퍼 테스트.

목적
- SPS Harness MCP 소스 도구(source_read/write/patch/delete/rename, run_pytest_verification)를
  호출하면 harness_source_audit에 1건씩 자동 기록되는지 확인한다.
- 기록은 반드시 등록된 Verified SQL(config.SOURCE_AUDIT["verified_query_id"])로만 한다.
- 행 id는 SOURCE_AUDIT Object로 identifier_generate가 발급한 Level 4 ID를 쓴다(AUTO_INCREMENT 없음).
- user_id는 AI 에이전트 세션 ID, created_by/updated_by는 요청자(테이블 COMMENT 기준).
- 기록 실패(ID 발급 실패 포함)가 원래 도구 결과를 막지 않는지(가용성 우선) 확인한다.
- dry_run=True 인 변경 도구(patch/delete/rename)는 실제 변경이 없으므로 기록하지 않는다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import config
from harness.mcp import source_audit

# INSERT 파라미터 순서(등록 Verified SQL 계약). 마지막 id는 NOT EXISTS 중복 검사용.
_PARAM_NAMES = ("id", "user_id", "file_name", "task_type", "learning_type", "accuracy",
                "created_by", "updated_by", "program_id", "client_ip", "duplicate_check_id")


@pytest.fixture()
def recorded(monkeypatch):
    """ID 발급과 Verified SQL 실행을 가로채 호출 인자를 모은다(실제 DB는 쓰지 않는다)."""
    calls: list[dict] = []
    issued: list[str] = []

    def fake_issue():
        identifier = f"SP_SR_SOURCE_AUDIT_20261024_000000_{len(issued) + 1:05d}"
        issued.append(identifier)
        return identifier

    def fake_execute(query_id, parameters_json="[]", apply=False):
        calls.append({"query_id": query_id, "params": json.loads(parameters_json), "apply": apply})
        return {"affected_rows": 1, "executed": True}

    monkeypatch.setattr(source_audit, "_issue_audit_id", fake_issue)
    monkeypatch.setattr(source_audit, "_execute_verified_sql", fake_execute)
    return calls


def _row(call: dict) -> dict:
    """파라미터 목록을 이름 기준 dict로 바꾼다."""
    return dict(zip(_PARAM_NAMES, call["params"]))


def test_source_read_is_recorded_with_verified_query(recorded):
    """정상: source_read 1회 → 등록 Query ID로 SOURCE_READ 1건, 발급 id·세션 user_id·요청자 기록."""
    def source_read(path, start_line=1, max_lines=200):
        return {"path": path, "content": []}

    result = source_audit.source_audit_recorded(source_read)("config.py", start_line=1)

    assert result == {"path": "config.py", "content": []}
    assert len(recorded) == 1
    assert recorded[0]["query_id"] == config.SOURCE_AUDIT["verified_query_id"]
    assert recorded[0]["apply"] is True
    row = _row(recorded[0])
    assert row["id"] == "SP_SR_SOURCE_AUDIT_20261024_000000_00001"
    assert row["duplicate_check_id"] == row["id"]
    assert row["user_id"] == config.SOURCE_AUDIT["agent_session_id"]
    assert row["created_by"] == row["updated_by"] == config.SOURCE_AUDIT["requester_id"]
    assert row["file_name"] == "config.py"
    assert row["task_type"] == "SOURCE_READ"
    assert row["learning_type"] == "source_read"
    assert row["accuracy"] is None


def test_patch_records_every_changed_path_with_distinct_ids(recorded):
    """정상: source_patch 실제 적용 → 결과 paths 각각 1건, 행마다 다른 id."""
    def source_patch(patch_text, dry_run=True):
        return {"applied": True, "paths": ["a.py", "b.py"]}

    source_audit.source_audit_recorded(source_patch)("diff", dry_run=False)

    rows = [_row(call) for call in recorded]
    assert [r["file_name"] for r in rows] == ["a.py", "b.py"]
    assert {r["task_type"] for r in rows} == {"SOURCE_PATCH"}
    assert len({r["id"] for r in rows}) == 2


@pytest.mark.parametrize("tool_name", ["source_patch", "source_delete", "source_rename"])
def test_dry_run_changes_are_not_recorded(recorded, tool_name):
    """잘못된/불필요 입력: dry_run 기본값(True)인 변경 도구는 기록하지 않는다."""
    def tool(*args, dry_run=True, **kwargs):
        return {"dry_run": dry_run, "paths": ["a.py"]}

    tool.__name__ = tool_name
    source_audit.source_audit_recorded(tool)("a.py")

    assert recorded == []


def test_pytest_accuracy_is_pass_ratio(recorded):
    """정상: run_pytest_verification → 테스트 경로별 기록, accuracy=통과/전체."""
    def run_pytest_verification(test_paths, *, title="x"):
        return {"results": [{"status": "PASSED"}, {"status": "FAILED"}, {"status": "PASSED"}, {"status": "PASSED"}]}

    source_audit.source_audit_recorded(run_pytest_verification)(["tests/test_a.py"])

    row = _row(recorded[0])
    assert row["task_type"] == "TEST_VERIFY"
    assert row["file_name"] == "tests/test_a.py"
    assert row["accuracy"] == pytest.approx(0.75)


def test_recording_failure_does_not_break_tool(monkeypatch):
    """잘못된 상황: 기록 DB 오류가 나도 원래 도구 결과는 그대로 돌려준다."""
    monkeypatch.setattr(source_audit, "_issue_audit_id", lambda: "SP_SR_SOURCE_AUDIT_X")

    def broken_execute(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(source_audit, "_execute_verified_sql", broken_execute)

    def source_read(path, start_line=1, max_lines=200):
        return {"ok": True}

    assert source_audit.source_audit_recorded(source_read)("config.py") == {"ok": True}


def test_id_issue_failure_skips_insert_and_keeps_tool_result(monkeypatch):
    """잘못된 상황: ID 발급이 실패하면 INSERT를 시도하지 않고 도구 결과는 그대로 돌려준다."""
    executed: list = []

    def broken_issue():
        raise LookupError("SOURCE_AUDIT Object missing")

    monkeypatch.setattr(source_audit, "_issue_audit_id", broken_issue)
    monkeypatch.setattr(source_audit, "_execute_verified_sql", lambda *a, **k: executed.append(a))

    def source_read(path, start_line=1, max_lines=200):
        return {"ok": True}

    assert source_audit.source_audit_recorded(source_read)("config.py") == {"ok": True}
    assert executed == []


def test_issue_audit_id_uses_configured_object_code(monkeypatch):
    """정상: 실제 발급 함수는 config의 Object 코드로 apply=True 발급하고 identifier를 돌려준다."""
    seen: dict = {}

    def fake_generate(object_code, **kwargs):
        seen.update(object_code=object_code, **kwargs)
        return {"identifier": "SP_SR_SOURCE_AUDIT_20261024_174851_00001"}

    monkeypatch.setattr(source_audit, "_identifier_generate", lambda: fake_generate)

    assert source_audit._issue_audit_id() == "SP_SR_SOURCE_AUDIT_20261024_174851_00001"
    assert seen["object_code"] == config.SOURCE_AUDIT["identifier_object_code"]
    assert seen["apply"] is True


def test_issue_audit_id_rejects_missing_identifier(monkeypatch):
    """잘못된 입력: 발급 결과에 identifier가 없으면 RuntimeError(빈 id로 INSERT 금지)."""
    monkeypatch.setattr(source_audit, "_identifier_generate", lambda: (lambda object_code, **k: {"dry_run": True}))

    with pytest.raises(RuntimeError):
        source_audit._issue_audit_id()


def test_tool_error_is_not_recorded(recorded):
    """잘못된 입력: 도구 자체가 실패하면 예외를 그대로 올리고 기록하지 않는다."""
    def source_read(path, start_line=1, max_lines=200):
        raise FileNotFoundError(path)

    with pytest.raises(FileNotFoundError):
        source_audit.source_audit_recorded(source_read)("missing.py")
    assert recorded == []


def test_unknown_tool_name_is_rejected():
    """잘못된 입력: 감사 대상 목록에 없는 도구를 감싸면 기동 시 바로 실패한다."""
    def not_a_source_tool():
        return None

    with pytest.raises(ValueError):
        source_audit.source_audit_recorded(not_a_source_tool)


def test_server_wraps_all_source_tools_before_registration():
    """등록부 대조: 서버가 감사 대상 도구 전부를 mcp.tool() 등록 전에 감싸는지 확인한다."""
    server_source = Path("harness/mcp/sps_harness_server.py").read_text(encoding="utf-8")
    wrap_at = server_source.index("source_audit_recorded(globals()[_audit_tool_name])")
    for tool_name in source_audit.SOURCE_AUDIT_TASK_TYPES:
        assert wrap_at < server_source.index(f"mcp.tool()({tool_name})")
