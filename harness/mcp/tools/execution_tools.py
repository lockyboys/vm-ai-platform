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

from config import LOG_PATH
from common.common_function import ensure_dirs, logger

PROJECT_ROOT = Path("/data/vm_project").resolve()
EXECUTION_ROOT = (PROJECT_ROOT / "FastAPI" / "LangGraph").resolve()
MAX_TIMEOUT_SECONDS = 120
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
    timeout_seconds: int = 120,
    execute_confirmed: bool = False,
) -> dict[str, Any]:
    """
    Plan or execute one approved project-relative Python source file.

    dry_run=True never starts Python or an LLM. Execution also requires
    execute_confirmed=True, which the caller may set only after explicit user approval.
    """
    source_path = _resolve_source_path(path)
    timeout = max(1, min(int(timeout_seconds), MAX_TIMEOUT_SECONDS))
    command = [sys.executable, str(source_path)]

    plan: dict[str, Any] = {
        "dry_run": bool(dry_run),
        "executed": False,
        "path": str(source_path.relative_to(PROJECT_ROOT)),
        "command": ["python", str(source_path.relative_to(PROJECT_ROOT))],
        "timeout_seconds": timeout,
        "llm_call_allowed": not dry_run and execute_confirmed,
        "approval_required": not dry_run and not execute_confirmed,
        "log_path": str(Path(LOG_PATH) / "sps_source_execution.log"),
    }
    if dry_run or not execute_confirmed:
        return plan

    ensure_dirs()
    logger.info("MCP source execution started: %s", plan["path"])
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
