"""Expose the existing main orchestrator through an isolated systemd worker."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from time import monotonic
from typing import Any

import config as project_config
from common.common_function import normalize_required_text
from haness.mcp.tools.multi_persona_tools import (
    PROJECT_ROOT, _mask_secrets, _stop_review, _systemd_command,
)


def _write_report_file(path: Path, content: str) -> None:
    """오케스트레이터 실행 감사 로그를 동기식으로 파일에 저장합니다.

    목적:
        대용량 리포트 파일 I/O를 별도 워커 스레드로 위임하기 위한 내부 헬퍼.
    입력:
        - path (Path): 기록할 파일 경로
        - content (str): stdout 및 stderr 결합 텍스트
    주의점:
        이벤트 루프 차단을 방지하기 위해 반드시 asyncio.to_thread와 함께 호출합니다.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


async def run_sps_orchestrator(query: str, dry_run: bool = True) -> dict:
    """Run a requested task with the existing SPS main LangGraph orchestrator.

    Its configured crawler can browse sites and download files. Default dry-run
    returns the execution plan without starting Gemini or a crawler.
    """
    if not isinstance(query, str):
        raise ValueError("query must be text")
    query = normalize_required_text(query, "query")
    if len(query) > 20000:
        raise ValueError("query exceeds 20000 characters")
    timeout = int(project_config.SPS_MAIN_ORCHESTRATOR_TIMEOUT_SECONDS)
    if not 1 <= timeout <= 120:
        raise ValueError("Orchestrator timeout must be between 1 and 120 seconds")
    unit, command = _systemd_command(
        ["-m", "haness.mcp.tools.orchestrator_tools", "--worker"], timeout, "orchestrator")
    plan: dict[str, Any] = {
        "dry_run": bool(dry_run),
        "executed": False,
        "command": command,
        "timeout_seconds": timeout,
    }
    if dry_run:
        return plan

    # Pass the task through stdin rather than exposing its content in process arguments.
    started = monotonic()
    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(PROJECT_ROOT),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        output, errors = await asyncio.wait_for(
            process.communicate(json.dumps({"query": query}).encode("utf-8")),
            timeout=timeout + 4,
        )
    except asyncio.TimeoutError:
        await _stop_review(process, unit)
        return {**plan, "executed": True, "success": False, "timed_out": True}
    except asyncio.CancelledError:
        await _stop_review(process, unit)
        raise
    except Exception:
        # 예상치 못한 I/O 또는 OS 파이프 예외 시 서브프로세스 및 unit 리소스 누수 방지
        await _stop_review(process, unit)
        raise

    elapsed = monotonic() - started
    timed_out = process.returncode != 0 and elapsed >= timeout
    text = _mask_secrets(output.decode("utf-8", errors="replace"))
    errors_text = _mask_secrets(errors.decode("utf-8", errors="replace"))

    # Preserve an auditable full response and bound the MCP preview.
    report = PROJECT_ROOT / "harness/memory/orchestrator_runs" / (unit + ".txt")
    # 파일 생성 및 쓰기를 스레드 풀로 오프로딩하여 이벤트 루프 블로킹 방지
    await asyncio.to_thread(_write_report_file, report, text + errors_text)

    return {
        **plan,
        "executed": True,
        "success": not timed_out and process.returncode == 0 and bool(text.strip()),
        "returncode": process.returncode,
        "timed_out": timed_out,
        "elapsed_seconds": round(elapsed, 3),
        "output": text[:12000],
        "stderr": errors_text[:12000],
        "output_truncated": len(text) > 12000 or len(errors_text) > 12000,
        "report_path": str(report.relative_to(PROJECT_ROOT)),
    }


async def _worker() -> None:
    # Load the original graph only inside the requested, environment-configured worker.
    from FastAPI.LangGraph.sps_main_orchestrator import ChatRequest, api_chat_orchestrator

    raw_input = sys.stdin.read()
    if not raw_input.strip():
        sys.stderr.write("Worker error: received empty stdin input\n")
        sys.exit(1)

    try:
        request = json.loads(raw_input)
        query = request["query"]
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query field must be a non-empty string")
    except Exception as exc:
        sys.stderr.write(f"Worker JSON parsing error: {exc}\n")
        sys.exit(1)

    try:
        result = await api_chat_orchestrator(ChatRequest(query=query))

        # Pydantic v2(model_dump), v1(dict) 호환 및 일반 dict 직렬화 보장
        if hasattr(result, "model_dump"):
            payload = result.model_dump()
        elif hasattr(result, "dict"):
            payload = result.dict()
        else:
            payload = result

        print(json.dumps(payload, ensure_ascii=False, default=str))
    except Exception as exc:
        sys.stderr.write(f"Orchestrator execution failed: {exc}\n")
        sys.exit(1)


if __name__ == "__main__" and sys.argv[1:] == ["--worker"]:
    asyncio.run(_worker())