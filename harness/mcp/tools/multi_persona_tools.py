"""스스로 고치는 소스 리뷰 앱(Self-fixing source review app) — SPS MCP 도구 review_python_source.

[이 앱이 하는 일 — 2026-11-11 명시, LuckyBoys 요청]
  AI(gemini·openai·claude·ollama)가 Python 소스를 리뷰해 고친 전체 소스를 내면,
  앱이 테스트로 '더 나아졌는지' 확인해 스스로 원본에 반영하고, 실패하면 되돌린 뒤
  실패한 테스트를 같은 AI에게 돌려줘 다시 고치게 한다(사람 개입 없음, Git 커밋은 사람이 지시).

[자동 수정(auto_apply) 안내 — 2026-11-10, LuckyBoys 결정: 완전 자동]
- review_python_source는 검증된 리뷰 제안을 원본 소스에 직접 적용한다
  (config.MULTI_PERSONA_REVIEW_AUTO_APPLY, 호출 시 auto_apply 인자로 개별 지정 가능).
- 적용 전 job 폴더에 original.py 백업 → 문법 컴파일 → test_paths pytest → 실패 시 자동 되돌림.
- Git 커밋은 하지 않는다(사람이 확인 후 지시).

⚠ 주의: test_paths 없이 호출하면 문법만 맞아도 원본이 바뀐다(동작이 달라져도 되돌리지 않음).
  중요한 파일은 반드시 test_paths=["tests/...", "harness/tests/..."]를 함께 넘길 것.
  허용 폴더: config.MULTI_PERSONA_AUTO_APPLY_TEST_ROOTS (tests/, harness/tests/)

[실패 피드백 재시도 — 2026-11-11, LuckyBoys 결정]
- 자동 적용이 되돌려지거나 일부만 적용되면, 실패한 테스트(이름·기대값·실제값)와 새로 깨진 테스트를
  job 폴더 round<N>/feedback.txt로 만들어 직전 수정안과 함께 같은 AI에게 다시 리뷰시킨다(--error-path).
- 판정 기준(퇴행 금지 + 통과 수 증가)은 그대로다. 나빠지면 반영하지 않는다(라운드마다 단조 개선).
- 최대 라운드·최소 남은 시간·피드백 개수는 config.MULTI_PERSONA_AUTO_APPLY_* 에서 읽는다.

[2026-11-21 개선 — LuckyBoys 승인: 실패 테스트 집중·추가 기능 차단·느린 모델 시간 배분]
- 실패 테스트 집중: 1라운드 전에 원본으로 테스트를 한 번 돌려, 이미 실패하는 테스트(이름·메시지·테스트 코드 일부)를
  job 폴더 focus.txt로 만들어 1라운드부터 --error-path로 준다(사용자 오류 로그가 있으면 뒤에 붙임).
- 추가 기능 차단: 퇴행을 낸 제안은 바뀐 함수·클래스를 하나씩 원본으로 되돌려 본다(harness/mcp/tools/auto_apply.py).
- 시간 배분: config.MULTI_PERSONA_REVIEW_PROVIDERS[공급자]["job_timeout_seconds"]가 있으면 그 공급자만 작업 한도를
  그 값으로 쓴다(상한 config.MULTI_PERSONA_REVIEW_PROVIDER_TIMEOUT_MAX_SECONDS). 없으면 예전 한도 그대로.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from uuid import uuid4
from time import monotonic

import config as project_config
# 2026-11-21: Ollama 사전 점검용 함수 두 개를 함께 가져온다(테스트가 이 모듈 이름으로 대역을 넣는다).
from common.common_function import (list_ollama_models, logger, normalize_required_text,
                                    resolve_ollama_base_url)
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
    2026-11-12: 공용 CLI에는 config.MULTI_PERSONA_REVIEW_WEB_SEARCH가 False일 때 "--no-web-search"를
    붙여 소스 리뷰 중 Tavily 검색과 그로 인한 router 재호출을 막는다(전용 CLI는 이 인자를 모르므로 붙이지 않음).
    잘못된 입력(문자열 아님, 등록되지 않은 이름)은 리뷰 시작 전에 거부한다.
    """
    name = project_config.MULTI_PERSONA_REVIEW_DEFAULT_PROVIDER if provider is None else provider
    if not isinstance(name, str) or name not in project_config.MULTI_PERSONA_REVIEW_PROVIDERS:
        raise ValueError("provider must be one of: "
                         + ", ".join(sorted(project_config.MULTI_PERSONA_REVIEW_PROVIDERS)))
    entry = project_config.MULTI_PERSONA_REVIEW_PROVIDERS[name]
    extra = ["--provider", entry["llm"]] if entry.get("llm") else []
    if entry.get("llm") and not project_config.MULTI_PERSONA_REVIEW_WEB_SEARCH:
        extra.append("--no-web-search")
    if name == project_config.MULTI_PERSONA_REVIEW_DEFAULT_PROVIDER:
        return name, REVIEW_SOURCE, extra
    return name, PROJECT_ROOT / entry["cli"], extra


def _provider_timeout(provider_name: str) -> tuple[int, bool]:
    """공급자별 작업 한도(초)와 '공급자 전용 값인지'를 돌려준다 (2026-11-21, LuckyBoys 승인: ollama 3시간).

    - config.MULTI_PERSONA_REVIEW_PROVIDERS[이름]에 job_timeout_seconds가 없으면 예전 한도
      (config.MULTI_PERSONA_REVIEW_TIMEOUT_SECONDS)와 False.
    - 있으면 1 이상 config.MULTI_PERSONA_REVIEW_PROVIDER_TIMEOUT_MAX_SECONDS 이하 정수여야 한다
      (bool·문자열·0 이하·상한 초과는 작업 시작 전에 ValueError).
    """
    entry = project_config.MULTI_PERSONA_REVIEW_PROVIDERS[provider_name]
    if "job_timeout_seconds" not in entry:
        return int(project_config.MULTI_PERSONA_REVIEW_TIMEOUT_SECONDS), False
    value = entry["job_timeout_seconds"]
    cap = int(project_config.MULTI_PERSONA_REVIEW_PROVIDER_TIMEOUT_MAX_SECONDS)
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= cap:
        raise ValueError(f"job_timeout_seconds for {provider_name} must be an integer between 1 and {cap}")
    return value, True


def _worker_timeout_limit() -> int:
    """워커가 받아들이는 작업 한도 최댓값: 예전 상한과 공급자 전용 상한 중 큰 값."""
    return max(int(project_config.SPS_SOURCE_EXECUTION_TIMEOUT_SECONDS),
               int(project_config.MULTI_PERSONA_REVIEW_PROVIDER_TIMEOUT_MAX_SECONDS))


class _EnvironmentNotReady(Exception):
    """리뷰를 시작하면 안 되는 실행 환경 문제(Ollama 연결·모델). 메시지가 그대로 보고 이유가 된다."""


def _ollama_preflight(provider_name) -> str | None:
    """Ollama 공급자의 리뷰 전 환경 점검 (2026-11-21, LuckyBoys 선택 1안). 문제가 없으면 None.

    왜: 터널이 끊기거나 AI 서버 IP가 바뀌면 자동 선택이 개발 서버 CPU Ollama로 떨어져, AI 호출 8번이 모두
        시간 초과로 40분을 날렸다(job 86dcf050). 모델이 없는 Ollama(노트북에 12b 없음)도 같은 낭비가 된다.
    점검(읽기 전용 GET 2번, AI 생성 호출 없음):
      1) 주소: common/llm_provider.py와 같은 규칙(OLLAMA_BASE_URL → config 고정값 → 후보 자동 선택)으로 고른 주소가
         config.MULTI_PERSONA_OLLAMA_REJECT_URLS(개발 서버 CPU)이면 실패.
      2) 모델: llm_provider와 같은 규칙(모델 환경변수 → default_model → config.SPS_SOURCE_PARTNER_OLLAMA_MODEL)의
         모델이 /api/tags 목록에 없으면 실패(태그 없는 이름은 ':latest'로도 찾는다).
    다른 공급자(gemini·openai·claude)는 점검하지 않는다(None).
    반환 문장은 '[환경 점검 실패]'로 시작하고 사람이 할 일(터널·IP·pull)을 안내한다.
    """
    entry = project_config.MULTI_PERSONA_REVIEW_PROVIDERS.get(
        provider_name or project_config.MULTI_PERSONA_REVIEW_DEFAULT_PROVIDER) or {}
    if entry.get("llm") != "ollama":
        return None
    head = "[환경 점검 실패] "
    pinned = os.getenv("OLLAMA_BASE_URL", "").strip() or project_config.SPS_SOURCE_PARTNER_OLLAMA_BASE_URL
    try:
        base_url = resolve_ollama_base_url(pinned, project_config.SPS_SOURCE_PARTNER_OLLAMA_CANDIDATES,
                                           project_config.SPS_SOURCE_PARTNER_OLLAMA_PROBE_TIMEOUT_SECONDS)["base_url"]
    except Exception as error:  # 후보 전부 응답 없음·설정 오류
        return (head + "Ollama 후보 주소가 하나도 응답하지 않음 — AI 서버가 켜져 있는지, 개발 서버의 "
                f"터널(11435)이 열려 있는지, .env의 GPU IP가 맞는지 확인하세요 ({type(error).__name__})")
    rejected = {url.rstrip("/") for url in project_config.MULTI_PERSONA_OLLAMA_REJECT_URLS}
    if base_url.rstrip("/") in rejected:
        return (head + f"자동 선택이 리뷰에 쓰면 안 되는 주소({base_url}, 개발 서버 CPU)로 떨어짐 — "
                "개발 서버의 AI 서버 터널(ssh -L 11435) 또는 노트북 터널이 끊겼거나 AI 서버 IP가 바뀌었습니다. "
                "터널·IP를 확인하세요")
    settings = project_config.MULTI_PERSONA_LLM_PROVIDERS["ollama"]
    model = (os.getenv(settings["model_env"], "").strip() or settings["default_model"]
             or project_config.SPS_SOURCE_PARTNER_OLLAMA_MODEL)
    try:
        names = list_ollama_models(base_url, project_config.MULTI_PERSONA_OLLAMA_PREFLIGHT_TIMEOUT_SECONDS)
    except Exception as error:
        return head + f"{base_url}/api/tags 조회 실패 — Ollama 상태를 확인하세요 ({type(error).__name__})"
    wanted = {model} if ":" in model else {model, model + ":latest"}
    if not wanted & set(names):
        return (head + f"모델 '{model}'이(가) {base_url} Ollama에 없음 — 그 서버에서 'ollama pull {model}' 하거나 "
                ".env의 모델 이름을 확인하세요")
    return None


def _project_path(value: str, field_name: str) -> Path:
    """Resolve caller paths inside the project, including symlink targets."""
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be text")
    path = (PROJECT_ROOT / Path(normalize_required_text(value, field_name)).expanduser()).resolve()
    if PROJECT_ROOT not in path.parents:
        raise ValueError(f"{field_name} must stay inside the project")
    return path


def _systemd_command(arguments: list[str], timeout: int, purpose: str,
                     runtime_cap: int | None = None) -> tuple[str, list[str]]:
    """Build a fixed-account transient worker without reading secret file contents."""
    # 요청 작업 시간에 결과 저장 여유를 더한 값을 systemd 상한으로 유지한다.
    unit = "sps-" + purpose + "-" + uuid4().hex
    # 2026-10-31 회귀 수정: 유닛 수명은 config.SPS_GENERAL_UNIT_RUNTIME_SECONDS(현재 3600)를
    # 넘지 않는다. 호출자가 더 큰 값(예: 30010, 3600+grace)을 넘겨도 RuntimeMaxSec는 상한으로 고정한다.
    # 상한값은 하드코딩하지 않고 루트 config.py에서 읽는다(Repository/Metadata 우선 원칙).
    # 2026-11-14 LuckyBoys 선택 A: 자기 수리(self_repair_run)만 config.SELF_REPAIR['job_timeout_seconds']
    # (36,000초)를 runtime_cap 으로 넘겨 상한을 올린다. runtime_cap=None(기본)이면 기존 동작 그대로.
    # 잘못된 runtime_cap(양의 정수 아님, bool 포함)은 명령을 만들기 전에 거부한다.
    if runtime_cap is not None and (isinstance(runtime_cap, bool) or not isinstance(runtime_cap, int)
                                    or runtime_cap < 1):
        raise ValueError("runtime_cap must be a positive integer")
    cap = int(project_config.SPS_GENERAL_UNIT_RUNTIME_SECONDS) if runtime_cap is None else runtime_cap
    runtime_max = min(int(timeout), cap)
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


def _auto_apply(source: Path, proposed: Path, job_dir: Path, request: dict, budget: float,
                expected_sha256: str | None = None) -> dict:
    """자동 적용 — 2026-11-10 재사용 모듈 harness.mcp.tools.auto_apply로 분리, 여기서는 위임만 한다.

    ⚠ test_paths가 없으면 문법만 맞아도 원본이 바뀐다(세부 동작은 auto_apply 모듈 헤더 참고).
    expected_sha256: 재시도 라운드에서는 '그 라운드 시작 때의 원본 해시'를 넘긴다(없으면 제출 당시 해시).
    """
    return auto_apply.apply_with_rollback(
        source, proposed, job_dir, expected_sha256 or request["source_sha256"],
        request.get("test_paths") or [], budget, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# 2026-11-11 실패 피드백 재시도(LuckyBoys 결정: "그런 오류를 만나면 앱이 스스로 대응")
# 배경: 어려운 시험(테트리스)에서 AI가 오류 87개를 고쳤지만, 다른 오류에 가려져 우연히 통과하던
#       테스트 1개가 새로 실패해 전부 되돌려졌다. AI는 그 실패를 볼 기회가 없었다.
# 대응: 실패 결과를 오류 로그로 돌려주고 한 번 더 고치게 한다. 판정 기준은 완화하지 않는다.
# ---------------------------------------------------------------------------
_ROUND_KEYS = ("applied", "partial", "rolled_back", "reason",
               "tests_passed_before", "tests_passed_after", "tests_total")


# ---------------------------------------------------------------------------
# 2026-11-21 상황별 대응표 + 고쳐질 때까지 반복 (LuckyBoys 요청)
# 수정 중 만나는 상황마다 다음 행동을 config.MULTI_PERSONA_SELFFIX_ACTIONS 한 곳에서 정한다.
#   상황(situation)        뜻                                          허용 행동
#   all_passed            제안 반영 후 테스트 전부 통과(성공)            stop
#   improved              퇴행 없이 통과 수 증가(부분 반영)              next_round / stop
#   no_gain               통과 수가 늘지 않아 되돌림                     next_round / stop
#   regressed             원래 통과하던 테스트를 깨서 되돌림              next_round / stop
#   format_rejected       답이 출력 형식 검사에서 거부됨                  retry_same_round / next_round / stop
#   cli_error             리뷰 CLI 비정상 종료                           stop / next_round
#   provider_fatal        크레딧 부족·키 오류·Ollama 메모리 부족 등        stop
#   review_timeout        리뷰가 남은 시간 안에 안 끝남                   stop
#   time_low              다음 라운드를 시작할 시간이 모자람               stop
# retry_same_round는 config.MULTI_PERSONA_AUTO_APPLY_UNVERIFIED_RETRIES번까지 같은 라운드를 다시 하고,
# 그래도 안 되면 next_round로 넘어간다. 반복은 '전부 통과'(성공) 또는 '제자리걸음'(통과 수가
# config.MULTI_PERSONA_SELFFIX_STAGNATION_ROUNDS 라운드 연속 늘지 않음)에서 끝난다.
# config.MULTI_PERSONA_AUTO_APPLY_MAX_ROUNDS는 비용·시간을 막는 안전 상한이다.
# ---------------------------------------------------------------------------
_ALLOWED_ACTIONS = {
    "all_passed": {"stop"},
    "improved": {"next_round", "stop"},
    "no_gain": {"next_round", "stop"},
    "regressed": {"next_round", "stop"},
    "format_rejected": {"retry_same_round", "next_round", "stop"},
    "cli_error": {"stop", "next_round"},
    "provider_fatal": {"stop"},      # 다시 불러도 같은 오류(비용만 듦)
    "review_timeout": {"stop"},      # 남은 시간이 없으므로 계속할 수 없음
    "time_low": {"stop"},
}


def _selffix_actions() -> dict:
    """config 대응표를 검사해 돌려준다. 모든 상황이 있고 허용된 행동이어야 한다(아니면 AI를 더 부르기 전에 ValueError)."""
    table = getattr(project_config, "MULTI_PERSONA_SELFFIX_ACTIONS", None)
    if not isinstance(table, dict):
        raise ValueError("MULTI_PERSONA_SELFFIX_ACTIONS must be a dict")
    for situation, allowed in _ALLOWED_ACTIONS.items():
        if table.get(situation) not in allowed:
            raise ValueError(f"MULTI_PERSONA_SELFFIX_ACTIONS[{situation!r}] must be one of {sorted(allowed)}")
    return table


def _stagnation_limit() -> int:
    """제자리걸음 기준(연속 라운드 수). 1 이상 정수가 아니면(bool·문자열 포함) ValueError."""
    value = getattr(project_config, "MULTI_PERSONA_SELFFIX_STAGNATION_ROUNDS", None)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("MULTI_PERSONA_SELFFIX_STAGNATION_ROUNDS must be a positive integer")
    return value


def _classify_apply(auto_result: dict) -> str:
    """자동 적용 결과를 상황 이름으로 바꾼다(all_passed / improved / regressed / no_gain)."""
    if auto_result.get("applied"):
        return "improved" if auto_result.get("partial") else "all_passed"
    return "regressed" if auto_result.get("newly_failed") else "no_gain"


def _passed_count(auto_result: dict) -> int:
    """지금 디스크의 소스 기준 통과 수: 반영됐으면 적용 후 수, 되돌렸으면 적용 전 수."""
    key = "tests_passed_after" if auto_result.get("applied") else "tests_passed_before"
    value = auto_result.get(key)
    return value if isinstance(value, int) else -1


def _round_view(auto_result: dict) -> dict:
    """라운드 기록에 남길 자동 적용 결과 요약(2026-11-21: 대응표 상황 이름 situation 추가)."""
    view = {key: auto_result.get(key) for key in _ROUND_KEYS}
    view["situation"] = _classify_apply(auto_result)
    return view


def _needs_retry(auto_result: dict) -> bool:
    """되돌려졌거나(테스트·문법 실패) 일부만 적용돼 실패 테스트가 남았으면 다음 라운드가 필요하다."""
    return bool(auto_result.get("rolled_back") or auto_result.get("partial"))


def _failure_context(text, max_lines) -> list[str]:
    """pytest 실패 본문에서 '가장 안쪽 프레임'의 테스트 코드(assert 앞 줄들)와 E 줄을 뽑는다 (2026-11-21).

    이유: 'AssertionError' 한 줄만으로는 작은 모델이 테스트가 무엇을 넣고 무엇을 기대하는지 모른다.
    - 마지막 '>' 줄(실제로 실패한 줄)부터 위로, 4칸 들여쓴 소스 줄이 이어지는 동안 모은다
      (바깥 감싼 함수 프레임은 '_ _ _' 구분 줄에서 끊겨 빠진다).
    - 그 아래 'E' 줄을 붙인다. 전체는 max_lines 줄 이내(코드는 끝쪽, 즉 assert 가까운 줄을 남긴다).
    잘못된 입력(본문 없음·'>' 줄 없음·max_lines가 1 미만이거나 정수 아님)이면 빈 목록.
    """
    if not text or isinstance(max_lines, bool) or not isinstance(max_lines, int) or max_lines < 1:
        return []
    lines = text.splitlines()
    marks = [index for index, line in enumerate(lines) if line.startswith(">")]
    if not marks:
        return []
    last = marks[-1]
    start = last
    while start > 0 and lines[start - 1].startswith("    "):
        start -= 1
    errors = []
    for line in lines[last + 1:]:
        if not line.startswith("E"):
            break
        errors.append(line)
    errors = errors[:max(1, max_lines // 3)]
    room = max_lines - len(errors)
    code = lines[start:last + 1][-room:] if room > 0 else []
    return [line.rstrip() for line in code + errors]


def _context_lines() -> int:
    """피드백에 실패 테스트 코드를 몇 줄까지 붙일지(config). 없거나 잘못된 값이면 0(= 붙이지 않음)."""
    value = getattr(project_config, "MULTI_PERSONA_AUTO_APPLY_FEEDBACK_CONTEXT_LINES", 0)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return 0
    return value


def _junit_failures(xml_path: Path, limit: int, context: int = 0) -> list[str]:
    """pytest junit xml에서 실패·오류 테스트의 '- 이름: 메시지'를 최대 limit개 뽑는다(파일이 없으면 빈 목록).

    context(2026-11-21): 1 이상이면 각 실패 아래에 '    | '로 시작하는 테스트 코드 줄(_failure_context)을 붙인다.
    limit는 줄 수가 아니라 실패 테스트 개수다(context=0이면 예전과 결과가 같다).
    """
    try:
        root = ET.parse(xml_path).getroot()
    except (OSError, ET.ParseError):
        return []
    lines, count = [], 0
    for case in root.iter("testcase"):
        problem = case.find("failure")
        if problem is None:
            problem = case.find("error")
        if problem is None:
            continue
        message = " ".join((problem.get("message") or "").split())
        # 2026-11-16: message가 'AssertionError' 한 단어뿐이면 AI가 무엇을 기대하는지 모른다.
        # pytest 본문에서 실패한 줄(">")과 오류 줄("E")을 덧붙여 기대값이 전달되게 한다(최대 3줄).
        detail = [" ".join(line.split()) for line in (problem.text or "").splitlines()
                  if line.lstrip().startswith((">", "E "))][:3]
        if detail:
            message = (message + " | " if message else "") + " / ".join(detail)
        elif not message:
            message = " ".join((problem.text or "").split())
        lines.append(f"- {case.get('name')}: {message[:300]}")
        if context:
            lines.extend("    | " + line for line in _failure_context(problem.text, context))
        count += 1
        if count >= limit:
            break
    return lines


def _write_focus_feedback(job_dir: Path, request: dict, user_log: Path | None, budget: float) -> Path | None:
    """1라운드 전에 원본으로 테스트를 돌려, 이미 실패하는 테스트를 focus.txt로 남긴다 (2026-11-21).

    반환: focus.txt 경로 / 자동 적용·테스트가 없거나, 원본 테스트가 모두 통과하거나, 테스트 실행이 실패하면 None
    (None이면 1라운드는 예전처럼 사용자 오류 로그만 받는다). 원본 소스는 바꾸지 않는다(테스트만 실행).
    """
    tests = request.get("test_paths") or []
    if not request.get("auto_apply") or not tests or budget < 60:
        return None
    try:
        code, tail, outcome = auto_apply._run_tests(PROJECT_ROOT, tests, time.monotonic() + budget,
                                                    job_dir / "junit_focus.xml")
    except Exception as error:  # 테스트 실행 문제로 리뷰 자체를 막지 않는다
        logger.warning("focus test run failed: %s", type(error).__name__)
        return None
    if code == 0:
        return None
    limit = max(1, int(project_config.MULTI_PERSONA_AUTO_APPLY_FEEDBACK_MAX_FAILURES))
    failures = _junit_failures(job_dir / "junit_focus.xml", limit, _context_lines())
    lines = ["[먼저 고칠 실패 테스트 — 원본 소스로 테스트를 돌린 결과]",
             "아래 테스트가 지금 원본에서 실패합니다. 이 실패를 없애는 것이 이번 수정의 목표입니다."]
    if outcome is not None:
        lines.append(f"통과 테스트 수: {len(outcome[0])} / 전체 {outcome[1]}")
    lines.extend(failures or ["pytest 출력 끝부분:", tail or "(없음)"])
    lines.append("실패한 테스트가 확인하는 함수만 고치세요. 다른 함수(외부 API 호출 방식·반환 문장·출력 형식)와 "
                 "이미 통과하는 동작은 바꾸지 말고, 새 기능 추가·리팩터링은 하지 마세요.")
    if user_log is not None:
        lines += ["", "[사용자가 준 오류 로그]", user_log.read_text(encoding="utf-8", errors="replace")]
    focus = job_dir / "focus.txt"
    focus.write_text(_mask_secrets("\n".join(lines)), encoding="utf-8")
    focus.chmod(0o600)
    return focus


def _write_round_feedback(path: Path, result_dir: Path, auto_result: dict,
                          rejected: list[str] | None = None) -> None:
    """다음 라운드 리뷰 CLI의 --error-path로 넘길 실패 요약을 쓴다(비밀값은 마스킹, 소유자만 읽기).

    rejected(2026-11-14 추가): 직전 시도의 답이 출력 검사에서 거부된 이유. 있으면 맨 앞에 적어
    AI가 같은 형식 실수를 반복하지 않게 한다(job ca0a8c65: 맞게 고친 2차 답이 형식 때문에 버려짐).
    """
    limit = max(1, int(project_config.MULTI_PERSONA_AUTO_APPLY_FEEDBACK_MAX_FAILURES))
    lines = []
    if rejected:
        lines.append("[직전 답이 출력 검사에서 거부됨 — 수정 내용은 버려졌으니 아래를 지켜 다시 제출]")
        lines.extend(f"- {reason}" for reason in rejected)
        lines.append("2번 진단에서 수정할 함수는 '수정 필요'로, 고치지 않을 함수는 '수정 불필요'로 분명히 나누고, "
                     "'수정 필요'로 적은 함수는 3번 전체 소스에서 실제 실행 코드까지 고치세요. "
                     "3번에는 전체 소스를 닫힌 python 코드 블록 하나로 출력하세요.")
    lines += ["[자동 수정 검증 실패 — 직전 수정안을 테스트로 확인한 결과]",
              f"사유: {auto_result.get('reason') or '일부 테스트 실패(부분 적용)'}",
             f"통과 테스트 수: 적용 전 {auto_result.get('tests_passed_before', '?')} → "
             f"적용 후 {auto_result.get('tests_passed_after', '?')} / 전체 {auto_result.get('tests_total', '?')}"]
    newly = auto_result.get("newly_failed") or []
    if newly:
        lines.append("원래 통과하다가 새로 실패한 테스트(퇴행 — 다른 오류에 가려져 있던 결함일 수 있음, 반드시 해결):")
        lines.extend(f"- {name}" for name in newly)
        # 2026-11-16: 퇴행은 대부분 '결함 외의 부분을 바꿔서' 생긴다(메모리 에이전트 시험의 ChatGPT·Claude).
        lines.append("위 테스트가 확인하는 함수는 원래 코드의 동작(반환 문장·외부 API 호출 방식과 인자·출력 형식)으로 "
                     "되돌리고, 진단한 결함과 관련된 줄만 고치세요. 새 기능 추가·리팩터링은 하지 마세요.")
    # 2026-11-21: 실패 테스트 코드 일부도 함께 준다(무엇을 기대하는지 알게).
    failures = _junit_failures(result_dir / "junit_after.xml", limit, _context_lines())
    if failures:
        lines.append(f"실패한 테스트와 메시지(최대 {limit}개):")
        lines.extend(failures)
    else:
        lines.extend(["pytest 출력 끝부분:", auto_result.get("test_output_tail") or "(없음)"])
    lines.append("위 실패가 모두 사라지도록 입력 소스를 고치세요. 이미 통과하는 동작은 바꾸지 마세요.")
    path.write_text(_mask_secrets("\n".join(lines)), encoding="utf-8")
    path.chmod(0o600)


def _contract_errors(text: str) -> list[str]:
    """리뷰 CLI 출력에서 '[출력 검증] 오류=[...]' 줄을 뽑는다(오류가 없으면 빈 목록)."""
    return [line.strip() for line in text.splitlines()
            if line.startswith("[출력 검증] 오류=") and not line.startswith("[출력 검증] 오류=[]")]


def _provider_fatal(text: str) -> str | None:
    """리뷰 CLI 출력에서 치명적 공급자 오류 표시 줄(크레딧 부족 402·키 오류 401)을 찾는다(2026-11-14).

    표시 줄 머리말은 config.MULTI_PERSONA_FATAL_PROVIDER_MARKER. 있으면 그 줄(최대 500자), 없으면 None.
    이 줄이 있으면 다시 시도해도 같은 오류이므로 재시도·다음 라운드를 하지 않고 결과에 보고한다.
    """
    marker = project_config.MULTI_PERSONA_FATAL_PROVIDER_MARKER
    for line in text.splitlines():
        if line.startswith(marker):
            return line.strip()[:500]
    return None


def _round_temperature(number) -> float:
    """재시도 라운드 번호(1부터)의 작업 AI temperature (2026-11-14, LuckyBoys 결정: 1차 0.4 → 2차 0.2 → 3차 0.0).

    config.MULTI_PERSONA_AUTO_APPLY_ROUND_TEMPERATURES에서 읽고, 라운드가 더 많으면 마지막 값을 쓴다.
    잘못된 설정(비었거나 0.0~1.0 밖, 숫자 아님)이나 잘못된 라운드 번호는 AI를 부르기 전에 ValueError.
    """
    if not isinstance(number, int) or isinstance(number, bool) or number < 1:
        raise ValueError("round number must be a positive integer")
    temps = project_config.MULTI_PERSONA_AUTO_APPLY_ROUND_TEMPERATURES
    if not isinstance(temps, (list, tuple)) or not temps or any(
            isinstance(t, bool) or not isinstance(t, (int, float)) or not 0.0 <= t <= 1.0 for t in temps):
        raise ValueError("MULTI_PERSONA_AUTO_APPLY_ROUND_TEMPERATURES must be numbers between 0.0 and 1.0")
    return float(temps[min(number, len(temps)) - 1])


def _run_feedback_rounds(request: dict, job_dir: Path, source: Path, first_proposed: Path,
                         first_result: dict, started: float, timeout: int):
    """1차 자동 적용이 실패하면 실패 테스트를 피드백으로 주고 같은 AI로 리뷰를 다시 돌린다.

    반환: (최종 auto_apply 결과, 라운드 기록 목록, 마지막 제안 파일)
    - 최대 라운드: config.MULTI_PERSONA_AUTO_APPLY_MAX_ROUNDS(1 이하이면 재시도 없음)
    - 남은 시간 < config.MULTI_PERSONA_AUTO_APPLY_RETRY_MIN_SECONDS 이면 멈춘다(그 절반은 테스트·저장 여유).
    - 입력 소스: 직전 라운드가 (일부) 적용됐으면 지금 원본, 아니면 직전 제안 소스(고친 것을 잃지 않게).
    - 판정 기준선은 '그 라운드 시작 때 디스크의 원본'이다(auto_apply 규칙 그대로 = 나빠지면 반영 안 함).
    - 2026-11-14: 라운드의 답이 출력 검사에서 거부되면(검증 미통과) 바로 멈추지 않고, 거부 이유를 피드백
      맨 앞에 넣어 같은 라운드를 config.MULTI_PERSONA_AUTO_APPLY_UNVERIFIED_RETRIES번까지 다시 시도한다
      (폴더 round<N>_retry<k>, 기록에는 attempt=k). 라운드 수에는 세지 않으며 0 이하이면 예전처럼 멈춘다.
      리뷰 CLI가 비정상 종료(returncode != 0)한 경우는 다시 시도하지 않는다.
    - 2026-11-21: 상황마다 config.MULTI_PERSONA_SELFFIX_ACTIONS 대응표대로 움직이고, 전부 통과(성공)나
      제자리걸음(config.MULTI_PERSONA_SELFFIX_STAGNATION_ROUNDS 라운드 연속 통과 수 그대로)까지 반복한다.
    """
    actions = _selffix_actions()          # 잘못된 대응표·기준은 2라운드 AI를 부르기 전에 멈춘다
    stagnation_limit = _stagnation_limit()
    rounds = [{"round": 1, "verified": True, **_round_view(first_result)}]
    auto_result, last_proposed, last_dir = first_result, first_proposed, job_dir
    max_rounds = int(project_config.MULTI_PERSONA_AUTO_APPLY_MAX_ROUNDS)
    min_seconds = int(project_config.MULTI_PERSONA_AUTO_APPLY_RETRY_MIN_SECONDS)
    format_retries = int(project_config.MULTI_PERSONA_AUTO_APPLY_UNVERIFIED_RETRIES)
    _, review_cli, provider_args = _review_cli(request.get("provider"))
    # 제자리걸음 판정: 지금까지 가장 많이 통과한 수(best)가 늘지 않은 연속 라운드 수(stagnant)
    first_situation = _classify_apply(first_result)
    best = max(_passed_count(first_result), first_result.get("tests_passed_before") or 0)
    stagnant = 0 if first_situation in ("improved", "all_passed") else 1
    if first_situation != "all_passed" and actions[first_situation] == "stop":
        rounds[-1]["stop_reason"] = f"1라운드 상황 '{first_situation}' → 대응표(stop)에 따라 멈춤"
        return auto_result, rounds, last_proposed
    number, attempt, rejected = 2, 0, []  # attempt: 같은 라운드 재시도 번호, rejected: 직전 거부 이유
    while True:
        if not _needs_retry(auto_result):
            break                                                   # 전부 통과 = 성공 종료(멈춤 이유 없음)
        if stagnant >= stagnation_limit:
            rounds[-1]["stop_reason"] = (f"{stagnant}라운드 연속 통과 수가 늘지 않아(제자리걸음) 멈춤 — "
                                         f"최고 통과 {best}개")
            break
        if number > max_rounds:
            rounds[-1]["stop_reason"] = f"최대 라운드({max(max_rounds, 1)})(안전 상한)를 모두 썼는데도 테스트가 다 통과하지 않음"
            break
        remaining = timeout - (monotonic() - started)
        if remaining < min_seconds:
            # 상황 time_low(대응표: stop). 2026-11-18: 반복을 끝내는 모든 경로에 stop_reason을 남긴다.
            rounds.append({"round": number, "skipped": "not enough time left", "remaining_seconds": round(remaining),
                           "situation": "time_low",
                           "stop_reason": f"남은 시간 {round(remaining)}초가 최소 {min_seconds}초보다 적어 "
                                          f"{number}라운드부터 실행 안 함"})
            break
        # 2026-11-21 (LuckyBoys 선택 1안): 라운드마다 AI를 부르기 전에 Ollama 연결·모델을 점검한다.
        # 실패는 다시 불러도 같은 '치명 오류'로 보고 대응표의 provider_fatal(stop)대로 멈춘다.
        env_problem = _ollama_preflight(request.get("provider"))
        if env_problem:
            rounds.append({"round": number, "skipped": "environment not ready", "situation": "provider_fatal",
                           "provider_fatal_error": env_problem,
                           "stop_reason": f"{number}라운드 전 환경 점검 실패로 멈춤: {env_problem}"})
            break
        round_dir = job_dir / (f"round{number}" + (f"_retry{attempt}" if attempt else ""))
        round_dir.mkdir(mode=0o700, exist_ok=True)
        candidate = round_dir / source.name
        candidate.write_bytes((source if auto_result.get("applied") else last_proposed).read_bytes())
        feedback = round_dir / "feedback.txt"
        _write_round_feedback(feedback, last_dir, auto_result, rejected)
        round_sha = hashlib.sha256(source.read_bytes()).hexdigest()  # 라운드 도중 외부 변경 감지용
        # 2026-11-14: 공용 CLI(--provider를 받는 CLI)에는 라운드별 작업 AI 온도를 넘긴다(전용 CLI는 이 인자를 모름).
        temperature = _round_temperature(number) if "--provider" in provider_args else None
        temp_args = ["--agent-temperature", str(temperature)] if temperature is not None else []
        command = [str(PROJECT_ROOT / "venv/bin/python"), "-u", str(review_cli), *provider_args, *temp_args,
                   "--source-path", str(candidate), "--error-path", str(feedback),
                   "--output-dir", str(round_dir)]
        round_started = monotonic()
        try:
            completed = subprocess.run(command, cwd=str(PROJECT_ROOT), stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, timeout=max(1, int(remaining - min_seconds / 2)),
                                       check=False)
        except subprocess.TimeoutExpired:
            rounds.append({"round": number, "verified": False, "reason": "review timed out",
                           "situation": "review_timeout",
                           "review_seconds": round(monotonic() - round_started, 3),
                           "stop_reason": f"{number}라운드 리뷰가 남은 시간 안에 끝나지 않아(시간 초과) 멈춤"})
            break
        text = _mask_secrets(completed.stdout.decode("utf-8", errors="replace"))
        log = round_dir / "review_output.txt"
        log.write_text(text + _mask_secrets(completed.stderr.decode("utf-8", errors="replace")), encoding="utf-8")
        log.chmod(0o600)
        proposed = round_dir / "proposed.py"
        verified, reasons = _judge_verification(text, proposed)
        entry = {"round": number, "verified": verified, "review_seconds": round(monotonic() - round_started, 3)}
        if temperature is not None:
            entry["agent_temperature"] = temperature
        if attempt:
            entry["attempt"] = attempt
        # 2026-11-14: 크레딧 부족(402)·키 오류(401)로 멈췄으면 이유를 남기고 같은 라운드 재시도도 하지 않는다.
        fatal = _provider_fatal(text)
        if completed.returncode != 0 or not verified:
            situation = "provider_fatal" if fatal else ("cli_error" if completed.returncode != 0 else "format_rejected")
            entry = {**entry, "returncode": completed.returncode, "reasons": reasons,
                     **({"provider_fatal_error": fatal} if fatal else {}), "situation": situation}
            rounds.append(entry)
            action = actions[situation]
            if action == "retry_same_round" and attempt < format_retries:
                # 같은 라운드를 다시 시도한다: 거부 이유(검증 사유 + 출력 검사 오류 줄)를 피드백에 넣는다.
                attempt += 1
                rejected = reasons + _contract_errors(text)
                continue
            if action == "stop":
                # 2026-11-18: 여기서 멈추는 이유가 기록에 없어 '시간 한도'로 잘못 보고됐다 → 이유를 적는다.
                if fatal:
                    entry["stop_reason"] = f"치명적 공급자 오류로 멈춤: {fatal}"
                elif completed.returncode != 0:
                    entry["stop_reason"] = f"{number}라운드 리뷰 CLI 비정상 종료(returncode={completed.returncode})"
                else:
                    entry["stop_reason"] = f"{number}라운드가 출력 형식 검사에서 떨어져 대응표(stop)에 따라 멈춤"
                break
            # next_round(또는 같은 라운드 재시도 한도 소진): 이 라운드는 '나아지지 않음'으로 세고 다음 라운드로 간다.
            entry["next_action"] = (f"같은 라운드 재시도 한도({max(format_retries, 0)}회) 소진 → 다음 라운드"
                                    if action == "retry_same_round" else "다음 라운드")
            rejected = reasons + _contract_errors(text) if situation == "format_rejected" else []
            stagnant += 1
            number, attempt = number + 1, 0
            continue
        auto_result = _auto_apply(source, proposed, round_dir, request,
                                  budget=timeout - (monotonic() - started), expected_sha256=round_sha)
        last_proposed, last_dir = proposed, round_dir
        rounds.append({**entry, **_round_view(auto_result)})
        situation = _classify_apply(auto_result)
        if situation in ("improved", "all_passed") and _passed_count(auto_result) > best:
            best, stagnant = _passed_count(auto_result), 0          # 나아짐 → 제자리걸음 초기화
        else:
            stagnant += 1
        if situation != "all_passed" and actions[situation] == "stop":
            rounds[-1]["stop_reason"] = f"{number}라운드 상황 '{situation}' → 대응표(stop)에 따라 멈춤"
            break
        number, attempt, rejected = number + 1, 0, []
    return auto_result, rounds, last_proposed


async def review_python_source(
    source_path: str,
    error_path: str | None = None,
    dry_run: bool = True,
    job_id: str | None = None,
    auto_apply: bool | None = None,
    test_paths: list[str] | None = None,
    provider: str | None = None,
) -> dict:
    """Self-fixing source review app (스스로 고치는 소스 리뷰 앱).

    An AI reviews the Python source and proposes a full fixed source; the app applies it by itself
    only when tests prove it is better, and otherwise restores the original and retries with feedback.
    - provider: gemini | openai | claude | ollama (config.MULTI_PERSONA_REVIEW_PROVIDERS).
    - Default dry-run validates paths without starting Python or an LLM.
    - dry_run=False starts a durable job and returns job_id; call again with the same source_path
      and job_id to read status/results. A disconnect does not cancel the job.
    - auto_apply (default from config): back up the original, compile, run test_paths (inside tests/
      or harness/tests/) with pytest. Policy "improve": apply when no previously passing test breaks
      and more tests pass; otherwise restore the original automatically.
    - Feedback rounds: if tests still fail, the failing tests are sent back to the same AI and the
      review runs again (config.MULTI_PERSONA_AUTO_APPLY_MAX_ROUNDS). Git commit is left to a human.
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
    # 2026-11-21: 공급자별 작업 한도(예: ollama 10800초). 전용 값이 없으면 예전 한도·검사를 그대로 쓴다.
    timeout, provider_specific = _provider_timeout(provider_name)
    grace = int(project_config.SPS_WORKER_RESULT_GRACE_SECONDS)
    if not provider_specific:
        # 워커의 실행 한도보다 큰 값은 제출 단계에서 거부해 비동기 실패를 막는다.
        if not 1 <= timeout <= project_config.SPS_SOURCE_EXECUTION_TIMEOUT_SECONDS:
            raise ValueError("Review timeout exceeds the configured source execution limit")
        # 2026-11-02: 리뷰 시간 + 결과 저장 여유가 유닛 상한을 넘으면 systemd가 결과 저장 전에 워커를 죽인다.
        if timeout + grace > int(project_config.SPS_GENERAL_UNIT_RUNTIME_SECONDS):
            raise ValueError("Review timeout plus result grace exceeds the transient unit runtime limit")
    # 공급자 전용 값이면 유닛 상한(runtime_cap)도 '한도 + 결과 저장 여유'로 올려야 systemd가 중간에 죽이지 않는다.
    runtime_cap = timeout + grace if provider_specific else None
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
        timeout + grace, "source-review", runtime_cap=runtime_cap)
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
    # 2026-11-21: 환경 점검(Ollama 연결·모델) 실패 이유. 있으면 AI를 부르지 않은 것이다.
    environment_problem = None
    try:
        source = _project_path(request["source_path"], "source_path")
        if hashlib.sha256(source.read_bytes()).hexdigest() != request["source_sha256"]:
            raise ValueError("Source changed after review submission")
        # Reconstruct the fixed CLI rather than executing a caller-supplied command.
        # 2026-11-10: 제출 때 저장한 provider로 CLI를 다시 고른다(이전 job은 기본 provider).
        _, review_cli, provider_args = _review_cli(request.get("provider"))
        command = [str(PROJECT_ROOT / "venv/bin/python"), "-u", str(review_cli), *provider_args,
                   "--source-path", str(source)]
        timeout = int(request["timeout_seconds"])
        # 2026-11-21: 공급자 전용 한도(최대 config.MULTI_PERSONA_REVIEW_PROVIDER_TIMEOUT_MAX_SECONDS)도 받아들인다.
        if not 1 <= timeout <= _worker_timeout_limit():
            raise ValueError("Invalid review timeout")
        user_log = None
        if request.get("error_path"):
            log = _project_path(request["error_path"], "error_path")
            if log.suffix not in {".log", ".txt"} or log.is_dir():
                raise ValueError("Invalid review error path")
            user_log = log
        # 2026-11-21 (LuckyBoys 선택 1안): Ollama 연결·모델 점검. 실패하면 리뷰 CLI(AI 호출)를 아예 시작하지 않는다.
        env_problem = _ollama_preflight(request.get("provider"))
        if env_problem:
            raise _EnvironmentNotReady(env_problem)
        # 2026-11-21 실패 테스트 집중: 원본에서 이미 실패하는 테스트를 1라운드부터 알려 준다(사용자 로그는 그 뒤에 붙음).
        focus_started = monotonic()
        focus = _write_focus_feedback(request_path.parent, request, user_log, timeout - (monotonic() - started))
        # focus 테스트에 쓴 시간(초, 정수로 내림)만큼만 리뷰 CLI 한도에서 뺀다(테스트를 안 돌렸으면 예전 한도 그대로).
        focus_seconds = int(monotonic() - focus_started)
        result["focus_path"] = str(focus.relative_to(PROJECT_ROOT)) if focus is not None else None
        if focus is not None:
            command.extend(["--error-path", str(focus)])
        elif user_log is not None:
            command.extend(["--error-path", str(user_log)])
        # 2026-11-02: 제안 파일 충돌 방지 — 이 job 폴더에만 보고서·제안 소스를 쓴다.
        command.extend(["--output-dir", str(request_path.parent)])
        completed = subprocess.run(command, cwd=str(PROJECT_ROOT),
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   timeout=max(1, timeout - focus_seconds), check=False)
        output, errors, returncode = completed.stdout, completed.stderr, completed.returncode
    except subprocess.TimeoutExpired as error:
        # subprocess.run kills/reaps its child; captured partial output remains available.
        output, errors = error.stdout or b"", error.stderr or b""
        timed_out = True
    except _EnvironmentNotReady as error:
        # 환경 점검 실패: AI를 부르지 않았다. 이유는 아래에서 provider_fatal_error로 올린다.
        environment_problem = str(error)
        errors = environment_problem.encode("utf-8", errors="replace")
    except Exception as error:
        errors = str(error).encode("utf-8", errors="replace")
    text = _mask_secrets(output.decode("utf-8", errors="replace"))
    stderr = _mask_secrets(errors.decode("utf-8", errors="replace"))
    # 2026-11-14: 리뷰 CLI가 치명적 공급자 오류(크레딧 부족 402·키 오류 401)로 멈췄는지 확인한다.
    # 2026-11-21: 환경 점검 실패도 같은 칸(provider_fatal_error)으로 보고한다.
    provider_fatal = _provider_fatal(text + "\n" + stderr) or environment_problem
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
        # 2026-11-14: 크레딧 부족(402)·키 오류(401)로 멈췄으면 그 이유를 그대로 보고한다.
        auto_result = {"auto_apply": True, "applied": False, "rolled_back": False,
                       "reason": provider_fatal or "review not verified"}
    # 2026-11-11: 1차 적용이 실패/부분이면 실패 테스트를 피드백으로 주고 같은 AI로 다시 고치게 한다.
    rounds, final_proposed = None, proposed
    if request.get("auto_apply") and success and request.get("test_paths"):
        try:
            auto_result, rounds, final_proposed = _run_feedback_rounds(
                request, request_path.parent, source, proposed, auto_result, started,
                int(request["timeout_seconds"]))
        except Exception as error:  # 재시도 중 오류가 1차 결과 저장을 막지 않게 한다
            rounds = [{"round": "retry", "error": _mask_secrets(f"{type(error).__name__}: {error}")[:300]}]
    # 2026-11-14: 재시도 라운드에서 치명적 공급자 오류로 멈췄으면 그 이유도 결과 맨 위 항목으로 올린다.
    if provider_fatal is None and rounds and isinstance(rounds[-1], dict):
        provider_fatal = rounds[-1].get("provider_fatal_error")
    limit = request["output_limit"]
    result.update(state="timed_out" if timed_out else ("completed" if success else "failed"),
                  provider_fatal_error=provider_fatal,
                  success=success, process_completed=process_completed,
                  timed_out=timed_out, returncode=returncode,
                  elapsed_seconds=round(monotonic() - started, 3), source_unchanged=unchanged,
                  model_verified=success,
                  verification_reasons=verification_reasons,
                  auto_apply_result=auto_result,
                  auto_apply_rounds=rounds,
                  final_proposed_path=(str(final_proposed.relative_to(PROJECT_ROOT))
                                       if final_proposed.is_file() else None),
                  tests_executed=bool(auto_result.get("test_returncode") is not None),
                  proposed_path=str(proposed.relative_to(PROJECT_ROOT)) if proposed.is_file() else None,
                  report_path=str(report.relative_to(PROJECT_ROOT)),
                  output=text[:limit], stderr=stderr[:limit],
                  output_truncated=len(text) > limit or len(stderr) > limit)
    _write_json(result_path, result)


if __name__ == "__main__" and len(sys.argv) == 3 and sys.argv[1] == "--worker":
    _run_review_job(sys.argv[2])
