"""[실행·판정] 자기 수리 대상을 실행하고 성공 기준으로 판정한다 (2026-11-12 분리, 원본: self_repair_engine.py §2).

판정(verdict) 3종
    exit_code : 종료 코드 0 이면 성공
    json_min  : stdout 마지막 JSON 줄(또는 파일)의 field 값이 min_param 값 이상이면 성공(건수 부족 → shortfall)
    pytest    : 지정 테스트가 통과하면 성공(command 를 생략하면 pytest 자체를 실행)
실패 결과: {'category': exit_code|test_failed|unreadable|shortfall, 'error', 'evidence'}
설정: 루트 config.py 의 SELF_REPAIR['max_evidence_chars'] (일반 지침 4).
"""
from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

import config as project_config  # 루트 공통 설정(일반 지침 4)
from harness.selffix.job_runner import PROJECT_ROOT

_SETTINGS = project_config.SELF_REPAIR


def _argv(spec: dict, params: dict) -> list[str]:
    """셸 없이 실행할 인자 목록을 만든다(command 없는 pytest 판정이면 pytest 를 실행)."""
    if spec["command"] is None:
        return [sys.executable, "-m", "pytest", "-q", *spec["verdict"]["tests"]]
    command = spec["command"]
    head = ([sys.executable, "-m", command["module"]] if "module" in command
            else [sys.executable, str(PROJECT_ROOT / command["script"])])
    return head + [argument.format(**params) for argument in spec["args_template"]]


def _default_run(spec: dict, params: dict) -> dict:
    """대상을 새 프로세스로 실행한다. 시간 초과도 결과로 돌려준다(예외로 숨기지 않음)."""
    try:
        done = subprocess.run(_argv(spec, params), cwd=str(PROJECT_ROOT), capture_output=True, text=True,
                              timeout=spec["timeout_seconds"])
        return {"returncode": done.returncode, "stdout": done.stdout, "stderr": done.stderr}
    except subprocess.TimeoutExpired as error:
        return {"returncode": -9, "stdout": str(error.stdout or ""),
                "stderr": f"timeout after {spec['timeout_seconds']}s"}


def _evidence(run_result: dict) -> str:
    """수리 작업문에 넣을 증빙: 출력 끝부분(오류는 보통 끝에 있다)."""
    limit = int(_SETTINGS["max_evidence_chars"])
    text = f"[stdout]\n{run_result.get('stdout', '')}\n[stderr]\n{run_result.get('stderr', '')}"
    return text[-limit:]


def evaluate(verdict: dict, run_result: dict, params: dict) -> dict | None:
    """성공이면 None, 실패면 {'category','error','evidence'}."""
    evidence = _evidence(run_result)
    returncode = run_result.get("returncode")
    if verdict["type"] == "exit_code":
        return None if returncode == 0 else {"category": "exit_code", "error": f"exit code {returncode}",
                                             "evidence": evidence}
    if verdict["type"] == "pytest":
        return None if returncode == 0 else {"category": "test_failed", "error": f"pytest exit {returncode}",
                                             "evidence": evidence}
    # json_min: 출력(또는 파일)에서 숫자를 읽어 목표와 비교
    try:
        if verdict["source"] == "stdout":
            lines = [line for line in str(run_result.get("stdout", "")).splitlines() if line.strip()]
            data = json.loads(lines[-1])
        else:
            data = json.loads((PROJECT_ROOT / verdict["file_template"].format(**params)).read_text(encoding="utf-8"))
        value: Any = data
        for part in verdict["field"].split("."):
            value = value[part]
        expected = int(params[verdict["min_param"]])
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{verdict['field']} is not an integer")
    except Exception as error:  # noqa: BLE001 - 판독 불가도 실패 유형으로 보고한다(성공으로 숨기지 않음)
        return {"category": "unreadable", "error": f"{type(error).__name__}: {str(error)[:300]}",
                "evidence": evidence}
    if value >= expected:
        return None
    return {"category": "shortfall", "error": f"{verdict['field']}={value} < 목표 {expected}", "evidence": evidence}
