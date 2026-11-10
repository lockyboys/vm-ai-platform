"""Expose the existing Multi-Persona source-review CLI as one SPS MCP tool.

[자동 수정(auto_apply) 안내 — 2026-11-10, LuckyBoys 결정: 완전 자동]
- review_python_source는 검증된 리뷰 제안을 원본 소스에 직접 적용한다
  (config.MULTI_PERSONA_REVIEW_AUTO_APPLY, 호출 시 auto_apply 인자로 개별 지정 가능).
- 적용 전 job 폴더에 original.py 백업 → 문법 컴파일 → test_paths pytest → 실패 시 자동 되돌림.
- Git 커밋은 하지 않는다(사람이 확인 후 지시).

⚠ 주의: test_paths 없이 호출하면 문법만 맞아도 원본이 바뀐다(동작이 달라져도 되돌리지 않음).
  중요한 파일은 반드시 test_paths=["tests/...", "harness/tests/..."]를 함께 넘길 것.
  허용 폴더: config.MULTI_PERSONA_AUTO_APPLY_TEST_ROOTS (tests/, harness/tests/)
"""
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
# 2026-11-10: 자동 수정(백업→적용→검증→되돌림) 로직은 재사용 모듈로 분리했다.
from harness.mcp.tools import auto_apply

PROJECT_ROOT = Path(project_config.PROJECT_ROOT).resolve()
# 2026-11-10: 리뷰 CLI는 config.MULTI_PERSONA_REVIEW_PROVIDERS에서 LLM별로 고른다(하드코딩 제거).
# REVIEW_SOURCE는 기본 provider의 CLI이며, 테스트가 이 값을 바꿔 임시 CLI를 쓸 수 있다.
REVIEW_SOURCE = PROJECT_ROOT / project_config.MULTI_PERSONA_REVIEW_PROVIDERS[
    project_config.MULTI_PERSONA_REVIEW_DEFAULT_PROVIDER]["cli"]


def _review_cli(provider: str | None) -> tuple[str, Path, list[str]]:
    """provider 이름을 검사하고 (이름, 리뷰 CLI 경로, CLI 추가 인자)를 돌려준다.

    gemini·openai·claude는 같은 CLI를 쓰고 ["--provider", <llm>]으로 LLM만 바꾼다.
    ollama처럼 전용 CLI는 추가 인자가 없다.
    잘못된 입력(문자열 아님, 등록되지 않은 이름)은 리뷰 시작 전에 거부한다.
    """
    name = project_config.MULTI_PERSONA_REVIEW_DEFAULT_PROVIDER if provider is None else provider
    if not isinstance(name, str) or name not in project_config.MULTI_PERSONA_REVIEW_PROVIDERS:
        raise ValueError("provider must be one of: "
                         + ", ".join(sorted(project_config.MULTI_PERSONA_REVIEW_PROVIDERS)))
    entry = project_config.MULTI_PERSONA_REVIEW_PROVIDERS[name]
    extra = ["--provider", entry["llm"]] if entry.get("llm") else []
    if name == project_config.MULTI_PERSONA_REVIEW_DEFAULT_PROVIDER:
        return name, REVIEW_SOURCE, extra
    return name, PROJECT_ROOT / entry["cli"], extra


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
    """테스트 경로 검사 — 2026-11-10 재사용 모듈 harness.mcp.tools.auto_apply로 분리, 여기서는 위임만 한다."""
    # PROJECT_ROOT를 호출 시점에 넘겨 테스트의 monkeypatch(임시 저장소)도 그대로 동작하게 한다.
    return auto_apply.validate_test_paths(values, PROJECT_ROOT)


def _auto_apply(source: Path, proposed: Path, job_dir: Path, request: dict, budget: float) -> dict:
    """자동 적용 — 2026-11-10 재사용 모듈 harness.mcp.tools.auto_apply로 분리, 여기서는 위임만 한다.

    ⚠ test_paths가 없으면 문법만 맞아도 원본이 바뀐다(세부 동작은 auto_apply 모듈 헤더 참고).
    """
    return auto_apply.apply_with_rollback(
        source, proposed, job_dir, request["source_sha256"],
        request.get("test_paths") or [], budget, PROJECT_ROOT)


async def review_python_source(
    source_path: str,
    error_path: str | None = None,
    dry_run: bool = True,
    job_id: str | None = None,
    auto_apply: bool | None = None,
    test_paths: list[str] | None = None,
    provider: str | None = None,
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
    # 2026-11-10: 리뷰 LLM 선택(gemini / ollama ...). 같은 출력 계약이라 검증·자동 적용은 공통이다.
    provider_name, review_cli, provider_args = _review_cli(provider)
    if not review_cli.is_file():
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
    review_command = [str(PROJECT_ROOT / "venv/bin/python"), "-u", str(review_cli), *provider_args,
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
            "auto_apply": apply_changes, "test_paths": checked_tests,
            "provider": provider_name}
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
        # 2026-11-10: 제출 때 저장한 provider로 CLI를 다시 고른다(이전 job은 기본 provider).
        _, review_cli, provider_args = _review_cli(request.get("provider"))
        command = [str(PROJECT_ROOT / "venv/bin/python"), "-u", str(review_cli), *provider_args,
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
