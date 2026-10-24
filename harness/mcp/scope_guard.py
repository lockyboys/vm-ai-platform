"""파괴적 MCP 도구를 `mcp:admin` scope 뒤로 숨기는 가드 모듈.

목적:
- 지금은 토큰 하나(`mcp:tools`)로 45개 도구가 전부 호출된다. 이 모듈은 DB 실행·삭제,
  git 변경 같은 파괴적 도구만 별도 scope(`mcp:admin`)를 요구하도록 만들 수 있게 한다.

가장 중요한 안전 설계 (서비스 중단 방지):
- 동작 모드는 환경변수 `SPS_MCP_ADMIN_SCOPE_MODE`로 정한다. 기본값은 `off`다.
  * off     : 아무 검사도 하지 않는다(이 모듈을 적용해도 기존 동작과 100% 동일).
  * audit   : 차단하지 않고, admin scope가 없으면 "차단될 호출"이라고 로그만 남긴다.
  * enforce : admin scope가 없으면 PermissionError로 호출을 거부한다.
- 모르는 값(오타 등)은 서비스가 멈추지 않도록 `off`로 취급하고 경고 로그를 남긴다.
  (보안보다 가용성을 우선한 선택이다. enforce 전환 전 audit 로그로 반드시 확인할 것.)
- 모드는 호출 시점마다 읽으므로 코드를 고치지 않고 환경변수만 바꿔 껐다 켤 수 있다.
  (환경변수 반영에는 서비스 재시작이 필요하다.)

주의:
- 토큰 scope는 FastMCP 인증 계층이 검증한 뒤 contextvar로 노출하는 값
  (`mcp.server.auth.middleware.auth_context.get_access_token`)만 신뢰한다.
  이 값을 읽지 못하면(SDK 버전 차이 등) enforce 모드에서는 안전하게 거부한다.
"""

from __future__ import annotations

import functools
import inspect
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar

LOGGER = logging.getLogger(__name__)

# 파괴적 도구에 요구할 scope 이름. 기본 scope(`mcp:tools`)와 반드시 달라야 한다.
ADMIN_SCOPE = "mcp:admin"

# 동작 모드를 정하는 환경변수 이름과 허용 값.
MODE_ENV = "SPS_MCP_ADMIN_SCOPE_MODE"
VALID_MODES = ("off", "audit", "enforce")

# 가드를 적용할 도구 이름 목록(서버 등록 코드와 테스트가 같은 목록을 쓰도록 한 곳에 둔다).
# 1단계: 가장 파괴적인 도구만 포함한다. 범위를 넓힐 때는 이 집합만 늘린다.
ADMIN_TOOL_NAMES = frozenset(
    {
        "verified_sql_execute",
        "mariadb_ddl_execute",
        "mongodb_delete_document",
        "mongodb_backup_delete",
        "mongodb_delete_backup",  # mongodb_backup_delete와 같은 기능의 별칭이라 같이 묶는다.
        "git_commit",
        "git_stage_delete",
    }
)

F = TypeVar("F", bound=Callable[..., Any])

# 잘못된 모드 경고가 호출마다 쏟아지지 않도록 한 번만 남긴다.
_warned_invalid_mode = False


def get_guard_mode() -> str:
    """현재 가드 모드(off/audit/enforce)를 돌려준다. 모르는 값은 off로 취급한다."""
    global _warned_invalid_mode
    raw = os.getenv(MODE_ENV, "off").strip().lower()
    if raw in VALID_MODES:
        return raw
    if not _warned_invalid_mode:
        LOGGER.warning("%s 값 %r 은(는) 알 수 없어 off로 처리합니다.", MODE_ENV, raw)
        _warned_invalid_mode = True
    return "off"


# 대시보드에서 볼 수 있도록 가드 판정을 한 줄짜리 JSON으로 남긴다(off 모드는 기록하지 않는다).
# 도구 인자(SQL, 문서 내용 등)는 비밀이 섞일 수 있어 절대 기록하지 않는다.
AUDIT_LOG_PATH = (
    Path(__file__).resolve().parents[2] / "harness" / "memory" / "scope_audit" / "admin_scope_calls.jsonl"
)
# 파일이 이 크기를 넘으면 .1로 한 번 돌려 두고 새로 쓴다(디스크가 무한히 차지 않게).
AUDIT_LOG_MAX_BYTES = 5 * 1024 * 1024
_KST = timezone(timedelta(hours=9))


def _record_audit(tool_name: str, mode: str, decision: str, *, scope_known: bool) -> None:
    """가드 판정 1건을 감사 로그 파일에 추가한다. 실패해도 도구 호출은 막지 않는다.

    입력: tool_name(도구 이름), mode(audit/enforce), decision(allowed/would_block/blocked),
    scope_known(토큰 scope를 읽을 수 있었는지)
    출력: 없음. 기록 실패는 경고 로그만 남긴다(가용성 우선).
    """
    record = {
        "at": datetime.now(_KST).isoformat(timespec="seconds"),
        "tool": tool_name,
        "mode": mode,
        "decision": decision,
        "scope_known": scope_known,
    }
    try:
        AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        if AUDIT_LOG_PATH.exists() and AUDIT_LOG_PATH.stat().st_size > AUDIT_LOG_MAX_BYTES:
            AUDIT_LOG_PATH.replace(AUDIT_LOG_PATH.with_name(AUDIT_LOG_PATH.name + ".1"))
        with AUDIT_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        LOGGER.warning("관리자 scope 감사 로그를 쓰지 못했습니다: %s", AUDIT_LOG_PATH)


def _current_scopes() -> set[str] | None:
    """검증된 현재 요청 토큰의 scope 집합을 돌려준다. 읽을 수 없으면 None."""
    try:
        # SDK 버전에 따라 없을 수 있어 호출 시점에 가져온다(임포트 실패로 서비스가 죽지 않게).
        from mcp.server.auth.middleware.auth_context import get_access_token

        token = get_access_token()
    except Exception:  # noqa: BLE001 - 어떤 이유로든 못 읽으면 "알 수 없음"으로 처리한다.
        return None
    if token is None:
        return None
    return set(getattr(token, "scopes", None) or [])


def _check_admin_scope(tool_name: str) -> None:
    """모드에 따라 admin scope를 검사한다. 거부해야 할 때만 PermissionError를 던진다."""
    mode = get_guard_mode()
    if mode == "off":
        return

    scopes = _current_scopes()
    if scopes is not None and ADMIN_SCOPE in scopes:
        if mode == "audit":
            LOGGER.info("[admin-scope-audit] tool=%s admin scope 확인됨", tool_name)
        _record_audit(tool_name, mode, "allowed", scope_known=True)
        return

    # 여기까지 오면 admin scope가 없거나, scope 자체를 읽지 못한 경우다.
    if mode == "audit":
        LOGGER.warning(
            "[admin-scope-audit] tool=%s 는 enforce 모드였다면 차단됐을 호출입니다 (scope 확인 가능=%s)",
            tool_name,
            scopes is not None,
        )
        _record_audit(tool_name, mode, "would_block", scope_known=scopes is not None)
        return

    LOGGER.warning("[admin-scope-enforce] tool=%s 호출 거부 (scope 확인 가능=%s)", tool_name, scopes is not None)
    _record_audit(tool_name, mode, "blocked", scope_known=scopes is not None)
    raise PermissionError(f"Tool '{tool_name}' requires the '{ADMIN_SCOPE}' scope.")


def admin_scope_required(tool_function: F) -> F:
    """도구 함수를 감싸 호출 직전에 admin scope를 검사한다(동기·비동기 모두 지원).

    FastMCP는 함수 시그니처로 입력 스키마를 만들기 때문에, 감싼 뒤에도 원본과 같은
    시그니처·docstring이 보이도록 한다. 문자열 타입힌트(`from __future__ import annotations`)는
    감싼 함수의 전역 이름공간에서는 풀리지 않으므로, 원본에서 미리 해석한 시그니처를 붙여 둔다.
    """
    tool_name = getattr(tool_function, "__name__", "unknown")

    if inspect.iscoroutinefunction(tool_function):

        @functools.wraps(tool_function)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            _check_admin_scope(tool_name)
            return await tool_function(*args, **kwargs)

        wrapper: Callable[..., Any] = async_wrapper
    else:

        @functools.wraps(tool_function)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            _check_admin_scope(tool_name)
            return tool_function(*args, **kwargs)

        wrapper = sync_wrapper

    try:
        # 타입힌트를 원본 모듈 기준으로 미리 풀어 둔다(실패해도 기본 동작은 유지).
        wrapper.__signature__ = inspect.signature(tool_function, eval_str=True)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        LOGGER.warning("도구 %s 의 시그니처를 미리 해석하지 못했습니다. 기본 시그니처를 사용합니다.", tool_name)

    return wrapper  # type: ignore[return-value]
