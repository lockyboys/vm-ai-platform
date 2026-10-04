"""pipeline_results dual-store persistence and compensation regressions."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from services.db import pipeline_results_repository as repository

DOC_ID = "SP_RP_OBJECT_20260707_212013_00004"


class FakeIdentifierCoordinator:
    def __init__(self, database):
        self.database = database

    def prepare_registered_object(self, **kwargs):
        return {"object_code": "EXECUTION_HISTORY"}, {"sequence": "reserved"}

    def acquire(self, prepared):
        pass

    def resolve(self, **kwargs):
        return SimpleNamespace(identifier="SP_RP_EXECUTION_HISTORY_TEST_00001")

    def release(self, prepared):
        pass


class FakeMaria:
    def __init__(self, role, fail_on_link=False):
        self.database_name = "te_common" if role == "COMMON" else "te_story_platform"
        self.config = {"host": "db", "port": "3306"}
        self.role = role
        self.fail_on_link = fail_on_link
        self.calls = []
        self.rollbacks = 0
        self.commits = 0
        self.next_id = 100

    def fetch_one(self, sql, params=None):
        if "FROM sp_object" in sql:
            code = params[0]
            object_ids = {
                "DOCUMENT": DOC_ID,
                "EXECUTION_HISTORY": "SP_RP_EXECUTION_HISTORY_OBJECT",
                "MDB": "SP_RP_MDB_TEST",
                "MCO": "SP_RP_MCO_TEST",
                "MCM": "SP_RP_MCM_TEST",
            }
            return {
                "object_id": object_ids[code], "object_code": code,
                "object_name": code, "object_description": "test object",
                "business_code": "SP", "domain_code": "RP",
                "object_type_code": "OBJECT", "object_level": 3,
                "target_identifier_field": "execution_history_id",
                "identifier_target_code": "OB",
                "sequence_scope_code": "DAILY", "sequence_length": 5,
                "status_code": "ACTIVE", "active_yn": "Y",
            }
        if "FROM cm_verified_sql_query" in sql:
            return {"query_id": repository.PIPELINE_RESULTS_INDEX_QUERY_NAME,
                    "crud_type": "CREATE", "verified_yn": "Y",
                    "status_code": "ACTIVE"}
        if "FROM cm_common_code" in sql:
            return {"common_code_json": (
                '{"source_database_role":"COMMON","mongodb_database_role":"COMMON",'
                '"source_table_name":"pipeline_results",'
                '"source_identifier_column_name":"id",'
                '"mongodb_collection_name":"pipeline_result_payload",'
                '"execution_link_required_yn":"Y",'
                '"execution_link_type_code":"MONGODB"}'
            )}
        raise AssertionError(sql)

    def execute(self, sql, params=None):
        if "sp_object_execution_link" in sql and self.fail_on_link:
            raise RuntimeError("injected link failure")
        self.calls.append((sql, params))
        return 1

    def last_insert_id(self):
        return self.next_id

    def begin(self):
        self.calls.append(("BEGIN", None))

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def ping_mariadb(self):
        return True

    def close(self):
        pass


class FakeMongo:
    def __init__(self):
        self.inserted = []
        self.deleted = []

    def find_one(self, collection, query):
        assert collection == "cm_verified_sql_query_payload"
        return {"payload": {"verified_sql_payload": {
            "sql_text": (
                "INSERT INTO pipeline_results "
                "(user_id, file_name, task_type, learning_type, accuracy) "
                "VALUES (%s, %s, %s, %s, %s)"
            )
        }}}

    def ping_mongodb(self):
        return True

    def insert_one(self, collection, document):
        self.inserted.append((collection, document))
        return SimpleNamespace(inserted_id="mongo-inserted")

    def delete_one(self, collection, filter_document):
        self.deleted.append((collection, filter_document))

    def close(self):
        pass


def make_factory(fail_on_link=False):
    story = FakeMaria("STORY")
    common = FakeMaria("COMMON", fail_on_link=fail_on_link)
    mongo = FakeMongo()

    def factory(*, database_role, connect_mariadb=True, connect_mongodb=False):
        if database_role == "STORY":
            return story
        if connect_mongodb:
            return mongo
        return common

    return factory, story, common, mongo


def test_pipeline_result_saves_index_payload_and_document_object(monkeypatch):
    factory, story, common, mongo = make_factory()
    monkeypatch.setattr(repository, "IdentifierCoordinator", FakeIdentifierCoordinator)

    result = repository.save_pipeline_results(
        user_id="u-1", file_name="health.csv", task_type="classification",
        learning_type="supervised", accuracy=0.91,
        data={"analysis": {"rows": 12}}, actor_id="tester",
        database_factory=factory,
    )

    assert result == {
        "pipeline_result_id": 100,
        "execution_history_id": "SP_RP_EXECUTION_HISTORY_TEST_00001",
        "status": "SUCCESS",
    }
    assert common.commits == 1
    assert len(mongo.inserted) == 1
    collection, document = mongo.inserted[0]
    assert collection == "pipeline_result_payload"
    assert document["data_json"] == {"analysis": {"rows": 12}}
    assert document["_sps"]["source_object_id"] == DOC_ID
    assert document["_sps"]["source_object_code"] == "DOCUMENT"
    link = next(params for sql, params in common.calls if "sp_object_execution_link" in sql)
    assert link[1] == DOC_ID
    assert link[2] == "SP_RP_MCM_TEST"
    assert mongo.deleted == []


def test_pipeline_link_failure_rolls_back_index_and_compensates_mongo(monkeypatch):
    factory, story, common, mongo = make_factory(fail_on_link=True)
    monkeypatch.setattr(repository, "IdentifierCoordinator", FakeIdentifierCoordinator)

    with pytest.raises(RuntimeError, match="injected link failure"):
        repository.save_pipeline_results(
            user_id="u-1", file_name="health.csv", task_type="classification",
            learning_type="supervised", accuracy=0.91,
            data={"analysis": {"rows": 12}}, actor_id="tester",
            database_factory=factory,
        )

    assert common.rollbacks == 1
    assert len(mongo.inserted) == 1
    assert mongo.deleted == [(
        "pipeline_result_payload",
        {"_sps.source_table_name": "pipeline_results",
         "_sps.source_identifier": 100},
    )]


def test_pipeline_entrypoint_uses_repository_storage_not_save_both():
    source = Path(__file__).resolve().parents[2].joinpath("pipeline.py").read_text(
        encoding="utf-8"
    )
    assert "save_pipeline_results(" in source
    assert "save_both(" not in source
