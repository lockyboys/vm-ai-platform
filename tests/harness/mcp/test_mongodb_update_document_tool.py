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
