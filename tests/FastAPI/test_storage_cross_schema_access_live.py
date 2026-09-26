"""Read-only access check for MariaDB writes spanning COMMON and STORY."""
from common.database import CommonDatabase
from engine.common.repository_schema_guard import assert_schema_documented


def test_common_connection_can_read_story_metadata():
    common = CommonDatabase(database_role="COMMON")
    story = CommonDatabase(database_role="STORY")
    try:
        assert (common.config["host"], common.config["port"]) == (
            story.config["host"], story.config["port"]
        ), "COMMON and STORY must share a MariaDB instance for one transaction"
        assert common.fetch_one(
            "SELECT object_id FROM te_story_platform.sp_object WHERE object_code = %s",
            ("EXECUTION_HISTORY",),
        )
        assert story.fetch_one(
            "SELECT query_id FROM te_common.cm_verified_sql_query LIMIT 1"
        )
        assert_schema_documented(common, "te_common", ("cm_verified_sql_query", "ev_evidence"))
        assert_schema_documented(story, story.database_name,
                                 ("sp_object", "sp_execution_history",
                                  "sp_object_execution_link"))
    finally:
        common.close()
        story.close()
