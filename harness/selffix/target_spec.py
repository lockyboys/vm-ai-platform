"""[입력·검증] 자기 수리 대상 스펙·파라미터 검증 (2026-11-12 분리, 원본: self_repair_engine.py §1).

보안 원칙(SECURITY, 원본 그대로)
    - 등록된 대상만 실행하고, 인자는 셸 없이 리스트로 넘긴다 → 여기서 스펙 모양을 엄격히 검사한다.
    - 파라미터는 스펙에 선언된 이름만, 값은 str(한 줄, 200자 이내) 또는 int 만 받는다.
판정(verdict) 3종: exit_code / json_min / pytest (자세한 뜻은 runner.py)
설정: 루트 config.py 의 SELF_REPAIR (일반 지침 4).
"""
from __future__ import annotations

import re
import string
from pathlib import PurePosixPath
from typing import Any

import config as project_config  # 루트 공통 설정(일반 지침 4)
# 수리 범위(scope) 검증은 페르소나 수리 체인의 규칙을 그대로 쓴다(커밋 6a1c4ce 에서 일반화)
from harness.mcp.agents.persona_repair_chain import resolve_scope
from harness.selffix.job_runner import PROJECT_ROOT

_SETTINGS = project_config.SELF_REPAIR          # 엔진 설정(기본 라운드 수 등)

NAME_PATTERN = re.compile(r"^[a-z0-9_]{1,64}$")                       # 대상 이름
PARAM_PATTERN = re.compile(r"^[a-z_][a-z0-9_]{0,63}$")                 # 파라미터 이름
MODULE_PATTERN = re.compile(r"^[A-Za-z_]\w*(\.[A-Za-z_]\w*)*$")        # python -m 모듈 이름
FIELD_PATTERN = re.compile(r"^[A-Za-z_]\w*(\.[A-Za-z_]\w*)*$")         # JSON 필드 경로(a.b.c)
VERDICT_TYPES = {"exit_code", "json_min", "pytest"}
MAX_PARAM_TEXT = 200                                                   # 문자열 파라미터 길이 상한
MAX_ROUNDS = 5                                                         # 수리 라운드 상한(비용 보호)
MAX_TIMEOUT_SECONDS = 36000                                            # 대상 1회 실행 상한


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
