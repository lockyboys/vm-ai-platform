"""Tests for Verified SQL MongoDB payload fallback."""

from __future__ import annotations

from harness.mcp.tools import verified_sql_tools


class FakeDatabase:
    def find(self, *, collection_name, filter_document, limit):
        assert collection_name == "verified_sql_payload"
        assert filter_document["_sps.source_identifier"] == "CM_CO_QUERY_1"
        assert limit == 1
        return [{
            "payload": {
                "verified_sql_payload": {
                    "query_description": "{\"database_role\":\"STORY\"}",
                    "sql_text": "SELECT 1",
                    "verification_description": "MongoDB payload",
                }
            }
        }]


def test_hydrates_empty_sql_text_from_mongodb_payload() -> None:
    result = verified_sql_tools._hydrate_query_payload_from_mongodb(
        FakeDatabase(),
        {"query_id": "CM_CO_QUERY_1", "sql_text": None},
    )
    assert result["sql_text"] == "SELECT 1"
    assert result["query_description"] == "{\"database_role\":\"STORY\"}"


class MetadataDatabase(FakeDatabase):
    def __init__(self, database_role="COMMON"):
        self.closed = False
        self.metadata = {"query_id": "CM_CO_QUERY_1", "query_name": "read_memory",
                         "crud_type": "READ", "certified_level_code": "A"}
        self.payload_missing = False

    def check_projection(self, sql):
        projection = sql.split("FROM cm_verified_sql_query")[0]
        assert all(column not in projection for column in
                   ("query_description", "sql_text", "verification_description"))
        assert "verified_yn = 'Y'" in sql
        assert "status_code = 'ACTIVE'" in sql
        assert "deleted_dt IS NULL" in sql

    def fetch_one(self, sql, params):
        self.check_projection(sql)
        assert "certified_level_code = 'A'" in sql
        assert params == ("CM_CO_QUERY_1",)
        return self.metadata

    def fetch_all(self, sql, params):
        self.check_projection(sql)
        assert params == ("CM_CO_QUERY_1",)
        return [dict(self.metadata)]

    def find(self, **kwargs):
        if self.payload_missing:
            return []
        return super().find(**kwargs)

    def close(self):
        self.closed = True


def test_execute_loader_works_after_payload_columns_are_removed():
    result = verified_sql_tools._load_executable_query(MetadataDatabase(), "CM_CO_QUERY_1")
    assert result["sql_text"] == "SELECT 1"
    assert result["crud_type"] == "READ"


def test_execute_loader_rejects_unapproved_query_before_loading_payload():
    import pytest
    database = MetadataDatabase()
    database.metadata = None
    with pytest.raises(ValueError, match="not an executable"):
        verified_sql_tools._load_executable_query(database, "CM_CO_QUERY_1")


def test_execute_loader_fails_closed_when_payload_is_missing():
    import pytest
    database = MetadataDatabase()
    database.payload_missing = True
    with pytest.raises(ValueError, match="missing in MongoDB"):
        verified_sql_tools._load_executable_query(database, "CM_CO_QUERY_1")


def test_query_listing_loads_descriptions_without_exposing_sql(monkeypatch):
    from harness.mcp.tools import mongodb_tools
    database = MetadataDatabase()
    monkeypatch.setattr(mongodb_tools, "CommonDatabase", lambda **kwargs: database)
    result = mongodb_tools.verified_sql(query_id="CM_CO_QUERY_1")
    assert result[0]["sql_text"] is None
    assert result[0]["query_description"] == '{"database_role":"STORY"}'
    assert result[0]["verification_description"] == "MongoDB payload"
    assert database.closed


def test_query_listing_includes_sql_only_when_requested(monkeypatch):
    from harness.mcp.tools import mongodb_tools
    database = MetadataDatabase()
    monkeypatch.setattr(mongodb_tools, "CommonDatabase", lambda **kwargs: database)
    result = mongodb_tools.verified_sql(query_id="CM_CO_QUERY_1", include_sql_text=True)
    assert result[0]["sql_text"] == "SELECT 1"
    assert database.closed


def test_query_listing_closes_connection_on_missing_payload(monkeypatch):
    import pytest
    from harness.mcp.tools import mongodb_tools
    database = MetadataDatabase()
    database.payload_missing = True
    monkeypatch.setattr(mongodb_tools, "CommonDatabase", lambda **kwargs: database)
    with pytest.raises(ValueError, match="missing in MongoDB"):
        mongodb_tools.verified_sql(query_id="CM_CO_QUERY_1")
    assert database.closed
