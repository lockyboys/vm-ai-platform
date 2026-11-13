"""스스로 고치는 엔진 분리 + 메리츠 판정 불일치 수정 테스트 (2026-11-12, LuckyBoys 승인).

검증 대상
1) 분리: harness/selffix/ 새 모듈(target_spec / runner / repair_loop / registry / job_runner)이 있고,
   기존 진입점 harness.mcp.agents.self_repair_engine 이 같은 함수 객체를 그대로 내보낸다(외부 import 무변경).
2) 잘못된 입력: job_id 경로 조작, 잘못된 대상 스펙은 새 모듈에서도 ValueError.
3) 메리츠 재현: 수집기가 탐색(DISCOVER) 단계에서 실패하면 status.json 에 success 키가 없다.
   수정 전에는 엔진이 KeyError → 'unreadable' 로만 보고해 건수가 몇 건인지 알 수 없었다.
   수정 후에는 어댑터가 success 를 0 으로 채우고(success_missing=True 로 표시) 엔진은 'shortfall' 로 판정한다.
네트워크·LLM·systemd 를 쓰지 않는다.
"""
import io
import json
from contextlib import redirect_stdout

import pytest

from harness.mcp.agents import self_repair_engine as engine
from harness.mcp.tools import document_collect_target as adapter
from harness.selffix import job_runner, registry, repair_loop, runner, target_spec

# json_min 판정 규칙(config.SELF_REPAIR_TARGETS['document_collect'] 의 verdict 와 같은 모양)
VERDICT = {"type": "json_min", "source": "stdout", "field": "success", "min_param": "expected_min_count"}
PARAMS = {"name": "meritz", "company_name": "메리츠화재", "expected_min_count": 1}


# ---------------------------------------------------------------- 1) 분리 + 기존 진입점 유지
@pytest.mark.parametrize("name, module", [
    ("validate_target", target_spec), ("validate_params", target_spec),
    ("evaluate", runner), ("run_with_repair", repair_loop),
    ("register_target", registry), ("list_targets", registry), ("get_target", registry),
])
def test_engine_reexports_split_functions(name, module):
    # 외부 코드·테스트가 쓰는 engine.<함수> 가 새 모듈의 같은 객체여야 한다(복사본이면 수정이 갈라진다)
    assert getattr(engine, name) is getattr(module, name)


def test_engine_keeps_mcp_entrypoints():
    # MCP 서버가 등록하는 두 도구는 계속 엔진 모듈에 있어야 한다
    assert callable(engine.self_repair_run) and callable(engine.self_repair_target_register)


# ---------------------------------------------------------------- 2) 잘못된 입력
@pytest.mark.parametrize("job_id", ["../etc", "ABC", "1234", "g" * 32, None, 5])
def test_job_files_rejects_bad_job_id(job_id, tmp_path):
    with pytest.raises(ValueError):
        job_runner.job_files(tmp_path, job_id)


def test_job_files_builds_paths_inside_given_dir(tmp_path):
    request, result = job_runner.job_files(tmp_path, "a" * 32)
    assert request == tmp_path / ("job_" + "a" * 32) / "request.json"
    assert result.name == "result.json"


@pytest.mark.parametrize("spec", [None, {}, {"name": "Bad-Name"}, {"name": "ok", "verdict": {"type": "nope"}}])
def test_target_spec_rejects_bad_spec(spec):
    with pytest.raises(ValueError):
        target_spec.validate_target(spec)


# ---------------------------------------------------------------- 3) 메리츠 재현·수정
def _adapter_stdout(status: dict) -> dict:
    """가짜 수집기 결과로 어댑터 main 을 실행하고 stdout 마지막 줄 JSON 을 돌려준다."""
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = adapter.main(["--collect", "meritz", "메리츠화재", "1"],
                            run_collector=lambda request: (status, "/tmp/status.json", ""))
    assert code == 0
    return json.loads([line for line in buffer.getvalue().splitlines() if line.strip()][-1])


# 메리츠 실제 출력(2026-11-11 job da702ac6…)과 같은 모양: 탐색 실패라 success·targets 키가 없다
DISCOVER_FAILED = {"state": "FAILED", "phase": "DISCOVER", "profile": "meritz", "result": "REPAIR_FAILED"}


def test_adapter_fills_missing_success_with_zero_and_marks_it():
    line = _adapter_stdout(DISCOVER_FAILED)
    assert line["success"] == 0 and line["success_missing"] is True
    assert line["phase"] == "DISCOVER"                       # 원래 status 값은 그대로 보존


@pytest.mark.parametrize("bad", ["12", 1.5, True, None, [1]])
def test_adapter_treats_non_integer_success_as_missing(bad):
    # 정수가 아닌 값(문자열·실수·bool·None)은 건수로 믿지 않는다 → 0 + 표시
    line = _adapter_stdout({**DISCOVER_FAILED, "success": bad})
    assert line["success"] == 0 and line["success_missing"] is True


def test_adapter_keeps_real_success_count():
    line = _adapter_stdout({"state": "COMPLETED", "targets": 12, "success": 10, "failed": 2})
    assert line["success"] == 10 and line["success_missing"] is False


def test_engine_judges_discover_failure_as_shortfall_not_unreadable():
    # 재현: 수정 전에는 category='unreadable'(KeyError: 'success') 였다
    stdout = json.dumps(_adapter_stdout(DISCOVER_FAILED), ensure_ascii=False)
    failure = engine.evaluate(VERDICT, {"returncode": 0, "stdout": stdout, "stderr": ""}, PARAMS)
    assert failure["category"] == "shortfall" and "success=0" in failure["error"]
