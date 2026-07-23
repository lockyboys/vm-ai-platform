"""
SPS Object Level Resolver

Purpose:
    sp_object.parent_object_id 계층을 해석하여 Object Level을 계산한다.

Principles:
    - parent_object_id가 Object 계층의 Single Source of Truth이다.
    - Engine, Generator, Runtime은 Object Level을 직접 계산하지 않는다.
    - 모든 Object Level 판단은 이 Resolver를 통해 수행한다.
    - 순환 참조, 누락된 부모, 최대 Level 초과를 Soft Lock으로 차단한다.
"""

from __future__ import annotations

from typing import Any


class ObjectLevelResolver:
    """Repository의 parent_object_id 계층을 기준으로 Object Level을 계산한다."""

    def __init__(self, database_manager, max_level: int = 5):
        self.database_manager = database_manager
        self.max_level = max_level
        self._parent_cache: dict[str, str | None] = {}
        self._level_cache: dict[str, int] = {}

    def resolve_object_level(self, object_id: str) -> int:
        """Object ID의 부모 계층을 따라 Object Level을 계산한다."""
        if not object_id:
            raise ValueError("object_id is required.")

        if object_id in self._level_cache:
            return self._level_cache[object_id]

        visited: set[str] = set()
        current_object_id = object_id
        level = 0

        while current_object_id:
            if current_object_id in visited:
                raise ValueError(
                    "Circular Object hierarchy detected. "
                    f"object_id={object_id}, circular_object_id={current_object_id}"
                )

            visited.add(current_object_id)
            level += 1

            if level > self.max_level:
                raise ValueError(
                    "Object hierarchy exceeds maximum level. "
                    f"object_id={object_id}, max_level={self.max_level}"
                )

            current_object_id = self._load_parent_object_id(current_object_id)

        self._level_cache[object_id] = level
        return level

    def resolve_child_level(self, parent_object_id: str | None) -> int:
        """신규 Object의 parent_object_id를 기준으로 자식 Level을 계산한다."""
        if parent_object_id in (None, ""):
            return 1

        parent_level = self.resolve_object_level(parent_object_id)
        child_level = parent_level + 1

        if child_level > self.max_level:
            raise ValueError(
                "Child Object level exceeds maximum level. "
                f"parent_object_id={parent_object_id}, max_level={self.max_level}"
            )

        return child_level

    def _load_parent_object_id(self, object_id: str) -> str | None:
        """활성 Object의 parent_object_id를 Repository에서 조회한다."""
        if object_id in self._parent_cache:
            return self._parent_cache[object_id]

        sql = """
            SELECT
                object_id,
                parent_object_id
            FROM sp_object
            WHERE object_id = %s
              AND active_yn = 'Y'
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
            LIMIT 1
        """

        row: dict[str, Any] | None = self.database_manager.fetch_one(
            sql,
            (object_id,),
        )

        if not row:
            raise ValueError(
                "Object hierarchy metadata not found. "
                f"object_id={object_id}"
            )

        parent_object_id = row.get("parent_object_id") or None
        self._parent_cache[object_id] = parent_object_id
        return parent_object_id
