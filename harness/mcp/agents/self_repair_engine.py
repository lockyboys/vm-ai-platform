"""범용 자기 수리 엔진 — 어디서나 쓰는 "스스로 고치는 앱"의 MCP 진입점 (2026-11-10 LuckyBoys, 2026-11-12 분리).

한 줄 요약
    등록된 대상(target)을 실행 → 성공 기준(verdict)으로 판정 → 실패하면 페르소나 수리 체인으로 소스를 고치고
    (git add 까지, 커밋 없음) → 다시 실행해서 확인한다. 대상은 등록소(config.py 표시 블록 / MariaDB)에서만 꺼낸다.

2026-11-12 분리(LuckyBoys 결정: harness/selffix/ 한 곳으로 모으기)
    역할별 본체는 harness/selffix/ 로 옮겼고, 이 파일에는 MCP 도구 2개와 background worker 만 남겼다.
        harness/selffix/target_spec.py  [입력·검증]  validate_target, validate_params
        harness/selffix/runner.py       [실행·판정]  _argv, _default_run, evaluate
        harness/selffix/repair_loop.py  [수리]       _build_task, _default_partner, run_with_repair
        harness/selffix/registry.py     [등록]       register_target, list_targets, get_target
        harness/selffix/job_runner.py   [job 공통]   job_files, job_status, now_stamp
    기존 import(engine.validate_target 등)가 깨지지 않도록 같은 함수 객체를 그대로 다시 내보낸다.
    원본 백업: harness/backups/selffix_split_20261112/harness/mcp/agents/self_repair_engine.py
    주의: 테스트에서 등록소 내부(_render_block)를 바꿔치기하려면 harness.selffix.registry 를 patch 해야 한다.

왜 이렇게 만들었나(원본 설명 유지)
    - 기존 autodiscover_self_repair 는 "수집기 탐색 실패(NEEDS_NEW_RULE)" 한 가지만 고쳤다.
      메리츠 10건 사례처럼 "성공처럼 보이지만 건수 부족"은 못 고쳤고, 다른 프로그램에는 쓸 수 없었다.
    - 그래서 실행 방법·판정 방법·수리 범위를 '대상 스펙'으로 빼고, 엔진은 그 스펙만 보고 움직이게 했다.

보안 원칙(SECURITY)
    - MCP 로 임의 명령을 실행하지 않는다. 등록된 대상만 실행하고, 인자는 셸 없이 리스트로 넘긴다.
    - 실행·등록 모두 dry_run=True 가 기본값이다. 수리는 git add 까지만 하고 커밋하지 않는다.

설정: 루트 config.py 의 SELF_REPAIR / SELF_REPAIR_TARGETS (일반 지침 4).
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from time import monotonic
from typing import Any
from uuid import uuid4

import config as project_config  # 루트 공통 설정(일반 지침 4)
# [job 공통] 경로 검사·상태 조회 + 기존 systemd 명령·0600 원자 저장·비밀값 마스킹
from harness.selffix.job_runner import (KST, JOB_ID_PATTERN, PROJECT_ROOT, _mask_secrets,  # noqa: F401
                                        _systemd_command, _write_json, job_files, job_status, now_stamp)
# [입력·검증] 다시 내보내기(외부 import 유지)
from harness.selffix.target_spec import (FIELD_PATTERN, MAX_PARAM_TEXT, MAX_ROUNDS, MAX_TIMEOUT_SECONDS,  # noqa: F401
                                         MODULE_PATTERN, NAME_PATTERN, PARAM_PATTERN, VERDICT_TYPES,
                                         _positive_int, _safe_relative, _template_fields, _validate_command,
                                         _validate_verdict, validate_params, validate_target)
# [실행·판정]
from harness.selffix.runner import _argv, _default_run, _evidence, evaluate  # noqa: F401
# [수리]
from harness.selffix.repair_loop import _build_task, _default_partner, run_with_repair  # noqa: F401
# [등록]
from harness.selffix.registry import (BLOCK_END, BLOCK_START, BLOCK_VARIABLE, CONFIG_PATH,  # noqa: F401
                                      _read_block, _render_block, _replace_block, _repository_unavailable,
                                      get_target, list_targets, register_target)

_SETTINGS = project_config.SELF_REPAIR          # 엔진 설정(보고서·job 폴더, repository 테이블, job 상한 등)
_now_stamp = now_stamp                          # 기존 이름 유지
OUTPUT_LIMIT = 12000                            # MCP 응답 미리보기 한도


# ---------------------------------------------------------------------------
# 5. MCP 도구
# ---------------------------------------------------------------------------
def _parse_json(text: str, field: str) -> Any:
    try:
        return json.loads(text)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError(f"{field} must be JSON: {error}") from error


async def self_repair_target_register(spec_json: str, backend: str = "config", overwrite: bool = False,
                                      dry_run: bool = True) -> dict:
    """Register a self-repair target (backend=config|repository). dry_run=True by default."""
    return register_target(_parse_json(spec_json, "spec_json"), backend=backend, overwrite=overwrite,
                           dry_run=dry_run, config_path=CONFIG_PATH)


def _job_files(job_id: Any) -> tuple[Path, Path]:
    """job_id 형식을 검사(경로 조작 차단)하고 request/result 파일 경로를 돌려준다."""
    return job_files(PROJECT_ROOT / str(_SETTINGS["job_dir"]), job_id)


async def _job_status(job_id: str) -> dict:
    """result.json 이 있으면 그대로, 없으면 systemd 유닛 상태로 running/failed 를 판정한다."""
    request_path, result_path = _job_files(job_id)
    return await job_status(request_path, result_path, "self_repair")


async def self_repair_run(target: str, params_json: str = "{}", dry_run: bool = True,
                          job_id: str | None = None) -> dict:
    """Run a registered target with self-repair as a background job. dry_run=True by default; job_id reads status."""
    if job_id is not None:
        return await _job_status(job_id)
    spec = get_target(target)
    params = validate_params(spec, _parse_json(params_json, "params_json"))
    timeout = int(_SETTINGS["job_timeout_seconds"])
    new_id = uuid4().hex
    # 2026-11-14 LuckyBoys 선택 A: 자기 수리 유닛만 수명 상한을 job_timeout_seconds(36,000초)로 올린다
    # (기본 일반 유닛 상한 3600에 잘려 1시간에 강제 종료되던 문제. 다른 작업은 영향 없음).
    unit, command = _systemd_command(
        ["-m", "harness.mcp.agents.self_repair_engine", "--job-worker", new_id], timeout, "self-repair",
        runtime_cap=timeout)
    command = [argument for argument in command if argument not in {"--wait", "--pipe"}]  # 독립 유닛
    plan = {"dry_run": bool(dry_run), "executed": False, "job_id": new_id, "unit": unit, "command": command,
            "timeout_seconds": timeout, "target": spec["name"], "params": params, "argv": _argv(spec, params)}
    if dry_run:
        return plan
    request_path, result_path = _job_files(new_id)
    request_path.parent.mkdir(parents=True, mode=0o700)
    _write_json(request_path, {**plan, "started_at": time.time()})   # 0600 원자적 저장
    process = await asyncio.create_subprocess_exec(
        *command, cwd=str(PROJECT_ROOT), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        _, errors = await asyncio.wait_for(process.communicate(), timeout=10)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return {**plan, "executed": True, "state": "status_unavailable", "success": None}
    if process.returncode != 0:
        result = {**plan, "executed": False, "state": "failed", "success": False,
                  "stderr": _mask_secrets(errors.decode("utf-8", errors="replace"))}
        _write_json(result_path, result)
        return result
    return {**plan, "executed": True, "state": "running", "success": None}


def _run_job(job_id: str) -> None:
    """독립 systemd 유닛 안에서 job 하나를 실행하고 결과를 남긴다(실패도 결과 파일로)."""
    request_path, result_path = _job_files(job_id)
    plan = json.loads(request_path.read_text(encoding="utf-8"))
    started = monotonic()
    report, error = None, ""
    try:
        report = run_with_repair(get_target(plan["target"]), plan["params"])
    except Exception as exc:  # noqa: BLE001 - 조회에서 확인할 수 있게 결과 파일로 남긴다
        error = f"{type(exc).__name__}: {exc}"
    text = _mask_secrets(json.dumps(report, ensure_ascii=False, default=str)) if report is not None else ""
    _write_json(result_path, {**plan, "dry_run": False, "executed": True,
                              "state": "completed" if not error else "failed",
                              "success": bool(report and report["result"] == "OK"),
                              "result": (report or {}).get("result", "FAILED"),
                              "error": _mask_secrets(error) or None, "evidence": (report or {}).get("evidence"),
                              "elapsed_seconds": round(monotonic() - started, 3),
                              "output": text[:OUTPUT_LIMIT], "output_truncated": len(text) > OUTPUT_LIMIT})


if __name__ == "__main__" and len(sys.argv) == 3 and sys.argv[1] == "--job-worker":
    _run_job(sys.argv[2])
