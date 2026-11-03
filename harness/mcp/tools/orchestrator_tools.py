"""Expose the existing main orchestrator through an isolated systemd worker."""
from __future__ import annotations

import asyncio
import json
import re
import sys
import time
from time import monotonic
from uuid import uuid4

import config as project_config
from common.common_function import normalize_required_text
from harness.mcp.agents.source_partner_agent import run_source_partner_agent as _run_source_partner_agent
from harness.mcp.tools.change_set_graph import run_change_set as _run_change_set
# 2026-11-02: 백그라운드 job 상태 파일은 리뷰 job과 같은 원자적 JSON 저장 함수를 재사용한다.
from harness.mcp.tools.multi_persona_tools import (
    PROJECT_ROOT, _mask_secrets, _stop_review, _systemd_command, _write_json,
)


async def run_sps_orchestrator(query: str, dry_run: bool = True) -> dict:
    """Run a task with the SPS LangGraph orchestrator.

    mode=source_agent runs the actual PARTNER LLM/tool loop, while
    mode=change_set directly runs its deterministic source-change backend.
    Source patches proceed after their dry-run check. source_write and git
    commit receive only the explicit confirmation fields supplied at this MCP
    boundary. Git staging runs inside the backend graph. Other queries keep
    using the existing Gemini graph.
    """
    if not isinstance(query, str):
        raise ValueError("query must be text")
    query = normalize_required_text(query, "query")
    if len(query) > 20000:
        raise ValueError("query exceeds 20000 characters")
    if query.lstrip().startswith("{"):
        try:
            payload = json.loads(query)
        except json.JSONDecodeError as exc:
            raise ValueError("JSON query is invalid") from exc
        if isinstance(payload, dict):
            # 2026-11-02 LuckyBoys: MCP 호출은 180초에서 끊기므로 긴 작업은 백그라운드 job으로 띄우고
            # job_id로 상태를 조회한다. 기존 동기 경로(아래)는 그대로 둔다(기존 호출자 호환).
            #   제출: {"mode": "job_submit", "query": "<기존 query 그대로>"}
            #   조회: {"mode": "job_status", "job_id": "<32자리 hex>"}
            if payload.get("mode") == "job_submit":
                return await _submit_orchestrator_job(payload.get("query"), bool(dry_run))
            if payload.get("mode") == "job_status":
                return await _orchestrator_job_status(payload.get("job_id"))
            if payload.get("mode") == "persona_source":
                # Lazy import keeps the legacy crawler/review routes unchanged.
                from harness.mcp.agents.persona_source_runtime import submit
                return submit(payload, dry_run=bool(dry_run))
            if payload.get("mode") == "source_analysis":
                from harness.mcp.tools.source_analysis_graph import run_source_analysis
                return await asyncio.to_thread(run_source_analysis, payload, bool(dry_run))
            if payload.get("mode") == "change_set":
                # 파일·Git 작업은 동기 도구이므로 이벤트 루프를 막지 않게 별도 스레드에서 그래프를 실행한다.
                return await asyncio.to_thread(_run_change_set, payload, bool(dry_run))
            if payload.get("mode") == "source_agent":
                source_write_confirmed = payload.get("source_write_confirmed", False)
                if not isinstance(source_write_confirmed, bool):
                    raise ValueError("source_write_confirmed must be boolean")
                recursion_limit = payload.get("recursion_limit", 18)
                if (isinstance(recursion_limit, bool)
                        or not isinstance(recursion_limit, int)
                        or not 1 <= recursion_limit <= 256):
                    raise ValueError("recursion_limit must be an integer from 1 to 256")
                raw_allowed_paths = payload.get("allowed_source_paths")
                allowed_source_paths = None
                if raw_allowed_paths is not None:
                    if not isinstance(raw_allowed_paths, list) or not raw_allowed_paths:
                        raise ValueError("allowed_source_paths must be a non-empty list")
                    from pathlib import PurePosixPath
                    allowed_source_paths = []
                    for path in raw_allowed_paths:
                        if not isinstance(path, str) or not path.strip():
                            raise ValueError("allowed_source_paths entries must be non-empty text")
                        normalized = path.strip().replace("\\", "/")
                        relative = PurePosixPath(normalized)
                        if (relative.is_absolute() or ".." in relative.parts
                                or relative.as_posix() != normalized):
                            raise ValueError("allowed_source_paths must be canonical project-relative paths")
                        allowed_source_paths.append(normalized)
                    if len(allowed_source_paths) != len(set(allowed_source_paths)):
                        raise ValueError("allowed_source_paths entries must be unique")
                commit = payload.get("commit", {})
                if not isinstance(commit, dict):
                    raise ValueError("commit must be an object")
                commit_confirmed = commit.get("confirmed", False)
                if not isinstance(commit_confirmed, bool):
                    raise ValueError("commit.confirmed must be boolean")
                task = payload.get("task")
                if not isinstance(task, str):
                    raise ValueError("source_agent task must be text")
                return await _run_source_partner_agent(
                    task,
                    dry_run=bool(dry_run),
                    source_write_confirmed=source_write_confirmed,
                    commit_confirmed=commit_confirmed,
                    recursion_limit=recursion_limit,
                    allowed_source_paths=allowed_source_paths,
                )

    timeout = int(project_config.SPS_MAIN_ORCHESTRATOR_TIMEOUT_SECONDS)
    if not 1 <= timeout <= 120:
        raise ValueError("Orchestrator timeout must be between 1 and 120 seconds")
    unit, command = _systemd_command(
        ["-m", "harness.mcp.tools.orchestrator_tools", "--worker"], timeout, "orchestrator")
    plan = {"dry_run": bool(dry_run), "executed": False, "command": command,
            "timeout_seconds": timeout}
    if dry_run:
        return plan
    # Pass the task through stdin rather than exposing its content in process arguments.
    started = monotonic()
    process = await asyncio.create_subprocess_exec(
        *command, cwd=str(PROJECT_ROOT), stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        output, errors = await asyncio.wait_for(
            process.communicate(json.dumps({"query": query}).encode()), timeout=timeout + 4)
    except asyncio.TimeoutError:
        await _stop_review(process, unit)
        return {**plan, "executed": True, "success": False, "timed_out": True}
    except asyncio.CancelledError:
        await _stop_review(process, unit)
        raise
    elapsed = monotonic() - started
    timed_out = process.returncode != 0 and elapsed >= timeout
    text = _mask_secrets(output.decode("utf-8", errors="replace"))
    errors = _mask_secrets(errors.decode("utf-8", errors="replace"))
    # Preserve an auditable full response and bound the MCP preview.
    report = PROJECT_ROOT / "harness/memory/orchestrator_runs" / (unit + ".txt")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(text + errors, encoding="utf-8")
    return {**plan, "executed": True, "success": not timed_out and process.returncode == 0 and bool(text.strip()),
            "returncode": process.returncode, "timed_out": timed_out,
            "elapsed_seconds": round(elapsed, 3),
            "output": text[:12000], "stderr": errors[:12000],
            "output_truncated": len(text) > 12000 or len(errors) > 12000,
            "report_path": str(report.relative_to(PROJECT_ROOT))}


async def _run_query_inline(query: str) -> dict:
    """query 하나를 현재 프로세스에서 실행하고 결과 dict를 돌려준다(동기 워커·백그라운드 job 공용).

    주의: 동작은 2026-11-02 이전 _worker 본문과 같다. 출력(print)은 호출자가 한다.
    """
    # Relay source execution through a fresh worker even when MCP is already running.
    # This requires no service restart and preserves the existing crawler endpoint.
    try:
        payload = json.loads(query)
    except (TypeError, json.JSONDecodeError):
        payload = None
    if isinstance(payload, dict) and payload.get("mode") in {"persona_source", "source_agent"}:
        return await run_sps_orchestrator(query, dry_run=False)
    from FastAPI.LangGraph.sps_main_orchestrator import ChatRequest, api_chat_orchestrator
    # FastAPI normally injects the Authorization header. This worker calls the
    # endpoint function directly, so it must pass the configured server key
    # explicitly; otherwise the Header descriptor reaches authentication code
    # as a value and the request fails before the graph starts.
    authorization = f"Bearer {project_config.SPS_MAIN_ORCHESTRATOR_API_KEY}"
    return await api_chat_orchestrator(
        ChatRequest(query=query), authorization=authorization)


async def _worker() -> None:
    request = json.loads(sys.stdin.read())
    print(json.dumps(await _run_query_inline(request["query"]), ensure_ascii=False))


# ---------------------------------------------------------------------------
# 2026-11-02 백그라운드 job (LuckyBoys 승인: 실행 상한 = 공용 유닛 상한 3600초)
#   - 제출은 systemd 유닛을 --wait 없이 띄우고 job_id를 즉시 돌려준다(MCP 180초 끊김 회피).
#   - 워커는 request.json을 읽어 _run_query_inline으로 실행하고 result.json을 원자적으로 쓴다.
#   - 상한은 config.SPS_GENERAL_UNIT_RUNTIME_SECONDS, 결과 저장 여유는 SPS_WORKER_RESULT_GRACE_SECONDS.
# ---------------------------------------------------------------------------
_JOB_ID_PATTERN = re.compile(r"[0-9a-f]{32}")
_JOB_OUTPUT_LIMIT = 12000  # 기존 동기 경로와 같은 MCP 미리보기 한도


def _orchestrator_job_files(job_id: str):
    """job_id 형식을 검사(경로 조작 차단)하고 request/result 파일 경로를 돌려준다."""
    if not isinstance(job_id, str) or _JOB_ID_PATTERN.fullmatch(job_id) is None:
        raise ValueError("job_id must be a 32-character hexadecimal identifier")
    folder = PROJECT_ROOT / "harness/memory/orchestrator_jobs" / ("job_" + job_id)
    return folder / "request.json", folder / "result.json"


def _job_timeout_seconds() -> int:
    """job 전체 상한(초). 공용 유닛 상한에서 결과 저장 여유를 뺀 값이 실제 실행 한도다."""
    total = int(project_config.SPS_GENERAL_UNIT_RUNTIME_SECONDS)
    grace = int(project_config.SPS_WORKER_RESULT_GRACE_SECONDS)
    if total <= grace or grace < 0:
        raise ValueError("SPS_GENERAL_UNIT_RUNTIME_SECONDS must exceed SPS_WORKER_RESULT_GRACE_SECONDS")
    return total


async def _submit_orchestrator_job(query, dry_run: bool) -> dict:
    """기존 query를 백그라운드 job으로 제출한다. dry_run이면 계획만 돌려준다."""
    if not isinstance(query, str):
        raise ValueError("job_submit query must be text")
    query = normalize_required_text(query, "query")
    if len(query) > 20000:
        raise ValueError("query exceeds 20000 characters")
    # job 안에서 다시 job을 띄우는 재귀 제출을 막는다.
    try:
        inner = json.loads(query)
    except json.JSONDecodeError:
        inner = None
    if isinstance(inner, dict) and inner.get("mode") in {"job_submit", "job_status"}:
        raise ValueError("job_submit query cannot be another job request")
    timeout = _job_timeout_seconds()
    job_id = uuid4().hex
    unit, command = _systemd_command(
        ["-m", "harness.mcp.tools.orchestrator_tools", "--job-worker", job_id], timeout, "orchestrator-job")
    # 독립 유닛: 제출 호출이 기다리지 않도록 --wait/--pipe를 뺀다.
    command = [argument for argument in command if argument not in {"--wait", "--pipe"}]
    plan = {"dry_run": bool(dry_run), "executed": False, "job_id": job_id, "unit": unit,
            "command": command, "timeout_seconds": timeout}
    if dry_run:
        return plan
    request_path, result_path = _orchestrator_job_files(job_id)
    request_path.parent.mkdir(parents=True, mode=0o700)
    # query는 프로세스 인자에 노출하지 않고 0600 파일로만 넘긴다.
    _write_json(request_path, {**plan, "query": query, "started_at": time.time()})
    process = await asyncio.create_subprocess_exec(
        *command, cwd=str(PROJECT_ROOT),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
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


async def _orchestrator_job_status(job_id) -> dict:
    """result.json이 있으면 그대로, 없으면 systemd 유닛 상태로 running/failed를 판정한다."""
    request_path, result_path = _orchestrator_job_files(job_id)
    if not request_path.is_file():
        raise FileNotFoundError(f"orchestrator job not found: {job_id}")
    if result_path.is_file():
        return json.loads(result_path.read_text(encoding="utf-8"))
    request = json.loads(request_path.read_text(encoding="utf-8"))
    request.pop("query", None)  # 상태 응답에 원문 요청을 다시 싣지 않는다.
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
    if result_path.is_file():  # 조회 중에 끝났을 수 있다.
        return json.loads(result_path.read_text(encoding="utf-8"))
    properties = dict(line.split("=", 1) for line in output.decode(errors="replace").splitlines() if "=" in line)
    if properties.get("LoadState") == "not-found" or properties.get("ActiveState") in {"failed", "inactive"}:
        return {**state, "state": "failed", "success": False,
                "error": "Orchestrator job stopped without a final result",
                "unit_result": properties.get("Result", "unknown")}
    return state


def _run_orchestrator_job(job_id: str) -> None:
    """독립 systemd 유닛 안에서 job 하나를 실행하고 마스킹된 결과를 저장한다."""
    request_path, result_path = _orchestrator_job_files(job_id)
    request = json.loads(request_path.read_text(encoding="utf-8"))
    query = request.pop("query")
    started = monotonic()
    limit = int(request["timeout_seconds"]) - int(project_config.SPS_WORKER_RESULT_GRACE_SECONDS)
    result = {**request, "dry_run": False, "executed": True}
    text, timed_out, error = "", False, ""
    try:
        value = asyncio.run(asyncio.wait_for(_run_query_inline(query), timeout=limit))
        text = json.dumps(value, ensure_ascii=False, default=str)
    except asyncio.TimeoutError:
        timed_out = True
    except Exception as exc:  # 실패도 결과 파일로 남겨 조회에서 확인할 수 있게 한다.
        error = f"{type(exc).__name__}: {exc}"
    text, error = _mask_secrets(text), _mask_secrets(error)
    report = request_path.parent / "report.txt"
    report.write_text(text + ("\n" + error if error else ""), encoding="utf-8")
    report.chmod(0o600)
    success = not timed_out and not error and bool(text.strip())
    result.update(state="timed_out" if timed_out else ("completed" if success else "failed"),
                  success=success, timed_out=timed_out, error=error or None,
                  elapsed_seconds=round(monotonic() - started, 3),
                  report_path=str(report.relative_to(PROJECT_ROOT)),
                  output=text[:_JOB_OUTPUT_LIMIT], output_truncated=len(text) > _JOB_OUTPUT_LIMIT)
    _write_json(result_path, result)


if __name__ == "__main__" and sys.argv[1:] == ["--worker"]:
    asyncio.run(_worker())
elif __name__ == "__main__" and len(sys.argv) == 3 and sys.argv[1] == "--job-worker":
    _run_orchestrator_job(sys.argv[2])
