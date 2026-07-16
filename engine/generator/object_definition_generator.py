"""
SPS Object Definition Generator

Responsibility:
    확정된 Object Definition Row를 sp_object에 저장한다.

Rules:
    - Request 정규화를 수행하지 않는다.
    - Repository 검증을 수행하지 않는다.
    - Identifier를 발급하지 않는다.
    - Transaction을 제어하지 않는다.
    - Lock을 제어하지 않는다.
    - Object 생성 판단을 수행하지 않는다.
"""

from __future__ import annotations

from typing import Any

from common.database import CommonDatabase


class ObjectDefinitionGenerator:
    """확정된 Object Definition을 Repository에 저장한다."""

    def __init__(
        self,
        database: CommonDatabase,
    ) -> None:
        if database is None:
            raise ValueError(
                "ObjectDefinitionGenerator requires a database "
                "owned by ObjectDefinitionEngine."
            )

        self.database = database

    def generate(
        self,
        *,
        object_id: str,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        """
        ObjectDefinitionEngine이 검증하고 확정한 데이터를 저장한다.

        Transaction의 시작, Commit, Rollback은 Engine이 소유한다.
        """
        affected = self.database.execute(
            """
            INSERT INTO sp_object
            (
                object_id,
                object_code,
                object_name,
                business_code,
                domain_code,
                object_type_code,
                object_description,
                parent_object_id,
                object_level,
                sort_no,
                status_code,
                active_yn,
                version_no,
                lifecycle_id,
                created_by,
                created_dt,
                updated_by,
                updated_dt,
                deleted_by,
                deleted_dt,
                client_ip,
                program_id,
                target_identifier_field,
                sequence_scope_code,
                sequence_length,
                identifier_target_code
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                CURRENT_TIMESTAMP,
                %s,
                CURRENT_TIMESTAMP,
                NULL,
                NULL,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                object_id,
                request["object_code"],
                request["object_name"],
                request["business_code"],
                request["domain_code"],
                request["object_type_code"],
                request.get("object_description"),
                request.get("parent_object_id"),
                request["object_level"],
                request.get("sort_no", 0),
                request["status_code"],
                request["active_yn"],
                request["version_no"],
                request.get("lifecycle_id"),
                request["created_by"],
                request["updated_by"],
                request["client_ip"],
                request["program_id"],
                request.get("target_identifier_field"),
                request["sequence_scope_code"],
                request["sequence_length"],
                request["identifier_target_code"],
            ),
        )

        if affected != 1:
            raise RuntimeError(
                "sp_object generation failed. "
                f"object_id={object_id}, "
                f"affected_rows={affected}"
            )

        return {
            "success": True,
            "status": "GENERATED",
            "generator": self.__class__.__name__,
            "object_id": object_id,
            "object_code": request["object_code"],
            "affected_rows": affected,
        }
