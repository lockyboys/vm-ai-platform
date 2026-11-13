"""범용 자기 수리 엔진 테스트 (2026-11-10 LuckyBoys: 어디서나 쓰는 일반화된 스스로 고치는 앱).

네트워크·LLM·systemd 없이 함수 주입만 사용한다.
  - validate_target: 잘못된 대상 스펙 거부
  - evaluate: exit_code / json_min / pytest 판정
  - run_with_repair: 실패→수리 PASS→재실행 성공, NO_CHANGE, 실패 시 restore, 라운드 상한, scope 전달
  - register_target(config): dry-run 은 파일 불변, 적용은 임시 사본만 변경, compile 실패 시 원본 유지
  - repository 백엔드 미가용 시 ValueError
  - 미등록 대상 실행 거부, job dry-run 계획, 잘못된 job_id 거부
"""
from __future__ import annotations

import asyncio
import json
import re

import pytest

from harness.mcp.agents import self_repair_engine as engine


def _spec(**overrides):
    """테스트용 정상 대상 스펙(실제 존재하는 모듈 이름만 사용, 실행은 주입으로 대체)."""
    spec = {
        "name": "sample_target",
        "command": {"module": "harness.mcp.agents.self_repair_engine"},
        "args_template": ["--count", "{expected}"],
        "params": ["expected"],
        "verdict": {"type": "json_min", "source": "stdout", "field": "result.success", "min_param": "expected"},
        "scope": {"allowed_paths": ["harness/mcp/agents/self_repair_engine.py"],
                  "regression_tests": ["harness/tests/test_self_repair_engine_20261110.py"]},
        "max_rounds": 2,
        "timeout_seconds": 60,
    }
    spec.update(overrides)
    return spec


# ---------------------------------------------------------------------------
# validate_target
# ---------------------------------------------------------------------------
def test_validate_target_accepts_good_spec():
    assert engine.validate_target(_spec())["name"] == "sample_target"


@pytest.mark.parametrize("overrides", [
    {"name": "Bad-Name"},
    {"command": {}},
    {"command": {"script": "../outside.py"}},
    {"command": {"script": "/abs/path.py"}},
    {"command": {"script": "no_such_file_20261110.py"}},
    {"command": {"module": "bad module"}},
    {"args_template": "--x"},
    {"args_template": ["{unknown}"]},
    {"params": ["bad-name"]},
    {"verdict": {"type": "nope"}},
    {"verdict": {"type": "json_min", "source": "stdout", "field": "success", "min_param": "missing"}},
    {"verdict": {"type": "pytest", "tests": []}},
    {"scope": {"allowed_paths": [], "regression_tests": ["a.py"]}},
    {"max_rounds": 0},
    {"max_rounds": True},
    {"timeout_seconds": 36001},
])
def test_validate_target_rejects_bad_spec(overrides):
    with pytest.raises(ValueError):
        engine.validate_target(_spec(**overrides))


@pytest.mark.parametrize("params", [{"other": 1}, {"expected": "a\nb"}, {"expected": [1]}, {}])
def test_validate_params_rejects_bad_values(params):
    with pytest.raises(ValueError):
        engine.validate_params(engine.validate_target(_spec()), params)


# ---------------------------------------------------------------------------
# evaluate
# ---------------------------------------------------------------------------
def test_evaluate_exit_code():
    assert engine.evaluate({"type": "exit_code"}, {"returncode": 0, "stdout": "", "stderr": ""}, {}) is None
    failure = engine.evaluate({"type": "exit_code"}, {"returncode": 2, "stdout": "", "stderr": "boom"}, {})
    assert failure["category"] == "exit_code" and "boom" in failure["evidence"]


def test_evaluate_json_min_shortfall_and_success():
    verdict = {"type": "json_min", "source": "stdout", "field": "result.success", "min_param": "expected"}
    short = engine.evaluate(verdict, {"returncode": 0, "stdout": 'log\n{"result": {"success": 10}}\n', "stderr": ""},
                            {"expected": 1000})
    assert short["category"] == "shortfall" and "10" in short["error"] and "1000" in short["error"]
    assert engine.evaluate(verdict, {"returncode": 0, "stdout": '{"result": {"success": 1000}}', "stderr": ""},
                           {"expected": 1000}) is None


def test_evaluate_json_min_unreadable():
    verdict = {"type": "json_min", "source": "stdout", "field": "success", "min_param": "expected"}
    failure = engine.evaluate(verdict, {"returncode": 0, "stdout": "not json", "stderr": ""}, {"expected": 1})
    assert failure["category"] == "unreadable"


def test_evaluate_pytest():
    verdict = {"type": "pytest", "tests": ["harness/tests/x.py"]}
    assert engine.evaluate(verdict, {"returncode": 0, "stdout": "1 passed", "stderr": ""}, {}) is None
    assert engine.evaluate(verdict, {"returncode": 1, "stdout": "1 failed", "stderr": ""}, {})["category"] == "test_failed"


# ---------------------------------------------------------------------------
# run_with_repair
# ---------------------------------------------------------------------------
def _staged_result():
    """PARTNER 가 staged change set 을 남긴 것처럼 보이는 수리 결과."""
    change = {"change_set_id": "cs1", "success": True, "dry_run": False,
              "staged_groups": {"source": ["harness/mcp/agents/self_repair_engine.py"]}}
    return {"verdict": "PASS", "tool_evidence": [{"content": json.dumps(change)}], "steps": []}


@pytest.fixture
def report_dir(tmp_path, monkeypatch):
    monkeypatch.setitem(engine._SETTINGS, "report_dir", str(tmp_path))
    return tmp_path


def test_run_with_repair_fails_then_repairs_then_ok(report_dir):
    outputs = iter(['{"result": {"success": 10}}', '{"result": {"success": 1000}}'])
    seen_scope = []

    def partner(task, round_no, scope):
        seen_scope.append(scope)
        assert "shortfall" in task
        return _staged_result()

    out = engine.run_with_repair(
        _spec(), {"expected": 1000},
        run_fn=lambda spec, params: {"returncode": 0, "stdout": next(outputs), "stderr": ""},
        partner_fn=partner, backup_fn=lambda paths: {}, restore_fn=lambda backups: None)
    assert out["result"] == "OK"
    assert out["first"]["category"] == "shortfall"
    assert seen_scope[0]["allowed_paths"] == ["harness/mcp/agents/self_repair_engine.py"]
    assert list(report_dir.rglob("repair_*.json"))          # 증빙 파일이 남는다


def test_run_with_repair_ok_without_repair(report_dir):
    out = engine.run_with_repair(
        _spec(), {"expected": 1},
        run_fn=lambda spec, params: {"returncode": 0, "stdout": '{"result": {"success": 5}}', "stderr": ""},
        partner_fn=lambda *a: pytest.fail("no repair expected"),
        backup_fn=lambda paths: {}, restore_fn=lambda backups: None)
    assert out["result"] == "OK" and out["rounds"] == []


def test_run_with_repair_no_change_stops(report_dir):
    out = engine.run_with_repair(
        _spec(), {"expected": 1000},
        run_fn=lambda spec, params: {"returncode": 0, "stdout": '{"result": {"success": 1}}', "stderr": ""},
        partner_fn=lambda task, round_no, scope: {"verdict": "PASS", "tool_evidence": [], "steps": []},
        backup_fn=lambda paths: {}, restore_fn=lambda backups: None)
    assert out["result"] == "REPAIR_FAILED"
    assert out["rounds"][0]["outcome"] == "NO_CHANGE"


def test_run_with_repair_restores_on_failed_verdict_and_caps_rounds(report_dir):
    restored = []
    out = engine.run_with_repair(
        _spec(max_rounds=2), {"expected": 1000},
        run_fn=lambda spec, params: {"returncode": 0, "stdout": '{"result": {"success": 1}}', "stderr": ""},
        partner_fn=lambda task, round_no, scope: {**_staged_result(), "verdict": "TEST_FAILED"},
        backup_fn=lambda paths: {"backup": True}, restore_fn=lambda backups: restored.append(backups))
    assert out["result"] == "REPAIR_FAILED"
    assert len(out["rounds"]) == 2 and len(restored) == 2   # 라운드 상한 + 매번 원복


# ---------------------------------------------------------------------------
# 등록소
# ---------------------------------------------------------------------------
CONFIG_TEXT = "X = 1\n"


def test_register_config_dry_run_does_not_change_file(tmp_path):
    path = tmp_path / "config_copy.py"
    path.write_text(CONFIG_TEXT, encoding="utf-8")
    plan = engine.register_target(_spec(), backend="config", dry_run=True, config_path=path)
    assert plan["dry_run"] is True and path.read_text(encoding="utf-8") == CONFIG_TEXT


def test_register_config_apply_writes_block_and_backup(tmp_path):
    path = tmp_path / "config_copy.py"
    path.write_text(CONFIG_TEXT, encoding="utf-8")
    engine.register_target(_spec(), backend="config", dry_run=False, config_path=path)
    text = path.read_text(encoding="utf-8")
    assert text.startswith(CONFIG_TEXT) and engine.BLOCK_START in text and "sample_target" in text
    namespace = {}
    exec(compile(text, str(path), "exec"), namespace)
    assert namespace["SELF_REPAIR_TARGETS"]["sample_target"]["max_rounds"] == 2
    assert list(tmp_path.glob("config_copy_BACKUP_*.py"))
    with pytest.raises(ValueError):                         # 같은 이름은 overwrite=True 일 때만
        engine.register_target(_spec(), backend="config", dry_run=False, config_path=path)
    engine.register_target(_spec(max_rounds=3), backend="config", dry_run=False, overwrite=True, config_path=path)
    assert "'max_rounds': 3" in path.read_text(encoding="utf-8")


def test_register_config_keeps_original_when_compile_fails(tmp_path, monkeypatch):
    path = tmp_path / "config_copy.py"
    path.write_text(CONFIG_TEXT, encoding="utf-8")
    # 2026-11-12 분리: 등록소 본체가 harness/selffix/registry.py 로 옮겨져 그 모듈의 _render_block 을 바꿔치기한다
    from harness.selffix import registry
    monkeypatch.setattr(registry, "_render_block", lambda targets: "SELF_REPAIR_TARGETS = {(\n")
    with pytest.raises(ValueError):
        engine.register_target(_spec(), backend="config", dry_run=False, config_path=path)
    assert path.read_text(encoding="utf-8") == CONFIG_TEXT


def test_repository_backend_unavailable():
    with pytest.raises(ValueError, match="repository backend unavailable"):
        engine.register_target(_spec(), backend="repository", dry_run=True)


def test_unknown_backend_rejected():
    with pytest.raises(ValueError):
        engine.register_target(_spec(), backend="nope")


# ---------------------------------------------------------------------------
# MCP 도구
# ---------------------------------------------------------------------------
def test_run_rejects_unregistered_target():
    with pytest.raises(ValueError, match="not registered"):
        asyncio.run(engine.self_repair_run("no_such_target_20261110"))


def test_run_dry_run_plan(monkeypatch):
    monkeypatch.setattr(engine, "get_target", lambda name: engine.validate_target(_spec()))

    async def forbidden(*args, **kwargs):
        raise AssertionError("dry-run must not start a process")
    monkeypatch.setattr(asyncio, "create_subprocess_exec", forbidden)
    plan = asyncio.run(engine.self_repair_run("sample_target", '{"expected": 10}'))
    assert plan["dry_run"] is True and plan["executed"] is False
    assert re.fullmatch(r"[0-9a-f]{32}", plan["job_id"])
    assert "--wait" not in plan["command"] and "--pipe" not in plan["command"]


@pytest.mark.parametrize("job_id", ["../etc", "ABC", "1234", "g" * 32])
def test_bad_job_id_rejected(job_id):
    with pytest.raises(ValueError):
        asyncio.run(engine.self_repair_run("sample_target", job_id=job_id))


def test_register_tool_dry_run_default(monkeypatch, tmp_path):
    path = tmp_path / "config_copy.py"
    path.write_text(CONFIG_TEXT, encoding="utf-8")
    monkeypatch.setattr(engine, "CONFIG_PATH", path)
    result = asyncio.run(engine.self_repair_target_register(json.dumps(_spec())))
    assert result["dry_run"] is True and path.read_text(encoding="utf-8") == CONFIG_TEXT
