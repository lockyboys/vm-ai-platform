"""
File Story: CommonDatabase와 MariaMongoWriteService를 사용하여 에이전트의 장기 기억(Long-term Memory)을 안전하게 영구 저장 및 회상(Recall)한다.
Change History:
    - 20260909 | CODEX | 완료된 대화 저장, 재시작 복원, 사용자 격리 기능 최초 추가.
    - 20260910 | SENIOR_REVIEWER | JSON 직렬화 잘림 버그 정밀 수정, DB information_schema 캐싱 버그 원천 해결, Context Manager 자원 해제 강화.
"""

import hashlib
import json
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

# 공통 모듈 및 데이터베이스 백엔드 모듈 임포트
from common.common_function import normalize_required_text
from common.database import CommonDatabase, MariaMongoWriteService
from engine.identifier import IdentifierCoordinator
from engine.common.repository_schema_guard import assert_schema_documented

# 시스템 상수 정의
MEMORY_OBJECT_CODE = "MONGODB_AGENT_LONG_TERM_MEMORY"
MEMORY_PROGRAM_ID = "LANGGRAPH_LONG_TERM_MEMORY_AGENT"

# MariaDB information_schema 반복 조회를 방지하기 위한 전역 컬럼 메타데이터 캐시 테이블
_COLUMN_LENGTH_CACHE = {}


def _resolve_column_length(database, table_name="sp_execution_history", column_name="execution_history_id"):
    """
    MariaDB 메타데이터 테이블(information_schema.columns) 조회를 캐싱하여 Hot Path 상의 SQL RTT 및 DB Lock 오버헤드를 제거한다.

    :param database: MariaDB 데이터베이스 커넥션 객체
    :param table_name: 검증 대상 테이블명
    :param column_name: 최대 길이를 확인할 컬럼명
    :return: 컬럼 최대 허용 문자 길이 (int)
    """
    cache_key = (database.database_name, table_name, column_name)

    # 캐시된 컬럼 길이가 존재할 경우 DB 조회 없이 즉시 반환 (Hot Path 최적화)
    if cache_key in _COLUMN_LENGTH_CACHE:
        return _COLUMN_LENGTH_CACHE[cache_key]

    # 캐시 미스 시 정보 조회 수행
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


def _registered_objects_batch(database, object_codes):
    """
    저장에 필요한 다수의 sp_object 메타데이터를 단일 IN SQL 쿼리로 배치 조회하여 네트워크 RTT를 극단적으로 단축한다.

    :param database: MariaDB 데이터베이스 커넥션 객체
    :param object_codes: 조회 대상 오브젝트 코드 리스트 (예: ['EXECUTION_HISTORY', 'MDB', 'MCM'])
    :return: {object_code: metadata_dict} 구조의 딕셔너리
    """
    if not object_codes:
        return {}

    format_strings = ', '.join(['%s'] * len(object_codes))
    rows = database.fetch_all(
        f"""SELECT object_id, object_code, object_name, business_code, domain_code,
                  object_level, identifier_target_code, sequence_scope_code,
                  sequence_length, target_identifier_field
           FROM sp_object
           WHERE object_code IN ({format_strings}) AND active_yn = 'Y'
             AND status_code = 'ACTIVE' AND deleted_dt IS NULL""",
        tuple(object_codes),
    )

    result = {row["object_code"]: row for row in rows}

    # 누락된 오브젝트 등록 상태 검증
    for code in object_codes:
        if code not in result:
            raise RuntimeError(f"Register sp_object before saving memory: {code}")

    return result


def _next_execution_id(database, actor, client_ip):
    """
    IdentifierCoordinator를 사용하여 원자적이고 동시성이 보장된 실행 이력 ID(Execution History ID)를 발급받는다.

    :param database: MariaDB 커넥션 객체
    :param actor: 식별자 생성을 요청하는 주체 (subject_id)
    :param client_ip: 접속 클라이언트 IP
    :return: 생성된 고유 식별자 문자열
    """
    # sp_object 메타데이터 조회
    objects = _registered_objects_batch(database, ["EXECUTION_HISTORY"])
    metadata = objects["EXECUTION_HISTORY"]

    coordinator = IdentifierCoordinator(database)

    # 식별자 채번 준비 요청 생성
    request, prepared = coordinator.prepare_registered_object(
        object_metadata=metadata,
        created_by=actor,
        updated_by=actor,
        client_ip=client_ip,
        program_id=MEMORY_PROGRAM_ID,
    )

    # 식별자 최대 허용 길이 캐시 조회
    max_length = _resolve_column_length(database)

    # 락 획득 및 격리된 트랜잭션 내에서 식별자 해소(Resolve)
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


def load_settings():
    """
    환경 변수 및 설정 파일(agent_memory_settings.json)로부터 에이전트 동작 옵션을 로드 및 검증한다.

    :return: 설정값 딕셔너리
    """
    path = Path(os.getenv("AGENT_MEMORY_SETTINGS", str(Path(__file__).with_name("agent_memory_settings.json"))))
    settings = json.loads(path.read_text(encoding="utf-8"))

    # 컬렉션 및 기본 환경 변수 오버라이드 처리
    settings["collection_name"] = os.getenv("AGENT_MEMORY_COLLECTION", "agent_long_term_memory")
    for name in ("database_role", "collection_name", "domain_code"):
        settings[name] = normalize_required_text(settings.get(name), name)

    settings["domain_code"] = os.getenv("AGENT_DOMAIN", settings["domain_code"])

    # 양의 정수 설정 항목 검증
    for name in ("history_turn_limit", "recall_limit", "recall_char_limit"):
        if not isinstance(settings[name], int) or settings[name] <= 0:
            raise ValueError(f"{name} must be a positive integer")

    return settings


class PersistentMemory:
    """
    LangGraph 에이전트의 장기 기억(Long-term Memory)을 안전하게 관리하는 영구 저장소 클래스.

    - Dual-Write (MariaDB + MongoDB) 트랜잭션 안전성 보장
    - 사용자/도메인 단위 데이터 격리
    - Context Manager Pattern (__enter__, __exit__) 기반 완전한 커넥션 생명주기 관리
    """

    def __init__(self, settings=None, database=None):
        """
        PersistentMemory 객체를 초기화한다.

        :param settings: 에이전트 설정 딕셔너리 (None일 경우 외부 설정 파일 로드)
        :param database: 주입받을 CommonDatabase 커넥션 객체 (None일 경우 내부에서 자체 생성)
        """
        self.settings = settings or load_settings()

        if database is not None:
            self.database = database
            self._owned_database = False  # 외부에서 주입된 DB 객체는 close() 시 해제하지 않음
        else:
            self.database = CommonDatabase(
                database_role=self.settings["database_role"],
                connect_mariadb=False,
                connect_mongodb=True,
            )
            self._owned_database = True   # 직접 생성한 DB 객체는 close() 시 해제 책임 보유

        self.collection = self.settings["collection_name"]
        self.domain = self.settings["domain_code"]

    def __enter__(self):
        """Context Manager 진입"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context Manager 종료 시 자원 해제 보장"""
        self.close()

    def scope(self, subject_id):
        """
        사용자 식별자 및 도메인 격리를 위한 기본 몽고DB 조회 스코프를 생성한다.
        """
        return {
            "subject_id": normalize_required_text(subject_id, "subject_id"),
            "domain_code": self.domain,
            "program_id": MEMORY_PROGRAM_ID,
        }

    def request_filter(self, subject_id, thread_id, request_id):
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
        # 요청 단위를 식별할 SHA256 고유 해시 키 생성
        doc_id = hashlib.sha256(json.dumps(values).encode("utf-8")).hexdigest()
        return {"_id": doc_id, **scope}

    def completed(self, subject_id, thread_id, request_id):
        """
        특정 request_id에 대한 처리가 이미 완료되었는지 몽고DB에서 조회한다 (멱등성 확인).
        """
        return self.database.find_one(
            self.collection, self.request_filter(subject_id, thread_id, request_id)
        )

    def history(self, subject_id, thread_id):
        """
        현재 대화 스레드의 최근 대화 기록(Turn)을 반환한다.
        """
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
        """
        현재 대화 스레드를 제외한 과거 대화 기록 중, 검색어와 연관된 기억을 회상(Recall)한다.
        JSON 직렬화 시 잘림(Truncation) 문제로 발생하는 하류 JSONDecodeError를 완전히 예방한다.

        :param subject_id: 사용자 ID
        :param thread_id: 현재 진행 중인 대화 스레드 ID (조회 대상에서 제외)
        :param query: 관련 기억을 검색할 쿼리 문자열
        :return: 유효한 JSON 포맷의 회상 데이터 문자열
        """
        scope = {**self.scope(subject_id), "thread_id": {"$ne": thread_id}}

        # 쿼리 내 2자 이상의 단어 추출 및 최대 12개 키워드 선정
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
        )

        # 연관 키워드 검색 결과가 없는 경우 최신 대화 항목으로 Fallback
        if not rows and terms:
            rows = self.database.find(
                self.collection,
                scope,
                limit=self.settings["recall_limit"],
                sort=[("created_dt", -1), ("_id", -1)],
            )

        # 정밀 JSON 직렬화 및 길이 측정 조립
        results = []
        limit = self.settings["recall_char_limit"]

        for row in reversed(rows):
            candidate_item = {"query": row["query"], "response": row["response"]}
            # 후보 항목을 포함한 리스트의 전체 직렬화 길이를 정밀 측정
            test_list = results + [candidate_item]
            test_json = json.dumps(test_list, ensure_ascii=False)

            # 용량 제한 초과 시 이전 단계에서 조립 중단
            if len(test_json) > limit:
                break

            results.append(candidate_item)

        # 완성된 안전한 유효 JSON 문자열 반환
        return json.dumps(results, ensure_ascii=False)

    def save(self, subject_id, thread_id, request_id, query, result, client_ip):
        """
        에이전트의 수행 결과를 MariaDB 트랜잭션 및 MongoDB 문서로 원자적 저장(Dual Write)한다.

        :param subject_id: 사용자 식별자
        :param thread_id: 대화 스레드 ID
        :param request_id: 요청 고유 ID
        :param query: 사용자 질문 내용
        :param result: 에이전트 응답 및 토큰 사용량 포함 결과 딕셔너리
        :param client_ip: 요청 클라이언트 IP
        :return: 저장 결과 딕셔너리
        """
        if self.collection != "agent_long_term_memory" or self.settings["database_role"].upper() != "STORY":
            raise RuntimeError("Agent memory requires the registered STORY/agent_long_term_memory collection")

        selector = self.request_filter(subject_id, thread_id, request_id)
        already_saved = self.completed(subject_id, thread_id, request_id)

        # 동일 request_id 재요청 시 멱등성 응답 처리
        if already_saved is not None:
            if (already_saved["query"] != query or
                    already_saved.get("source_context") != result.get("source_context")):
                raise ValueError("request_id already belongs to another query")
            return {
                "status": "success",
                "response": already_saved["response"],
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

        # MariaDB 트랜잭션 전용 커넥션 생성
        repository = CommonDatabase(database_role="STORY", connect_mongodb=False)
        try:
            # 1. 스키마 문서화 여부 사전에 일괄 검증
            assert_schema_documented(
                repository, repository.database_name,
                ("sp_object", "sp_execution_history", "sp_object_execution_link"),
            )

            # 2. 관련 sp_object 메타데이터 단일 쿼리로 일괄 조회
            objects = _registered_objects_batch(
                repository, [MEMORY_OBJECT_CODE, "MDB", "MCM"]
            )
            memory_object = objects[MEMORY_OBJECT_CODE]
            database_object = objects["MDB"]
            master_object = objects["MCM"]

            # 3. Execution History ID 생성
            history_id = _next_execution_id(repository, subject_id, document["client_ip"])

            # 4. MariaDB + MongoDB 원자적 쓰기 서비스 실행 (오류 시 보상 삭제 트랜잭션 수행)
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
                     master_object["object_id"], subject_id, document["client_ip"],
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
        finally:
            # MariaDB 커넥션 자원 확실한 해제
            repository.close()

        # 저장 후 읽기 검증 (Read-back Verification)
        stored = self.completed(subject_id, thread_id, request_id)
        if stored is None:
            raise RuntimeError("Memory read-back failed")
        if (stored["query"] != query or
                stored.get("source_context") != result.get("source_context")):
            raise ValueError("request_id already belongs to another query")

        return {
            "status": "success",
            "response": stored["response"],
            "token_usage": stored.get("token_usage", {}),
            "request_id": request_id,
            "memory_saved": True,
        }

    def close(self):
        """
        PersistentMemory가 생성한 내부 데이터베이스 접속 자원을 안전하게 종료한다.
        """
        if self._owned_database and self.database:
            self.database.close()
            self.database = None
