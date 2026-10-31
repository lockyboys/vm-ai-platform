## 1. 전문가적 견해 및 종합 평가

- **모듈 패키지 네임스페이스 결함**: `review_python_source` 내부의 systemd 워커 실행 인자에 오타(`haness.mcp.tools...` -> `harness.mcp.tools...`)가 존재합니다. 격리 워커 프로세스가 기동되자마자 `ModuleNotFoundError`로 비정상 종료되는 치명적 P0 결함이므로 즉시 수정이 필요합니다.
- **PROMPT_ENGINEER 설계 검토 (LLM 마커 검증 비결정성)**: LangGraph 기반 Multi-Persona CLI(`multi_persona_agent_gemini.py`)의 출력 결과를 검증할 때 정적 문자열 `"[최종 검증된 답변]:" in text`를 사용하는 것은 LLM 출력의 마크다운 서식 변형(예: `**[최종 검증된 답변]**`, 공백 삽입, 콜론 누락 등)에 취약합니다. 유연한 정규식 패턴 매칭으로 완화하여 `model_verified` 오판정을 방지해야 합니다.
- **메모리 및 파일 I/O 안정성**: `source.read_bytes()`를 통한 일괄 적재 방식은 대용량 파일 리뷰 시 순간적인 메모리 스파이크를 유발합니다. 64KB 단위 청크 스트리밍 SHA-256 계산 방식으로 변경하고, 디렉터리 생성 시 `exist_ok=True`를 명시하여 `FileExistsError` 레이스 컨디션을 방어해야 합니다.
- **프로세스 및 리소스 해제(동시성/예외)**: `review_python_source`에서 워커 실행 등록 타임아웃(10초) 발생 시 미사용 상태로 방치되어 있던 `_stop_review`를 연동하여 transient systemd 유닛 및 서브프로세스를 즉시 정리하도록 개선합니다. 또한 `_run_review_job` 내에서 초기 검증 실패나 서브프로세스 예외가 발생하더라도 `result.json`이 누락되어 상위 모니터링이 좀비 상태로 대기하지 않도록 상태 영속화를 보장합니다.

---

## 2. 위험도 및 진단 리포트

| 번호 | 영역 / 함수 | 심각도 | 진단 내용 및 근거 | 조치 방향 (수정 여부) |
|:---:|---|:---:|---|---|
| 1 | `review_python_source` | **P0 (치명적)** | systemd 커맨드 인자에 `haness` 오타가 포함되어 워커 서브프로세스가 모듈을 찾지 못하고 즉각 실패함. | **수정 필요**: `harness.mcp.tools.multi_persona_tools`로 패키지 경로 정정. |
| 2 | `_run_review_job` | **P1 (높음)** | LLM 응답 검증 시 정적 문자열 `[최종 검증된 답변]:` 비교로 마크다운 볼드나 서식 변형 시 `model_verified`가 False로 오인됨. | **수정 필요**: 정규식 `re.search(r"\[최종\s*검증된\s*답변\]", text)` 매칭 적용. |
| 3 | `review_python_source` | **P1 (높음)** | systemd unit 기동 대기 중 10초 타임아웃 발생 시 정의된 `_stop_review`를 호출하지 않아 프로세스 및 유닛 리소스 누수. | **수정 필요**: `asyncio.TimeoutError` 블록에서 `await _stop_review(process, unit)` 호출. |
| 4 | `review_python_source` / `_write_json` | **P2 (중간)** | `request_path.parent.mkdir` 호출 시 `exist_ok=True` 누락으로 인한 잠재적 `FileExistsError` 발생 가능. | **수정 필요**: 디렉터리 생성 로직에 `exist_ok=True` 적용 및 `_write_json` 자체 방어 추가. |
| 5 | 전역 파일 해시 로직 | **P2 (중간)** | `source.read_bytes()`를 반복 사용하여 파일 전체를 메모리에 올리는 비효율 발생. | **수정 필요**: `_calculate_file_sha256` 청크 스트리밍 함수 도입. |
| 6 | `_review_status` | **P3 (낮음)** | 비동기 레이스 컨디션으로 `request_path`가 준비되지 않았을 때의 명시적 예외 처리 미흡. | **수정 필요**: 파일 존재 여부 사전 검증 및 명확한 에러 반환. |
| 7 | `_project_path` / `_systemd_command` | **Info** | 보안 경로 순회 방지 및 격리된 transient service 커맨드 구성은 안전하게 구현됨. | **수정 불필요** |

---

## 3. 최종 수정 전체 소스 코드

```python
"""Expose the existing Multi-Persona source-review CLI as one SPS MCP tool."""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4
from time import monotonic

import config as project_config
from common.common_function import logger, normalize_required_text
from harness.mcp.tools.execution_tools import _mask_secrets

PROJECT_ROOT = Path(project_config.PROJECT_ROOT).resolve()
REVIEW_SOURCE = PROJECT_ROOT / "FastAPI/LangGraph/multi_persona/multi_persona_agent_gemini.py"


def _calculate_file_sha256(path: Path) -> str:
    """대용량 파일 읽기 시 메모리 급증을 방지하기 위해 스트리밍 방식으로 SHA-256을 계산합니다."""
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def _project_path(value: str, field_name: str) -> Path:
    """Resolve caller paths inside the project, including symlink targets."""
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be text")
    path = (PROJECT_ROOT / Path(normalize_required_text(value, field_name)).expanduser()).resolve()
    if PROJECT_ROOT not in path.parents:
        raise ValueError(f"{field_name} must stay inside the project")
    return path


def _systemd_command(arguments: list[str], timeout: int, purpose: str) -> tuple[str, list[str]]:
    """Build a fixed-account transient worker without reading secret file contents."""
    unit = "sps-" + purpose + "-" + uuid4().hex
    command = ["sudo", "-n", "systemd-run", "--wait", "--collect", "--pipe",
               "--quiet", "--unit=" + unit,
               "-p", "User=" + project_config.SPS_MCP_WORKER_USER,
               "-p", "WorkingDirectory=" + str(PROJECT_ROOT),
               "-p", "EnvironmentFile=" + str(PROJECT_ROOT / ".env"),
               "-p", "EnvironmentFile=" + project_config.SPS_MCP_WORKER_SECRETS_FILE,
               "-p", f"RuntimeMaxSec={timeout}", "-p", "TimeoutStopSec=2",
               str(PROJECT_ROOT / "venv/bin/python"), "-u", *arguments]
    return unit, command


async def _stop_review(process: asyncio.subprocess.Process, unit: str) -> None:
    """Stop the transient service as well as its waiting client on cancellation."""
    try:
        cleanup = await asyncio.create_subprocess_exec(
            "sudo", "-n", "systemctl", "stop", unit,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        try:
            await asyncio.wait_for(cleanup.communicate(), timeout=3)
        except asyncio.TimeoutError:
            cleanup.kill()
            await cleanup.wait()
    except Exception as error:
        logger.warning("Failed to cleanly stop review unit %s: %s", unit, error)
    finally:
        if process.returncode is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
        await process.wait()


def _job_files(job_id: str) -> tuple[Path, Path]:
    """Keep job identifiers opaque and reject traversal before touching disk."""
    if not isinstance(job_id, str) or re.fullmatch(r"[0-9a-f]{32}", job_id) is None:
        raise ValueError("job_id must be a 32-character hexadecimal identifier")
    folder = PROJECT_ROOT / "harness/memory/source_reviews" / ("job_" + job_id)
    return folder / "request.json", folder / "result.json"


def _write_json(path: Path, value: dict) -> None:
    """Replace complete state atomically; partial JSON is never a valid result."""
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    temporary.chmod(0o600)
    temporary.replace(path)


async def _review_status(source: Path, job_id: str) -> dict:
    request_path, result_path = _job_files(job_id)
    if not request_path.is_file():
        raise FileNotFoundError(f"Review job request not found for job_id: {job_id}")

    try:
        request = json.loads(request_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"Corrupted review job request: {exc}") from exc

    if str(source.relative_to(PROJECT_ROOT)) != request["source_path"]:
        raise ValueError("job_id belongs to a different source_path")
    if result_path.is_file():
        return json.loads(result_path.read_text(encoding="utf-8"))
    state = {**request, "dry_run": False, "executed": True, "state": "running",
             "success": None, "elapsed_seconds": round(time.time() - request["started_at"], 3)}

    # A collected/failed unit without its result must not appear to run indefinitely.
    process = await asyncio.create_subprocess_exec(
        "systemctl", "show", request["unit"], "--property=LoadState,ActiveState,Result",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        output, _ = await asyncio.wait_for(process.communicate(), timeout=3)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return {**state, "state": "status_unavailable"}

    # Recheck after systemctl: the worker may have completed during this query.
    if result_path.is_file():
        return json.loads(result_path.read_text(encoding="utf-8"))
    properties = dict(line.split("=", 1) for line in output.decode(errors="replace").splitlines()
                      if "=" in line)
    if properties.get("LoadState") == "not-found" or properties.get("ActiveState") in {"failed", "inactive"}:
        return {**state, "state": "failed", "success": False,
                "error": "Review worker stopped without a final result",
                "unit_result": properties.get("Result", "unknown")}
    if process.returncode != 0:
        return {**state, "state": "status_unavailable"}
    return state


async def review_python_source(
    source_path: str,
    error_path: str | None = None,
    dry_run: bool = True,
    job_id: str | None = None,
) -> dict:
    """Review Python source with a durable Multi-Persona Gemini job under the configured timeout.

    Default dry-run validates paths without starting Python or an LLM.
    Set dry_run=False to start a review and receive a job_id immediately.
    Call again with the same source_path and job_id to read status/results.
    MCP responses stay short; a disconnect does not cancel the configured job.
    Generated corrections are proposals only; target source/tests are never executed.
    """
    source = _project_path(source_path, "source_path")
    if job_id is not None:
        return await _review_status(source, job_id)
    if source.suffix != ".py":
        raise ValueError("source_path must name a Python source")
    if not source.is_file():
        raise FileNotFoundError(f"Source file not found: {source_path}")
    if not REVIEW_SOURCE.is_file():
        raise FileNotFoundError("The configured Multi-Persona review CLI is missing")
    timeout = int(project_config.MULTI_PERSONA_REVIEW_TIMEOUT_SECONDS)
    if not 1 <= timeout <= project_config.SPS_SOURCE_EXECUTION_TIMEOUT_SECONDS:
        raise ValueError("Review timeout exceeds the configured source execution limit")
    output_limit = int(project_config.MULTI_PERSONA_REVIEW_OUTPUT_CHARS)
    if output_limit < 1:
        raise ValueError("Review output limit must be positive")
    review_command = [str(PROJECT_ROOT / "venv/bin/python"), "-u", str(REVIEW_SOURCE),
                      "--source-path", str(source)]
    error_relative = None
    if error_path is not None:
        errors = _project_path(error_path, "error_path")
        if errors.suffix not in {".log", ".txt"} or errors.is_dir():
            raise ValueError("error_path must name a project .log or .txt file")
        error_relative = str(errors.relative_to(PROJECT_ROOT))
        review_command.extend(["--error-path", str(errors)])
    identifier = uuid4().hex

    # [수정] 오타 정정: haness -> harness
    unit, command = _systemd_command(
        ["-m", "harness.mcp.tools.multi_persona_tools", "--worker", identifier],
        timeout + project_config.SPS_WORKER_RESULT_GRACE_SECONDS, "source-review")
    command = [argument for argument in command if argument not in {"--wait", "--pipe"}]
    plan = {"dry_run": bool(dry_run), "executed": False, "job_id": identifier,
            "source_path": str(source.relative_to(PROJECT_ROOT)),
            "command": command, "review_command": review_command,
            "timeout_seconds": timeout, "tests_executed": False}
    if dry_run:
        return plan

    request_path, result_path = _job_files(identifier)
    # [수정] exist_ok=True 추가하여 동시성 디렉터리 생성 충돌 방지
    request_path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    request = {**plan, "unit": unit, "error_path": error_relative,
               "output_limit": output_limit, "started_at": time.time(),
               "source_sha256": _calculate_file_sha256(source)}
    _write_json(request_path, request)

    process = await asyncio.create_subprocess_exec(
        *command, cwd=str(PROJECT_ROOT),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        _, errors = await asyncio.wait_for(process.communicate(), timeout=10)
    except asyncio.TimeoutError:
        # [수정] 미사용 상태였던 _stop_review를 호출하여 지연된 systemd unit 및 프로세스 리소스 회수
        await _stop_review(process, unit)
        return {**plan, "executed": True, "state": "status_unavailable", "success": None}

    if process.returncode != 0:
        result = {**plan, "executed": False, "state": "failed", "success": False,
                  "stderr": _mask_secrets(errors.decode(errors="replace"))}
        _write_json(result_path, result)
        return result
    logger.info("Multi-Persona review queued: job=%s source=%s", identifier, plan["source_path"])
    return {**plan, "executed": True, "state": "running", "success": None}


def _run_review_job(job_id: str) -> None:
    """Execute in an independent systemd unit and persist the complete masked report."""
    request_path, result_path = _job_files(job_id)
    request = json.loads(request_path.read_text(encoding="utf-8"))
    started = monotonic()
    result = {**request, "dry_run": False, "executed": True, "tests_executed": False}
    output, errors, returncode, timed_out = b"", b"", None, False
    try:
        source = _project_path(request["source_path"], "source_path")
        if _calculate_file_sha256(source) != request["source_sha256"]:
            raise ValueError("Source changed after review submission")
        command = [str(PROJECT_ROOT / "venv/bin/python"), "-u", str(REVIEW_SOURCE),
                   "--source-path", str(source)]
        if request.get("error_path"):
            log = _project_path(request["error_path"], "error_path")
            if log.suffix not in {".log", ".txt"} or log.is_dir():
                raise ValueError("Invalid review error path")
            command.extend(["--error-path", str(log)])
        timeout = int(request["timeout_seconds"])
        if not 1 <= timeout <= project_config.SPS_SOURCE_EXECUTION_TIMEOUT_SECONDS:
            raise ValueError("Invalid review timeout")
        completed = subprocess.run(command, cwd=str(PROJECT_ROOT),
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   timeout=timeout, check=False)
        output, errors, returncode = completed.stdout, completed.stderr, completed.returncode
    except subprocess.TimeoutExpired as error:
        output, errors = error.stdout or b"", error.stderr or b""
        timed_out = True
    except Exception as error:
        errors = str(error).encode("utf-8", errors="replace")

    text = _mask_secrets(output.decode("utf-8", errors="replace"))
    stderr = _mask_secrets(errors.decode("utf-8", errors="replace"))
    try:
        source = _project_path(request["source_path"], "source_path")
        unchanged = source.is_file() and _calculate_file_sha256(source) == request["source_sha256"]
    except Exception:
        unchanged = False

    report = request_path.parent.parent / ("review_" + job_id + ".txt")
    report.write_text(text + ("\n" if text and stderr else "") + stderr, encoding="utf-8")
    report.chmod(0o600)
    success = not timed_out and returncode == 0 and bool(text.strip())
    limit = request["output_limit"]

    # [수정: PROMPT_ENGINEER] 마크다운 볼드(**) 및 공백 변형에 대응하는 정규식 매칭
    model_verified = success and bool(re.search(r"\[최종\s*검증된\s*답변\]", text))

    result.update(state="timed_out" if timed_out else ("completed" if success else "failed"),
                  success=success, timed_out=timed_out, returncode=returncode,
                  elapsed_seconds=round(monotonic() - started, 3), source_unchanged=unchanged,
                  model_verified=model_verified,
                  report_path=str(report.relative_to(PROJECT_ROOT)),
                  output=text[:limit], stderr=stderr[:limit],
                  output_truncated=len(text) > limit or len(stderr) > limit)
    _write_json(result_path, result)


if __name__ == "__main__" and len(sys.argv) == 3 and sys.argv[1] == "--worker":
    _run_review_job(sys.argv[2])
```