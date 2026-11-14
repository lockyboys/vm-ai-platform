"""범용 자기 수리 엔진 — 어디서나 쓰는 "스스로 고치는 앱" (2026-11-10 LuckyBoys).

한 줄 요약
    등록된 대상(target)을 실행 → 성공 기준(verdict)으로 판정 → 실패하면 페르소나 수리 체인으로 소스를 고치고
    (git add 까지, 커밋 없음) → 다시 실행해서 확인한다. 대상은 등록소(config.py 표시 블록 / MariaDB)에서만 꺼낸다.

왜 이렇게 만들었나
    - 기존 autodiscover_self_repair 는 "수집기 탐색 실패(NEEDS_NEW_RULE)" 한 가지만 고쳤다.
      메리츠 10건 사례처럼 "성공처럼 보이지만 건수 부족"은 못 고쳤고, 다른 프로그램에는 쓸 수 없었다.
    - 그래서 실행 방법·판정 방법·수리 범위를 '대상 스펙'으로 빼고, 엔진은 그 스펙만 보고 움직이게 했다.
    - 수리 범위(scope)는 persona_repair_chain.run_chain(scope=...) 로 넘긴다(커밋 6a1c4ce 에서 일반화).

보안 원칙(SECURITY)
    - MCP 로 임의 명령을 실행하지 않는다. 등록된 대상만 실행하고, 인자는 셸 없이 리스트로 넘긴다.
    - 파라미터는 스펙에 선언된 이름만, 값은 str(한 줄, 200자 이내) 또는 int 만 받는다.
    - 실행·등록 모두 dry_run=True 가 기본값이다. 수리는 git add 까지만 하고 커밋하지 않는다.

판정(verdict) 3종
    exit_code : 종료 코드 0 이면 성공
    json_min  : stdout 마지막 JSON 줄(또는 파일)의 field 값이 min_param 값 이상이면 성공(건수 부족 → shortfall)
    pytest    : 지정 테스트가 통과하면 성공(command 를 생략하면 pytest 자체를 실행)

등록소(backend)
    config     : 루트 config.py 의 '# >>> SELF_REPAIR_TARGETS (generated)' ~ '# <<< SELF_REPAIR_TARGETS' 블록만
                 백업 → 결정적 직렬화 → compile 검사 → 원자적 교체. 블록 밖(다른 설정)은 건드리지 않는다.
    repository : MariaDB 테이블(config.SELF_REPAIR['repository_table']). 2차 작업(DDL 승인) 전이라 지금은
                 'repository backend unavailable' 오류를 명확히 돌려주고 아무것도 바꾸지 않는다.

설정: 루트 config.py 의 SELF_REPAIR / SELF_REPAIR_TARGETS (일반 지침 4).
DB: 이번 단계는 DB 를 연결·변경하지 않는다(repository 백엔드는 2차 DDL 승인 후 common/database.py 로 구현 예정).
"""
from __future__ import annotations

import ast
import asyncio
import json
import os
import pprint
import re
import string
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path, PurePosixPath
from time import monotonic
from typing import Any, Callable
from uuid import uuid4
from zoneinfo import ZoneInfo

import config as project_config  # 루트 공통 설정(일반 지침 4)
# 수리 범위 검증·수리 체인(커밋 6a1c4ce 에서 scope 일반화)
from harness.mcp.agents.persona_repair_chain import resolve_scope, run_chain
# 기존 수리 루프의 검증된 부품 재사용(수정하지 않음): staged 확인, 백업, 원복
from harness.mcp.agents.autodiscover_self_repair import backup_sources, restore_sources, staged_change_sets
# 백그라운드 job: orchestrator_tools 와 같은 systemd 명령·0600 원자적 JSON 저장·비밀값 마스킹
from harness.mcp.tools.multi_persona_tools import PROJECT_ROOT, _mask_secrets, _systemd_command, _write_json

_SETTINGS = project_config.SELF_REPAIR          # 엔진 설정(보고서·job 폴더, repository 테이블, job 상한 등)
CONFIG_PATH = PROJECT_ROOT / "config.py"        # config 백엔드가 고치는 파일(테스트에서는 임시 사본으로 교체)
BLOCK_START = "# >>> SELF_REPAIR_TARGETS (generated)"
BLOCK_END = "# <<< SELF_REPAIR_TARGETS"
BLOCK_VARIABLE = "SELF_REPAIR_TARGETS"
KST = ZoneInfo("Asia/Seoul")

NAME_PATTERN = re.compile(r"^[a-z0-9_]{1,64}$")                       # 대상 이름
PARAM_PATTERN = re.compile(r"^[a-z_][a-z0-9_]{0,63}$")                 # 파라미터 이름
MODULE_PATTERN = re.compile(r"^[A-Za-z_]\w*(\.[A-Za-z_]\w*)*$")        # python -m 모듈 이름
FIELD_PATTERN = re.compile(r"^[A-Za-z_]\w*(\.[A-Za-z_]\w*)*$")         # JSON 필드 경로(a.b.c)
JOB_ID_PATTERN = re.compile(r"[0-9a-f]{32}")                           # 경로 조작 차단용 job_id
VERDICT_TYPES = {"exit_code", "json_min", "pytest"}
MAX_PARAM_TEXT = 200                                                   # 문자열 파라미터 길이 상한
MAX_ROUNDS = 5                                                         # 수리 라운드 상한(비용 보호)
MAX_TIMEOUT_SECONDS = 36000                                            # 대상 1회 실행 상한
OUTPUT_LIMIT = 12000                                                   # MCP 응답 미리보기 한도


# ---------------------------------------------------------------------------
# 1. 대상 스펙 검증
# ---------------------------------------------------------------------------
def _positive_int(value: Any, field: str, upper: int) -> int:
    """1..upper 정수만 통과. bool 은 int 하위형이라 따로 거부한다."""
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= upper:
        raise ValueError(f"{field} must be an integer in 1..{upper}")
    return value


def _safe_relative(path: Any, field: str) -> str:
    """프로젝트 상대 경로만 허용(절대경로·'..'·역슬래시·빈 값 금지)."""
    if not isinstance(path, str) or not path or "\\" in path:
        raise ValueError(f"{field} must be a project-relative path")
    pure = PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"{field} must stay inside the project")
    return str(pure)


def _template_fields(template: str) -> list[str]:
    """'{name}' 자리표시 이름만 뽑는다. 형식 지정자·변환자·속성 접근은 거부한다(주입 방지)."""
    names = []
    for _, field, spec, conversion in string.Formatter().parse(template):
        if field is None:
            continue
        if spec or conversion or not PARAM_PATTERN.fullmatch(field):
            raise ValueError(f"invalid placeholder in template: {template!r}")
        names.append(field)
    return names


def _validate_verdict(verdict: Any, params: list[str]) -> dict:
    """판정 규칙 검사. json_min 은 읽을 위치·필드·목표 파라미터, pytest 는 테스트 목록이 필요하다."""
    if not isinstance(verdict, dict) or verdict.get("type") not in VERDICT_TYPES:
        raise ValueError(f"verdict.type must be one of {sorted(VERDICT_TYPES)}")
    verdict = dict(verdict)
    if verdict["type"] == "json_min":
        if verdict.get("source") not in {"stdout", "file"}:
            raise ValueError("json_min verdict needs source stdout|file")
        if verdict["source"] == "file":
            template = _safe_relative(verdict.get("file_template"), "verdict.file_template")
            if not set(_template_fields(template)) <= set(params):
                raise ValueError("verdict.file_template uses an undeclared param")
        if not isinstance(verdict.get("field"), str) or not FIELD_PATTERN.fullmatch(verdict["field"]):
            raise ValueError("verdict.field must be a dotted identifier path")
        if verdict.get("min_param") not in params:
            raise ValueError("verdict.min_param must be one of params")
    elif verdict["type"] == "pytest":
        tests = verdict.get("tests")
        if not isinstance(tests, list) or not tests:
            raise ValueError("pytest verdict needs a non-empty tests list")
        verdict["tests"] = [_safe_relative(test, "verdict.tests") for test in tests]
    return verdict


def _validate_command(command: Any, verdict_type: str) -> dict | None:
    """실행 방법: module 또는 script 중 정확히 하나. pytest 판정은 생략 가능(pytest 자체가 실행)."""
    if command is None and verdict_type == "pytest":
        return None
    if not isinstance(command, dict) or len(command) != 1 or not ({"module", "script"} & set(command)):
        raise ValueError("command must be {'module': ...} or {'script': ...}")
    if "module" in command:
        if not isinstance(command["module"], str) or not MODULE_PATTERN.fullmatch(command["module"]):
            raise ValueError("command.module must be a dotted module name")
        return {"module": command["module"]}
    script = _safe_relative(command["script"], "command.script")
    if not script.endswith(".py") or not (PROJECT_ROOT / script).is_file():
        raise ValueError("command.script must be an existing .py file in the project")
    return {"script": script}


def validate_target(spec: Any) -> dict:
    """대상 스펙을 검사하고 정규화한 복사본을 돌려준다. 잘못되면 ValueError."""
    if not isinstance(spec, dict):
        raise ValueError("target spec must be an object")
    name = spec.get("name")
    if not isinstance(name, str) or not NAME_PATTERN.fullmatch(name):
        raise ValueError("name must match [a-z0-9_]{1,64}")
    params = spec.get("params", [])
    if (not isinstance(params, list) or len(set(params)) != len(params)
            or not all(isinstance(p, str) and PARAM_PATTERN.fullmatch(p) for p in params)):
        raise ValueError("params must be a list of unique lowercase identifiers")
    verdict = _validate_verdict(spec.get("verdict"), params)
    command = _validate_command(spec.get("command"), verdict["type"])
    args_template = spec.get("args_template", [])
    if not isinstance(args_template, list) or not all(isinstance(a, str) for a in args_template):
        raise ValueError("args_template must be a list of strings")
    for argument in args_template:
        if not set(_template_fields(argument)) <= set(params):
            raise ValueError(f"args_template uses an undeclared param: {argument!r}")
    if spec.get("scope") is None:
        raise ValueError("scope is required (allowed_paths, regression_tests)")
    return {"name": name, "command": command, "args_template": list(args_template), "params": list(params),
            "verdict": verdict, "scope": resolve_scope(spec["scope"]),
            "max_rounds": _positive_int(spec.get("max_rounds", _SETTINGS["default_max_rounds"]),
                                        "max_rounds", MAX_ROUNDS),
            "timeout_seconds": _positive_int(spec.get("timeout_seconds"), "timeout_seconds", MAX_TIMEOUT_SECONDS)}


def validate_params(spec: dict, params: Any) -> dict:
    """선언된 파라미터만, 빠짐없이, 안전한 값(str 한 줄 / int)으로 받는다."""
    if not isinstance(params, dict):
        raise ValueError("params must be an object")
    declared = set(spec["params"])
    if set(params) != declared:
        raise ValueError(f"params must be exactly {sorted(declared)}")
    for key, value in params.items():
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            raise ValueError(f"param {key} must be str or int")
        if isinstance(value, str) and (len(value) > MAX_PARAM_TEXT or any(ch in value for ch in "\r\n\x00")):
            raise ValueError(f"param {key} must be one line of at most {MAX_PARAM_TEXT} chars")
    return dict(params)


# ---------------------------------------------------------------------------
# 2. 실행과 판정
# ---------------------------------------------------------------------------
def _argv(spec: dict, params: dict) -> list[str]:
    """셸 없이 실행할 인자 목록을 만든다(command 없는 pytest 판정이면 pytest 를 실행)."""
    if spec["command"] is None:
        return [sys.executable, "-m", "pytest", "-q", *spec["verdict"]["tests"]]
    command = spec["command"]
    head = ([sys.executable, "-m", command["module"]] if "module" in command
            else [sys.executable, str(PROJECT_ROOT / command["script"])])
    return head + [argument.format(**params) for argument in spec["args_template"]]


def _default_run(spec: dict, params: dict) -> dict:
    """대상을 새 프로세스로 실행한다. 시간 초과도 결과로 돌려준다(예외로 숨기지 않음)."""
    try:
        done = subprocess.run(_argv(spec, params), cwd=str(PROJECT_ROOT), capture_output=True, text=True,
                              timeout=spec["timeout_seconds"])
        return {"returncode": done.returncode, "stdout": done.stdout, "stderr": done.stderr}
    except subprocess.TimeoutExpired as error:
        return {"returncode": -9, "stdout": str(error.stdout or ""),
                "stderr": f"timeout after {spec['timeout_seconds']}s"}


def _evidence(run_result: dict) -> str:
    """수리 작업문에 넣을 증빙: 출력 끝부분(오류는 보통 끝에 있다)."""
    limit = int(_SETTINGS["max_evidence_chars"])
    text = f"[stdout]\n{run_result.get('stdout', '')}\n[stderr]\n{run_result.get('stderr', '')}"
    return text[-limit:]


def evaluate(verdict: dict, run_result: dict, params: dict) -> dict | None:
    """성공이면 None, 실패면 {'category','error','evidence'}."""
    evidence = _evidence(run_result)
    returncode = run_result.get("returncode")
    if verdict["type"] == "exit_code":
        return None if returncode == 0 else {"category": "exit_code", "error": f"exit code {returncode}",
                                             "evidence": evidence}
    if verdict["type"] == "pytest":
        return None if returncode == 0 else {"category": "test_failed", "error": f"pytest exit {returncode}",
                                             "evidence": evidence}
    # json_min: 출력(또는 파일)에서 숫자를 읽어 목표와 비교
    try:
        if verdict["source"] == "stdout":
            lines = [line for line in str(run_result.get("stdout", "")).splitlines() if line.strip()]
            data = json.loads(lines[-1])
        else:
            data = json.loads((PROJECT_ROOT / verdict["file_template"].format(**params)).read_text(encoding="utf-8"))
        value: Any = data
        for part in verdict["field"].split("."):
            value = value[part]
        expected = int(params[verdict["min_param"]])
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{verdict['field']} is not an integer")
    except Exception as error:  # noqa: BLE001 - 판독 불가도 실패 유형으로 보고한다(성공으로 숨기지 않음)
        return {"category": "unreadable", "error": f"{type(error).__name__}: {str(error)[:300]}",
                "evidence": evidence}
    if value >= expected:
        return None
    return {"category": "shortfall", "error": f"{verdict['field']}={value} < 목표 {expected}", "evidence": evidence}


# ---------------------------------------------------------------------------
# 3. 실행 → 판정 → 수리 → 재실행
# ---------------------------------------------------------------------------
def _build_task(spec: dict, failure: dict, rounds: list[dict]) -> str:
    """수리 체인에 넘길 작업문. 대상·실패·범위만 담고 특정 사이트·대상 하드코딩을 금지한다."""
    previous = "\n".join(f"- round {r['round']}: {r['outcome']} {r.get('detail', '')}"[:300] for r in rounds) or "- 없음"
    return (f"[자기 수리 대상] {spec['name']}\n"
            f"[실패 유형] {failure['category']}\n[오류] {failure['error']}\n"
            f"[증빙(출력 끝부분)]\n{failure['evidence']}\n"
            f"[수정 허용 경로] {json.dumps(spec['scope']['allowed_paths'], ensure_ascii=False)}\n"
            f"[회귀 테스트] {json.dumps(spec['scope']['regression_tests'], ensure_ascii=False)}\n"
            f"[이전 라운드]\n{previous}\n"
            "[규칙] 원인을 찾아 허용 경로 안에서 최소 수정한다. 사이트 이름·URL·대상 이름을 코드에 하드코딩하지 않는다. "
            "테스트로 재현 후 고치고 git add 까지만 한다(커밋 금지).")


def _default_partner(task: str, round_no: int, scope: dict) -> dict:
    """기본 수리기: 페르소나 수리 체인을 대상별 scope 로 실행한다."""
    return run_chain(task, staged_fn=staged_change_sets, round_no=round_no, scope=scope)


def _now_stamp() -> str:
    """파일 이름용 KST 시각(초 단위)."""
    return datetime.now(KST).strftime("%Y%m%d_%H%M%S")


def run_with_repair(spec: dict, params: dict, run_fn: Callable = None, partner_fn: Callable = None,
                    backup_fn: Callable = None, restore_fn: Callable = None) -> dict:
    """대상을 실행하고, 실패하면 max_rounds 까지 수리·재실행한다. 증빙 JSON 을 남긴다."""
    spec = validate_target(spec)
    params = validate_params(spec, params)
    run_fn = run_fn or _default_run
    partner_fn = partner_fn or _default_partner
    backup_fn = backup_fn or backup_sources
    restore_fn = restore_fn or restore_sources

    failure = evaluate(spec["verdict"], run_fn(spec, params), params)
    first, rounds = failure, []
    if failure is not None and _SETTINGS.get("enabled", True):
        for round_no in range(1, spec["max_rounds"] + 1):
            task = _build_task(spec, failure, rounds)
            backups = backup_fn(list(spec["scope"]["allowed_paths"]))
            try:
                report = partner_fn(task, round_no, spec["scope"])
            except Exception as error:  # noqa: BLE001 - 수리기 오류는 원복 후 다음 라운드
                restore_fn(backups)
                rounds.append({"round": round_no, "outcome": "ERROR", "detail": f"{type(error).__name__}: {error}"})
                continue
            if not staged_change_sets(report):
                # 아무것도 바꾸지 못했으면 같은 시도를 반복해도 비용만 든다 → 중단
                rounds.append({"round": round_no, "outcome": "NO_CHANGE"})
                break
            if report.get("verdict") != "PASS":
                restore_fn(backups)  # 검증을 통과하지 못한 수정은 되돌린다
                rounds.append({"round": round_no, "outcome": str(report.get("verdict", "미확인"))})
                continue
            failure = evaluate(spec["verdict"], run_fn(spec, params), params)
            rounds.append({"round": round_no, "outcome": "STAGED",
                           "detail": "OK" if failure is None else failure["error"]})
            if failure is None:
                break
    if failure is None:
        verdict_text = "OK"
    else:
        verdict_text = "REPAIR_FAILED" if rounds else "FAILED"
    result = {"target": spec["name"], "result": verdict_text, "first": first, "rounds": rounds,
              "final": failure, "checked_kst": datetime.now(KST).isoformat()}
    evidence_path = PROJECT_ROOT / str(_SETTINGS["report_dir"]) / spec["name"] / f"repair_{_now_stamp()}.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(evidence_path, result)
    return {**result, "evidence": str(evidence_path)}


# ---------------------------------------------------------------------------
# 4. 등록소 (config / repository)
# ---------------------------------------------------------------------------
def _render_block(targets: dict) -> str:
    """대상 목록을 결정적(정렬)인 파이썬 리터럴로 직렬화한다."""
    return f"{BLOCK_VARIABLE} = {pprint.pformat(targets, sort_dicts=True, width=100)}\n"


def _read_block(text: str) -> dict:
    """config 텍스트의 표시 블록에서 대상 목록을 읽는다(리터럴만 허용, 코드 실행 없음)."""
    has_start, has_end = BLOCK_START in text, BLOCK_END in text
    if not has_start and not has_end:
        return {}
    if has_start != has_end:
        raise ValueError("SELF_REPAIR_TARGETS block markers are incomplete")
    body = text.split(BLOCK_START, 1)[1].split(BLOCK_END, 1)[0]
    match = re.search(rf"^{BLOCK_VARIABLE}\s*=\s*", body, flags=re.MULTILINE)
    if match is None:
        return {}
    value = ast.literal_eval(body[match.end():].strip())
    if not isinstance(value, dict):
        raise ValueError("SELF_REPAIR_TARGETS must be a dict literal")
    return value


def _repository_unavailable() -> ValueError:
    """2차 작업(MariaDB 테이블 DDL 승인) 전까지 repository 백엔드는 명확히 거부한다."""
    return ValueError(f"repository backend unavailable: 2차 DDL 승인 필요 "
                      f"(table={_SETTINGS['repository_table']} 미생성, 지금은 config 백엔드만 사용)")


def _replace_block(text: str, targets: dict) -> tuple[str, str]:
    """표시 블록만 새 내용으로 바꾼 전체 텍스트와 동작(replace_block/append_block)을 돌려준다."""
    block = (f"{BLOCK_START}\n# 자동 생성: self_repair_target_register 가 관리한다. 손으로 고치지 말 것.\n"
             f"{_render_block(targets)}{BLOCK_END}\n")
    if BLOCK_START in text:
        head, rest = text.split(BLOCK_START, 1)
        tail = rest.split(BLOCK_END, 1)[1].lstrip("\n")
        return head + block + tail, "replace_block"
    return text + ("" if text.endswith("\n") else "\n") + "\n" + block, "append_block"


def register_target(spec: Any, backend: str = "config", overwrite: bool = False, dry_run: bool = True,
                    config_path: Path | str | None = None) -> dict:
    """대상을 등록한다. config 는 표시 블록만 원자적으로 교체, repository 는 2차 작업 전까지 명확히 거부."""
    if backend not in {"config", "repository"}:
        raise ValueError("backend must be 'config' or 'repository'")
    spec = validate_target(spec)
    if backend == "repository":
        raise _repository_unavailable()
    path = Path(config_path) if config_path is not None else CONFIG_PATH
    original = path.read_text(encoding="utf-8")
    targets = _read_block(original)
    if spec["name"] in targets and not overwrite:
        raise ValueError(f"target already registered: {spec['name']} (overwrite=True 로만 교체)")
    new_text, action = _replace_block(original, {**targets, spec["name"]: spec})
    try:
        compile(new_text, str(path), "exec")       # 깨진 config 는 절대 쓰지 않는다
    except SyntaxError as error:
        raise ValueError(f"generated config does not compile: {error}") from error
    plan = {"dry_run": bool(dry_run), "backend": "config", "path": str(path), "target": spec["name"],
            "action": action, "overwrite": bool(overwrite and spec["name"] in targets), "spec": spec}
    if dry_run:
        return plan
    backup = path.with_name(f"{path.stem}_BACKUP_{_now_stamp()}{path.suffix}")
    backup.write_text(original, encoding="utf-8")                      # 원본 보존(일반 지침 7)
    handle, temp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(new_text)
        os.chmod(temp_name, path.stat().st_mode & 0o777)
        os.replace(temp_name, path)                                    # 원자적 교체
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return {**plan, "applied": True, "backup": str(backup)}


def list_targets() -> dict:
    """등록된 대상 목록. config 파일을 매번 다시 읽는다(서버 재시작 없이 등록 반영)."""
    targets = _read_block(CONFIG_PATH.read_text(encoding="utf-8"))
    return {"targets": targets, "sources": {"config": True, "repository": str(_repository_unavailable())}}


def get_target(name: str) -> dict:
    """등록된 대상 하나를 검증해서 돌려준다. 미등록이면 ValueError(임의 실행 차단)."""
    targets = list_targets()["targets"]
    if name not in targets:
        raise ValueError(f"target not registered: {name}")
    return validate_target(targets[name])


# ---------------------------------------------------------------------------
# 5. MCP 도구
# ---------------------------------------------------------------------------
def _parse_json(text: str, field: str) -> Any:
    try:
        return json.loads(text)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError(f"{field} must be JSON: {error}") from error


async def self_repair_target_register(spec_json: str, backend: str = "config", overwrite: bool = False,
                                      dry_run: bool = True) -> dict:
    """Register a self-repair target (backend=config|repository). dry_run=True by default."""
    return register_target(_parse_json(spec_json, "spec_json"), backend=backend, overwrite=overwrite,
                           dry_run=dry_run, config_path=CONFIG_PATH)


def _job_files(job_id: Any) -> tuple[Path, Path]:
    """job_id 형식을 검사(경로 조작 차단)하고 request/result 파일 경로를 돌려준다."""
    if not isinstance(job_id, str) or JOB_ID_PATTERN.fullmatch(job_id) is None:
        raise ValueError("job_id must be a 32-character hexadecimal identifier")
    folder = PROJECT_ROOT / str(_SETTINGS["job_dir"]) / ("job_" + job_id)
    return folder / "request.json", folder / "result.json"


async def _job_status(job_id: str) -> dict:
    """result.json 이 있으면 그대로, 없으면 systemd 유닛 상태로 running/failed 를 판정한다."""
    request_path, result_path = _job_files(job_id)
    if not request_path.is_file():
        raise FileNotFoundError(f"self_repair job not found: {job_id}")
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
                "error": "self_repair job stopped without a final result",
                "unit_result": properties.get("Result", "unknown")}
    return state


async def self_repair_run(target: str, params_json: str = "{}", dry_run: bool = True,
                          job_id: str | None = None) -> dict:
    """Run a registered target with self-repair as a background job. dry_run=True by default; job_id reads status."""
    if job_id is not None:
        return await _job_status(job_id)
    spec = get_target(target)
    params = validate_params(spec, _parse_json(params_json, "params_json"))
    timeout = int(_SETTINGS["job_timeout_seconds"])
    new_id = uuid4().hex
    unit, command = _systemd_command(
        ["-m", "harness.mcp.agents.self_repair_engine", "--job-worker", new_id], timeout, "self-repair")
    command = [argument for argument in command if argument not in {"--wait", "--pipe"}]  # 독립 유닛
    plan = {"dry_run": bool(dry_run), "executed": False, "job_id": new_id, "unit": unit, "command": command,
            "timeout_seconds": timeout, "target": spec["name"], "params": params, "argv": _argv(spec, params)}
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
    """독립 systemd 유닛 안에서 job 하나를 실행하고 결과를 남긴다(실패도 결과 파일로)."""
    request_path, result_path = _job_files(job_id)
    plan = json.loads(request_path.read_text(encoding="utf-8"))
    started = monotonic()
    report, error = None, ""
    try:
        report = run_with_repair(get_target(plan["target"]), plan["params"])
    except Exception as exc:  # noqa: BLE001 - 조회에서 확인할 수 있게 결과 파일로 남긴다
        error = f"{type(exc).__name__}: {exc}"
    text = _mask_secrets(json.dumps(report, ensure_ascii=False, default=str)) if report is not None else ""
    _write_json(result_path, {**plan, "dry_run": False, "executed": True,
                              "state": "completed" if not error else "failed",
                              "success": bool(report and report["result"] == "OK"),
                              "result": (report or {}).get("result", "FAILED"),
                              "error": _mask_secrets(error) or None, "evidence": (report or {}).get("evidence"),
                              "elapsed_seconds": round(monotonic() - started, 3),
                              "output": text[:OUTPUT_LIMIT], "output_truncated": len(text) > OUTPUT_LIMIT})


if __name__ == "__main__" and len(sys.argv) == 3 and sys.argv[1] == "--job-worker":
    _run_job(sys.argv[2])
