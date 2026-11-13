"""스스로 고치는 앱 — 백그라운드 job 공통 부품 (2026-11-12 분리, 원본: harness/mcp/agents/self_repair_engine.py).

여기 있는 것
    PROJECT_ROOT / KST       : 프로젝트 루트와 한국 시간대
    job_files(job_dir, id)   : job_id 형식 검사(경로 조작 차단) + request/result 파일 경로
    now_stamp()              : 파일 이름용 KST 시각
    job_status(...)          : result.json 이 있으면 그대로, 없으면 systemctl 로 running/failed 판정
systemd 명령·0600 원자 저장·비밀값 마스킹은 아직 multi_persona_tools 에 있다(리뷰 앱 분리 단계에서 옮길 예정, 미확인).
"""
from __future__ import annotations

import asyncio
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

# 2026-11-12: systemd 명령·원자 저장·마스킹은 기존 구현을 그대로 재사용(수정하지 않음)
from harness.mcp.tools.multi_persona_tools import PROJECT_ROOT, _mask_secrets, _systemd_command, _write_json

KST = ZoneInfo("Asia/Seoul")
JOB_ID_PATTERN = re.compile(r"[0-9a-f]{32}")  # 경로 조작 차단용 job_id(소문자 16진수 32자리)

__all__ = ["PROJECT_ROOT", "KST", "JOB_ID_PATTERN", "job_files", "now_stamp", "job_status",
           "_mask_secrets", "_systemd_command", "_write_json"]


def job_files(job_dir: Path, job_id: Any) -> tuple[Path, Path]:
    """job_id 형식을 검사(경로 조작 차단)하고 request/result 파일 경로를 돌려준다.

    job_dir: job 폴더들이 들어갈 상위 폴더(절대 경로). 폴더 이름은 'job_<id>'.
    """
    if not isinstance(job_id, str) or JOB_ID_PATTERN.fullmatch(job_id) is None:
        raise ValueError("job_id must be a 32-character hexadecimal identifier")
    folder = Path(job_dir) / ("job_" + job_id)
    return folder / "request.json", folder / "result.json"


def now_stamp() -> str:
    """파일 이름용 KST 시각(초 단위)."""
    return datetime.now(KST).strftime("%Y%m%d_%H%M%S")


async def job_status(request_path: Path, result_path: Path, label: str) -> dict:
    """result.json 이 있으면 그대로, 없으면 systemd 유닛 상태로 running/failed 를 판정한다.

    label: 오류 문구에 넣을 job 종류 이름(예: 'self_repair').
    """
    if not request_path.is_file():
        # 원본 문구 유지: '<label> job not found: <job_id>'
        raise FileNotFoundError(f"{label} job not found: {request_path.parent.name.removeprefix('job_')}")
    if result_path.is_file():
        return json.loads(result_path.read_text(encoding="utf-8"))
    request = json.loads(request_path.read_text(encoding="utf-8"))
    state = {**request, "executed": True, "state": "running", "success": None,
             "elapsed_seconds": round(time.time() - request["started_at"], 3)}
    process = await asyncio.create_subprocess_exec(
        "systemctl", "show", request["unit"], "--property=LoadState,ActiveState,Result",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        output, _ = await asyncio.wait_for(process.communicate(), timeout=3)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return {**state, "state": "status_unavailable"}
    if result_path.is_file():  # 조회 중에 끝났을 수 있다
        return json.loads(result_path.read_text(encoding="utf-8"))
    properties = dict(line.split("=", 1) for line in output.decode(errors="replace").splitlines() if "=" in line)
    if properties.get("LoadState") == "not-found" or properties.get("ActiveState") in {"failed", "inactive"}:
        return {**state, "state": "failed", "success": False,
                "error": f"{label} job stopped without a final result",
                "unit_result": properties.get("Result", "unknown")}
    return state
