# =============================================================================
# File Name   : harness/mcp/tools/execution_tools.py
# Purpose     : 허용된 프로젝트 Python 소스의 dry-run/실행 결과를 반환하는 MCP 도구
# =============================================================================
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import config as project_config
from config import LOG_PATH
from common.common_function import ensure_dirs, logger
# 2026-10-25 LuckyBoys: 위험 명령(sudo·ssh·curl 등) 탐지·표시·승인 확인. 구현은 haness에 두고 연결만 한다(일반 지침 10).
from haness.mcp.tools.command_approval import approval_matches, command_names, scan

PROJECT_ROOT = Path("/data/vm_project").resolve()
EXECUTION_ROOT = (PROJECT_ROOT / "FastAPI" / "LangGraph").resolve()
# 실행 시간 상한은 두지 않고 양의 정수 여부만 검증한다.
MAX_TIMEOUT_SECONDS = 3600
MAX_OUTPUT_CHARS = 12000
_SECRET_PATTERN = re.compile(
    r"(?i)(api[_-]?key|token|password|secret|authorization)(\s*[=:]\s*)[^\s,;]+"
)


def _mask_secrets(value: str) -> str:
    return _SECRET_PATTERN.sub(r"\1\2[REDACTED]", value)


def _resolve_source_path(path: str) -> Path:
    candidate = (PROJECT_ROOT / path).resolve()
    if candidate.suffix != ".py":
        raise ValueError("Only Python source files are allowed.")
    if EXECUTION_ROOT not in candidate.parents:
        raise ValueError("Execution is limited to FastAPI/LangGraph sources.")
    if not candidate.is_file():
        raise FileNotFoundError(f"Source file not found: {path}")
    return candidate


def _trim_output(value: str) -> str:
    masked = _mask_secrets(value)
    if len(masked) <= MAX_OUTPUT_CHARS:
        return masked
    return masked[:MAX_OUTPUT_CHARS] + "\n...[truncated]"


def mcp_codex_apps_run_python_source(
    path: str,
    input_text: str = "",
    dry_run: bool = True,
    timeout_seconds: int = project_config.SPS_SOURCE_EXECUTION_TIMEOUT_SECONDS,
    execute_confirmed: bool = False,
    ssh_target: str = "",
    ssh_operation: str = "hash",
    argv: list[str] | None = None,
    job_id: str = "",
    approved_commands: list[str] | None = None,
) -> dict[str, Any]:
    """
    Plan or execute one approved project-relative Python source file.

    dry_run=True never starts Python or an LLM. Execution also requires
    execute_confirmed=True, which the caller may set only after explicit user approval.

    위험 명령 승인(2026-10-25): 결과의 commands_detected/approval_commands에 실행 파일과 그 파일이
    import하는 프로젝트 모듈에서 찾은 sudo·ssh·curl 등을 항상 표시한다. 찾은 명령이 있으면
    approved_commands가 approval_commands와 정확히 같아야만 실행한다. 호출자는 사용자에게
    approval_commands를 보여 주고 허락을 받은 뒤에만 그 목록을 넘긴다.
    """
    # SSH 접속은 중앙 설정의 대상만 허용하고 haness 구현에 위임합니다.
    if ssh_target:
        # 원격 실행은 그 자체가 ssh 사용이다 → 실행 시 approved_commands에 "ssh"가 있어야 한다.
        if not dry_run and execute_confirmed and "ssh" not in (approved_commands or []):
            return {"dry_run": False, "executed": False, "approval_required": True,
                    "approval_commands": ["ssh"], "commands_detected": [{"command": "ssh", "target": ssh_target}],
                    "blocked_reason": "ssh_target 실행은 사용자 승인(approved_commands=['ssh'])이 필요합니다."}
        from haness.mcp.tools.ssh_execution_tools import run_remote
        return run_remote(
            path=path, ssh_target=ssh_target, ssh_operation=ssh_operation,
            argv=argv, job_id=job_id, dry_run=dry_run,
            execute_confirmed=execute_confirmed, timeout_seconds=timeout_seconds,
        )
    if job_id:
        # 조회는 실행 승인 없이 가능하며 작업 소스 경로를 반드시 대조한다.
        from haness.mcp.tools.source_execution_jobs import status
        return status(path, job_id)
    if argv or ssh_operation != "hash":
        raise ValueError("SSH arguments require ssh_target")
    source_path = _resolve_source_path(path)
    if type(timeout_seconds) is not int or timeout_seconds < 1:
        raise ValueError("timeout_seconds must be a positive integer")
    timeout = timeout_seconds
    command = [sys.executable, str(source_path)]
    # 실행 전에 항상 위험 명령을 찾아 표시한다(dry-run 포함).
    detected = scan(source_path, PROJECT_ROOT)
    names = command_names(detected)
    commands_ok = approval_matches(detected, approved_commands)

    plan: dict[str, Any] = {
        "dry_run": bool(dry_run),
        "executed": False,
        "path": str(source_path.relative_to(PROJECT_ROOT)),
        "command": ["python", str(source_path.relative_to(PROJECT_ROOT))],
        "timeout_seconds": timeout,
        "llm_call_allowed": not dry_run and execute_confirmed and commands_ok,
        "approval_required": not dry_run and (not execute_confirmed or not commands_ok),
        "approval_commands": names,
        "commands_detected": detected[:50],
        "approved_commands": sorted(set(approved_commands or [])),
        "log_path": str(Path(LOG_PATH) / "sps_source_execution.log"),
    }
    if dry_run or not execute_confirmed:
        return plan
    if not commands_ok:
        plan["blocked_reason"] = ("위험 명령 사용 파일입니다. approval_commands를 사용자에게 보여 주고 허락을 받은 뒤 "
                                  "approved_commands에 같은 목록을 넣어 다시 호출하세요.")
        logger.info("MCP source execution blocked for approval: %s %s", plan["path"], names)
        return plan

    if timeout > project_config.SPS_GENERAL_UNIT_RUNTIME_SECONDS:
        # 장기 실행은 독립 유닛으로 넘겨 MCP 요청을 계속 열어 두지 않는다.
        from haness.mcp.tools.source_execution_jobs import submit
        return submit(plan, source_path, input_text)
    ensure_dirs()
    logger.info("MCP source execution started: %s approved_commands=%s", plan["path"], names)
    try:
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            input=input_text,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
            env=os.environ.copy(),
        )
    except subprocess.TimeoutExpired as error:
        logger.exception("MCP source execution timed out: %s", plan["path"])
        return {
            **plan,
            "executed": True,
            "timed_out": True,
            "returncode": None,
            "stdout": _trim_output(error.stdout or ""),
            "stderr": _trim_output(error.stderr or ""),
        }
    except OSError as error:
        logger.exception("MCP source execution failed: %s", plan["path"])
        return {
            **plan,
            "executed": True,
            "timed_out": False,
            "returncode": None,
            "stdout": "",
            "stderr": _trim_output(str(error)),
        }

    logger.info(
        "MCP source execution finished: %s returncode=%s",
        plan["path"],
        completed.returncode,
    )
    return {
        **plan,
        "executed": True,
        "timed_out": False,
        "returncode": completed.returncode,
        "stdout": _trim_output(completed.stdout),
        "stderr": _trim_output(completed.stderr),
    }
