"""Work Repository business rules for session ownership and stored assets."""

from __future__ import annotations

from typing import Any, Callable

from common.database import CommonDatabase


class WorkRepository:
    """sp_work_session, sp_work_item, sp_work_asset의 Work 권한 규칙을 제공한다."""

    def __init__(self, database_factory: Callable[..., CommonDatabase] = CommonDatabase) -> None:
        self._database_factory = database_factory

    def verify_owner(self, work_session_id: str, user_id: str) -> bool:
        """완료·성공 Work Session이 현재 사용자 소유인지 확인한다."""
        database = self._database_factory(database_role="STORY")
        try:
            work_session = database.fetch_one(
                """
                SELECT work_session_id
                FROM sp_work_session
                WHERE work_session_id = %s
                  AND created_by = %s
                  AND work_status_code = 'COMPLETED'
                  AND work_result_code = 'SUCCESS'
                  AND deleted_dt IS NULL
                """,
                (work_session_id, user_id),
            )
        finally:
            database.close()
        return work_session is not None

    def get_owned_asset(
        self,
        *,
        work_session_id: str,
        user_id: str,
        asset_type_code: str,
    ) -> dict[str, Any] | None:
        """소유권이 검증된 Work Session에서 저장 완료된 Asset을 조회한다."""
        if not self.verify_owner(work_session_id, user_id):
            return None
        database = self._database_factory(database_role="STORY")
        try:
            return database.fetch_one(
                """
                SELECT asset.work_asset_id, asset.asset_name, asset.asset_path, asset.asset_type_code
                FROM sp_work_item work_item
                JOIN sp_work_asset asset
                  ON asset.work_item_id = work_item.work_item_id
                WHERE work_item.work_session_id = %s
                  AND asset.asset_type_code = %s
                  AND asset.asset_status_code = 'STORED'
                  AND asset.deleted_dt IS NULL
                """,
                (work_session_id, asset_type_code),
            )
        finally:
            database.close()

    def get_stored_asset(self, work_asset_id: str, asset_type_code: str) -> dict[str, Any] | None:
        """시스템이 지정한 저장 완료 Asset을 조회한다."""
        database = self._database_factory(database_role="STORY")
        try:
            return database.fetch_one(
                """
                SELECT work_asset_id, asset_name, asset_path, asset_type_code
                FROM sp_work_asset
                WHERE work_asset_id = %s
                  AND asset_type_code = %s
                  AND asset_status_code = 'STORED'
                  AND deleted_dt IS NULL
                """,
                (work_asset_id, asset_type_code),
            )
        finally:
            database.close()
