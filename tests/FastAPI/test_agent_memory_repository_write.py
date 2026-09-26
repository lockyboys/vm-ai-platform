"""Memory writes must link the Mongo document to SPS history atomically."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from FastAPI.LangGraph import agent_memory


class MongoDouble:
    def __init__(self):
        self.rows = {}
        self.deleted = []

    def find_one(self, collection, selector):
        row = self.rows.get(selector["_id"])
        if row is None or not all(row.get(k) == v for k, v in selector.items()):
            return None
        return deepcopy(row)

    def insert_one(self, collection, document):
        if document["_id"] in self.rows:
            raise RuntimeError("duplicate request")
        self.rows[document["_id"]] = deepcopy(document)
        return SimpleNamespace(inserted_id=document["_id"])

    def delete_one(self, collection, selector):
        self.deleted.append((collection, selector))
        self.rows.pop(selector["_id"], None)


class StoryDouble:
    database_name = "te_story_platform"

    def __init__(self):
        self.statements = []
        self.committed = 0
        self.rolled_back = 0
        self.fail_link = False
        self.fail_commit = False
        self.objects = {
            agent_memory.MEMORY_OBJECT_CODE: "SP_RP_MCO_20260924_00001",
            "MDB": "SP_RP_MDB_2026_00001",
            "MCM": "SP_RP_MCM_20260801_00001",
            "EXECUTION_HISTORY": "SP_RP_EXECUTION_HISTORY_20260723_00001",
        }

    def fetch_one(self, sql, params):
        if "information_schema.tables" in sql:
            return {"table_comment": "SPS Repository"}
        if "information_schema.columns" in sql:
            return {"character_maximum_length": 99}
        if "FROM sp_object" in sql:
            object_code = params[0]
            if object_code not in self.objects:
                return None
            return {
                "object_id": self.objects[object_code], "object_code": object_code,
                "object_name": "te_story_platform.sp_execution_history",
                "business_code": "SP", "domain_code": "RP", "object_level": 3,
                "identifier_target_code": "EG", "sequence_scope_code": "DAILY",
                "sequence_length": 5, "target_identifier_field": "execution_history_id",
            }
        raise AssertionError(sql)

    def fetch_all(self, sql, params):
        assert "information_schema.columns" in sql
        return [{"column_name": "id", "column_comment": "Identifier"}]

    def begin(self):
        self.statements.clear()

    def execute(self, sql, params):
        if "INSERT INTO sp_object_execution_link" in sql and self.fail_link:
            raise RuntimeError("link insert failed")
        self.statements.append((sql, params))
        return 1

    def commit(self):
        self.committed += 1
        if self.fail_commit and self.committed == 2:
            raise RuntimeError("MariaDB commit failed")

    def rollback(self):
        self.rolled_back += 1
        self.statements.clear()

    def close(self):
        pass


class CoordinatorDouble:
    def __init__(self, database):
        assert isinstance(database, StoryDouble)

    def prepare_registered_object(self, *, object_metadata, **audit):
        assert object_metadata["object_code"] == "EXECUTION_HISTORY"
        return {"object_code": "EXECUTION_HISTORY"}, {"lock_name": "memory"}

    def acquire(self, prepared):
        pass

    def release(self, prepared):
        pass

    def resolve(self, *, request, prepared, maximum_length):
        assert maximum_length == 99
        return SimpleNamespace(identifier="SP_RP_EXECUTION_HISTORY_20260924_00001")


@pytest.fixture
def memory(monkeypatch):
    story = StoryDouble()
    mongo = MongoDouble()
    monkeypatch.setattr(agent_memory, "CommonDatabase", lambda **kwargs: story)
    monkeypatch.setattr(agent_memory, "IdentifierCoordinator", CoordinatorDouble)
    settings = {"database_role": "STORY", "collection_name": "agent_long_term_memory",
                "domain_code": "general"}
    return agent_memory.PersistentMemory(settings=settings, database=mongo), story, mongo


def test_memory_save_links_history_and_is_idempotent(memory):
    service, story, mongo = memory
    result = service.save("actor", "thread", "request", "question",
                          {"response": "answer"}, "127.0.0.1")
    assert result["memory_saved"] is True
    assert len(mongo.rows) == 1
    assert len(story.statements) == 3
    assert "INSERT INTO sp_execution_history" in story.statements[0][0]
    assert "INSERT INTO sp_object_execution_link" in story.statements[1][0]
    assert "UPDATE sp_execution_history" in story.statements[2][0]
    assert story.committed == 2
    assert service.save("actor", "thread", "request", "question",
                        {"response": "answer"}, "127.0.0.1") == result
    assert story.committed == 2
    with pytest.raises(ValueError, match="request_id"):
        service.save("actor", "thread", "request", "different",
                     {"response": "answer"}, "127.0.0.1")


def test_link_failure_rolls_back_and_deletes_only_inserted_memory(memory):
    service, story, mongo = memory
    story.fail_link = True
    with pytest.raises(RuntimeError, match="link insert failed"):
        service.save("actor", "thread", "request", "question",
                     {"response": "answer"}, "127.0.0.1")
    assert story.rolled_back == 1
    assert story.committed == 1  # Identifier reservation survives the failed write.
    assert mongo.rows == {}
    assert mongo.deleted[0][0] == "agent_long_term_memory"
    story.fail_link = False
    assert service.save("actor", "thread", "request", "question",
                        {"response": "answer"}, "127.0.0.1")["memory_saved"]


def test_mariadb_commit_failure_compensates_mongodb(memory):
    service, story, mongo = memory
    story.fail_commit = True
    with pytest.raises(RuntimeError, match="MariaDB commit failed"):
        service.save("actor", "thread", "request", "question",
                     {"response": "answer"}, "127.0.0.1")
    assert story.rolled_back == 1
    assert mongo.rows == {}
