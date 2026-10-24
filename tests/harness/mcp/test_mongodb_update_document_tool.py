"""Regression tests for the explicit single-document MongoDB update tool."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from harness.mcp.tools import mongodb_tools


class _FakeDatabase:
    database_role = "HEALTH"

    def __init__(self, **_: object) -> None:
        self.update_calls: list[tuple[object, ...]] = []

    def list_collection_names(self) -> list[str]:
        return ["sp_impact_analysis_text"]

    def find(self, **_: object) -> list[dict[str, object]]:
        return [{"_id": "document-1"}]

    def update_one(self, *args: object) -> SimpleNamespace:
        self.update_calls.append(args)
        return SimpleNamespace(matched_count=1, modified_count=1)

    def close(self) -> None:
        return None


def test_mongodb_update_document_dry_run_requires_exact_sps_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = _FakeDatabase()
    monkeypatch.setattr(mongodb_tools, "CommonDatabase", lambda **_: database)

    result = mongodb_tools.mongodb_update_document(
        role="HEALTH",
        collection_name="sp_impact_analysis_text",
        filter_json='{"_sps.contract_code":"IMPACT_ANALYSIS_DETAIL","_sps.source_identifier":"SP_RP_IMPACT_ANALYSIS_20260701_090144_00001"}',
        set_json='{"payload.sp_impact_analysis_text.affected_file_path":"sample.py","audit.client_ip":"127.0.0.1"}',
    )

    assert result["applied"] is False
    assert result["matched_count"] == 1
    assert database.update_calls == []


def test_mongodb_update_document_allows_only_payload_or_audit_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(mongodb_tools, "CommonDatabase", _FakeDatabase)

    with pytest.raises(ValueError, match="payload"):
        mongodb_tools.mongodb_update_document(
            role="HEALTH",
            collection_name="sp_impact_analysis_text",
            filter_json='{"_sps.contract_code":"IMPACT_ANALYSIS_DETAIL","_sps.source_identifier":"SP_RP_IMPACT_ANALYSIS_20260701_090144_00001"}',
            set_json='{"_sps.source_identifier":"other"}',
        )


def test_mongodb_update_document_updates_exactly_one_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = _FakeDatabase()
    monkeypatch.setattr(mongodb_tools, "CommonDatabase", lambda **_: database)

    result = mongodb_tools.mongodb_update_document(
        role="HEALTH",
        collection_name="sp_impact_analysis_text",
        filter_json='{"_sps.contract_code":"IMPACT_ANALYSIS_DETAIL","_sps.source_identifier":"SP_RP_IMPACT_ANALYSIS_20260701_090144_00001"}',
        set_json='{"audit.client_ip":"127.0.0.1"}',
        apply=True,
    )

    assert result["modified_count"] == 1
    assert len(database.update_calls) == 1


# ---------------------------------------------------------------------------
# 2026-10-24 식별자 정정 경로(KST 정정): contract_code가 없는 Verified SQL Payload 문서는
# _sps.source_table_name + _sps.source_identifier로 1건을 지정하고, 식별자 필드
# (_sps.source_identifier, _sps.execution_history_id)만 정정할 수 있다.
# ---------------------------------------------------------------------------
_TABLE_FILTER = (
    '{"_sps.source_table_name":"cm_verified_sql_query",'
    '"_sps.source_identifier":"CM_CO_OBJECT_READ_BY_CODE_20261023_194626_00013"}'
)


def test_identifier_correction_dry_run_by_source_table(monkeypatch: pytest.MonkeyPatch) -> None:
    """정상: source_table_name 필터로 식별자 정정 dry-run → 1건 일치, 실제 변경 없음."""
    database = _FakeDatabase()
    monkeypatch.setattr(mongodb_tools, "CommonDatabase", lambda **_: database)
    database.list_collection_names = lambda: ["cm_verified_sql_query_payload"]

    result = mongodb_tools.mongodb_update_document(
        role="COMMON",
        collection_name="cm_verified_sql_query_payload",
        filter_json=_TABLE_FILTER,
        set_json='{"_sps.source_identifier":"CM_CO_OBJECT_READ_BY_CODE_20261024_194626_00013"}',
    )

    assert result["applied"] is False
    assert result["matched_count"] == 1
    assert database.update_calls == []


def test_identifier_correction_apply_updates_one_document(monkeypatch: pytest.MonkeyPatch) -> None:
    """정상: 식별자 정정 apply → update_one 1회, $set에 새 식별자만 포함."""
    database = _FakeDatabase()
    monkeypatch.setattr(mongodb_tools, "CommonDatabase", lambda **_: database)
    database.list_collection_names = lambda: ["cm_verified_sql_query_payload"]

    result = mongodb_tools.mongodb_update_document(
        role="COMMON",
        collection_name="cm_verified_sql_query_payload",
        filter_json=_TABLE_FILTER,
        set_json='{"_sps.source_identifier":"CM_CO_OBJECT_READ_BY_CODE_20261024_194626_00013",'
                 '"_sps.execution_history_id":"SP_RP_EXECUTION_HISTORY_20261024_194626_00013"}',
        apply=True,
    )

    assert result["modified_count"] == 1
    assert database.update_calls[0][2] == {"$set": {
        "_sps.source_identifier": "CM_CO_OBJECT_READ_BY_CODE_20261024_194626_00013",
        "_sps.execution_history_id": "SP_RP_EXECUTION_HISTORY_20261024_194626_00013",
    }}


@pytest.mark.parametrize("set_json", [
    '{"_sps.source_identifier":""}',            # 빈 식별자
    '{"_sps.source_identifier":"  "}',          # 공백 식별자
    '{"_sps.source_identifier":123}',           # 문자열이 아닌 값
    '{"_sps.source_table_name":"other_table"}',  # 허용되지 않은 _sps 필드
])
def test_identifier_correction_rejects_invalid_values(monkeypatch: pytest.MonkeyPatch, set_json: str) -> None:
    """잘못된 입력: 빈/공백/비문자 식별자나 허용 외 _sps 필드는 ValueError."""
    monkeypatch.setattr(mongodb_tools, "CommonDatabase", _FakeDatabase)

    with pytest.raises(ValueError):
        mongodb_tools.mongodb_update_document(
            role="COMMON",
            collection_name="cm_verified_sql_query_payload",
            filter_json=_TABLE_FILTER,
            set_json=set_json,
        )
