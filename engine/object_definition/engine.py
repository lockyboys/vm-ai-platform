"""Object Definition의 단일 실행 원본.

Change History
20260912 | Codex | #24: 구형 create·Sequence 준비 계약을 공통 Engine에서 호환한다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from common.database import CommonDatabase
from engine.core import (
    BaseEngine,
    ExecutionContext,
    ExecutionPlan,
)
from engine.generator.object_definition_generator import (
    ObjectDefinitionGenerator,
)
from engine.identifier import IdentifierCoordinator
from engine.object_definition.request_processor import (
    ObjectDefinitionRequestProcessor,
)
from engine.object_definition.repository_resolver import (
    ObjectDefinitionRepositoryResolver,
)


class ObjectDefinitionEngine(BaseEngine):
    """Object Definition 생성 생명주기 조정 Engine."""

    def __init__(
        self,
        database: CommonDatabase | None = None,
    ) -> None:
        self.database = database or CommonDatabase(
            database_role="STORY_PLATFORM"
        )

        self.request_processor = (
            ObjectDefinitionRequestProcessor()
        )

        self.repository_resolver = (
            ObjectDefinitionRepositoryResolver(self.database)
        )

        self.identifier_coordinator = (
            IdentifierCoordinator(self.database)
        )

        self.generator = ObjectDefinitionGenerator(
            self.database
        )

    def create(
        self,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        """구형 호출의 CREATED/ALREADY_EXISTS 응답을 유지하는 공통 진입점.

        신규 Object는 BaseEngine의 검증·저장·트랜잭션 경로로 실행한다.
        이미 등록된 Object는 재생성하거나 번호를 증가시키지 않고, 구형
        등록 도구가 필요로 하는 Sequence 기준 행만 공통 Allocator로 보장한다.
        """
        normalized = self.normalize_request(request)
        self.request_processor.validate(normalized)
        self.repository_resolver.validate_references(normalized)
        existing = self.repository_resolver.find_existing(normalized["object_code"])

        if existing is None:
            result = self.execute(normalized)
            return {
                **result,
                "status": "CREATED",
                "message": "Object Definition created successfully.",
                "identifier_target_code": normalized["identifier_target_code"],
                "object": self.repository_resolver.find_existing(normalized["object_code"]),
            }

        prepared = self.identifier_coordinator.prepare(request=normalized)
        normalized["object_level"] = prepared["object_level"]
        self.identifier_coordinator.acquire(prepared)
        try:
            with self.transaction():
                self._ensure_sequence_metadata(
                    normalized,
                    prepared["blueprint"],
                    prepared["sequence_date"],
                    prepared["sequence_length"],
                    prepared["now"],
                )
        finally:
            self.identifier_coordinator.release(prepared)

        rule = prepared["rule_resolution"]
        return {
            "success": False,
            "status": "ALREADY_EXISTS",
            "message": f"Object already exists. object_code={normalized['object_code']}",
            "affected_rows": 0,
            "object": existing,
            "rule_id": rule.rule_id,
            "rule_code": rule.rule_code,
            "rule_action_id": rule.rule_action_id,
            "rule_action_type_code": rule.action_type_code,
            "resolution_source": rule.resolution_source,
        }

    def _ensure_sequence_metadata(
        self,
        normalized: dict[str, Any],
        blueprint: dict[str, Any],
        sequence_date: str,
        sequence_length: int,
        now: datetime,
    ) -> dict[str, Any]:
        """구형 도구의 호출 형식만 유지하고 실제 준비는 공통 Allocator에 위임한다.

        이 호환 메서드는 채번이나 트랜잭션 시작·종료를 하지 않는다.
        기존 호출자가 소유한 트랜잭션과 감사값을 그대로 사용한다.
        """
        return self.identifier_coordinator.sequence_allocator.ensure_sequence(
            request=normalized,
            blueprint=blueprint,
            sequence_date=sequence_date,
            sequence_length=sequence_length,
            now=now,
        )

    def normalize_request(
        self,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        return self.request_processor.normalize(request)

    def validate_request(
        self,
        request: dict[str, Any],
    ) -> None:
        self.request_processor.validate(request)

        self.repository_resolver.validate_references(
            request
        )

        existing = self.repository_resolver.find_existing(
            request["object_code"]
        )

        if existing:
            raise ValueError(
                "Object already exists. "
                f"object_code={request['object_code']}"
            )

    def build_execution_plan(
        self,
        request: dict[str, Any],
    ) -> ExecutionPlan:
        return ExecutionPlan(
            name="OBJECT_DEFINITION_CREATE",
            steps=[
                "NORMALIZE_REQUEST",
                "VALIDATE_REQUEST",
                "PREPARE_IDENTIFIER",
                "ACQUIRE_IDENTIFIER_LOCK",
                "BEGIN_TRANSACTION",
                "ALLOCATE_SEQUENCE",
                "GENERATE_IDENTIFIER",
                "GENERATE_OBJECT",
                "VERIFY_RESULT",
                "COMMIT_TRANSACTION",
                "RELEASE_IDENTIFIER_LOCK",
            ],
        )

    def pre_execute(
        self,
        context: ExecutionContext,
    ) -> None:
        prepared = self.identifier_coordinator.prepare(
            request=context.request
        )

        # sp_object에도 Rule Resolver가 확정한 Level만 저장한다.
        # 호출자가 보낸 object_level은 Rule이 EXPLICIT_RULE로 허용한
        # 입력일 때만 여기까지 반영될 수 있다.
        context.request["object_level"] = prepared["object_level"]

        self.identifier_coordinator.acquire(prepared)

        context.shared["identifier_prepared"] = prepared
        context.shared["identifier_lock_acquired"] = True

    def resolve_repository(
        self,
        context: ExecutionContext,
    ) -> dict[str, Any]:
        return {
            "database_role": "STORY_PLATFORM",
            "table_name": "sp_object",
        }

    def resolve_identifier(
        self,
        context: ExecutionContext,
    ) -> str:
        prepared = context.shared[
            "identifier_prepared"
        ]

        resolution = self.identifier_coordinator.resolve(
            request=context.request,
            prepared=prepared,
            maximum_length=99,
        )

        context.shared["identifier_resolution"] = resolution

        return resolution.identifier

    def execute_generator(
        self,
        *,
        context: ExecutionContext,
    ) -> dict[str, Any]:
        return self.generator.generate(
            object_id=context.identifier,
            request=context.request,
        )

    def verify_result(
        self,
        result: dict[str, Any],
        context: ExecutionContext,
    ) -> None:
        if result.get("affected_rows") != 1:
            raise RuntimeError(
                "Object Definition generation verification failed."
            )

    def post_execute(
        self,
        context: ExecutionContext,
    ) -> None:
        resolution = context.shared.get(
            "identifier_resolution"
        )

        if resolution is None:
            return

        context.result.update(
            {
                "sequence_date": resolution.sequence_date,
                "sequence_no": resolution.sequence_no,
                "sequence_length": resolution.sequence_length,
                "blueprint_code": resolution.blueprint_code,
                "rule_id": resolution.rule_id,
                "rule_code": resolution.rule_code,
                "rule_action_id": resolution.rule_action_id,
                "rule_action_type_code": resolution.rule_action_type_code,
                "object_level": resolution.object_level,
                "resolution_source": resolution.resolution_source,
            }
        )

    def cleanup(
        self,
        context: ExecutionContext,
    ) -> None:
        if not context.shared.get(
            "identifier_lock_acquired"
        ):
            return

        prepared = context.shared.get(
            "identifier_prepared"
        )

        if prepared is None:
            return

        self.identifier_coordinator.release(prepared)

        context.shared["identifier_lock_acquired"] = False

    def begin_transaction(self) -> None:
        self.database.begin()

    def commit_transaction(self) -> None:
        self.database.commit()

    def rollback_transaction(self) -> None:
        self.database.rollback()
