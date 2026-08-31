# =============================================================================
# File Name   : tests/harness/mcp/test_identifier_tools.py
# Purpose     : SPS Harness Identifier Generation Tool tests
# =============================================================================
# CHANGE HISTORY
# =============================================================================
# 20260830 | OpenAI | Repository Object metadata 기반 Identifier 발급 테스트를 추가했음
# =============================================================================

from __future__ import annotations

from types import SimpleNamespace

import pytest

from harness.mcp.tools import identifier_tools


class _FakeDatabase:
    instances: list["_FakeDatabase"] = []

    def __init__(self, database_role: str) -> None:
        assert database_role == "STORY"
        self.began = False
        self.committed = False
        self.rolled_back = False
        self.closed = False
        self.__class__.instances.append(self)

    def begin(self) -> None:
        self.began = True

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


class _FakeIdentifierCoordinator:
    def __init__(self, database: _FakeDatabase) -> None:
        self.database = database
        self.acquired = False
        self.released = False

    def resolve_identifier_maximum_length(self, *, object_metadata: dict[str, str]) -> int:
        assert object_metadata["object_code"] == "EXECUTION_HISTORY"
        return 64

    def prepare_registered_object(self, **_: object) -> tuple[dict[str, str], dict[str, str]]:
        return (
            {"object_code": "EXECUTION_HISTORY"},
            {"sequence_scope_code": "DAILY", "sequence_date": "20260830"},
        )

    def acquire(self, _: dict[str, str]) -> None:
        self.acquired = True

    def resolve(self, **_: object) -> SimpleNamespace:
        return SimpleNamespace(
            blueprint_code="BP_OBJECT",
            sequence_no=7,
            sequence_length=5,
            rule_id="SP_RP_RL_RULE_20260731_00001",
            rule_code="RL_OBJECT_LEVEL_CLASSIFICATION",
        )

    def render_resolution(self, **_: object) -> str:
        return "SP_EG_EXECUTION_HISTORY_20260830_00007"

    def release(self, _: dict[str, str]) -> None:
        self.released = True


@pytest.fixture
def object_metadata() -> dict[str, str]:
    return {
        "object_code": "EXECUTION_HISTORY",
        "object_name": "te_story_platform.sp_execution_history",
        "target_identifier_field": "execution_history_id",
        "identifier_target_code": "EG",
    }


def test_identifier_generate_dry_run_uses_registered_metadata_without_allocation(
    monkeypatch: pytest.MonkeyPatch,
    object_metadata: dict[str, str],
) -> None:
    monkeypatch.setattr(identifier_tools, "CommonDatabase", _FakeDatabase)
    monkeypatch.setattr(identifier_tools, "IdentifierCoordinator", _FakeIdentifierCoordinator)
    monkeypatch.setattr(
        identifier_tools,
        "_load_registered_object_metadata",
        lambda *_: object_metadata,
    )
    _FakeDatabase.instances.clear()

    result = identifier_tools.identifier_generate(
        object_code="execution_history",
        apply=False,
    )

    assert result["dry_run"] is True
    assert result["object_code"] == "EXECUTION_HISTORY"
    assert result["target_identifier_field"] == "execution_history_id"
    assert result["maximum_length"] == 64
    database = _FakeDatabase.instances[0]
    assert database.began is False
    assert database.closed is True


def test_identifier_generate_apply_allocates_and_commits(
    monkeypatch: pytest.MonkeyPatch,
    object_metadata: dict[str, str],
) -> None:
    monkeypatch.setattr(identifier_tools, "CommonDatabase", _FakeDatabase)
    monkeypatch.setattr(identifier_tools, "IdentifierCoordinator", _FakeIdentifierCoordinator)
    monkeypatch.setattr(
        identifier_tools,
        "_load_registered_object_metadata",
        lambda *_: object_metadata,
    )
    _FakeDatabase.instances.clear()

    result = identifier_tools.identifier_generate(
        object_code="EXECUTION_HISTORY",
        actor_id="SPS_ADMIN",
        apply=True,
    )

    assert result["dry_run"] is False
    assert result["identifier"] == "SP_EG_EXECUTION_HISTORY_20260830_00007"
    assert result["sequence_no"] == 7
    database = _FakeDatabase.instances[0]
    assert database.began is True
    assert database.committed is True
    assert database.rolled_back is False
    assert database.closed is True
