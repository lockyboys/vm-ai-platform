"""SPS Harness MCP 소스 도구 호출을 harness_source_audit에 자동 기록하는 래퍼 모듈.

목적
- source_read / source_write / source_patch / source_delete / source_rename /
  run_pytest_verification 을 호출할 때마다 te_common.harness_source_audit에
  파일 단위 1건씩 감사 기록을 남긴다(사용자 지시 2026-10-24: 소스 작업·소스 읽기 모두 기록).

설계 원칙
- Repository First: INSERT SQL을 소스에 쓰지 않는다. cm_verified_sql_query에 등록된
  Query ID(config.SOURCE_AUDIT["verified_query_id"])를 verified_sql_execute로만 실행한다.
- 행 id: 테이블 COMMENT에 따라 AUTO_INCREMENT를 쓰지 않고, SOURCE_AUDIT Object
  (sp_object, 업무 SP / 도메인 SR)로 identifier_generate가 발급한 Level 4 ID를 쓴다.
  예: SP_SR_SOURCE_AUDIT_20261024_174851_00001 (KST, 시간대 Rule 기준)
- user_id: AI 에이전트 세션 ID({AI 모델 ID}_{YYYYMMDD}_{HHMMSS} KST). 사람 ID가 아니다.
  created_by / updated_by: 요청자. 두 값 모두 config.SOURCE_AUDIT에서 읽는다.
- 가용성 우선: 기록 단계(ID 발급, INSERT, 결과 해석)의 어떤 오류도 원래 도구 결과를
  막지 않는다. 경고 로그만 남긴다. (2026-10-24 버그: pytest 결과 항목이 dict가 아니라
  객체여서 통과율 계산이 예외를 던져 도구 자체가 실패했다 → 기록 단계를 통째로 보호한다.)
- 실제 변경만 기록: source_patch / source_delete / source_rename 의 dry_run=True 호출은
  파일이 바뀌지 않으므로 기록하지 않는다. 읽기(source_read)와 쓰기(source_write)는 항상 기록한다.
- 도구가 예외로 실패하면 기록하지 않고 예외를 그대로 올린다(실패를 성공처럼 남기지 않음).
- 기록 내용에는 파일 경로·작업 유형·통과율만 넣고, 파일 내용이나 patch 본문은 넣지 않는다.

harness_source_audit 컬럼 매핑(테이블 COMMENT 기준)
- id            : identifier_generate(SOURCE_AUDIT) 발급 Level 4 ID
- user_id       : AI 에이전트 세션 ID
- file_name     : 프로젝트 루트 기준 상대경로
- task_type     : SOURCE_READ / SOURCE_WRITE / SOURCE_PATCH / SOURCE_DELETE / SOURCE_RENAME / TEST_VERIFY
- learning_type : 도구 이름(예: source_read)
- accuracy      : TEST_VERIFY만 통과 테스트 수 / 전체 테스트 수, 나머지는 NULL
- created_by / updated_by : 요청자
"""

from __future__ import annotations

import functools
import inspect
import json
import logging
from typing import Any, Callable, Iterable, TypeVar

import config

LOGGER = logging.getLogger(__name__)

# 감사 대상 도구 이름 → harness_source_audit.task_type.
# 서버 등록 코드(sps_harness_server.py)와 테스트가 같은 목록을 쓰도록 한 곳에 둔다.
SOURCE_AUDIT_TASK_TYPES: dict[str, str] = {
    "source_read": "SOURCE_READ",
    "source_write": "SOURCE_WRITE",
    "source_patch": "SOURCE_PATCH",
    "source_delete": "SOURCE_DELETE",
    "source_rename": "SOURCE_RENAME",
    "run_pytest_verification": "TEST_VERIFY",
}

# dry_run 인자를 가지며, dry_run=True면 파일이 바뀌지 않는 도구들.
_DRY_RUN_TOOLS = frozenset({"source_patch", "source_delete", "source_rename"})

F = TypeVar("F", bound=Callable[..., Any])


def _execute_verified_sql(query_id: str, parameters_json: str = "[]", apply: bool = False) -> dict:
    """등록된 Verified SQL을 실행한다(테스트에서 이 함수만 바꿔 끼운다).

    순환 import를 피하려고 호출 시점에 가져온다. 서버에서 admin scope 가드가 감싼
    전역 이름이 아니라 도구 모듈의 원본 함수를 쓴다(내부 감사 기록은 사용자 호출이 아님).
    """
    from harness.mcp.tools.verified_sql_tools import verified_sql_execute

    return verified_sql_execute(query_id=query_id, parameters_json=parameters_json, apply=apply)


def _identifier_generate() -> Callable[..., dict]:
    """identifier_generate 원본 함수를 돌려준다(호출 시점 import, 테스트에서 교체)."""
    from harness.mcp.tools.identifier_tools import identifier_generate

    return identifier_generate


def _issue_audit_id() -> str:
    """SOURCE_AUDIT Object로 Level 4 행 id 1건을 실제 발급한다(apply=True).

    Raises:
        RuntimeError: 발급 결과에 identifier가 없을 때(빈 id로 INSERT하지 않기 위해).
    """
    settings = config.SOURCE_AUDIT
    result = _identifier_generate()(
        settings["identifier_object_code"],
        actor_id=settings["requester_id"],
        program_id=settings["program_id"],
        client_ip=settings["client_ip"],
        apply=True,
    )
    identifier = str((result or {}).get("identifier") or "").strip()
    if not identifier:
        raise RuntimeError(f"harness_source_audit id was not issued: {result!r}")
    return identifier


def _bound_arguments(tool_function: Callable[..., Any], args: tuple, kwargs: dict) -> dict[str, Any]:
    """호출 인자를 이름 기준 dict로 바꾼다(기본값 포함). 해석 실패 시 kwargs만 쓴다."""
    try:
        bound = inspect.signature(tool_function).bind(*args, **kwargs)
        bound.apply_defaults()
        return dict(bound.arguments)
    except (TypeError, ValueError):
        return dict(kwargs)


def _target_files(tool_name: str, arguments: dict[str, Any], result: Any) -> list[str]:
    """도구별로 기록할 파일 경로 목록을 만든다."""
    if tool_name == "source_patch":
        # patch 본문은 기록하지 않고, 도구가 돌려준 실제 변경 경로만 쓴다.
        paths = result.get("paths") if isinstance(result, dict) else None
        return [str(path) for path in (paths or [])]
    if tool_name == "source_rename":
        # 이동 전·후 경로를 한 행에 남겨 추적할 수 있게 한다.
        return [f"{arguments.get('source_path', '')} -> {arguments.get('destination_path', '')}"]
    if tool_name == "run_pytest_verification":
        test_paths: Iterable[str] = arguments.get("test_paths") or []
        return [str(path) for path in test_paths]
    path = arguments.get("path")
    return [str(path)] if path else []


def _item_status(item: Any) -> str:
    """pytest 결과 항목의 status를 dict·객체(PytestCaseResult) 모두에서 읽는다."""
    if isinstance(item, dict):
        return str(item.get("status", ""))
    return str(getattr(item, "status", ""))


def _pass_ratio(result: Any) -> float | None:
    """pytest 결과의 통과율(PASSED 수 / 전체 수). 결과가 없으면 None."""
    if isinstance(result, dict):
        items = result.get("results") or []
    else:
        items = getattr(result, "results", None) or []
    if not items:
        return None
    passed = sum(1 for item in items if _item_status(item).upper() == "PASSED")
    return passed / len(items)


def _log_client_info(tool_name: str) -> None:
    """호출한 MCP 클라이언트의 clientInfo(name, version)를 INFO 로그로 남긴다(2026-10-24 추가).

    목적: AI별 user_id 규칙을 정하기 전에 각 앱(Claude/ChatGPT/Codex/Gemini)이 실제로 보내는
          clientInfo 값을 서버 로그(journalctl -u sps-harness)에서 수집하기 위함.
    주의: 요청 컨텍스트가 없거나(내부 호출·테스트) clientInfo가 없으면 unknown으로 남기고,
          어떤 경우에도 예외를 올리지 않는다(도구 결과를 막지 않음). 로그 외 동작 변경 없음.
    """
    name = version = "unknown"
    try:
        from mcp.server.lowlevel.server import request_ctx  # mcp 1.28.1에서 확인한 경로

        context = request_ctx.get()  # 컨텍스트가 없으면 LookupError
        params = getattr(context.session, "client_params", None)
        info = getattr(params, "clientInfo", None)
        if info is not None:
            name = str(getattr(info, "name", None) or "unknown")
            version = str(getattr(info, "version", None) or "unknown")
    except Exception:  # noqa: BLE001 - 진단 로그 실패가 도구를 멈추면 안 된다.
        pass
    LOGGER.info(
        "source_audit client_info: client_name=%s client_version=%s tool=%s",
        name,
        version,
        tool_name,
    )


def _record(tool_name: str, file_names: list[str], accuracy: float | None) -> None:
    """파일 경로마다 id를 발급해 harness_source_audit 1건을 등록 Verified SQL로 넣는다. 실패는 로그만."""
    settings = config.SOURCE_AUDIT
    for file_name in file_names:
        try:
            audit_id = _issue_audit_id()
            parameters = [
                audit_id,                            # id (Level 4)
                settings["agent_session_id"],        # user_id (AI 에이전트 세션 ID)
                file_name,                           # file_name
                SOURCE_AUDIT_TASK_TYPES[tool_name],  # task_type
                tool_name,                           # learning_type
                accuracy,                            # accuracy
                settings["requester_id"],            # created_by (요청자)
                settings["requester_id"],            # updated_by (요청자)
                settings["program_id"],              # program_id
                settings["client_ip"],               # client_ip
                audit_id,                            # NOT EXISTS 중복 검사용 id
            ]
            _execute_verified_sql(
                settings["verified_query_id"],
                parameters_json=json.dumps(parameters, ensure_ascii=False),
                apply=True,
            )
        except Exception:  # noqa: BLE001 - 감사 기록 실패가 도구를 멈추면 안 된다.
            LOGGER.warning("harness_source_audit 기록 실패: tool=%s file=%s", tool_name, file_name, exc_info=True)


def source_audit_recorded(tool_function: F) -> F:
    """소스 도구를 감싸 정상 종료 후 harness_source_audit에 기록한다(동기 함수 전용).

    FastMCP는 함수 시그니처로 입력 스키마를 만들므로 원본 시그니처·docstring을 유지한다.
    감사 대상 목록에 없는 도구를 감싸면 기동 시 ValueError로 바로 알린다.
    """
    tool_name = getattr(tool_function, "__name__", "unknown")
    if tool_name not in SOURCE_AUDIT_TASK_TYPES:
        raise ValueError(f"'{tool_name}' is not a source audit tool.")

    @functools.wraps(tool_function)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = tool_function(*args, **kwargs)  # 실패하면 예외가 그대로 올라가고 기록하지 않는다.
        try:
            _log_client_info(tool_name)  # 클라이언트 식별값 수집용 로그(기록 여부와 무관하게 남김)
            arguments = _bound_arguments(tool_function, args, kwargs)
            if tool_name in _DRY_RUN_TOOLS and arguments.get("dry_run", True):
                return result
            accuracy = _pass_ratio(result) if tool_name == "run_pytest_verification" else None
            _record(tool_name, _target_files(tool_name, arguments, result), accuracy)
        except Exception:  # noqa: BLE001 - 결과 해석 오류도 도구 결과를 막지 않는다.
            LOGGER.warning("harness_source_audit 기록 준비 실패: tool=%s", tool_name, exc_info=True)
        return result

    try:
        # 문자열 타입힌트를 원본 모듈 기준으로 미리 풀어 둔다(scope_guard와 같은 처리).
        wrapper.__signature__ = inspect.signature(tool_function, eval_str=True)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        LOGGER.warning("도구 %s 의 시그니처를 미리 해석하지 못했습니다. 기본 시그니처를 사용합니다.", tool_name)
    return wrapper  # type: ignore[return-value]
