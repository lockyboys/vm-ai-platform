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
