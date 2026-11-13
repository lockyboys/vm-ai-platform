"""self_repair_collect — 건수가 부족해도 스스로 고치는 문서 수집 MCP 도구.

요청: LuckyBoys 2026-11-10 ("스스로 고치는 도구로 만들어 줘", 결정 B: 규칙 실패뿐 아니라 '목표 건수 미달'도 수리,
      목표 건수는 (가) 호출자가 expected_min_count 로 직접 넣는다).

왜 필요한가
    기존 수리 루프(harness/mcp/agents/autodiscover_self_repair.auto_with_repair)는 탐색기가
    NEEDS_NEW_RULE 을 낼 때만 수리한다. 메리츠화재처럼 "10건만 받고 성공"으로 끝나는 경우는
    실패로 보지 않아 아무도 고치지 않았다. 이 도구는 수집이 끝난 뒤 status.json 의 success(검증된 PDF 수)를
    목표와 비교해, 부족하면 같은 NEEDS_NEW_RULE 모양(category=shortfall)의 보고서를 만들어
    기존 수리 루프에 그대로 넘긴다. 수리 엔진은 새로 만들지 않고 재사용한다(중복 구현 금지).

흐름
    self_repair_collect(dry_run=False) → 독립 systemd 유닛(--job-worker) → run(request)
      → auto_with_repair(request, auto_fn=collect_and_check)
         1) collect_and_check: 수집기를 새 프로세스로 실행(--onboard 또는 --worker) → status.json → check_shortfall
         2) 부족이면 NEEDS_NEW_RULE(shortfall) → 페르소나 수리 체인 → 회귀 테스트 → git add(커밋 없음)
         3) 수리 뒤 collect_and_check 재실행(수집기는 이어받기 지원) → 목표 달성이면 DISCOVERED_COLLECTED

설정: 루트 config.py 의 SELF_REPAIR_COLLECT (일반 지침 4). 사이트 이름·URL 은 코드에 없다.
DB: 저장 요청이 없어 연결·변경하지 않는다(common.database 미사용 — 기존 수집기·수리 루프와 같은 기준).
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from time import monotonic
from typing import Any, Callable
from uuid import uuid4

import config as project_config  # 루트 공통 설정(일반 지침 4)
from common.common_function import now_kst_iso  # 공통 함수(일반 지침 4)
# 백그라운드 job 은 orchestrator_tools 와 같은 systemd 명령·원자적 JSON 저장·비밀값 마스킹을 재사용한다.
from harness.mcp.tools.multi_persona_tools import PROJECT_ROOT, _mask_secrets, _systemd_command, _write_json

_SETTINGS = project_config.SELF_REPAIR_COLLECT
NAME_PATTERN = re.compile(r"^[a-z0-9_]{1,64}$")      # 수집기 프로파일 이름 규칙과 같다
_JOB_ID_PATTERN = re.compile(r"[0-9a-f]{32}")          # 경로 조작 차단용 job_id 형식
MAX_COMPANY_CHARS = 100                                # 회사명 길이 상한(한 줄)
MAX_KEYWORD_CHARS = 50                                 # 문서 키워드 길이 상한
_OUTPUT_LIMIT = 12000                                  # MCP 응답 미리보기 한도(orchestrator_tools 와 같음)


# ---------------------------------------------------------------------------
# 순수 함수 (테스트 대상)
# ---------------------------------------------------------------------------
def _require_positive_int(value: Any, field: str) -> int:
    """1 이상 정수만 통과. bool 은 int 의 하위형이라 따로 거부한다(True 가 1로 통과하는 것 방지)."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field} must be an integer >= 1")
    return value


def check_shortfall(status: Any, expected_min_count: Any, evidence_path: str = "") -> dict | None:
    """수집 결과(status.json)가 목표에 못 미치면 수리용 보고서를, 충분하면 None 을 돌려준다.

    반환 모양은 profile_autodiscover 의 NEEDS_NEW_RULE 보고서와 같다 → build_repair_task 가 그대로 읽는다.
    success 가 없거나 정수가 아니면 판정할 수 없으므로 ValueError(성공으로 숨기지 않는다).
    """
    expected = _require_positive_int(expected_min_count, "expected_min_count")
    if not isinstance(status, dict):
        raise ValueError("status must be an object")
    success = status.get("success")
    if isinstance(success, bool) or not isinstance(success, int) or success < 0:
        raise ValueError("status.success must be a non-negative integer")
    if success >= expected:
        return None
    return {"result": "NEEDS_NEW_RULE",
            "failure": {"category": "shortfall",
                        "error": (f"수집 {success}건 < 목표 {expected}건 "
                                  f"(targets={status.get('targets', '미확인')}, failed={status.get('failed', '미확인')}, "
                                  f"catalog_rows={status.get('catalog_rows', '미확인')})"),
                        "evidence": evidence_path}}


def validate_request(request: Any) -> dict:
    """도구 입력을 검사하고 정규화한다(이름·회사명·목표 건수·문서 키워드)."""
    if not isinstance(request, dict):
        raise ValueError("request must be an object")
    name = request.get("name")
    if not isinstance(name, str) or not NAME_PATTERN.fullmatch(name):
        raise ValueError("name must match [a-z0-9_]{1,64}")
    company = request.get("company_name")
    if (not isinstance(company, str) or not 1 <= len(company.strip()) <= MAX_COMPANY_CHARS
            or any(ch in company for ch in "\r\n\t")):
        raise ValueError(f"company_name must be 1..{MAX_COMPANY_CHARS} chars on one line")
    keyword = request.get("document_keyword", "약관")
    if not isinstance(keyword, str) or not 1 <= len(keyword.strip()) <= MAX_KEYWORD_CHARS:
        raise ValueError(f"document_keyword must be 1..{MAX_KEYWORD_CHARS} chars")
    return {"name": name, "company_name": company.strip(),
            "expected_min_count": _require_positive_int(request.get("expected_min_count"), "expected_min_count"),
            "document_keyword": keyword.strip()}


# ---------------------------------------------------------------------------
# 수집기 실행 (테스트에서는 run_collector 주입으로 교체)
# ---------------------------------------------------------------------------
def _load_collector():
    """수집기 모듈을 경로로 연결한다(FastAPI 쪽 원래 위치 그대로, 패키지 import 경로가 없어 importlib 사용)."""
    script = Path(str(_SETTINGS["collector_script"]))
    spec = importlib.util.spec_from_file_location("self_repair_collect_collector", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_collector_subprocess(request: dict) -> tuple[dict, str]:
    """수집기를 새 파이썬 프로세스로 끝까지 실행하고 status.json 을 읽어 돌려준다.

    - 프로파일이 없으면(처음 보는 회사): 수집기의 parse_onboard 로 onboard_request.json 을 만들고 --onboard
      (공시실 웹 검색 → 탐색·수리 → 수집). parse_onboard 는 프로파일이 이미 있으면 거부하므로 분기한다.
    - 프로파일이 있으면(재수집·수리 후 재검증): --worker (카탈로그·다운로드 이어받기).
    - 새 프로세스로 돌리는 이유: 수리로 바뀐 수집기 코드를 매번 새로 읽기 위해서다.
    """
    collector = _load_collector()
    name = request["name"]
    # 수집기 자체 상한보다 크게 주면 validate_time_limit 이 거부하므로 둘 중 작은 값을 쓴다.
    limit = min(int(_SETTINGS["collect_time_limit_seconds"]), int(collector.MAX_TIME_LIMIT_SECONDS))
    out = collector.output_dir({"name": name})
    if (collector.PROFILE_DIR / f"{name}.json").exists():
        arguments = ["--worker", name, str(limit)]
    else:
        onboard = collector.parse_onboard({"profile": name, "company_name": request["company_name"],
                                           "document_keyword": request["document_keyword"],
                                           "time_limit_seconds": limit})
        collector.atomic_json(out / "onboard_request.json", onboard)
        arguments = ["--onboard", name, str(limit)]
    subprocess.run([sys.executable, str(_SETTINGS["collector_script"]), *arguments],
                   cwd=str(PROJECT_ROOT), capture_output=True, text=True,
                   timeout=limit + int(_SETTINGS["collector_grace_seconds"]))
    status_path = out / "status.json"
    if not status_path.is_file():
        raise RuntimeError(f"collector wrote no status.json: {status_path}")
    return json.loads(status_path.read_text(encoding="utf-8")), str(status_path)


def collect_and_check(request: dict, run_collector: Callable[[dict], tuple[dict, str]] = None) -> dict:
    """auto_with_repair 의 auto_fn 자리에 들어가는 함수: 수집 → 건수 판정 → 보고서.

    반환 result
      - NEEDS_NEW_RULE(shortfall): 목표 미달 → 수리 루프가 수리한다
      - DISCOVERED_COLLECTED: 목표 달성(기존 heal_succeeded 의 'DISCOVERED' 접두어 기준으로 성공)
      - FAILED: 수집기 실행·status 판독 자체가 실패(수리 대상 아님, 사유를 그대로 보고)
    """
    run_collector = run_collector or run_collector_subprocess
    try:
        status, status_path = run_collector(request)
        shortfall = check_shortfall(status, request["expected_min_count"], status_path)
    except Exception as error:  # noqa: BLE001 - 실패를 숨기지 않고 FAILED 로 보고한다
        return {"result": "FAILED", "error": f"{type(error).__name__}: {str(error)[:800]}",
                "checked_kst": now_kst_iso()}
    if shortfall:
        shortfall["status"] = status
        return shortfall
    return {"result": "DISCOVERED_COLLECTED", "success": status["success"], "status": status,
            "evidence": status_path, "checked_kst": now_kst_iso()}


def run(request: dict) -> dict:
    """입력 검사 후 기존 수리 루프에 위임한다(수리 엔진 재사용)."""
    from harness.mcp.agents.autodiscover_self_repair import auto_with_repair

    value = validate_request(request)
    return auto_with_repair(value, auto_fn=collect_and_check)


# ---------------------------------------------------------------------------
# MCP 도구 (백그라운드 job: MCP 호출이 길게 붙잡히지 않도록 제출 즉시 job_id 반환)
# ---------------------------------------------------------------------------
def _job_files(job_id: Any) -> tuple[Path, Path]:
    """job_id 형식을 검사(경로 조작 차단)하고 request/result 파일 경로를 돌려준다."""
    if not isinstance(job_id, str) or _JOB_ID_PATTERN.fullmatch(job_id) is None:
        raise ValueError("job_id must be a 32-character hexadecimal identifier")
    folder = PROJECT_ROOT / str(_SETTINGS["job_dir"]) / ("job_" + job_id)
    return folder / "request.json", folder / "result.json"


async def _job_status(job_id: str) -> dict:
    """result.json 이 있으면 그대로, 없으면 systemd 유닛 상태로 running/failed 를 판정한다."""
    request_path, result_path = _job_files(job_id)
    if not request_path.is_file():
        raise FileNotFoundError(f"self_repair_collect job not found: {job_id}")
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
                "error": "self_repair_collect job stopped without a final result",
                "unit_result": properties.get("Result", "unknown")}
    return state


async def self_repair_collect(name: str, company_name: str, expected_min_count: int,
                              document_keyword: str = "약관", dry_run: bool = True,
                              job_id: str | None = None) -> dict:
    """Collect documents and self-repair when the collected count is below expected_min_count.

    job_id 를 주면 상태 조회만 한다. dry_run=True(기본)는 계획만 돌려주고 프로세스를 띄우지 않는다.
    dry_run=False 는 독립 systemd 유닛으로 수집(+수리)을 시작하고 job_id 를 즉시 돌려준다.
    수리는 git add 까지만 하고 커밋하지 않는다(기존 수리 루프 규칙).
    """
    if job_id is not None:
        return await _job_status(job_id)
    request = validate_request({"name": name, "company_name": company_name,
                                "expected_min_count": expected_min_count,
                                "document_keyword": document_keyword})
    timeout = int(_SETTINGS["job_timeout_seconds"])
    new_id = uuid4().hex
    unit, command = _systemd_command(
        ["-m", "harness.mcp.tools.self_repair_collect_tools", "--job-worker", new_id], timeout,
        "self-repair-collect")
    # 독립 유닛: 제출 호출이 끝날 때까지 기다리지 않도록 --wait/--pipe 를 뺀다.
    command = [argument for argument in command if argument not in {"--wait", "--pipe"}]
    plan = {"dry_run": bool(dry_run), "executed": False, "job_id": new_id, "unit": unit,
            "command": command, "timeout_seconds": timeout, "request": request}
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
    """독립 systemd 유닛 안에서 job 하나를 실행하고 마스킹된 결과를 저장한다(실패도 결과 파일로 남긴다)."""
    request_path, result_path = _job_files(job_id)
    plan = json.loads(request_path.read_text(encoding="utf-8"))
    started = monotonic()
    report, error = None, ""
    try:
        report = run(plan["request"])
    except Exception as exc:  # noqa: BLE001 - 조회에서 확인할 수 있게 결과 파일로 남긴다
        error = f"{type(exc).__name__}: {exc}"
    text = _mask_secrets(json.dumps(report, ensure_ascii=False, default=str)) if report is not None else ""
    final = str((report or {}).get("result", "FAILED"))
    success = not error and final.startswith("DISCOVERED")
    _write_json(result_path, {**plan, "dry_run": False, "executed": True,
                              "state": "completed" if not error else "failed", "success": success,
                              "result": final, "error": _mask_secrets(error) or None,
                              "evidence": (report or {}).get("evidence"),
                              "elapsed_seconds": round(monotonic() - started, 3),
                              "output": text[:_OUTPUT_LIMIT], "output_truncated": len(text) > _OUTPUT_LIMIT})


if __name__ == "__main__" and len(sys.argv) == 3 and sys.argv[1] == "--job-worker":
    _run_job(sys.argv[2])
