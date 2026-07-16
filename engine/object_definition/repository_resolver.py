from __future__ import annotations

from typing import Any

from common.database import CommonDatabase


class ObjectDefinitionRepositoryResolver:
    """Object Definition 생성에 필요한 Repository 검증과 조회."""

    def __init__(self, database: CommonDatabase) -> None:
        self.database = database

    def find_existing(
        self,
        object_code: str,
    ) -> dict[str, Any] | None:
        row = self.database.fetch_one(
            """
            SELECT
                object_id,
                object_code,
                object_name,
                business_code,
                domain_code,
                object_type_code,
                object_level,
                identifier_target_code,
                sequence_scope_code,
                sequence_length,
                status_code,
                active_yn,
                created_dt
            FROM sp_object
            WHERE object_code = %s
              AND deleted_dt IS NULL
            LIMIT 1
            """,
            (object_code,),
        )

        return dict(row) if row else None

    def validate_references(
        self,
        request: dict[str, Any],
    ) -> None:
        self._require_row(
            """
            SELECT business_code
            FROM sp_business
            WHERE business_code = %s
              AND active_yn = 'Y'
              AND deleted_dt IS NULL
            LIMIT 1
            """,
            (request["business_code"],),
            (
                "Business Repository record not found. "
                f"business_code={request['business_code']}"
            ),
        )

        self._require_row(
            """
            SELECT domain_code
            FROM sp_domain
            WHERE domain_code = %s
              AND business_code = %s
              AND active_yn = 'Y'
              AND deleted_dt IS NULL
            LIMIT 1
            """,
            (
                request["domain_code"],
                request["business_code"],
            ),
            (
                "Domain Repository record not found or business mismatch. "
                f"business_code={request['business_code']}, "
                f"domain_code={request['domain_code']}"
            ),
        )

        self._require_row(
            """
            SELECT code
            FROM te_common.cm_common_code
            WHERE group_code IN ('OBJECT_TYPE', 'CM_OBJECT_TYPE')
              AND code = %s
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
            LIMIT 1
            """,
            (request["object_type_code"],),
            (
                "Object Type Repository record not found. "
                f"object_type_code={request['object_type_code']}"
            ),
        )

        self._require_row(
            """
            SELECT code
            FROM te_common.cm_common_code
            WHERE group_code = 'SPS_IDENTIFIER_TARGET'
              AND code = %s
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
            LIMIT 1
            """,
            (request["identifier_target_code"],),
            (
                "Identifier Target Repository record not found. "
                f"identifier_target_code="
                f"{request['identifier_target_code']}"
            ),
        )

    def _require_row(
        self,
        sql: str,
        params: tuple[Any, ...],
        error_message: str,
    ) -> dict[str, Any]:
        row = self.database.fetch_one(sql, params)

        if not row:
            raise ValueError(error_message)

        return dict(row)
