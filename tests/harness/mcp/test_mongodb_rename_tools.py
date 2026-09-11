from common.database import CommonDatabase
from harness.mcp.tools import mongodb_tools


class FakeMongoDatabase:
    database_role = "HEALTH"

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.collections = {"health_report_document": 4}
        self.renamed = None

    def list_collection_names(self):
        return list(self.collections)

    def count_documents(self, collection_name):
        return self.collections[collection_name]

    def rename_collection(self, source_name, target_name):
        self.collections[target_name] = self.collections.pop(source_name)
        self.renamed = (source_name, target_name)
        return target_name

    def close(self):
        pass


def test_mongodb_rename_collection_dry_run_returns_collision_safe_count(monkeypatch):
    database = FakeMongoDatabase()
    monkeypatch.setattr(mongodb_tools, "CommonDatabase", lambda **kwargs: database)

    result = mongodb_tools.mongodb_rename_collection(
        role="HEALTH",
        source_collection="health_report_document",
        target_collection="health_report_content",
        apply=False,
    )

    assert result["source_document_count"] == 4
    assert result["applied"] is False
    assert database.renamed is None


def test_mongodb_rename_collection_apply_verifies_target_count(monkeypatch):
    database = FakeMongoDatabase()
    monkeypatch.setattr(mongodb_tools, "CommonDatabase", lambda **kwargs: database)

    result = mongodb_tools.mongodb_rename_collection(
        role="HEALTH",
        source_collection="health_report_document",
        target_collection="health_report_content",
        apply=True,
    )

    assert database.renamed == ("health_report_document", "health_report_content")
    assert result["source_document_count"] == 4
    assert result["target_document_count"] == 4
    assert result["content_changed_yn"] == "N"


def test_mongodb_collection_stats_uses_requested_role(monkeypatch):
    database = FakeMongoDatabase()
    monkeypatch.setattr(mongodb_tools, "CommonDatabase", lambda **kwargs: database)

    assert mongodb_tools.mongodb_collection_stats(
        role="HEALTH",
        collection_name="health_report_document",
    ) == {
        "database_role": "HEALTH",
        "collection_name": "health_report_document",
        "document_count": 4,
    }


def test_common_database_builds_uri_from_legacy_mongodb_environment(monkeypatch):
    monkeypatch.delenv("MONGODB_URI", raising=False)
    monkeypatch.setenv("HEALTH_COMPANION_MONGODB_URI", "")
    monkeypatch.setenv("HEALTH_COMPANION_MONGODB_DATABASE", "")
    monkeypatch.setenv("MONGODB_HOST", "127.0.0.1")
    monkeypatch.setenv("MONGODB_PORT", "27017")
    monkeypatch.setenv("MONGODB_USER", "health_user")
    monkeypatch.setenv("MONGODB_PASSWORD", "pass@word")
    monkeypatch.setenv("MONGODB_DATABASE", "health_companion_ai")

    database = CommonDatabase(database_role="HEALTH", connect_mariadb=False)

    assert database._load_mongodb_config()["uri"] == (
        "mongodb://health_user:pass%40word@127.0.0.1:27017/"
    )


def test_common_database_rename_accepts_pymongo_command_document(monkeypatch):
    collection_names = {"health_report_document"}

    class FakeCollection:
        def rename(self, target_name, dropTarget=False):
            assert dropTarget is False
            collection_names.remove("health_report_document")
            collection_names.add(target_name)
            return {"ok": 1.0, "ns": f"health_companion_ai.{target_name}"}

    database = CommonDatabase(database_role="HEALTH", connect_mariadb=False)
    monkeypatch.setattr(
        database,
        "list_collection_names",
        lambda: sorted(collection_names),
    )
    monkeypatch.setattr(
        database,
        "get_collection",
        lambda collection_name: FakeCollection(),
    )

    assert database.rename_collection(
        "health_report_document",
        "health_report_content",
    ) == "health_report_content"
