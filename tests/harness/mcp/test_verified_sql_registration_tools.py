"""Tests for the Verified SQL registration-only Harness tool."""

from __future__ import annotations

from types import SimpleNamespace
import json

import pytest

from harness.mcp.tools import verified_sql_tools


class _FakeDatabase:
    instances: list["_FakeDatabase"] = []
    fail_next_link = False

    def __init__(self, database_role: str) -> None:
        self.database_role = database_role
        self.database_name = "te_story_platform" if database_role == "STORY" else "te_common"
        self.config = {"host": "127.0.0.1", "port": "3306"}
        self.documents: list[dict[str, object]] = []
        self.fail_link = _FakeDatabase.fail_next_link
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
        if "information_schema.tables" in sql:
            return {"table_comment": "SPS Repository"}
        if "information_schema.columns" in sql:
            return {"character_maximum_length": 99}
        if "FROM sp_object" in sql:
            assert self.database_role == "STORY"
            code = params[0]
            return {
                "object_id": "SP_RP_OBJECT_" + code,
                "object_code": code,
                "object_name": "te_common.cm_verified_sql_query",
                "business_code": "COMMON",
                "domain_code": "CM",
                "object_level": 4,
                "identifier_target_code": "QUERY",
                "sequence_scope_code": "DAILY",
                "sequence_length": 5,
                "target_identifier_field": "query_id",
            }
        raise AssertionError(sql)

    def fetch_all(
        self,
        sql: str,
        params: tuple[object, ...],
    ) -> list[dict[str, object]]:
        if "information_schema.columns" in sql:
            return [{"column_name": "id", "column_comment": "Identifier"}]
        assert "FROM sp_object" in sql
        assert params == ("query_id",)
        return [{"object_code": "TE_COMMON_CM_VERIFIED_SQL_QUERY"}]


    def execute(self, sql: str, params: tuple[object, ...]) -> int:
        if "sp_object_execution_link" in sql and self.fail_link:
            raise RuntimeError("execution link failed")
        self.executed.append((sql, params))
        return 1

    def insert_one(self, collection_name, document):
        stored = {"_id": "mongo-" + str(len(self.documents) + 1), **document}
        self.documents.append(stored)
        return SimpleNamespace(inserted_id=stored["_id"])

    def delete_one(self, collection_name, filter_document):
        def nested_value(document, path):
            value = document
            for part in path.split("."):
                value = value.get(part) if isinstance(value, dict) else None
            return value

        self.documents = [
            document for document in self.documents
            if not all(nested_value(document, key) == value
                       for key, value in filter_document.items())
        ]

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
        assert object_metadata["object_code"] in {
            "TE_COMMON_CM_VERIFIED_SQL_QUERY", "EXECUTION_HISTORY",
            "TE_COMMON_EV_EVIDENCE",
        }
        assert created_by == updated_by == "SPS_ADMIN"
        assert client_ip == "127.0.0.1"
        assert program_id == "SPS_HARNESS_MCP"
        return {"object_code": object_metadata["object_code"]}, {"lock": "prepared"}

    def resolve_identifier_maximum_length(
        self,
        *,
        object_metadata: dict[str, object],
    ) -> int:
        assert object_metadata["object_name"] == "te_common.cm_verified_sql_query"
        assert object_metadata["target_identifier_field"] == "query_id"
        return 99

    def acquire(self, prepared: dict[str, object]) -> None:
        assert prepared == {"lock": "prepared"}

    def resolve(
        self,
        *,
        request: dict[str, object],
        prepared: dict[str, object],
        maximum_length: int,
    ) -> SimpleNamespace:
        assert request["object_code"] in {
            "TE_COMMON_CM_VERIFIED_SQL_QUERY", "EXECUTION_HISTORY", "TE_COMMON_EV_EVIDENCE",
        }
        assert prepared == {"lock": "prepared"}
        assert maximum_length == 99
        if request["object_code"] == "EXECUTION_HISTORY":
            return SimpleNamespace(identifier="SP_RP_EXECUTION_HISTORY_20260803_00001")
        if request["object_code"] == "TE_COMMON_EV_EVIDENCE":
            return SimpleNamespace(identifier="CM_EV_EVIDENCE_20260803_00001")
        return SimpleNamespace(
            identifier="CM_CO_TE_COMMON_CM_VERIFIED_SQL_QUERY_20260803_00001",
            sequence_no=1,
            sequence_length=5,
        )

    def render_resolution(
        self,
        *,
        request: dict[str, object],
        prepared: dict[str, object],
        resolution: SimpleNamespace,
        object_code: str,
        maximum_length: int,
    ) -> str:
        assert request == {"object_code": "TE_COMMON_CM_VERIFIED_SQL_QUERY"}
        assert prepared == {"lock": "prepared"}
        assert resolution.sequence_no == 1
        assert resolution.sequence_length == 5
        assert maximum_length == 99
        assert object_code == "CHECK_OBJECT_LIFECYCLE_COUNT"
        return "CM_CO_CHECK_OBJECT_LIFECYCLE_COUNT_20260803_00001"

    def release(self, prepared: dict[str, object]) -> None:
        assert prepared == {"lock": "prepared"}


class _FakeQueryIdentifierFeatureRuleResolver:
    def __init__(self, database: _FakeDatabase) -> None:
        assert database.database_role == "COMMON"

    def resolve(self, query_feature_code: str) -> SimpleNamespace:
        normalized = query_feature_code.strip().upper()
        if normalized in {
            "SQL",
            "SQL_QUERY",
            "VERIFIED_SQL",
            "VERIFIED_SQL_QUERY",
            "TE_COMMON_CM_VERIFIED_SQL_QUERY",
        }:
            raise ValueError(f"the active Rule forbids: {normalized}")
        if normalized in {"A", "READ-RULE", "READ RULE"}:
            raise ValueError(
                "query_feature_code does not satisfy the active "
                "Query Identifier Feature Rule."
            )
        return SimpleNamespace(
            query_feature_code=normalized,
            rule_id="CM_CO_RULE_QUERY_IDENTIFIER_FEATURE",
            rule_code="RL_VERIFIED_SQL_QUERY_IDENTIFIER_FEATURE",
        )


def test_verified_sql_register_dry_run_does_not_allocate_or_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verified_sql_tools, "CommonDatabase", _FakeDatabase)
    monkeypatch.setattr(
        verified_sql_tools, "IdentifierCoordinator", _FakeIdentifierCoordinator
    )
    monkeypatch.setattr(
        verified_sql_tools,
        "QueryIdentifierFeatureRuleResolver",
        _FakeQueryIdentifierFeatureRuleResolver,
    )
    _FakeDatabase.instances.clear()

    result = verified_sql_tools.verified_sql_register(
        query_name="Check Object Lifecycle Count",
        query_feature_code="CHECK_OBJECT_LIFECYCLE_COUNT",
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
        "query_feature_code": "CHECK_OBJECT_LIFECYCLE_COUNT",
        "query_feature_rule_id": "CM_CO_RULE_QUERY_IDENTIFIER_FEATURE",
        "query_feature_rule_code": "RL_VERIFIED_SQL_QUERY_IDENTIFIER_FEATURE",
    }
    assert len(_FakeDatabase.instances) == 1
    assert _FakeDatabase.instances[0].database_role == "COMMON"
    assert _FakeDatabase.instances[0].closed is True


def test_verified_sql_register_allocates_identifier_and_inserts_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verified_sql_tools, "CommonDatabase", _FakeDatabase)
    monkeypatch.setattr(
        verified_sql_tools, "IdentifierCoordinator", _FakeIdentifierCoordinator
    )
    monkeypatch.setattr(
        verified_sql_tools,
        "QueryIdentifierFeatureRuleResolver",
        _FakeQueryIdentifierFeatureRuleResolver,
    )
    _FakeDatabase.instances.clear()

    result = verified_sql_tools.verified_sql_register(
        query_name="Check Object Lifecycle Count",
        query_feature_code="CHECK_OBJECT_LIFECYCLE_COUNT",
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

    assert result["query_id"] == "CM_CO_CHECK_OBJECT_LIFECYCLE_COUNT_20260803_00001"
    assert result["verified_yn"] == "Y"
    assert result["certified_level_code"] == "A"
    common_database = next(
        database
        for database in _FakeDatabase.instances
        if database.database_role == "COMMON" and database.executed
    )
    assert len(common_database.executed) == 4
    assert common_database.committed is True
    assert common_database.closed is True
    assert "INSERT INTO cm_verified_sql_query" in common_database.executed[1][0]
    assert "sp_execution_history" in common_database.executed[0][0]
    assert "sp_object_execution_link" in common_database.executed[2][0]
    assert result["execution_history_id"] == "SP_RP_EXECUTION_HISTORY_20260803_00001"


def test_verified_sql_register_rejects_unsafe_sql_before_opening_database() -> None:
    with pytest.raises(ValueError, match="not allowed"):
        verified_sql_tools.verified_sql_register(
            query_name="Alter Object Lifecycle",
            query_feature_code="ALTER_OBJECT_LIFECYCLE",
            query_description="Must not register DDL through Harness.",
            crud_type="ALTER",
            sql_text="ALTER TABLE sp_object_lifecycle ADD COLUMN invalid_column INT",
            registered_by="SPS_ADMIN",
            apply=True,
        )


@pytest.mark.parametrize(
    "query_feature_code",
    (
        "SQL",
        "SQL_QUERY",
        "VERIFIED_SQL",
        "VERIFIED_SQL_QUERY",
        "TE_COMMON_CM_VERIFIED_SQL_QUERY",
    ),
)
def test_verified_sql_register_rejects_generic_query_feature_code(
    query_feature_code: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verified_sql_tools, "CommonDatabase", _FakeDatabase)
    monkeypatch.setattr(
        verified_sql_tools,
        "QueryIdentifierFeatureRuleResolver",
        _FakeQueryIdentifierFeatureRuleResolver,
    )
    _FakeDatabase.instances.clear()

    with pytest.raises(ValueError, match="active Rule forbids"):
        verified_sql_tools.verified_sql_register(
            query_name="Read Rule Child Identifier Metadata",
            query_feature_code=query_feature_code,
            query_description="Read identifier metadata.",
            crud_type="READ",
            sql_text="SELECT object_code FROM sp_object",
            registered_by="SPS_ADMIN",
            apply=True,
        )

    assert len(_FakeDatabase.instances) == 1
    assert _FakeDatabase.instances[0].closed is True


@pytest.mark.parametrize("query_feature_code", ("A", "READ-RULE", "READ RULE"))
def test_verified_sql_register_rejects_invalid_query_feature_code(
    query_feature_code: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verified_sql_tools, "CommonDatabase", _FakeDatabase)
    monkeypatch.setattr(
        verified_sql_tools,
        "QueryIdentifierFeatureRuleResolver",
        _FakeQueryIdentifierFeatureRuleResolver,
    )
    _FakeDatabase.instances.clear()

    with pytest.raises(ValueError, match="active Query Identifier Feature Rule"):
        verified_sql_tools.verified_sql_register(
            query_name="Read Rule Child Identifier Metadata",
            query_feature_code=query_feature_code,
            query_description="Read identifier metadata.",
            crud_type="READ",
            sql_text="SELECT object_code FROM sp_object",
            registered_by="SPS_ADMIN",
            apply=True,
        )

    assert len(_FakeDatabase.instances) == 1
    assert _FakeDatabase.instances[0].closed is True

def test_verified_sql_register_inserts_supplied_evidence_in_same_transaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verified_sql_tools, "CommonDatabase", _FakeDatabase)
    monkeypatch.setattr(verified_sql_tools, "IdentifierCoordinator", _FakeIdentifierCoordinator)
    monkeypatch.setattr(verified_sql_tools, "QueryIdentifierFeatureRuleResolver",
                        _FakeQueryIdentifierFeatureRuleResolver)
    _FakeDatabase.instances.clear()
    result = verified_sql_tools.verified_sql_register(
        query_name="Check Object Lifecycle Count",
        query_feature_code="CHECK_OBJECT_LIFECYCLE_COUNT",
        query_description="Object lifecycle integrity query.",
        crud_type="READ",
        sql_text="SELECT COUNT(*) AS lifecycle_count FROM sp_object_lifecycle",
        registered_by="SPS_ADMIN", program_id="SPS_HARNESS_MCP", client_ip="127.0.0.1",
        evidence_json=json.dumps({
            "evidence_code": "TEST_EVIDENCE",
            "evidence_name": "Test source",
            "evidence_level_code": "A",
            "evidence_category_code": "DOCUMENT",
            "source_title": "Source",
        }), apply=True,
    )
    common = next(db for db in _FakeDatabase.instances
                  if db.database_role == "COMMON" and db.executed)
    assert result["evidence_id"] == "CM_EV_EVIDENCE_20260803_00001"
    assert any("INSERT INTO ev_evidence" in sql for sql, _ in common.executed)
    assert len(common.executed) == 5
    mongo = next(db for db in _FakeDatabase.instances
                 if db.database_role == "COMMON" and db.documents)
    assert mongo.documents[0]["_sps"]["evidence_id"] == result["evidence_id"]


def test_verified_sql_register_link_failure_compensates_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verified_sql_tools, "CommonDatabase", _FakeDatabase)
    monkeypatch.setattr(verified_sql_tools, "IdentifierCoordinator", _FakeIdentifierCoordinator)
    monkeypatch.setattr(verified_sql_tools, "QueryIdentifierFeatureRuleResolver",
                        _FakeQueryIdentifierFeatureRuleResolver)
    _FakeDatabase.instances.clear()
    monkeypatch.setattr(_FakeDatabase, "fail_next_link", True)
    with pytest.raises(RuntimeError, match="execution link failed"):
        verified_sql_tools.verified_sql_register(
            query_name="Check Object Lifecycle Count",
            query_feature_code="CHECK_OBJECT_LIFECYCLE_COUNT",
            query_description="Object lifecycle integrity query.",
            crud_type="READ",
            sql_text="SELECT COUNT(*) AS lifecycle_count FROM sp_object_lifecycle",
            registered_by="SPS_ADMIN", program_id="SPS_HARNESS_MCP",
            client_ip="127.0.0.1", apply=True,
        )
    common = next(db for db in _FakeDatabase.instances
                  if db.database_role == "COMMON" and db.rolled_back)
    assert common.committed is False
    assert all(not db.documents for db in _FakeDatabase.instances)
