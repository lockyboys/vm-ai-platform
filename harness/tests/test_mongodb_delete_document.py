from __future__ import annotations

from types import SimpleNamespace

import pytest

from harness.mcp.tools import mongodb_delete_tool


class _FakeDatabase:
    database_role = "COMMON"

    def __init__(self, *args, **kwargs):
        self.deleted = []

    def list_collection_names(self):
        return ["cm_verified_sql_query_payload"]

    def find(self, collection_name, filter_document, limit):
        return [{"_id": filter_document["_id"]}]

    def delete_one(self, collection_name, filter_document):
        self.deleted.append((collection_name, filter_document))
        return SimpleNamespace(deleted_count=1)

    def close(self):
        pass


def test_mongodb_delete_document_dry_run_does_not_delete(monkeypatch):
    fake = _FakeDatabase()
    monkeypatch.setattr(mongodb_delete_tool, "CommonDatabase", lambda **kwargs: fake)
    result = mongodb_delete_tool.mongodb_delete_document(
        role="COMMON",
        collection_name="cm_verified_sql_query_payload",
        contract_code="CM_VERIFIED_SQL_DETAIL",
        source_identifier="CM_CO_TE_COMMON_CM_VERIFIED_SQL_QUERY_20260731_00001",
        document_id="6abb8aea39fa62691ccba1b9",
        apply=False,
    )
    assert result["applied"] is False
    assert fake.deleted == []


def test_mongodb_delete_document_apply_deletes_exact_document(monkeypatch):
    fake = _FakeDatabase()
    monkeypatch.setattr(mongodb_delete_tool, "CommonDatabase", lambda **kwargs: fake)
    result = mongodb_delete_tool.mongodb_delete_document(
        role="COMMON",
        collection_name="cm_verified_sql_query_payload",
        contract_code="CM_VERIFIED_SQL_DETAIL",
        source_identifier="CM_CO_TE_COMMON_CM_VERIFIED_SQL_QUERY_20260731_00001",
        document_id="6abb8aea39fa62691ccba1b9",
        apply=True,
    )
    assert result["deleted_count"] == 1
    assert len(fake.deleted) == 1


def test_mongodb_delete_document_requires_valid_object_id():
    with pytest.raises(ValueError):
        mongodb_delete_tool.mongodb_delete_document(
            role="COMMON",
            collection_name="cm_verified_sql_query_payload",
            contract_code="CM_VERIFIED_SQL_DETAIL",
            source_identifier="target",
            document_id="not-an-object-id",
        )
