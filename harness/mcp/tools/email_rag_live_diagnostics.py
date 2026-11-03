"""메일 수집·MongoDB·Ollama RAG의 운영 연결을 비밀값 노출 없이 읽기 전용으로 점검합니다."""

from __future__ import annotations

import json
import os

from pymongo import MongoClient

from config import MONGO_DB, MONGO_TIMEOUT_MS, MONGO_URI
from common.common_function import normalize_required_text
from common.database import CommonDatabase
from FastAPI.LangGraph.Agent_Import_RAGs.LangGraph_email_RAG_Agent import (
    _create_embeddings,
    collect_mailbox_messages,
    load_mailbox_accounts,
    retrieve_internal_policy_documents,
)


def _failure(exc: Exception) -> dict[str, object]:
    """민감한 접속 문자열을 제외하고 예외 종류와 MongoDB 오류 코드만 남깁니다."""
    result: dict[str, object] = {"status": "failed", "error_type": type(exc).__name__}
    error_code = getattr(exc, "code", None)
    if error_code is not None:
        result["error_code"] = error_code
    return result


def check_mailboxes() -> dict:
    """설정된 계정을 검증하고 IMAP을 읽기 전용으로 조회하되 본문·주소·제목은 출력하지 않습니다."""
    if not os.getenv("EMAIL_ACCOUNTS_JSON", "").strip():
        return {"status": "missing_config", "configured": 0}
    try:
        accounts = load_mailbox_accounts()
        collected = collect_mailbox_messages(accounts, limit_per_account=1)
        return {
            "status": "ok" if not collected["errors"] else "partial",
            "configured": collected["configured_mailboxes"],
            "connected": collected["successful_mailboxes"],
            "message_count": collected["message_count"],
            "error_count": len(collected["errors"]),
        }
    except Exception as exc:
        return _failure(exc)


def check_ollama() -> dict:
    """실제 bge-m3 임베딩 한 건을 생성해 응답 개수와 벡터 차원만 확인합니다."""
    try:
        vectors = _create_embeddings(["SPS 이메일 RAG 운영 연결 점검"])
        return {
            "status": "ok",
            "model": os.getenv("OLLAMA_EMBEDDING_MODEL", "bge-m3"),
            "vectors": len(vectors),
            "dimensions": len(vectors[0]) if vectors else 0,
        }
    except Exception as exc:
        return _failure(exc)


def check_mongodb() -> dict:
    """루트 config.py 설정으로 애플리케이션 대상 Collection의 읽기 가능 여부를 확인합니다."""
    client = None
    common_db = None
    try:
        # 공통 DB 모듈의 설정 계약을 먼저 검증하고 실제 RAG와 같은 URI 우선순위를 사용합니다.
        common_db = CommonDatabase(
            database_role="HEALTH_COMPANION",
            connect_mariadb=False,
            connect_mongodb=False,
        )
        uri = normalize_required_text(
            str(
                os.getenv("MONGODB_URI")
                or os.getenv("HEALTH_COMPANION_MONGODB_URI")
                or MONGO_URI
                or ""
            ),
            "MONGO_URI",
        )
        database_name = normalize_required_text(
            str(os.getenv("MONGODB_DATABASE") or MONGO_DB or ""),
            "MONGO_DB",
        )
        collection_name = os.getenv("MONGODB_COLLECTION", "insurance_policy_terms_payload")
        client = MongoClient(uri, serverSelectionTimeoutMS=MONGO_TIMEOUT_MS)
        # 제한 계정은 admin.ping 권한이 없을 수 있어 실제 RAG와 동일한 Collection 읽기로 연결을 검증합니다.
        sample = client[database_name][collection_name].find_one(
            {"payload.embedding": {"$exists": True}},
            {"_id": 1},
        )
        return {
            "status": "ok",
            "database_configured": True,
            "collection": collection_name,
            "embedded_document_found": sample is not None,
        }
    except Exception as exc:
        return _failure(exc)
    finally:
        if client is not None:
            client.close()
        if common_db is not None:
            common_db.close()


def check_internal_rag() -> dict:
    """Ollama 임베딩과 MongoDB 검색을 연결해 실제 내부 RAG 결과 건수를 확인합니다."""
    try:
        results = retrieve_internal_policy_documents("실손의료보험 보장 범위", top_k=1)
        return {"status": "ok", "result_count": len(results)}
    except Exception as exc:
        return _failure(exc)


def main() -> None:
    """각 외부 시스템을 독립 점검해 한 장애가 다른 점검을 막지 않게 합니다."""
    result = {
        "mailboxes": check_mailboxes(),
        "ollama": check_ollama(),
        "mongodb": check_mongodb(),
        "internal_rag": check_internal_rag(),
        "data_changed": False,
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
