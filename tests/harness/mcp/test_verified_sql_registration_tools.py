"""Tests for the Verified SQL registration-only Harness tool."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from harness.mcp.tools import verified_sql_tools


class _FakeDatabase:
    instances: list["_FakeDatabase"] = []

    def __init__(self, database_role: str) -> None:
        self.database_role = database_role
        self.executed: list[tuple[str, tuple[object, ...]]] = []
        self.closed = False
        self.committed = False
        self.rolled_back = False
        _FakeDatabase.instances.append(self)

    def fetch_one(self, sql: str, params: tuple[object, ...]) -> dict[str, object] | None:
        if "FROM cm_verified_sql_query" in sql:
            return None
        if "FROM cm_common_code" in sql:
            return {"code": params[1]}
        if "FROM sp_object" in sql:
            assert self.database_role == "STORY"
            assert params == ("TE_COMMON_CM_VERIFIED_SQL_QUERY",)
            return {
                "object_code": "TE_COMMON_CM_VERIFIED_SQL_QUERY",
                "business_code": "COMMON",
                "domain_code": "CM",
                "object_level": 4,
                "identifier_target_code": "QUERY",
                "sequence_scope_code": "DAILY",
                "sequence_length": 5,
            }
        raise AssertionError(sql)

    def fetch_all(
        self,
        sql: str,
        params: tuple[object, ...],
    ) -> list[dict[str, object]]:
        assert "FROM sp_object" in sql
        assert params == ("query_id",)
        return [{"object_code": "TE_COMMON_CM_VERIFIED_SQL_QUERY"}]


    def execute(self, sql: str, params: tuple[object, ...]) -> int:
        self.executed.append((sql, params))
        return 1

    def begin(self) -> None:
        return None

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


class _FakeIdentifierCoordinator:
    def __init__(self, database: _FakeDatabase) -> None:
        assert database.database_role == "STORY"

    def prepare_registered_object(
        self,
        *,
        object_metadata: dict[str, object],
        created_by: str,
        updated_by: str,
        client_ip: str,
        program_id: str,
    ) -> tuple[dict[str, object], dict[str, object]]:
        assert object_metadata["object_code"] == "TE_COMMON_CM_VERIFIED_SQL_QUERY"
        assert created_by == updated_by == "SPS_ADMIN"
        assert client_ip == "127.0.0.1"
        assert program_id == "SPS_HARNESS_MCP"
        return {"object_code": object_metadata["object_code"]}, {"lock": "prepared"}

    def acquire(self, prepared: dict[str, object]) -> None:
        assert prepared == {"lock": "prepared"}

    def resolve(
        self,
        *,
        request: dict[str, object],
        prepared: dict[str, object],
    ) -> SimpleNamespace:
        assert request == {"object_code": "TE_COMMON_CM_VERIFIED_SQL_QUERY"}
        assert prepared == {"lock": "prepared"}
        return SimpleNamespace(
            identifier="CM_CO_TE_COMMON_CM_VERIFIED_SQL_QUERY_20260803_00001"
        )

    def release(self, prepared: dict[str, object]) -> None:
        assert prepared == {"lock": "prepared"}


def test_verified_sql_register_dry_run_does_not_allocate_or_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verified_sql_tools, "CommonDatabase", _FakeDatabase)
    monkeypatch.setattr(
        verified_sql_tools, "IdentifierCoordinator", _FakeIdentifierCoordinator
    )
    _FakeDatabase.instances.clear()

    result = verified_sql_tools.verified_sql_register(
        query_name="Check Object Lifecycle Count",
        query_description="Object lifecycle integrity query.",
        crud_type="READ",
        sql_text="SELECT COUNT(*) AS lifecycle_count FROM sp_object_lifecycle",
        registered_by="SPS_ADMIN",
        apply=False,
    )

    assert result == {
        "dry_run": True,
        "statement_keyword": "SELECT",
        "crud_type": "READ",
        "verified_yn": "N",
    }
    assert _FakeDatabase.instances == []


def test_verified_sql_register_allocates_identifier_and_inserts_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verified_sql_tools, "CommonDatabase", _FakeDatabase)
    monkeypatch.setattr(
        verified_sql_tools, "IdentifierCoordinator", _FakeIdentifierCoordinator
    )
    _FakeDatabase.instances.clear()

    result = verified_sql_tools.verified_sql_register(
        query_name="Check Object Lifecycle Count",
        query_description="Object lifecycle integrity query.",
        crud_type="READ",
        sql_text="SELECT COUNT(*) AS lifecycle_count FROM sp_object_lifecycle",
        registered_by="SPS_ADMIN",
        verified_yn=True,
        certified_level_code="A",
        verification_description="Reviewed for lifecycle integrity verification.",
        verified_by="SPS_REVIEWER",
        story_programming_rule_pass_yn=True,
        snake_case_pass_yn=True,
        table_exists_pass_yn=True,
        column_exists_pass_yn=True,
        crud_match_pass_yn=True,
        where_clause_pass_yn=True,
        program_id="SPS_HARNESS_MCP",
        client_ip="127.0.0.1",
        apply=True,
    )

    assert result["query_id"] == "CM_CO_TE_COMMON_CM_VERIFIED_SQL_QUERY_20260803_00001"
    assert result["verified_yn"] == "Y"
    assert result["certified_level_code"] == "A"
    common_database = next(
        database
        for database in _FakeDatabase.instances
        if database.database_role == "COMMON"
    )
    assert len(common_database.executed) == 1
    assert common_database.committed is True
    assert common_database.closed is True
    assert "INSERT INTO cm_verified_sql_query" in common_database.executed[0][0]


def test_verified_sql_register_rejects_unsafe_sql_before_opening_database() -> None:
    with pytest.raises(ValueError, match="not allowed"):
        verified_sql_tools.verified_sql_register(
            query_name="Alter Object Lifecycle",
            query_description="Must not register DDL through Harness.",
            crud_type="ALTER",
            sql_text="ALTER TABLE sp_object_lifecycle ADD COLUMN invalid_column INT",
            registered_by="SPS_ADMIN",
            apply=True,
        )
