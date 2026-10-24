## 1. 전문가적 견해 및 종합 평가

### [PROMPT_ENGINEER & 시스템 아키텍처 관점 종합 평가]
- **시스템 격리 및 LangGraph 통합 구조**: `systemd-run` 기반 임시 스코프(unit)를 통해 LangGraph 오케스트레이터 및 하위 크롤러를 별도 서브프로세스로 격리 실행하는 설계는 메모리 누수 방지 및 메인 MCP 서버 보호 관점에서 우수합니다. 무거운 런타임(`FastAPI.LangGraph.sps_main_orchestrator`)을 워커 프로세스 내부에서 지연 임포트(Lazy Import)하는 패턴 역시 초기 기동 부하를 억제합니다.
- **예외 처리 및 리소스 생명주기 관리 취약점**:
  - 서브프로세스 통신(`process.communicate`) 중 `TimeoutError`, `CancelledError` 외에 I/O 인터럽트 등 예기치 않은 예외(`Exception`) 발생 시 프로세스 및 systemd 유닛 정리 루틴(`_stop_review`)이 누락되어 고아 프로세스 및 유닛 누수가 발생할 위험이 있습니다.
  - 워커(`_worker`) 내부에서 `sys.stdin.read()`의 빈 입력 또는 JSON 파싱 실패, LangGraph 실행 예외 발생 시 표준 에러 기록 없이 프로세스가 비정상 종료(Traceback 출력 후 크래시)되어 호출자에게 원인이 불명확하게 전달됩니다.
- **데이터 직렬화 안전성**: LangGraph 실행 결과(`api_chat_orchestrator`)가 Pydantic 모델(v1 `dict()` 또는 v2 `model_dump()`)이거나 비JSON 직렬화 객체(예: `AIMessage`, 커스텀 상태 객체)를 포함할 경우 `json.dumps`에서 `TypeError`가 발생할 수 있습니다. 폴백 직렬화(`default=str`) 처리가 필요합니다.
- **동시성 및 I/O 블로킹**: 비동기 함수 내에서 대용량 텍스트 파일 생성 및 저장(`report.parent.mkdir`, `report.write_text`)을 메인 이벤트 루프에서 직접 동기 호출하여 다른 비동기 코루틴의 반응성을 저하시킬 수 있습니다. `asyncio.to_thread`를 통한 스레드 풀 위임이 필요합니다.
- **초안 검증 결과 및 미확인 사항**:
  - *근거*: Python `asyncio` 하위 프로세스 통신 중 태스크 취소 및 파이프 에러 발생 시 서브프로세스 종료 보장 필수(Python 공식 문서 권장사항).
  - *미확인 사항*: `api_chat_orchestrator`의 정확한 반환 스키마(Pydantic v1 vs v2 여부)와 디렉터리 경로명(`haness` vs `harness`)의 오타 여부는 외부 런타임 환경 설정에 종속되므로, 기존 인터페이스와 파일 경로(`PROJECT_ROOT / "harness/memory/orchestrator_runs"`)를 보존하여 역호환성을 유지합니다.

---

## 2. 위험도 및 진단 리포트

| 번호 | 위험도 | 구분 | 진단 항목 및 영향 | 권장 조치 및 근거 |
|---|---|---|---|---|
| 1 | **HIGH** | 리소스 해제 | `run_sps_orchestrator`에서 일반 예외(`Exception`) 발생 시 `_stop_review` 미호출로 systemd 유닛 및 프로세스 누수 위험 | `try...except Exception` 블록을 추가하여 예외 발생 시에도 `_stop_review` 호출 보장 |
| 2 | **HIGH** | 예외 처리 | `_worker`에서 `stdin` 빈 입력이나 JSON 파싱 실패 시 unhandled exception으로 크래시 | `json.loads` 예외 포착 및 `sys.stderr` 구조화 오류 기록 후 명시적 종료 코드(`sys.exit(1)`) 반환 |
| 3 | **MEDIUM** | 데이터 직렬화 | LangGraph 실행 결과가 Pydantic v1/v2 모델 또는 특수 객체일 경우 `json.dumps` 직렬화 실패 | `model_dump()`, `dict()` 우선 변환 및 `json.dumps(..., default=str)` 폴백 적용 |
| 4 | **MEDIUM** | 동시성/I/O | `run_sps_orchestrator` 내 `report.write_text` 동기 호출로 인한 이벤트 루프 블로킹 | `asyncio.to_thread`를 사용하여 파일 기록 I/O를 비동기 스레드 풀로 분리 |
| 5 | **LOW** | 프롬프트 무결성 | 20,000자 텍스트 입력 시 앞뒤 공백 및 널 바이트 등 제어 문자 포함 가능성 | 기존 `normalize_required_text` 유지 및 입력 검증 방어선 강화 |

---

## 3. 최종 수정 전체 소스 코드

```python
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
```