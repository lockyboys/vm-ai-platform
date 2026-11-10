"""Expose the existing Multi-Persona source-review CLI as one SPS MCP tool."""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import shutil  # 2026-11-10: 자동 적용 전 원본 백업(copy2)
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
    # 요청 작업 시간에 결과 저장 여유를 더한 값을 systemd 상한으로 유지한다.
    unit = "sps-" + purpose + "-" + uuid4().hex
    # 2026-10-31 회귀 수정: 유닛 수명은 config.SPS_GENERAL_UNIT_RUNTIME_SECONDS(현재 3600)를
    # 넘지 않는다. 호출자가 더 큰 값(예: 30010, 3600+grace)을 넘겨도 RuntimeMaxSec는 상한으로 고정한다.
    # 상한값은 하드코딩하지 않고 루트 config.py에서 읽는다(Repository/Metadata 우선 원칙).
    runtime_max = min(int(timeout), int(project_config.SPS_GENERAL_UNIT_RUNTIME_SECONDS))
    command = ["sudo", "-n", "systemd-run", "--wait", "--collect", "--pipe",
               "--quiet", "--unit=" + unit,
               "-p", "User=" + project_config.SPS_MCP_WORKER_USER,
               "-p", "WorkingDirectory=" + str(PROJECT_ROOT),
               "-p", "EnvironmentFile=" + str(PROJECT_ROOT / ".env"),
               "-p", "EnvironmentFile=" + project_config.SPS_MCP_WORKER_SECRETS_FILE,
               "-p", f"RuntimeMaxSec={runtime_max}", "-p", "TimeoutStopSec=2",
               str(PROJECT_ROOT / "venv/bin/python"), "-u", *arguments]
    return unit, command


async def _stop_review(process, unit: str) -> None:
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
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    temporary.chmod(0o600)
    temporary.replace(path)


def _judge_verification(text: str, proposed: Path) -> tuple[bool, list[str]]:
    """리뷰 결과를 '검증됨'으로 볼 수 있는지 세 조건을 모두 확인한다 (2026-11-02, LuckyBoys 결정).

    1) LLM verifier 통과: CLI는 verifier가 통과했을 때만 `[최종 검증된 답변]:`을 출력한다.
    2) 출력 계약 통과: CLI가 `[출력 검증] 오류=[]`을 출력해야 한다.
       (제목·문법·심볼 보존·진단 함수 반영·import 대상 실존 검사 포함)
    3) 제안 소스 파일이 이 job 전용 폴더에 실제로 생성되었다.
    하나라도 빠지면 False와 사유 목록을 돌려준다. 문구 하나만 보고 True로 판단하지 않는다.
    """
    reasons = []
    if "[최종 검증된 답변]:" not in text:
        reasons.append("LLM verifier 미통과(초안 대체 답변 또는 출력 없음)")
    if re.search(r"^\[출력 검증\] 오류=\[\]", text, re.M) is None:
        reasons.append("출력 계약 오류 또는 계약 검사 결과 없음")
    if not proposed.is_file():
        reasons.append("제안 소스 파일 미생성: " + proposed.name)
    return not reasons, reasons


def _persist_failure(result_path: Path, state: dict) -> dict:
    """결과 파일 없이 끝난 워커의 실패를 result.json에 남겨 이후 조회가 같은 판정을 받게 한다."""
    # 워커가 그 사이 결과를 썼다면 워커 결과를 우선한다(덮어쓰지 않음).
    if result_path.is_file():
        return json.loads(result_path.read_text(encoding="utf-8"))
    _write_json(result_path, state)
    return state


async def _review_status(source: Path, job_id: str) -> dict:
    request_path, result_path = _job_files(job_id)
    request = json.loads(request_path.read_text(encoding="utf-8"))
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
        # 2026-11-02: 실패를 응답으로만 돌려주지 않고 result.json에 영구 기록한다.
        return _persist_failure(result_path, {
            **state, "state": "failed", "success": False, "model_verified": False,
            "error": "Review worker stopped without a final result",
            "unit_result": properties.get("Result", "unknown")})
    if process.returncode != 0:
        return {**state, "state": "status_unavailable"}
    return state


def _validate_test_paths(values) -> list[str]:
    """자동 적용 후 돌릴 테스트 경로를 설정된 테스트 폴더 안으로만 제한한다 (2026-11-10).

    잘못된 입력(목록이 아님, 문자열이 아닌 값, 경로 탈출, 테스트 폴더 밖, 없는 파일)은
    리뷰를 시작하기 전에 거부해 워커가 임의 코드를 테스트로 실행하지 못하게 한다.
    """
    if values is None:
        return []
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise ValueError("test_paths must be a list of text paths")
    roots = [(PROJECT_ROOT / root).resolve() for root in project_config.MULTI_PERSONA_AUTO_APPLY_TEST_ROOTS]
    checked = []
    for value in values:
        path = _project_path(value, "test_paths")
        if not any(path == root or root in path.parents for root in roots):
            raise ValueError("test_paths must stay inside the configured test folders")
        if not path.exists():
            raise FileNotFoundError(f"Test path not found: {value}")
        checked.append(str(path.relative_to(PROJECT_ROOT)))
    return checked


def _auto_apply(source: Path, proposed: Path, job_dir: Path, request: dict, budget: float) -> dict:
    """검증된 제안을 원본에 적용하고, 검증에 실패하면 원본으로 되돌린다 (2026-11-10, 완전 자동).

    순서: 원본 해시 재확인 → job 폴더 original.py 백업 → 제안 기록 → 문법 컴파일
          → (지정 시) pytest → 실패하면 백업으로 복원. 결과는 result.json에 그대로 남긴다.
    """
    state = {"auto_apply": True, "applied": False, "rolled_back": False, "reason": None,
             "backup_path": None, "test_returncode": None}
    if budget < 30:
        state["reason"] = "not enough time left after review"
        return state
    # 리뷰 도중 사람이나 다른 작업이 원본을 바꿨다면 덮어쓰지 않는다.
    if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != request["source_sha256"]:
        state["reason"] = "source changed during review"
        return state
    backup = job_dir / "original.py"
    shutil.copy2(source, backup)
    backup.chmod(0o600)
    original_bytes = backup.read_bytes()
    state["backup_path"] = str(backup.relative_to(PROJECT_ROOT))
    try:
        source.write_bytes(proposed.read_bytes())
        # 파일(.pyc)을 만들지 않고 문법만 확인한다.
        compile(source.read_text(encoding="utf-8"), str(source), "exec")
        # ⚠ 주의(2026-11-10): test_paths를 주지 않으면 여기서 끝난다.
        #   즉 "문법만 맞으면" 제안이 원본에 그대로 남는다(동작이 바뀌어도 되돌리지 않음).
        #   중요한 파일은 반드시 관련 테스트 경로를 test_paths로 넘겨, pytest 실패 시 되돌리게 할 것.
        #   test_paths는 config.MULTI_PERSONA_AUTO_APPLY_TEST_ROOTS(tests/, harness/tests/) 안만 허용되며,
        #   pytest 시간은 MULTI_PERSONA_AUTO_APPLY_TEST_TIMEOUT_SECONDS와 리뷰 후 남은 시간 중 작은 값이다.
        tests = request.get("test_paths") or []
        if tests:
            run = subprocess.run(
                [str(PROJECT_ROOT / "venv/bin/python"), "-m", "pytest", "-q", *tests],
                cwd=str(PROJECT_ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=max(1, min(int(project_config.MULTI_PERSONA_AUTO_APPLY_TEST_TIMEOUT_SECONDS),
                                   int(budget) - 10)),
                check=False)
            state["test_returncode"] = run.returncode
            state["test_output_tail"] = _mask_secrets(run.stdout.decode("utf-8", errors="replace"))[-2000:]
            if run.returncode != 0:
                raise RuntimeError("tests failed after applying the proposal")
        state["applied"] = True
    except Exception as error:  # 컴파일 오류·테스트 실패·시간 초과 모두 되돌린다
        source.write_bytes(original_bytes)
        state.update(rolled_back=True, reason=f"{type(error).__name__}: {error}"[:500])
    return state


async def review_python_source(
    source_path: str,
    error_path: str | None = None,
    dry_run: bool = True,
    job_id: str | None = None,
    auto_apply: bool | None = None,
    test_paths: list[str] | None = None,
) -> dict:
    """Review Python source with a durable Multi-Persona Gemini job under the configured timeout.

    Default dry-run validates paths without starting Python or an LLM.
    Set dry_run=False to start a review and receive a job_id immediately.
    Call again with the same source_path and job_id to read status/results.
    MCP responses stay short; a disconnect does not cancel the configured job.
    auto_apply (default from config) applies only a verified proposal: the original is backed up
    to the job folder, the new source is compiled, test_paths (inside tests/ or harness/tests/)
    are run with pytest, and any failure restores the original automatically.
    """
    source = _project_path(source_path, "source_path")
    if job_id is not None:
        return await _review_status(source, job_id)
    if source.suffix != ".py":
        raise ValueError("source_path must name a Python source")
    if not source.is_file():
        raise FileNotFoundError(f"Source file not found: {source_path}")
    # 2026-11-10: 자동 적용 설정. 호출 인자가 없으면 config 기본값을 따른다.
    apply_changes = project_config.MULTI_PERSONA_REVIEW_AUTO_APPLY if auto_apply is None else bool(auto_apply)
    checked_tests = _validate_test_paths(test_paths)
    if not REVIEW_SOURCE.is_file():
        raise FileNotFoundError("The configured Multi-Persona review CLI is missing")
    timeout = int(project_config.MULTI_PERSONA_REVIEW_TIMEOUT_SECONDS)
    # 워커의 실행 한도보다 큰 값은 제출 단계에서 거부해 비동기 실패를 막는다.
    if not 1 <= timeout <= project_config.SPS_SOURCE_EXECUTION_TIMEOUT_SECONDS:
        raise ValueError("Review timeout exceeds the configured source execution limit")
    # 2026-11-02: 리뷰 시간 + 결과 저장 여유가 유닛 상한을 넘으면 systemd가 결과 저장 전에 워커를 죽인다.
    if (timeout + int(project_config.SPS_WORKER_RESULT_GRACE_SECONDS)
            > int(project_config.SPS_GENERAL_UNIT_RUNTIME_SECONDS)):
        raise ValueError("Review timeout plus result grace exceeds the transient unit runtime limit")
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
    # 2026-11-02: 리뷰 보고서·제안 소스를 job 전용 폴더에 써서 동시 리뷰가 서로 덮어쓰지 않게 한다.
    # (기존: 원본 옆 <stem>.review.md / <stem>.proposed.py 고정 이름)
    review_command.extend(["--output-dir", str(_job_files(identifier)[0].parent)])
    # The supervisor has ten seconds to persist results after its CLI reaches its own limit.
    unit, command = _systemd_command(
        ["-m", "harness.mcp.tools.multi_persona_tools", "--worker", identifier],
        timeout + project_config.SPS_WORKER_RESULT_GRACE_SECONDS, "source-review")
    command = [argument for argument in command if argument not in {"--wait", "--pipe"}]
    plan = {"dry_run": bool(dry_run), "executed": False, "job_id": identifier,
            "source_path": str(source.relative_to(PROJECT_ROOT)),
            "command": command, "review_command": review_command,
            "timeout_seconds": timeout, "tests_executed": False,
            "auto_apply": apply_changes, "test_paths": checked_tests}
    if dry_run:
        return plan
    request_path, result_path = _job_files(identifier)
    request_path.parent.mkdir(parents=True, mode=0o700)
    request = {**plan, "unit": unit, "error_path": error_relative,
               "output_limit": output_limit, "started_at": time.time(),
               "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
    _write_json(request_path, request)
    process = await asyncio.create_subprocess_exec(
        *command, cwd=str(PROJECT_ROOT),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        _, errors = await asyncio.wait_for(process.communicate(), timeout=10)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        # Starting a unit and waiting for the review are different operations.
        # Preserve the job identifier so a caller can inspect an ambiguous launch.
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
        if hashlib.sha256(source.read_bytes()).hexdigest() != request["source_sha256"]:
            raise ValueError("Source changed after review submission")
        # Reconstruct the fixed CLI rather than executing a caller-supplied command.
        command = [str(PROJECT_ROOT / "venv/bin/python"), "-u", str(REVIEW_SOURCE),
                   "--source-path", str(source)]
        if request.get("error_path"):
            log = _project_path(request["error_path"], "error_path")
            if log.suffix not in {".log", ".txt"} or log.is_dir():
                raise ValueError("Invalid review error path")
            command.extend(["--error-path", str(log)])
        # 2026-11-02: 제안 파일 충돌 방지 — 이 job 폴더에만 보고서·제안 소스를 쓴다.
        command.extend(["--output-dir", str(request_path.parent)])
        timeout = int(request["timeout_seconds"])
        if not 1 <= timeout <= project_config.SPS_SOURCE_EXECUTION_TIMEOUT_SECONDS:
            raise ValueError("Invalid review timeout")
        completed = subprocess.run(command, cwd=str(PROJECT_ROOT),
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   timeout=timeout, check=False)
        output, errors, returncode = completed.stdout, completed.stderr, completed.returncode
    except subprocess.TimeoutExpired as error:
        # subprocess.run kills/reaps its child; captured partial output remains available.
        output, errors = error.stdout or b"", error.stderr or b""
        timed_out = True
    except Exception as error:
        errors = str(error).encode("utf-8", errors="replace")
    text = _mask_secrets(output.decode("utf-8", errors="replace"))
    stderr = _mask_secrets(errors.decode("utf-8", errors="replace"))
    source = _project_path(request["source_path"], "source_path")
    unchanged = source.is_file() and hashlib.sha256(source.read_bytes()).hexdigest() == request["source_sha256"]
    report = request_path.parent.parent / ("review_" + job_id + ".txt")
    report.write_text(text + stderr, encoding="utf-8")
    report.chmod(0o600)
    # 프로세스가 정상 종료하고 출력이 있었는지(LLM 결과의 질과는 별개)
    process_completed = not timed_out and returncode == 0 and bool(text.strip())
    # 2026-11-02: '검증됨'은 verifier·계약(import 포함)·제안 파일 생성을 모두 만족해야 한다.
    proposed = request_path.parent / "proposed.py"
    verified, verification_reasons = _judge_verification(text, proposed)
    # 2026-11-02: LLM 호출이 모두 실패해도 CLI는 returncode 0으로 끝나 success=true로 보이던 문제 수정.
    # 리뷰의 성공은 "검증된 제안까지 만들어졌는가"로 판단한다. 프로세스 종료 여부는 process_completed로 따로 남긴다.
    success = process_completed and verified
    # 2026-11-10: 완전 자동 수정 — 검증된 리뷰만 적용하고, 실패하면 원본으로 되돌린다.
    if not request.get("auto_apply"):
        auto_result = {"auto_apply": False}
    elif success:
        auto_result = _auto_apply(source, proposed, request_path.parent, request,
                                  budget=int(request["timeout_seconds"]) - (monotonic() - started))
    else:
        auto_result = {"auto_apply": True, "applied": False, "rolled_back": False,
                       "reason": "review not verified"}
    limit = request["output_limit"]
    result.update(state="timed_out" if timed_out else ("completed" if success else "failed"),
                  success=success, process_completed=process_completed,
                  timed_out=timed_out, returncode=returncode,
                  elapsed_seconds=round(monotonic() - started, 3), source_unchanged=unchanged,
                  model_verified=success,
                  verification_reasons=verification_reasons,
                  auto_apply_result=auto_result,
                  tests_executed=bool(auto_result.get("test_returncode") is not None),
                  proposed_path=str(proposed.relative_to(PROJECT_ROOT)) if proposed.is_file() else None,
                  report_path=str(report.relative_to(PROJECT_ROOT)),
                  output=text[:limit], stderr=stderr[:limit],
                  output_truncated=len(text) > limit or len(stderr) > limit)
    _write_json(result_path, result)


if __name__ == "__main__" and len(sys.argv) == 3 and sys.argv[1] == "--worker":
    _run_review_job(sys.argv[2])
