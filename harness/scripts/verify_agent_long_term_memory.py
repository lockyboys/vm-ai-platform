"""Read-only evidence for the registered agent_long_term_memory workflow."""
from __future__ import annotations

import json

from common.database import CommonDatabase
from harness.scripts.register_agent_long_term_memory import OBJECT_CODE, ERD_CODE, FIELDS


def verify() -> dict[str, object]:
    repository = CommonDatabase(database_role="STORY")
    mongodb = CommonDatabase(database_role="STORY", connect_mariadb=False, connect_mongodb=True)
    try:
        object_row = repository.fetch_one(
            """SELECT object_id, lifecycle_id FROM sp_object
               WHERE object_code = %s AND active_yn = 'Y' AND deleted_dt IS NULL""",
            (OBJECT_CODE,),
        )
        erd = repository.fetch_one(
            """SELECT erd_id FROM sp_erd WHERE erd_code = %s
               AND enabled_yn = 'Y' AND deleted_dt IS NULL""",
            (ERD_CODE,),
        )
        collection = mongodb.get_collection("agent_long_term_memory")
        document_count = collection.count_documents({})
        output: dict[str, object] = {
            "object_id": object_row["object_id"] if object_row else None,
            "erd_id": erd["erd_id"] if erd else None,
            "mongodb_document_count": document_count,
            "registration_complete_yn": "N",
            "live_write_verified_yn": "N",
        }
        if not object_row or not erd:
            return output
        object_id = object_row["object_id"]
        def count(sql: str, params: tuple) -> int:
            return int(repository.fetch_one(sql, params)["count_value"])
        entity_count = count(
            """SELECT COUNT(*) AS count_value FROM sp_entity
               WHERE object_id = %s AND erd_id = %s AND deleted_dt IS NULL""",
            (object_id, erd["erd_id"]),
        )
        attribute_count = count(
            """SELECT COUNT(DISTINCT column_name) AS count_value FROM sp_attribute
               WHERE object_id = %s AND deleted_dt IS NULL""",
            (object_id,),
        )
        lifecycle_count = count(
            """SELECT COUNT(*) AS count_value FROM sp_object_lifecycle
               WHERE object_id = %s AND lifecycle_event_code = 'REGISTER'
                 AND deleted_dt IS NULL""",
            (object_id,),
        )
        registration_history_count = count(
            """SELECT COUNT(*) AS count_value FROM sp_execution_history
               WHERE object_id = %s AND program_id = 'REGISTER_AGENT_LONG_TERM_MEMORY'
                 AND deleted_dt IS NULL""",
            (object_id,),
        )
        runtime_history_count = count(
            """SELECT COUNT(*) AS count_value FROM sp_execution_history
               WHERE object_id = %s AND program_id = 'LANGGRAPH_LONG_TERM_MEMORY_AGENT'
                 AND execution_status_code = 'SUCCESS' AND history_status_code = 'SAVED'
                 AND deleted_dt IS NULL""",
            (object_id,),
        )
        link_count = count(
            """SELECT COUNT(*) AS count_value FROM sp_object_execution_link
               WHERE object_id = %s AND mongodb_collection_id = %s
                 AND deleted_dt IS NULL""",
            (object_id, object_id),
        )
        linked_document_count = 0
        for document in collection.find({}, {"_id": 1}):
            matched = repository.fetch_one(
                """SELECT history.execution_history_id
                   FROM sp_execution_history AS history
                   INNER JOIN sp_object_execution_link AS link
                     ON link.object_attempt_id = history.execution_history_id
                   WHERE history.generated_identifier = %s AND history.object_id = %s
                     AND history.execution_status_code = 'SUCCESS'
                     AND history.history_status_code = 'SAVED'
                     AND link.object_id = %s AND link.mongodb_collection_id = %s
                     AND history.deleted_dt IS NULL AND link.deleted_dt IS NULL
                   LIMIT 1""",
                (str(document["_id"]), object_id, object_id, object_id),
            )
            if matched:
                linked_document_count += 1
        output.update(entity_count=entity_count, attribute_count=attribute_count,
                      expected_attribute_count=len(FIELDS), lifecycle_count=lifecycle_count,
                      registration_history_count=registration_history_count,
                      runtime_history_count=runtime_history_count, execution_link_count=link_count,
                      linked_document_count=linked_document_count)
        output["registration_complete_yn"] = (
            "Y" if entity_count >= 1 and attribute_count >= len(FIELDS)
                   and lifecycle_count >= 1 and registration_history_count >= 1
                   and object_row["lifecycle_id"] else "N"
        )
        output["live_write_verified_yn"] = (
            "Y" if document_count > 0 and linked_document_count == document_count
                   and runtime_history_count >= document_count
                   and link_count >= document_count else "N"
        )
        return output
    finally:
        repository.close()
        mongodb.close()


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False, indent=2))
