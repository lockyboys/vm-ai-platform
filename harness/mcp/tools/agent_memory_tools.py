"""MCP runtime tool for the registered long-term memory dual-write path."""
from __future__ import annotations

import json
from typing import Any

from common.common_function import normalize_required_text
from FastAPI.LangGraph.agent_memory import PersistentMemory, load_settings


def agent_long_term_memory_save(
    subject_id: str,
    thread_id: str,
    request_id: str,
    query: str,
    response: str,
    token_usage_json: str = "{}",
    source_context: str = "",
    client_ip: str = "127.0.0.1",
    apply: bool = False,
) -> str:
    """Dry-run or execute one approved STORY/agent_long_term_memory dual write.

    apply=False only validates the request and returns the execution plan.
    apply=True invokes PersistentMemory.save(), which uses IdentifierCoordinator
    and MariaMongoWriteService for MariaDB history/link plus MongoDB storage.
    """
    subject_id = normalize_required_text(subject_id, "subject_id")
    thread_id = normalize_required_text(thread_id, "thread_id")
    request_id = normalize_required_text(request_id, "request_id")
    query = normalize_required_text(query, "query")
    response = normalize_required_text(response, "response")
    try:
        token_usage = json.loads(token_usage_json or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("token_usage_json must be valid JSON") from exc
    if not isinstance(token_usage, dict):
        raise ValueError("token_usage_json must decode to an object")
    plan = {
        "collection": "agent_long_term_memory",
        "database_role": "STORY",
        "sequence": [
            "schema/comment validation",
            "IdentifierCoordinator execution history identifier",
            "MariaMongoWriteService: sp_execution_history",
            "MongoDB agent_long_term_memory",
            "MariaDB sp_object_execution_link",
            "history SUCCESS update and commit",
        ],
        "apply": apply,
        "request_id": request_id,
    }
    if not apply:
        return json.dumps(plan, ensure_ascii=False)
    settings = load_settings()
    settings["collection_name"] = "agent_long_term_memory"
    settings["database_role"] = "STORY"
    memory = PersistentMemory(settings=settings)
    result: dict[str, Any] = memory.save(
        subject_id=subject_id,
        thread_id=thread_id,
        request_id=request_id,
        query=query,
        result={"response": response, "token_usage": token_usage, **({"source_context": source_context} if source_context else {})},
        client_ip=client_ip,
    )
    return json.dumps({"status": "applied", "request_id": request_id, "memory_saved": result.get("memory_saved", True), "result": result}, ensure_ascii=False)
