"""Register the MongoDB agent_long_term_memory collection in SPS Repository.

Run without --apply for a read-only preview. This never moves or deletes old
langgraph_agent_memory documents and creates no MariaDB payload table.
"""
from __future__ import annotations

import argparse
import json

from common.database import CommonDatabase, MariaMongoWriteService
from engine.identifier import IdentifierCoordinator
from engine.common.repository_schema_guard import assert_schema_documented

OBJECT_CODE = "MONGODB_AGENT_LONG_TERM_MEMORY"
ERD_CODE = "TE_STORY_PLATFORM_SP_RP_ERD"
PROGRAM_ID = "REGISTER_AGENT_LONG_TERM_MEMORY"
ACTOR = "SYSTEM"
CLIENT_IP = "127.0.0.1"
FIELDS = (
    ("_id", "MongoDB 문서 식별자", "VARCHAR", 64, "N"),
    ("subject_id", "사용자 식별자", "VARCHAR", 99, "N"),
    ("domain_code", "기억의 도메인", "VARCHAR", 99, "N"),
    ("program_id", "기억을 저장한 프로그램", "VARCHAR", 99, "N"),
    ("thread_id", "대화 식별자", "VARCHAR", 99, "N"),
    ("request_id", "요청 식별자", "VARCHAR", 99, "N"),
    ("query", "사용자의 질문", "TEXT", None, "N"),
    ("response", "완료된 답변", "TEXT", None, "N"),
    ("token_usage", "토큰 사용량", "JSON", None, "Y"),
    ("source_context", "근거와 출처가 있을 때의 문맥", "JSON", None, "Y"),
    ("created_dt", "문서 작성 시각", "DATETIME", None, "N"),
    ("created_by", "작성자 식별자", "VARCHAR", 99, "N"),
    ("client_ip", "클라이언트 주소", "VARCHAR", 99, "N"),
)


def _id(database: CommonDatabase, object_code: str, table: str, column: str) -> str:
    """Reserve an Identifier in its own transaction before any business commit.

    The Repository write may use another MariaDB connection. Identifier gaps
    after a later failure are intentional: a committed ID is never reused.
    """
    sequence_database = CommonDatabase(database_role=database.database_role)
    try:
        coordinator = IdentifierCoordinator(sequence_database)
        request = dict(coordinator.identifier_engine.load_object_metadata(object_code))
        request.update(
            created_by=ACTOR, updated_by=ACTOR, client_ip=CLIENT_IP, program_id=PROGRAM_ID,
        )
        row = sequence_database.fetch_one(
            """SELECT character_maximum_length AS maximum_length
               FROM information_schema.columns
               WHERE table_schema = %s AND table_name = %s AND column_name = %s""",
            (sequence_database.database_name, table, column),
        )
        if not row or not row.get("maximum_length"):
            raise RuntimeError(f"Identifier target missing: {table}.{column}")
        prepared = coordinator.prepare(request=request)
        coordinator.acquire(prepared)
        try:
            sequence_database.begin()
            try:
                identifier = coordinator.resolve(
                    request=request, prepared=prepared,
                    maximum_length=int(row["maximum_length"]),
                ).identifier
                sequence_database.commit()
                return identifier
            except Exception:
                sequence_database.rollback()
                raise
        finally:
            coordinator.release(prepared)
    finally:
        sequence_database.close()


def _schema_check(database: CommonDatabase) -> dict[str, int]:
    return assert_schema_documented(
        database, database.database_name,
        ("sp_object", "sp_erd", "sp_entity", "sp_attribute",
         "sp_object_lifecycle", "sp_execution_history", "sp_object_execution_link"),
    )


def register(*, apply: bool = False) -> dict[str, object]:
    repository = CommonDatabase(database_role="STORY")
    try:
        schema = _schema_check(repository)
        erd = repository.fetch_one(
            """SELECT erd_id, business_code, domain_code FROM sp_erd
               WHERE erd_code = %s AND enabled_yn = 'Y' AND deleted_dt IS NULL""",
            (ERD_CODE,),
        )
        if not erd:
            raise RuntimeError(f"Register ERD first: {ERD_CODE}")
        collection = repository.fetch_one(
            "SELECT object_id, object_name, deleted_dt FROM sp_object WHERE object_code = %s",
            (OBJECT_CODE,),
        )
        if collection and collection["deleted_dt"] is not None:
            raise RuntimeError("The collection Object is deleted; manual review is required")
        if collection and collection["object_name"] != "MongoDB.agent_long_term_memory":
            raise RuntimeError("Collection Object code belongs to another collection")
        result: dict[str, object] = {
            "applied": False, "object_code": OBJECT_CODE, "erd_id": erd["erd_id"],
            "existing_object_id": collection["object_id"] if collection else None,
            "attribute_names": [field[0] for field in FIELDS],
            "schema_column_counts": schema,
        }
        if not apply:
            return result

        mongodb = CommonDatabase(database_role="STORY", connect_mariadb=False, connect_mongodb=True)
        try:
            if "agent_long_term_memory" not in mongodb.list_collection_names():
                raise RuntimeError("Create/provision MongoDB agent_long_term_memory collection first")
            with MariaMongoWriteService(repository, mongodb) as writer:
                if collection:
                    object_id = collection["object_id"]
                else:
                    parent = repository.fetch_one(
                        """SELECT object_id FROM sp_object WHERE object_code = 'MDB'
                           AND active_yn = 'Y' AND deleted_dt IS NULL"""
                    )
                    kind = repository.fetch_one(
                        """SELECT object_type_code, object_level, identifier_target_code,
                                  sequence_scope_code, sequence_length, target_identifier_field
                           FROM sp_object WHERE object_code = 'MCO'
                             AND active_yn = 'Y' AND deleted_dt IS NULL"""
                    )
                    if not parent or not kind:
                        raise RuntimeError("Registered MongoDB MDB/MCO Object metadata is required")
                    object_id = _id(repository, "MCO", "sp_object", "object_id")
                    writer.execute_verified_mariadb(
                        """INSERT INTO sp_object
                           (object_id, object_code, object_name, business_code, domain_code,
                            object_type_code, object_description, parent_object_id, object_level,
                            identifier_target_code, sequence_scope_code, sequence_length,
                            target_identifier_field, created_by, client_ip, program_id)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (object_id, OBJECT_CODE, "MongoDB.agent_long_term_memory",
                         erd["business_code"], erd["domain_code"], kind["object_type_code"],
                         "사용자 대화의 장기 기억을 담는 MongoDB Collection Object.",
                         parent["object_id"], kind["object_level"], kind["identifier_target_code"],
                         kind["sequence_scope_code"], kind["sequence_length"],
                         kind["target_identifier_field"], ACTOR, CLIENT_IP, PROGRAM_ID),
                        expected_affected_rows=1,
                    )

                entity = repository.fetch_one(
                    """SELECT entity_id FROM sp_entity
                       WHERE object_id = %s AND erd_id = %s AND deleted_dt IS NULL""",
                    (object_id, erd["erd_id"]),
                )
                if entity:
                    entity_id = entity["entity_id"]
                else:
                    entity_id = _id(repository, "ENTITY", "sp_entity", "entity_id")
                    writer.execute_verified_mariadb(
                        """INSERT INTO sp_entity
                           (entity_id, erd_id, object_id, entity_name,
                            business_code, domain_code, entity_comment, entity_type_code,
                            created_by, client_ip, program_id)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (entity_id, erd["erd_id"], object_id, "agent_long_term_memory",
                         erd["business_code"], erd["domain_code"],
                         "MongoDB에 저장하는 사용자별 장기 기억 문서.", "MASTER",
                         ACTOR, CLIENT_IP, PROGRAM_ID), expected_affected_rows=1,
                    )

                for position, (name, comment, data_type, length, nullable) in enumerate(FIELDS, 1):
                    existing = repository.fetch_one(
                        """SELECT attribute_id FROM sp_attribute
                           WHERE object_id = %s AND column_name = %s AND deleted_dt IS NULL""",
                        (object_id, name),
                    )
                    if existing:
                        continue
                    writer.execute_verified_mariadb(
                        """INSERT INTO sp_attribute
                           (attribute_id, object_id, entity_id, attribute_name,
                            attribute_name_ko, attribute_name_en, column_name,
                            data_type, length_no, nullable_yn, primary_key_yn,
                            unique_yn, attribute_comment, sort_no, created_by, client_ip, program_id)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (_id(repository, "ATTRIBUTE", "sp_attribute", "attribute_id"),
                         object_id, entity_id, name, comment, name, name, data_type, length,
                         nullable, "Y" if name == "_id" else "N", "Y" if name == "_id" else "N",
                         comment, position, ACTOR, CLIENT_IP, PROGRAM_ID),
                        expected_affected_rows=1,
                    )

                lifecycle = repository.fetch_one(
                    """SELECT object_lifecycle_id FROM sp_object_lifecycle
                       WHERE object_id = %s AND lifecycle_event_code = 'REGISTER'
                         AND deleted_dt IS NULL""",
                    (object_id,),
                )
                if not lifecycle:
                    lifecycle_id = _id(repository, "TE_STORY_PLATFORM_SP_OBJECT_LIFECYCLE",
                                       "sp_object_lifecycle", "object_lifecycle_id")
                    writer.execute_verified_mariadb(
                        """INSERT INTO sp_object_lifecycle
                           (object_lifecycle_id, object_id, lifecycle_status_code,
                            lifecycle_event_code, lifecycle_reason, created_by, client_ip, program_id)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        (lifecycle_id, object_id, "REGISTERED", "REGISTER",
                         "MongoDB 장기기억 컬렉션 Repository 등록.",
                         ACTOR, CLIENT_IP, PROGRAM_ID), expected_affected_rows=1,
                    )
                    writer.execute_verified_mariadb(
                        "UPDATE sp_object SET lifecycle_id = %s WHERE object_id = %s",
                        (lifecycle_id, object_id), expected_affected_rows=1,
                    )

                history = repository.fetch_one(
                    """SELECT execution_history_id FROM sp_execution_history
                       WHERE object_id = %s AND program_id = %s AND deleted_dt IS NULL""",
                    (object_id, PROGRAM_ID),
                )
                if not history:
                    history_id = _id(repository, "EXECUTION_HISTORY",
                                     "sp_execution_history", "execution_history_id")
                    writer.execute_verified_mariadb(
                        """INSERT INTO sp_execution_history
                           (execution_history_id, trace_id, engine_code, object_code,
                            object_id, generated_identifier, repository_status_code,
                            mongodb_status_code, execution_status_code, history_status_code,
                            created_by, program_id, client_ip)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (history_id, history_id, "OBJECT_RUNTIME", OBJECT_CODE, object_id,
                         object_id, "SUCCESS", "READY", "SUCCESS", "SAVED",
                         ACTOR, PROGRAM_ID, CLIENT_IP), expected_affected_rows=1,
                    )
            result.update(applied=True, object_id=object_id, entity_id=entity_id)
            return result
        finally:
            mongodb.close()
    finally:
        repository.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(register(apply=args.apply), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
