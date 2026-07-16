from __future__ import annotations

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
        """기존 Runtime Adapter 호환 진입점."""
        return self.execute(request)

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
