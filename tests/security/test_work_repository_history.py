"""Regression tests for Repository-owned work history."""

from __future__ import annotations

from typing import Any

from work.work_repository import WorkRepository


class FakeStoryDatabase:
    """Work Repository 조회 계약만 검증하는 in-memory database double."""

    def __init__(self) -> None:
        self.queries: list[tuple[str, tuple[Any, ...]]] = []
        self.closed = False

    def fetch_one(self, sql: str, parameters: tuple[Any, ...]) -> dict[str, Any] | None:
        self.queries.append((sql, parameters))
        if parameters == ("session-1", "member-1"):
            return {"work_session_id": "session-1", "work_name": "owned work"}
        return None

    def fetch_all(self, sql: str, parameters: tuple[Any, ...]) -> list[dict[str, Any]]:
        self.queries.append((sql, parameters))
        if "FROM sp_work_session" in sql:
            return [{"work_session_id": "session-1", "work_name": "owned work"}]
        if "JOIN sp_work_asset" in sql:
            return [{"work_asset_id": "asset-1", "asset_name": "owned report"}]
        if "FROM sp_work_item" in sql:
            return [{"work_item_id": "item-1", "work_session_id": "session-1"}]
        return []

    def close(self) -> None:
        self.closed = True


def test_work_history_reads_only_owned_non_sensitive_repository_fields() -> None:
    database = FakeStoryDatabase()
    repository = WorkRepository(lambda **_kwargs: database)

    assert repository.list_owned_sessions("member-1") == [
        {"work_session_id": "session-1", "work_name": "owned work"}
    ]
    detail = repository.get_owned_session_detail("session-1", "member-1")

    assert detail is not None
    assert detail["work_items"] == [{"work_item_id": "item-1", "work_session_id": "session-1"}]
    assert detail["work_assets"] == [{"work_asset_id": "asset-1", "asset_name": "owned report"}]
    assert database.closed is True

    query_text = "\n".join(sql for sql, _parameters in database.queries)
    assert "created_by = %s" in query_text
    assert "deleted_dt IS NULL" in query_text
    assert "request_json" not in query_text
    assert "response_json" not in query_text
    assert "asset_path" not in query_text
