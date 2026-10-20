"""Level 4 Mongo document IDs must be reserved from the MCM class through the active Rule."""
from types import SimpleNamespace

import pytest

from common import database as common_database


class Database:
    database_name = "te_story_platform"
    def __init__(self):
        self.events = []
    def begin(self): self.events.append("begin")
    def commit(self): self.events.append("commit")
    def rollback(self): self.events.append("rollback")


class Coordinator:
    next_level = 4
    serial = 0
    def __init__(self, database):
        self.database = database
    def resolve_identifier_maximum_length(self, *, object_metadata):
        assert object_metadata["object_name"] == "te_story_platform.sp_object_execution_link"
        assert object_metadata["target_identifier_field"] == "mongodb_document_master_id"
        return 99
    def prepare_registered_object(self, *, object_metadata, **audit):
        assert object_metadata["object_code"] == "MCM"
        return {"object_code": "MCM"}, {"object_level": self.next_level}
    def acquire(self, prepared): self.database.events.append("acquire")
    def release(self, prepared): self.database.events.append("release")
    def resolve(self, *, request, prepared, maximum_length):
        type(self).serial += 1
        return SimpleNamespace(identifier=f"SP_RP_MCM_20261009_180200_{type(self).serial:05d}",
                               object_level=prepared["object_level"])


META = {"object_id": "SP_RP_MCM_20260801_00001", "object_code": "MCM",
        "object_name": "MongoDB Collection Master", "object_level": 3,
        "target_identifier_field": "mongodb_document_master_id"}


def test_unique_level4_ids(monkeypatch):
    # A new sequence is reserved per document, and the class ID is never copied.
    monkeypatch.setattr("engine.identifier.coordinator.IdentifierCoordinator", Coordinator)
    Coordinator.serial, Coordinator.next_level = 0, 4
    db = Database()
    ids = [common_database.reserve_document_master_id(db, META, "actor", "127.0.0.1", "TEST")
           for _ in range(2)]
    assert len(set(ids)) == 2
    assert all(value != META["object_id"] for value in ids)
    assert db.events == ["acquire", "begin", "commit", "release"] * 2


def test_level3_resolution_fails_without_reserving(monkeypatch):
    # A Level 3 Rule must fail before the sequence is consumed.
    monkeypatch.setattr("engine.identifier.coordinator.IdentifierCoordinator", Coordinator)
    Coordinator.serial, Coordinator.next_level = 0, 3
    db = Database()
    with pytest.raises(ValueError, match="Level 4"):
        common_database.reserve_document_master_id(db, META, "actor", "127.0.0.1", "TEST")
    assert db.events == []
    assert Coordinator.serial == 0


def test_mcm_call_sites_compile_and_do_not_embed_static_master_id():
    # Verify changed production modules compile and the old shared value is not written as a document ID.
    from pathlib import Path
    paths = [
        Path("FastAPI/LangGraph/agent_memory.py"),
        Path("FastAPI/LangGraph/agent_memory2.py"),
        Path("FastAPI/LangGraph/Agent_Import_RAGs/LangGraph_email_RAG_Agent.py"),
    ]
    for path in paths:
        content = path.read_text(encoding="utf-8")
        compile(content, str(path), "exec")
        assert "reserve_document_master_id(" in content
    email_source = paths[-1].read_text(encoding="utf-8")
    assert '"mongodb_document_master_id": os.getenv("MONGODB_DOCUMENT_MASTER_ID"' not in email_source
