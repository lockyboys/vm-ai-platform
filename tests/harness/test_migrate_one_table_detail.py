"""Harness-owned storage migration entrypoint tests."""

from __future__ import annotations

from harness.scripts import migrate_one_table_detail as migration


class FakeMongoLookupDatabase:
    def find(self, *, collection_name, filter_document, limit):
        assert collection_name == "verified_sql_payload"
        assert filter_document["_sps.source_identifier"] == "CM_CO_QUERY_1"
        assert limit == 1
        return [{"payload": {"verified_sql_payload": {"sql_text": "SELECT 1"}}}]


class FakeVerifiedQueryDatabase:
    def fetch_one(self, sql, params):
        assert "sql_text" not in sql
        query_name = params[0]
        return {
            "query_id": f"QUERY_{query_name}",
            "query_name": query_name,
            "crud_type": next(
                crud_type
                for operation_name, crud_type in migration._VERIFIED_QUERY_CRUD.items()
                if query_name == f"query_{operation_name}"
            ),
        }

    def find(self, *, collection_name, filter_document, limit):
        assert collection_name == "verified_sql_payload"
        assert filter_document["_sps.source_identifier"].startswith("QUERY_")
        assert limit == 1
        return [{"payload": {"verified_sql_payload": {"sql_text": "SELECT 1"}}}]


def test_harness_migration_uses_project_root_import_path() -> None:
    assert migration._PROJECT_ROOT_PATH.name == "vm_project"
    assert migration._PROGRAM_ID == "harness.scripts.migrate_one_table_detail"


def test_migration_reads_cleared_verified_sql_from_mongodb() -> None:
    row = migration._hydrate_verified_sql_text_from_mongodb(
        FakeMongoLookupDatabase(),
        {"query_id": "CM_CO_QUERY_1", "sql_text": None},
    )
    assert row["sql_text"] == "SELECT 1"


def test_verified_query_loader_reads_index_from_mariadb_and_payload_from_mongodb() -> None:
    contract = {
        "verified_query_names": {
            operation_name: f"query_{operation_name}"
            for operation_name in migration._VERIFIED_QUERY_CRUD
        }
    }

    rows = migration._load_verified_queries(FakeVerifiedQueryDatabase(), contract)

    assert set(rows) == set(migration._VERIFIED_QUERY_CRUD)
    assert all(row["sql_text"] == "SELECT 1" for row in rows.values())
