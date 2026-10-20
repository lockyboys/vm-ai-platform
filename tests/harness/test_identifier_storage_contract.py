"""Identifier storage contracts: reproduce Mongo failure without allocating IDs."""
import json
import pytest
from harness.mcp.tools import identifier_tools as tool

class Coordinator:
    def resolve_identifier_maximum_length(self, *, object_metadata):
        if object_metadata["object_name"] != "repo.sp_object":
            raise ValueError("physical object_name")
        assert object_metadata["target_identifier_field"] == "object_id"
        return 99

class Common:
    row = None
    closed = False
    def __init__(self, database_role):
        assert database_role == "COMMON"
    def fetch_one(self, sql, params):
        assert params == ("MCO",)
        return self.row
    def close(self):
        type(self).closed = True

@pytest.fixture(autouse=True)
def common(monkeypatch):
    Common.closed = False
    monkeypatch.setattr(tool, "CommonDatabase", Common)

def metadata():
    return {"object_name":"MongoDB Collection Object",
            "target_identifier_field":"mongodb_collection_id","identifier_target_code":"MCO"}

def test_collection_storage_keeps_original():
    Common.row = {"common_code_json":json.dumps({"identifier_storage":{
        "schema_name":"repo","table_name":"sp_object","column_name":"object_id"}})}
    original = metadata()
    assert tool._resolve_storage_maximum_length(Coordinator(), original) == 99
    assert original == metadata()
    assert Common.closed

def test_missing_contract_preserves_legacy_failure():
    Common.row = None
    with pytest.raises(ValueError, match="physical object_name"):
        tool._resolve_storage_maximum_length(Coordinator(), metadata())
    assert Common.closed

@pytest.mark.parametrize("storage", [[],{},{"schema_name":"repo","table_name":"sp_object"},
    {"schema_name":"repo;DROP","table_name":"sp_object","column_name":"object_id"}])
def test_bad_storage_fails_closed(storage):
    Common.row = {"common_code_json":json.dumps({"identifier_storage":storage})}
    with pytest.raises(ValueError):
        tool._resolve_storage_maximum_length(Coordinator(), metadata())
    assert Common.closed

def test_invalid_json_fails_closed():
    Common.row = {"common_code_json":"broken"}
    with pytest.raises(ValueError):
        tool._resolve_storage_maximum_length(Coordinator(), metadata())
    assert Common.closed
