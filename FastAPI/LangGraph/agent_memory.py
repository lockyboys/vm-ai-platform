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
from common.database import CommonDatabase


def load_settings():
    path = Path(os.getenv("AGENT_MEMORY_SETTINGS", str(Path(__file__).with_name("agent_memory_settings.json"))))
    settings = json.loads(path.read_text(encoding="utf-8"))
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
        selector = self.request_filter(subject_id, thread_id, request_id)
        document = {
            **selector, "thread_id": thread_id, "request_id": request_id,
            "query": query, "response": result["response"],
            "token_usage": result.get("token_usage", {}),
            **({"source_context": result["source_context"]} if "source_context" in result else {}),
            "created_dt": datetime.now(timezone.utc), "created_by": subject_id,
            "client_ip": normalize_required_text(client_ip, "client_ip"),
        }
        outcome = self.database.update_one(
            self.collection, selector, {"$setOnInsert": document}, upsert=True
        )
        if not outcome.acknowledged:
            raise RuntimeError("Memory write was not acknowledged")
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
