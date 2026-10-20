"""Regression tests: preserve Table semantics and require explicit Mongo metadata."""
import pytest
from harness.mcp.tools.entity_attribute_contract import validate_storage_contract

def test_existing_table_contract_is_preserved():
    """Legacy NULL Mongo bindings must remain a physical Table/Column contract."""
    result = validate_storage_contract(
        {"object_id": "table_object"},
        [{"object_id": "table_object", "column_name": "member_id", "data_type": "varchar"}],
    )
    assert result["storage_kind"] == "TABLE"

def test_mongodb_collection_and_nested_field_are_explicit():
    """Collection identity comes from Repository metadata, not a document sample."""
    result = validate_storage_contract(
        {"object_id": "collection_object", "mongodb_collection_id": "collection_id"},
        [{"object_id": "collection_object", "column_name": "audit.created_dt",
          "mongodb_field_path": "audit.created_dt", "data_type": "bson:date"}],
        collection_metadata={"mongodb_collection_id": "collection_id",
                             "object_id": "collection_object"},
    )
    assert result["storage_kind"] == "MONGODB"
    assert result["field_paths"] == ["audit.created_dt"]

@pytest.mark.parametrize("path", ["", "$set", "audit..date", ".date", "date.", "a"*151])
def test_invalid_mongodb_field_path_is_rejected(path):
    """Reject ambiguous/operator paths before any Repository writes."""
    with pytest.raises(ValueError):
        validate_storage_contract(
            {"object_id": "c", "mongodb_collection_id": "id"},
            [{"object_id": "c", "column_name": path, "mongodb_field_path": path,
              "data_type": "bson:date"}],
            collection_metadata={"mongodb_collection_id": "id", "object_id": "c"},
        )

def test_mongo_metadata_is_required():
    """A Document Object cannot be silently treated as a Collection Object."""
    with pytest.raises(ValueError):
        validate_storage_contract(
            {"object_id": "c", "mongodb_collection_id": "id"}, [],
        )

def test_mongo_identity_conflict_is_rejected():
    """The registered collection Object, not a document ID, owns the Entity."""
    with pytest.raises(ValueError):
        validate_storage_contract(
            {"object_id": "c", "mongodb_collection_id": "id"}, [],
            collection_metadata={"mongodb_collection_id": "id", "object_id": "other"},
        )

def test_table_does_not_accept_mongodb_fields():
    """SQL generators must not receive Mongo field paths as physical Columns."""
    with pytest.raises(ValueError):
        validate_storage_contract({"object_id": "t"}, [
            {"object_id": "t", "column_name": "a", "mongodb_field_path": "a",
             "data_type": "varchar"},
        ])

def test_bson_type_and_matching_field_are_required():
    """Do not infer BSON types from a bounded document sample."""
    with pytest.raises(ValueError):
        validate_storage_contract(
            {"object_id": "c", "mongodb_collection_id": "id"},
            [{"object_id": "c", "column_name": "a", "mongodb_field_path": "b",
              "data_type": "varchar"}],
            collection_metadata={"mongodb_collection_id": "id", "object_id": "c"},
        )
