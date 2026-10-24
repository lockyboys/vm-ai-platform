"""File Story: CommonDatabase로 사용자별 대화와 대화 간 기억을 영구 저장한다.
Change History: 20260909 | CODEX | 완료된 대화 저장, 재시작 복원, 사용자 격리 추가.
"""
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from common.common_function import normalize_required_text
from common.database import CommonDatabase, MariaMongoWriteService
from engine.identifier import IdentifierCoordinator
from engine.common.repository_schema_guard import assert_schema_documented


MEMORY_OBJECT_CODE = "MONGODB_AGENT_LONG_TERM_MEMORY"
MEMORY_PROGRAM_ID = "LANGGRAPH_LONG_TERM_MEMORY_AGENT"


def _registered_object(database, object_code):
    """A memory write must reference an existing active Repository Object."""
    row = database.fetch_one(
        """SELECT object_id, object_code, object_name, business_code, domain_code,
                  object_level, identifier_target_code, sequence_scope_code,
                  sequence_length, target_identifier_field
           FROM sp_object
           WHERE object_code = %s AND active_yn = 'Y'
             AND status_code = 'ACTIVE' AND deleted_dt IS NULL""",
        (object_code,),
    )
    if row is None:
        raise RuntimeError(f"Register sp_object before saving memory: {object_code}")
    return row


def _next_execution_id(database, actor, client_ip):
    """Use the same IdentifierCoordinator as the rest of the SPS repository."""
    metadata = _registered_object(database, "EXECUTION_HISTORY")
    coordinator = IdentifierCoordinator(database)
    request, prepared = coordinator.prepare_registered_object(
        object_metadata=metadata, created_by=actor, updated_by=actor,
        client_ip=client_ip, program_id=MEMORY_PROGRAM_ID,
    )
    # EXECUTION_HISTORY is a logical Object, so read the real target column
    # length from sp_execution_history rather than parsing its display name.
    column = database.fetch_one(
        """SELECT character_maximum_length FROM information_schema.columns
           WHERE table_schema = %s AND table_name = %s AND column_name = %s""",
        (database.database_name, "sp_execution_history", "execution_history_id"),
    )
    if not column or not column.get("character_maximum_length"):
        raise RuntimeError("sp_execution_history.execution_history_id schema is missing")
    coordinator.acquire(prepared)
    try:
        database.begin()
        try:
            identifier = coordinator.resolve(
                request=request, prepared=prepared,
                maximum_length=int(column["character_maximum_length"]),
            ).identifier
            database.commit()
            return identifier
        except Exception:
            database.rollback()
            raise
    finally:
        coordinator.release(prepared)


def load_settings():
    path = Path(os.getenv("AGENT_MEMORY_SETTINGS", str(Path(__file__).with_name("agent_memory_settings.json"))))
    settings = json.loads(path.read_text(encoding="utf-8"))
    # The local JSON file is deployment-specific; the versioned default must
    # always route new writes to the registered collection.
    settings["collection_name"] = os.getenv("AGENT_MEMORY_COLLECTION", "agent_long_term_memory")
    for name in ("database_role", "collection_name", "domain_code"):
        settings[name] = normalize_required_text(settings.get(name), name)
    settings["domain_code"] = os.getenv("AGENT_DOMAIN", settings["domain_code"])
    for name in ("history_turn_limit", "recall_limit", "recall_char_limit"):
        if not isinstance(settings[name], int) or settings[name] <= 0:
            raise ValueError(name + " must be a positive integer")
    return settings


class PersistentMemory:
    """완료된 질문·답변을 개별 문서로 저장하여 동시 요청의 덮어쓰기를 방지한다."""

    def __init__(self, settings=None, database=None):
        self.settings = settings or load_settings()
        self.database = database if database is not None else CommonDatabase(
            database_role=self.settings["database_role"],
            connect_mariadb=False, connect_mongodb=True,
        )
        self.collection = self.settings["collection_name"]
        self.domain = self.settings["domain_code"]

    def scope(self, subject_id):
        return {
            "subject_id": normalize_required_text(subject_id, "subject_id"),
            "domain_code": self.domain,
            "program_id": "LANGGRAPH_LONG_TERM_MEMORY_AGENT",
        }

    def request_filter(self, subject_id, thread_id, request_id):
        scope = self.scope(subject_id)
        values = [scope["subject_id"], self.domain,
                  normalize_required_text(thread_id, "thread_id"),
                  normalize_required_text(request_id, "request_id")]
        # Mongo 내부 멱등성 키이며 SPS Object Identifier로 사용하지 않는다.
        return {"_id": hashlib.sha256(json.dumps(values).encode()).hexdigest(), **scope}

    def completed(self, subject_id, thread_id, request_id):
        return self.database.find_one(
            self.collection, self.request_filter(subject_id, thread_id, request_id)
        )

    def history(self, subject_id, thread_id):
        rows = self.database.find(
            self.collection,
            {**self.scope(subject_id), "thread_id": normalize_required_text(thread_id, "thread_id")},
            limit=self.settings["history_turn_limit"],
            sort=[("created_dt", -1), ("_id", -1)],
        )
        messages = []
        for row in reversed(rows):
            messages.extend([("user", row["query"]), ("assistant", row["response"])])
        return messages

    def recall(self, subject_id, thread_id, query):
        """다른 대화의 관련 기억을 조회하며 없으면 최근 기억을 사용한다."""
        scope = {**self.scope(subject_id), "thread_id": {"$ne": thread_id}}
        terms = list(dict.fromkeys(re.findall(r"[\w가-힣]{2,}", query)))[:12]
        search = dict(scope)
        if terms:
            pattern = "|".join(re.escape(term) for term in terms)
            search["$or"] = [{"query": {"$regex": pattern, "$options": "i"}},
                             {"response": {"$regex": pattern, "$options": "i"}}]
        rows = self.database.find(self.collection, search, limit=self.settings["recall_limit"],
                                  sort=[("created_dt", -1), ("_id", -1)])
        if not rows and terms:
            rows = self.database.find(self.collection, scope, limit=self.settings["recall_limit"],
                                      sort=[("created_dt", -1), ("_id", -1)])
        return json.dumps(
            [{"query": row["query"], "response": row["response"]} for row in reversed(rows)],
            ensure_ascii=False,
        )[:self.settings["recall_char_limit"]]

    def save(self, subject_id, thread_id, request_id, query, result, client_ip):
        if self.collection != "agent_long_term_memory" or self.settings["database_role"].upper() != "STORY":
            raise RuntimeError("Agent memory requires the registered STORY/agent_long_term_memory collection")
        selector = self.request_filter(subject_id, thread_id, request_id)
        already_saved = self.completed(subject_id, thread_id, request_id)
        if already_saved is not None:
            if (already_saved["query"] != query or
                    already_saved.get("source_context") != result.get("source_context")):
                raise ValueError("request_id already belongs to another query")
            return {"status": "success", "response": already_saved["response"],
                    "token_usage": already_saved.get("token_usage", {}),
                    "request_id": request_id, "memory_saved": True}
        document = {
            **selector, "thread_id": thread_id, "request_id": request_id,
            "query": query, "response": result["response"],
            "token_usage": result.get("token_usage", {}),
            **({"source_context": result["source_context"]} if "source_context" in result else {}),
            "created_dt": datetime.now(timezone.utc), "created_by": subject_id,
            "client_ip": normalize_required_text(client_ip, "client_ip"),
        }
        # The history and link share one MariaDB transaction. If a subsequent
        # statement or commit fails, MariaMongoWriteService removes this Mongo
        # document as compensation. The saved request ID is the idempotency key.
        repository = CommonDatabase(database_role="STORY", connect_mongodb=False)
        try:
            assert_schema_documented(
                repository, repository.database_name,
                ("sp_object", "sp_execution_history", "sp_object_execution_link"),
            )
            memory_object = _registered_object(repository, MEMORY_OBJECT_CODE)
            database_object = _registered_object(repository, "MDB")
            master_object = _registered_object(repository, "MCM")
            # Reserve and commit the SPS identifier before opening the
            # business transaction; release the named lock after that commit.
            history_id = _next_execution_id(repository, subject_id, document["client_ip"])
            with MariaMongoWriteService(repository, self.database) as writer:
                writer.execute_verified_mariadb(
                    """INSERT INTO sp_execution_history
                       (execution_history_id, trace_id, engine_code, object_code,
                        object_id, generated_identifier, repository_status_code,
                        mongodb_status_code, execution_status_code, history_status_code,
                        created_by, program_id, client_ip)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (history_id, history_id, "OBJECT_RUNTIME", memory_object["object_code"],
                     memory_object["object_id"], selector["_id"], "READY", "READY",
                     "RUNNING", "READY", subject_id, MEMORY_PROGRAM_ID, document["client_ip"]),
                    expected_affected_rows=1,
                )
                writer.insert_mongodb_document(
                    collection_name=self.collection, document=document,
                    compensation_filter={"_id": selector["_id"]},
                )
                writer.execute_verified_mariadb(
                    """INSERT INTO sp_object_execution_link
                       (object_attempt_id, object_id, target_object_id,
                        execution_link_type_code, mongodb_database_id,
                        mongodb_collection_id, mongodb_document_master_id,
                        created_by, client_ip, program_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (history_id, memory_object["object_id"], master_object["object_id"],
                     "MONGODB", database_object["object_id"], memory_object["object_id"],
                     master_object["object_id"], subject_id, document["client_ip"],
                     MEMORY_PROGRAM_ID), expected_affected_rows=1,
                )
                writer.execute_verified_mariadb(
                    """UPDATE sp_execution_history
                       SET repository_status_code = %s, mongodb_status_code = %s,
                           execution_status_code = %s, history_status_code = %s,
                           updated_by = %s, updated_dt = CURRENT_TIMESTAMP
                       WHERE execution_history_id = %s""",
                    ("SUCCESS", "SUCCESS", "SUCCESS", "SAVED", subject_id, history_id),
                    expected_affected_rows=1,
                )
        finally:
            repository.close()
        stored = self.completed(subject_id, thread_id, request_id)
        if stored is None:
            raise RuntimeError("Memory read-back failed")
        if (stored["query"] != query or
                stored.get("source_context") != result.get("source_context")):
            raise ValueError("request_id already belongs to another query")
        return {"status": "success", "response": stored["response"],
                "token_usage": stored.get("token_usage", {}), "request_id": request_id,
                "memory_saved": True}

    def close(self):
        self.database.close()
