"""관리자 scope(mcp:admin) 분리 회귀 테스트.

검증 의도:
- scope_guard: off는 기존과 완전히 같고(기록도 없음), audit은 막지 않고 기록만, enforce는
  admin scope가 없을 때만 막는지 확인한다. 도구 인자는 감사 로그에 남지 않아야 한다.
- 서버 등록부: ADMIN_TOOL_NAMES 7개가 실제로 등록돼 있고, 등록 전에 가드로 감싸는지 확인한다.
- OAuth 설정: 필수 scope는 그대로 두고 관리자 scope만 "발급 가능"하게 추가됐는지 확인한다
  (필수 scope에 admin을 넣으면 admin 없는 토큰이 전부 거부되는 사고를 막기 위함).
"""

import asyncio
import inspect
import json
import re
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.mcp import scope_guard  # noqa: E402
from harness.mcp.oauth_provider import HarnessOAuthSettings  # noqa: E402

SERVER_SOURCE = PROJECT_ROOT / "harness" / "mcp" / "sps_harness_server.py"


@pytest.fixture
def audit_log(monkeypatch, tmp_path):
    """감사 로그를 임시 경로로 돌리고 그 경로를 돌려준다."""
    path = tmp_path / "scope_audit" / "admin_scope_calls.jsonl"
    monkeypatch.setattr(scope_guard, "AUDIT_LOG_PATH", path)
    return path


def _read_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _guarded_tool():
    calls = []

    def git_commit(message: str, secret_sql: str = "DROP TABLE x") -> str:
        """테스트용 가짜 도구."""
        calls.append(message)
        return "committed"

    return scope_guard.admin_scope_required(git_commit), calls


def test_off_mode_behaves_exactly_like_before(monkeypatch, audit_log):
    monkeypatch.delenv(scope_guard.MODE_ENV, raising=False)
    monkeypatch.setattr(scope_guard, "_current_scopes", lambda: None)
    tool, calls = _guarded_tool()

    assert tool("m") == "committed"
    assert calls == ["m"]
    assert not audit_log.exists()  # off는 기록조차 하지 않는다.


def test_audit_mode_never_blocks_and_records_would_block(monkeypatch, audit_log):
    monkeypatch.setenv(scope_guard.MODE_ENV, "audit")
    monkeypatch.setattr(scope_guard, "_current_scopes", lambda: {"mcp:tools"})
    tool, calls = _guarded_tool()

    assert tool("m", secret_sql="SELECT password FROM users") == "committed"
    assert calls == ["m"]
    records = _read_records(audit_log)
    assert len(records) == 1
    assert records[0]["tool"] == "git_commit"
    assert records[0]["decision"] == "would_block"
    assert records[0]["scope_known"] is True
    assert "password" not in audit_log.read_text(encoding="utf-8")  # 인자는 절대 기록하지 않는다.


def test_enforce_blocks_without_admin_scope(monkeypatch, audit_log):
    monkeypatch.setenv(scope_guard.MODE_ENV, "enforce")
    monkeypatch.setattr(scope_guard, "_current_scopes", lambda: {"mcp:tools"})
    tool, calls = _guarded_tool()

    with pytest.raises(PermissionError):
        tool("m")
    assert calls == []  # 원래 도구는 실행되지 않아야 한다.
    assert _read_records(audit_log)[0]["decision"] == "blocked"


def test_enforce_blocks_when_scope_unreadable(monkeypatch, audit_log):
    monkeypatch.setenv(scope_guard.MODE_ENV, "enforce")
    monkeypatch.setattr(scope_guard, "_current_scopes", lambda: None)
    tool, calls = _guarded_tool()

    with pytest.raises(PermissionError):
        tool("m")
    record = _read_records(audit_log)[0]
    assert record["decision"] == "blocked"
    assert record["scope_known"] is False


def test_enforce_allows_with_admin_scope(monkeypatch, audit_log):
    monkeypatch.setenv(scope_guard.MODE_ENV, "enforce")
    monkeypatch.setattr(scope_guard, "_current_scopes", lambda: {"mcp:tools", "mcp:admin"})
    tool, calls = _guarded_tool()

    assert tool("m") == "committed"
    assert _read_records(audit_log)[0]["decision"] == "allowed"


def test_unknown_mode_falls_back_to_off(monkeypatch, audit_log):
    monkeypatch.setenv(scope_guard.MODE_ENV, "enforec")  # 오타
    monkeypatch.setattr(scope_guard, "_current_scopes", lambda: None)
    tool, calls = _guarded_tool()

    assert tool("m") == "committed"
    assert not audit_log.exists()


def test_async_tool_and_signature_are_preserved(monkeypatch, audit_log):
    monkeypatch.setenv(scope_guard.MODE_ENV, "enforce")
    monkeypatch.setattr(scope_guard, "_current_scopes", lambda: {"mcp:admin"})

    async def verified_sql_execute(sql_id: str, dry_run: bool = True) -> str:
        """테스트용 비동기 도구."""
        return f"{sql_id}:{dry_run}"

    wrapped = scope_guard.admin_scope_required(verified_sql_execute)

    assert inspect.iscoroutinefunction(wrapped)
    assert list(inspect.signature(wrapped).parameters) == ["sql_id", "dry_run"]
    assert wrapped.__name__ == "verified_sql_execute"
    assert wrapped.__doc__ == "테스트용 비동기 도구."
    assert asyncio.run(wrapped("q1", dry_run=False)) == "q1:False"


def test_every_admin_tool_is_registered_and_wrapped_before_registration():
    source = SERVER_SOURCE.read_text(encoding="utf-8")
    guard_at = source.index("globals()[_admin_tool_name] = admin_scope_required(")
    first_registration_at = source.index("mcp.tool()(source_search)")
    assert guard_at < first_registration_at  # 등록 전에 감싸야 감싼 함수가 등록된다.

    for name in scope_guard.ADMIN_TOOL_NAMES:
        assert re.search(rf"^mcp\.tool\(\)\({re.escape(name)}\)$", source, re.MULTILINE), name


def _settings(**overrides) -> HarnessOAuthSettings:
    values = dict(
        issuer_url="https://example.test",
        resource_url="https://example.test/mcp",
        google_client_id="id",
        google_client_secret="secret",
        google_redirect_uri="https://example.test/oauth/google/callback",
        allowed_emails=frozenset({"owner@example.test"}),
        jwt_secret_key="x" * 32,
        access_token_expire_seconds=3600,
        refresh_token_expire_seconds=3600,
        authorization_code_expire_seconds=300,
        login_state_expire_seconds=600,
        scopes=("mcp:tools",),
        client_registry_path="/tmp/registry.json",
    )
    values.update(overrides)
    return HarnessOAuthSettings(**values)


def test_admin_scope_is_grantable_but_not_required():
    settings = _settings()
    assert settings.admin_scope == scope_guard.ADMIN_SCOPE
    assert settings.scopes == ("mcp:tools",)  # 필수 scope는 그대로다.
    assert settings.grantable_scopes == ("mcp:tools", "mcp:admin")
    assert settings.default_scopes == ("mcp:tools", "mcp:admin")


def test_default_grant_of_admin_can_be_turned_off():
    settings = _settings(default_grants_admin=False)
    assert settings.default_scopes == ("mcp:tools",)
    assert settings.grantable_scopes == ("mcp:tools", "mcp:admin")


def test_grantable_scopes_has_no_duplicates_when_admin_already_listed():
    settings = _settings(scopes=("mcp:tools", "mcp:admin"))
    assert settings.grantable_scopes == ("mcp:tools", "mcp:admin")
