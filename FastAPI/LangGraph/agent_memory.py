"""
File Story: CommonDatabase와 MariaMongoWriteService를 사용하여 에이전트의 장기 기억(Long-term Memory)을 안전하게 영구 저장 및 회상(Recall)한다.
Change History:
    - 20260909 | CODEX | 완료된 대화 저장, 재시작 복원, 사용자 격리 기능 최초 추가.
    - 20260910 | SENIOR_REVIEWER | JSON 직렬화 잘림 버그 정밀 수정, DB information_schema 캐싱 버그 원천 해결, Context Manager 자원 해제 강화.
    - 20260911 | VERIFIER | 동시성 쓰기 경쟁 상태(Race Condition) 멱등 Fallback, 회상(Recall) 최신 문맥 우선 보존, Hot Path 메타데이터 캐싱 및 스레드 락 적용.
"""

import copy
import hashlib
import json
import logging
import os
import re
import threading
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 공통 모듈 및 데이터베이스 백엔드 모듈 임포트
from common.common_function import normalize_required_text
from common.database import CommonDatabase, MariaMongoWriteService, reserve_document_master_id
from engine.identifier import IdentifierCoordinator
from engine.common.repository_schema_guard import assert_schema_documented

logger = logging.getLogger(__name__)

# 시스템 상수 정의
MEMORY_OBJECT_CODE = "MONGODB_AGENT_LONG_TERM_MEMORY"
MEMORY_PROGRAM_ID = "LANGGRAPH_LONG_TERM_MEMORY_AGENT"

# MariaDB information_schema 반복 조회를 방지하기 위한 전역 컬럼 메타데이터 캐시 및 스레드 락
_COLUMN_LENGTH_CACHE: Dict[Tuple[str, str, str], int] = {}
_CACHE_LOCK = threading.Lock()

# sp_object 및 스키마 검증 정적 캐시 (Hot Path 네트워크 RTT 최적화)
_REGISTERED_OBJECTS_CACHE: Dict[str, Dict[str, Any]] = {}
_VERIFIED_SCHEMAS = set()

# 설정 파일 메모리 캐시
_SETTINGS_CACHE: Optional[Dict[str, Any]] = None
_SETTINGS_LOCK = threading.Lock()


def _resolve_column_length(database: CommonDatabase, table_name: str = "sp_execution_history", column_name: str = "execution_history_id") -> int:
    """
    MariaDB 메타데이터 테이블(information_schema.columns) 조회를 캐싱하여 Hot Path 상의 SQL RTT 및 DB Lock 오버헤드를 제거한다.
    Double-Checked Locking을 통해 멀티스레드 환경의 안전성을 보장한다.

    :param database: MariaDB 데이터베이스 커넥션 객체
    :param table_name: 검증 대상 테이블명
    :param column_name: 최대 길이를 확인할 컬럼명
    :return: 컬럼 최대 허용 문자 길이 (int)
    """
    cache_key = (database.database_name, table_name, column_name)

    if cache_key in _COLUMN_LENGTH_CACHE:
        return _COLUMN_LENGTH_CACHE[cache_key]

    with _CACHE_LOCK:
        if cache_key in _COLUMN_LENGTH_CACHE:
            return _COLUMN_LENGTH_CACHE[cache_key]

        column = database.fetch_one(
            """SELECT character_maximum_length FROM information_schema.columns
               WHERE table_schema = %s AND table_name = %s AND column_name = %s""",
            (database.database_name, table_name, column_name),
        )

        if not column or not column.get("character_maximum_length"):
            raise RuntimeError(f"Database schema metadata is missing for {table_name}.{column_name}")

        length = int(column["character_maximum_length"])
        _COLUMN_LENGTH_CACHE[cache_key] = length
        return length


def _registered_objects_batch(database: CommonDatabase, object_codes: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    저장에 필요한 다수의 sp_object 메타데이터를 캐시에서 조회하고, 누락된 항목만 단일 SQL로 배치 조회한다.

    :param database: MariaDB 데이터베이스 커넥션 객체
    :param object_codes: 조회 대상 오브젝트 코드 리스트 (예: ['EXECUTION_HISTORY', 'MDB', 'MCM'])
    :return: {object_code: metadata_dict} 구조의 딕셔너리
    """
    if not object_codes:
        return {}

    missing_codes = [code for code in object_codes if code not in _REGISTERED_OBJECTS_CACHE]

    if missing_codes:
        with _CACHE_LOCK:
            truly_missing = [code for code in missing_codes if code not in _REGISTERED_OBJECTS_CACHE]
            if truly_missing:
                format_strings = ', '.join(['%s'] * len(truly_missing))
                rows = database.fetch_all(
                    f"""SELECT object_id, object_code, object_name, business_code, domain_code,
                              object_level, identifier_target_code, sequence_scope_code,
                              sequence_length, target_identifier_field
                       FROM sp_object
                       WHERE object_code IN ({format_strings}) AND active_yn = 'Y'
                         AND status_code = 'ACTIVE' AND deleted_dt IS NULL""",
                    tuple(truly_missing),
                )

                for row in rows:
                    _REGISTERED_OBJECTS_CACHE[row["object_code"]] = row

    result = {}
    for code in object_codes:
        if code not in _REGISTERED_OBJECTS_CACHE:
            raise RuntimeError(f"Register sp_object before saving memory: {code}")
        result[code] = _REGISTERED_OBJECTS_CACHE[code]

    return result


def _next_execution_id(database: CommonDatabase, actor: str, client_ip: str) -> str:
    """
    IdentifierCoordinator를 사용하여 원자적이고 동시성이 보장된 실행 이력 ID(Execution History ID)를 발급받는다.

    :param database: MariaDB 커넥션 객체
    :param actor: 식별자 생성을 요청하는 주체 (subject_id)
    :param client_ip: 접속 클라이언트 IP
    :return: 생성된 고유 식별자 문자열
    """
    objects = _registered_objects_batch(database, ["EXECUTION_HISTORY"])
    metadata = objects["EXECUTION_HISTORY"]

    coordinator = IdentifierCoordinator(database)

    request, prepared = coordinator.prepare_registered_object(
        object_metadata=metadata,
        created_by=actor,
        updated_by=actor,
        client_ip=client_ip,
        program_id=MEMORY_PROGRAM_ID,
    )

    max_length = _resolve_column_length(database)

    coordinator.acquire(prepared)
    try:
        database.begin()
        try:
            identifier = coordinator.resolve(
                request=request,
                prepared=prepared,
                maximum_length=max_length,
            ).identifier
            database.commit()
            return identifier
        except Exception:
            database.rollback()
            raise
    finally:
        coordinator.release(prepared)


def load_settings() -> Dict[str, Any]:
    """
    환경 변수 및 설정 파일(agent_memory_settings.json)로부터 에이전트 동작 옵션을 로드 및 검증한다.
    반복 I/O를 방지하기 위해 메모리 캐싱을 수행한다.

    :return: 설정값 딕셔너리
    """
    global _SETTINGS_CACHE
    if _SETTINGS_CACHE is not None:
        return copy.deepcopy(_SETTINGS_CACHE)

    with _SETTINGS_LOCK:
        if _SETTINGS_CACHE is not None:
            return copy.deepcopy(_SETTINGS_CACHE)

        default_path = Path(__file__).with_name("agent_memory_settings.json")
        path = Path(os.getenv("AGENT_MEMORY_SETTINGS", str(default_path)))

        if not path.is_file():
            raise FileNotFoundError(f"Agent memory settings file not found: {path.resolve()}")

        try:
            settings = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON format in settings file '{path}': {exc}") from exc

        settings["collection_name"] = os.getenv("AGENT_MEMORY_COLLECTION", settings.get("collection_name", "agent_long_term_memory"))
        for name in ("database_role", "collection_name", "domain_code"):
            settings[name] = normalize_required_text(settings.get(name), name)

        settings["domain_code"] = os.getenv("AGENT_DOMAIN", settings["domain_code"])

        for name in ("history_turn_limit", "recall_limit", "recall_char_limit"):
            if not isinstance(settings.get(name), int) or settings[name] <= 0:
                raise ValueError(f"{name} must be a positive integer")

        _SETTINGS_CACHE = settings
        return copy.deepcopy(_SETTINGS_CACHE)


class PersistentMemory:
    """
    LangGraph 에이전트의 장기 기억(Long-term Memory)을 안전하게 관리하는 영구 저장소 클래스.

    - Dual-Write (MariaDB + MongoDB) 트랜잭션 안전성 보장
    - 사용자/도메인 단위 데이터 격리
    - Context Manager Pattern (__enter__, __exit__) 기반 완전한 커넥션 생명주기 관리
    """

    def __init__(self, settings: Optional[Dict[str, Any]] = None, database: Optional[CommonDatabase] = None):
        """
        PersistentMemory 객체를 초기화한다.

        :param settings: 에이전트 설정 딕셔너리 (None일 경우 외부 설정 파일 로드)
        :param database: 주입받을 CommonDatabase 커넥션 객체 (None일 경우 내부에서 자체 생성)
        """
        self.settings = settings or load_settings()

        if database is not None:
            self.database = database
            self._owned_database = False
        else:
            self.database = CommonDatabase(
                database_role=self.settings["database_role"],
                connect_mariadb=False,
                connect_mongodb=True,
            )
            self._owned_database = True

        self.collection = self.settings["collection_name"]
        self.domain = self.settings["domain_code"]

    def __enter__(self):
        """Context Manager 진입"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context Manager 종료 시 자원 해제 보장"""
        self.close()

    def _ensure_active(self) -> None:
        """데이터베이스 연결 객체 유효성을 검증한다."""
        if self.database is None:
            raise RuntimeError("PersistentMemory database connection is closed or uninitialized")

    def scope(self, subject_id: str) -> Dict[str, str]:
        """
        사용자 식별자 및 도메인 격리를 위한 기본 몽고DB 조회 스코프를 생성한다.
        """
        return {
            "subject_id": normalize_required_text(subject_id, "subject_id"),
            "domain_code": self.domain,
            "program_id": MEMORY_PROGRAM_ID,
        }

    def request_filter(self, subject_id: str, thread_id: str, request_id: str) -> Dict[str, Any]:
        """
        요청 고유 식별자(_id) 해시를 생성하고 조회 필터를 구성한다.
        """
        scope = self.scope(subject_id)
        values = [
            scope["subject_id"],
            self.domain,
            normalize_required_text(thread_id, "thread_id"),
            normalize_required_text(request_id, "request_id"),
        ]
        doc_id = hashlib.sha256(json.dumps(values).encode("utf-8")).hexdigest()
        return {"_id": doc_id, **scope}

    def completed(self, subject_id: str, thread_id: str, request_id: str) -> Optional[Dict[str, Any]]:
        """
        특정 request_id에 대한 처리가 이미 완료되었는지 몽고DB에서 조회한다 (멱등성 확인).
        """
        self._ensure_active()
        return self.database.find_one(
            self.collection, self.request_filter(subject_id, thread_id, request_id)
        )

    def history(self, subject_id: str, thread_id: str) -> List[Tuple[str, str]]:
        """
        현재 대화 스레드의 최근 대화 기록(Turn)을 반환한다.
        손상 데이터로 인한 에러 방지를 위해 방어적 키 접근을 수행한다.
        """
        self._ensure_active()
        rows = self.database.find(
            self.collection,
            {**self.scope(subject_id), "thread_id": normalize_required_text(thread_id, "thread_id")},
            limit=self.settings["history_turn_limit"],
            sort=[("created_dt", -1), ("_id", -1)],
        ) or []

        messages = []
        for row in reversed(rows):
            query = row.get("query")
            response = row.get("response")
            if query is not None and response is not None:
                messages.extend([("user", query), ("assistant", response)])
        return messages

    def recall(self, subject_id: str, thread_id: str, query: str) -> str:
        """
        현재 대화 스레드를 제외한 과거 대화 기록 중, 검색어와 연관된 기억을 회상(Recall)한다.
        최신 기억을 우선 유지하며, JSON 직렬화 용량 제한을 준수한다.

        :param subject_id: 사용자 ID
        :param thread_id: 현재 진행 중인 대화 스레드 ID (조회 대상에서 제외)
        :param query: 관련 기억을 검색할 쿼리 문자열
        :return: 유효한 JSON 포맷의 회상 데이터 문자열
        """
        self._ensure_active()
        scope = {**self.scope(subject_id), "thread_id": {"$ne": thread_id}}

        terms = list(dict.fromkeys(re.findall(r"[\w가-힣]{2,}", query)))[:12]
        search = dict(scope)
        if terms:
            pattern = "|".join(re.escape(term) for term in terms)
            search["$or"] = [
                {"query": {"$regex": pattern, "$options": "i"}},
                {"response": {"$regex": pattern, "$options": "i"}},
            ]

        rows = self.database.find(
            self.collection,
            search,
            limit=self.settings["recall_limit"],
            sort=[("created_dt", -1), ("_id", -1)],
        ) or []

        if not rows and terms:
            rows = self.database.find(
                self.collection,
                scope,
                limit=self.settings["recall_limit"],
                sort=[("created_dt", -1), ("_id", -1)],
            ) or []

        collected = []
        limit = self.settings["recall_char_limit"]

        # 최신 순서(rows)로 먼저 글자 수 한도 내에서 수집하여 중요 기억 탈락 방지
        for row in rows:
            candidate_item = {
                "query": row.get("query", ""),
                "response": row.get("response", ""),
            }
            test_list = collected + [candidate_item]
            test_json = json.dumps(test_list, ensure_ascii=False)

            if len(test_json) > limit:
                break

            collected.append(candidate_item)

        # 최종 프롬프트 전달을 위해 시간순(오래된 순 -> 최신 순)으로 재배열
        results = list(reversed(collected))
        return json.dumps(results, ensure_ascii=False)

    def save(self, subject_id: str, thread_id: str, request_id: str, query: str, result: Dict[str, Any], client_ip: str) -> Dict[str, Any]:
        """
        에이전트의 수행 결과를 MariaDB 트랜잭션 및 MongoDB 문서로 원자적 저장(Dual Write)한다.
        동시 요청 경합 시 멱등성을 보장한다.

        :param subject_id: 사용자 식별자
        :param thread_id: 대화 스레드 ID
        :param request_id: 요청 고유 ID
        :param query: 사용자 질문 내용
        :param result: 에이전트 응답 및 토큰 사용량 포함 결과 딕셔너리
        :param client_ip: 요청 클라이언트 IP
        :return: 저장 결과 딕셔너리
        """
        self._ensure_active()
        if self.collection != "agent_long_term_memory" or self.settings["database_role"].upper() != "STORY":
            raise RuntimeError("Agent memory requires the registered STORY/agent_long_term_memory collection")

        if not isinstance(result, dict) or "response" not in result:
            raise ValueError("Parameter 'result' must be a dictionary containing a 'response' key")

        selector = self.request_filter(subject_id, thread_id, request_id)
        already_saved = self.completed(subject_id, thread_id, request_id)

        if already_saved is not None:
            if (already_saved.get("query") != query or
                    already_saved.get("source_context") != result.get("source_context")):
                raise ValueError("request_id already belongs to another query")
            return {
                "status": "success",
                "response": already_saved.get("response"),
                "token_usage": already_saved.get("token_usage", {}),
                "request_id": request_id,
                "memory_saved": True,
            }

        document = {
            **selector,
            "thread_id": thread_id,
            "request_id": request_id,
            "query": query,
            "response": result["response"],
            "token_usage": result.get("token_usage", {}),
            **({"source_context": result["source_context"]} if "source_context" in result else {}),
            "created_dt": datetime.now(ZoneInfo("Asia/Seoul")),
            "created_by": subject_id,
            "client_ip": normalize_required_text(client_ip, "client_ip"),
        }

        repository = CommonDatabase(database_role="STORY", connect_mongodb=False)
        try:
            # 1. 스키마 문서화 여부 프로세스 1회 검증
            schema_key = (repository.database_name, "sp_object", "sp_execution_history", "sp_object_execution_link")
            if schema_key not in _VERIFIED_SCHEMAS:
                with _CACHE_LOCK:
                    if schema_key not in _VERIFIED_SCHEMAS:
                        assert_schema_documented(
                            repository, repository.database_name,
                            ("sp_object", "sp_execution_history", "sp_object_execution_link"),
                        )
                        _VERIFIED_SCHEMAS.add(schema_key)

            # 2. 관련 sp_object 메타데이터 배치 조회 (캐시 활용)
            objects = _registered_objects_batch(
                repository, [MEMORY_OBJECT_CODE, "MDB", "MCM"]
            )
            memory_object = objects[MEMORY_OBJECT_CODE]
            database_object = objects["MDB"]
            master_object = objects["MCM"]

            # 3. Execution History ID 생성
            history_id = _next_execution_id(repository, subject_id, document["client_ip"])
            document_master_id = reserve_document_master_id(
                repository, master_object, subject_id, document["client_ip"], MEMORY_PROGRAM_ID,
            )
            document.update({
                "mongodb_database_id": database_object["object_id"],
                "mongodb_collection_id": memory_object["object_id"],
                "mongodb_document_master_id": document_master_id,
            })

            # 4. MariaDB + MongoDB 원자적 쓰기 서비스 실행 (동시성 경합 시 멱등 Fallback)
            try:
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
                        collection_name=self.collection,
                        document=document,
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
                         document_master_id, subject_id, document["client_ip"],
                         MEMORY_PROGRAM_ID),
                        expected_affected_rows=1,
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
            except Exception as write_err:
                logger.warning("Collision or error during Dual-Write: %s. Performing idempotency fallback check.", write_err)
                stored_on_race = self.completed(subject_id, thread_id, request_id)
                if stored_on_race is not None:
                    if (stored_on_race.get("query") == query and
                            stored_on_race.get("source_context") == result.get("source_context")):
                        return {
                            "status": "success",
                            "response": stored_on_race.get("response"),
                            "token_usage": stored_on_race.get("token_usage", {}),
                            "request_id": request_id,
                            "memory_saved": True,
                        }
                raise write_err
        finally:
            repository.close()

        stored = self.completed(subject_id, thread_id, request_id)
        if stored is None:
            raise RuntimeError("Memory read-back failed")
        if (stored.get("query") != query or
                stored.get("source_context") != result.get("source_context")):
            raise ValueError("request_id already belongs to another query")

        return {
            "status": "success",
            "response": stored.get("response"),
            "token_usage": stored.get("token_usage", {}),
            "request_id": request_id,
            "memory_saved": True,
        }

    def close(self) -> None:
        """
        PersistentMemory가 생성한 내부 데이터베이스 접속 자원을 안전하게 종료한다.
        """
        if self._owned_database and self.database is not None:
            try:
                self.database.close()
            finally:
                self.database = None