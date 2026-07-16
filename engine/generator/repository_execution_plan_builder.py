"""
Repository Execution Plan Builder

Repository Object와 선택적 Execution Link를 조회하여
실행 계획 조립에 필요한 Context를 생성한다.

Principles:
    - Repository First
    - Object First
    - Metadata Driven
    - No Hardcoding

Current Scope:
    - sp_object 조회
    - sp_object_execution_link 조회
    - Execution Link 0건 정상 처리
    - RepositoryExecutionPlan 조립 지원

Future Scope:
    - Entity 및 Attribute Repository 연결
    - Relationship 정책 연결
    - Metadata Validation 연결
"""

from __future__ import annotations

from typing import Any, Mapping

from common.database import CommonDatabase
from engine.model.repository_execution_plan import (
    RepositoryExecutionPlan,
)


class RepositoryExecutionPlanBuilder:
    """Repository 조회 결과로 실행 계획을 조립한다."""

    def __init__(
        self,
        database: CommonDatabase | None = None,
    ) -> None:
        self.database = database or CommonDatabase(
            database_role="STORY_PLATFORM"
        )

    def load_context(
        self,
        *,
        object_code: str,
    ) -> dict[str, Any]:
        """
        Object와 선택적 Execution Link Context를 조회한다.

        Execution Link가 없어도 정상 Context를 반환한다.
        """
        normalized_object_code = self._normalize_code(
            object_code,
            "object_code",
        )

        object_metadata = self._load_object(
            normalized_object_code
        )

        execution_links = self._load_execution_links(
            object_metadata["object_id"]
        )

        return {
            "object": object_metadata,
            "execution_links": execution_links,
            "execution_link_count": len(execution_links),
        }

    def build(
        self,
        *,
        object_code: str,
        operation_code: str,
        repository_metadata: Mapping[str, Any],
    ) -> RepositoryExecutionPlan:
        """
        Repository Context와 저장 구조 Metadata를 결합하여
        RepositoryExecutionPlan을 생성한다.

        repository_metadata는 다음 Repository 연결 전까지
        호출자가 전달한다.

        Required:
            database_role
            table_name
            primary_key
            columns
        """
        context = self.load_context(
            object_code=object_code,
        )

        relationships = [
            {
                "object_attempt_id": row[
                    "object_attempt_id"
                ],
                "object_id": row["object_id"],
                "target_object_id": row.get(
                    "target_object_id"
                ),
                "execution_link_type_code": row[
                    "execution_link_type_code"
                ],
                "mongodb_database_id": row.get(
                    "mongodb_database_id"
                ),
                "mongodb_collection_id": row.get(
                    "mongodb_collection_id"
                ),
                "mongodb_document_master_id": row.get(
                    "mongodb_document_master_id"
                ),
            }
            for row in context["execution_links"]
        ]

        return RepositoryExecutionPlan.from_repository(
            object_metadata=context["object"],
            operation_code=operation_code,
            repository_metadata=repository_metadata,
            relationships=relationships,
        )

    def _load_object(
        self,
        object_code: str,
    ) -> dict[str, Any]:
        row = self.database.fetch_one(
            """
            SELECT
                object_id,
                object_code,
                object_name,
                business_code,
                domain_code,
                object_type_code,
                object_description,
                parent_object_id,
                object_level,
                status_code,
                active_yn,
                version_no,
                lifecycle_id,
                target_identifier_field,
                sequence_scope_code,
                sequence_length,
                identifier_target_code
            FROM sp_object
            WHERE object_code = %s
              AND status_code = 'ACTIVE'
              AND active_yn = 'Y'
              AND deleted_dt IS NULL
            LIMIT 1
            """,
            (object_code,),
        )

        if not row:
            raise LookupError(
                "Active Repository Object not found. "
                f"object_code={object_code}"
            )

        return dict(row)

    def _load_execution_links(
        self,
        object_id: str,
    ) -> list[dict[str, Any]]:
        rows = self.database.fetch_all(
            """
            SELECT
                object_attempt_id,
                object_id,
                target_object_id,
                execution_link_type_code,
                mongodb_database_id,
                mongodb_collection_id,
                mongodb_document_master_id,
                created_by,
                created_dt,
                updated_by,
                updated_dt,
                client_ip,
                program_id
            FROM sp_object_execution_link
            WHERE object_id = %s
              AND deleted_dt IS NULL
            ORDER BY created_dt, object_attempt_id
            """,
            (object_id,),
        )

        return [
            dict(row)
            for row in (rows or [])
        ]

    @staticmethod
    def _normalize_code(
        value: str,
        field_name: str,
    ) -> str:
        normalized = str(value or "").strip().upper()

        if not normalized:
            raise ValueError(
                f"{field_name} must not be empty."
            )

        return normalized
