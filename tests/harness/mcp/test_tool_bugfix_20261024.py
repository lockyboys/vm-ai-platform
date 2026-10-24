"""2026-10-24 MCP 도구 버그 재현/회귀 테스트.

버그 1: mongodb_rename_collection이 CommonDatabase.rename_collection을 호출하지만 실제 클래스에 메서드가 없음
        (테스트 가짜 객체에만 있어 기존 테스트는 통과, 실제 실행은 AttributeError).
버그 2: mariadb_ddl_execute의 _parse_target이 따옴표 안의 ';'·'--'·'#'까지 문장 구분/주석으로 보고 거부해
        표준 테이블 COMMENT('[MONGODB_PAYLOAD] Collection: x; MongoDB Role: ...')를 넣을 수 없음.
주의: 실제 DB 연결 없이 가짜 컬렉션으로만 검증한다.
"""
from __future__ import annotations

import pytest

from common.database import CommonDatabase
from harness.mcp.tools.model_history_audit_ddl_tool import _parse_target


class FakeCollection:
    """pymongo Collection.rename 호출만 기록하는 가짜 컬렉션."""

    def __init__(self):
        self.calls = []

    def rename(self, new_name, **kwargs):
        self.calls.append((new_name, kwargs))


def _fake_database(fake):
    # __init__의 실제 연결을 피하고 get_collection만 가짜로 바꾼다.
    database = CommonDatabase.__new__(CommonDatabase)
    database.get_collection = lambda name: fake
    return database


def test_common_database_has_rename_collection():
    # 버그 1 재현: 실제 클래스에 메서드가 있어야 한다.
    assert callable(getattr(CommonDatabase, "rename_collection", None))


def test_rename_collection_calls_pymongo_without_drop_target():
    fake = FakeCollection()
    assert _fake_database(fake).rename_collection("old_payload", "new_payload") == "new_payload"
    # 기존 대상 컬렉션을 덮어쓰지 않도록 dropTarget=False를 명시해야 한다.
    assert fake.calls == [("new_payload", {"dropTarget": False})]


@pytest.mark.parametrize("source,target", [("a", "a"), ("", "b"), ("a", ""), ("a", "bad-name"), ("a", "x.y")])
def test_rename_collection_rejects_invalid_names(source, target):
    with pytest.raises(ValueError):
        _fake_database(FakeCollection()).rename_collection(source, target)


# ---------------------------------------------------------------- 버그 2
STANDARD_COMMENT = (
    "ALTER TABLE harness_source_audit COMMENT = '[MONGODB_PAYLOAD] Collection: x_payload; "
    "MongoDB Role: COMMON; MariaDB Role: INDEX_ONLY; 설명 -- 와 # 도 글자일 뿐'"
)


@pytest.mark.parametrize("statement", [
    STANDARD_COMMENT,
    STANDARD_COMMENT + ";",                                         # 끝의 ; 하나는 허용(기존 동작 유지)
    "ALTER TABLE t COMMENT = 'it''s; ok'",                          # SQL 표준 '' 이스케이프
    "ALTER TABLE t COMMENT = 'back\\'slash; ok'",                   # 백슬래시 이스케이프
    "ALTER TABLE t MODIFY COLUMN `c` int COMMENT \"a; b\"",          # 큰따옴표 문자열
])
def test_semicolon_and_comment_tokens_inside_quotes_allowed(statement):
    assert _parse_target(statement, "te_common")[0] == "ALTER"


@pytest.mark.parametrize("statement", [
    "ALTER TABLE t COMMENT = 'a'; DROP TABLE x",                    # 따옴표 밖 두 번째 문장
    "ALTER TABLE t COMMENT = 'a' -- 주석",                          # 따옴표 밖 주석
    "ALTER TABLE t COMMENT = 'a' /* 주석 */",
    "ALTER TABLE t COMMENT = 'a' # 주석",
    "ALTER TABLE t COMMENT = 'unterminated; DROP TABLE x",          # 닫히지 않은 따옴표
    "ALTER TABLE t COMMENT = 'a';;",
    "",
])
def test_statements_outside_quotes_still_rejected(statement):
    with pytest.raises(ValueError):
        _parse_target(statement, "te_common")


def test_existing_plain_ddl_unchanged():
    # 기존에 통과하던 문장은 그대로 통과해야 한다(회귀 방지).
    assert _parse_target("RENAME TABLE a TO b", "te_common") == ("RENAME", "a")
    assert _parse_target("ALTER TABLE te_common.t ADD COLUMN c int;", "te_common") == ("ALTER", "t")
